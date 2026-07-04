"""
OLX Data Monitor Bot — @olx_data_bot

Commands:
  /status   — show all scrapers + service health (any time)

Auto-post: every 3 hours to the chat where /start was used.
"""

import os
import logging
import asyncio
from datetime import datetime, timezone, timedelta

import requests
import yaml
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes,
)
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# ─────────────────────────────────────────────────────────────
# Electronics drill-down menu config
# ─────────────────────────────────────────────────────────────
with open(os.path.join(os.path.dirname(__file__), 'electronics_menu.yaml'), encoding='utf-8') as _f:
    _MENU = yaml.safe_load(_f)

# id → {label, emoji, report_label}
ELEC_CATEGORIES = {c['id']: c for c in _MENU.get('categories', [])}
# list of {id, label}; id is the number of days as a string ("0" = all time)
ELEC_PERIODS = _MENU.get('periods', [])
ELEC_PERIOD_LABEL = {p['id']: p['label'] for p in ELEC_PERIODS}

BOT_TOKEN  = os.getenv('OPS_BOT_TOKEN', '')
DJANGO_URL = os.getenv('DJANGO_URL', 'http://django:8000').rstrip('/')
ML_API_URL = os.getenv('ML_API_URL', 'http://ml_api:8500')
VISION_URL = os.getenv('CAR_VISION_URL', 'http://car-vision-api:8600')

AUTO_POST_INTERVAL = int(os.getenv('AUTO_POST_INTERVAL_SECONDS', str(3 * 3600)))  # 3 h

# Allowed Telegram user IDs — everyone else is rejected.
# Set in .env:  ADMIN_USER_IDS=123456789,987654321
_raw = os.getenv('ADMIN_USER_IDS', '')
ALLOWED_IDS: set[int] = {int(x.strip()) for x in _raw.split(',') if x.strip().isdigit()}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Data helpers
# ─────────────────────────────────────────────────────────────

def _get_scraper_runs() -> list[dict]:
    try:
        r = requests.get(f"{DJANGO_URL}/api/scraper-runs/", timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning("scraper-runs fetch failed: %s", e)
        return []


def _ping(url: str, path: str = '/') -> bool:
    try:
        r = requests.get(f"{url.rstrip('/')}{path}", timeout=4)
        return r.status_code < 500
    except Exception:
        return False


def _service_health() -> dict:
    django_ok = _ping(DJANGO_URL, '/api/cars/brand-models/')
    return {
        'Django API':   django_ok,
        'PostgreSQL':   django_ok,   # if Django answers, Postgres is up
        'ML API':       _ping(ML_API_URL, '/docs'),
        'Vision API':   _ping(VISION_URL, '/'),
        'Airflow':      _ping('http://airflow-webserver:8080', '/health'),
    }


def _scraper_health(runs: list[dict]) -> list[tuple[str, str]]:
    """
    Returns a list of (label, status_line) for each scraper type.
    Health is derived from the scraper_runs table, not Docker — so it works
    from inside the container without needing the Docker socket.
    """
    STALE_HOURS = 26   # car scraper runs every ~24h; alert if older than this
    STALE_HOURS_ONDEMAND = 168  # apartments/electronics run on-demand; warn after 7 days

    by_scraper: dict[str, list] = {}
    for r in runs:
        by_scraper.setdefault(r['scraper_name'], []).append(r)

    rows = []
    for scraper, em, stale_h in [
        ('cars',        '🚗', STALE_HOURS),
        ('apartments',  '🏘', STALE_HOURS_ONDEMAND),
        ('electronics', '💻', STALE_HOURS_ONDEMAND),
    ]:
        cats = by_scraper.get(scraper, [])
        if not cats:
            rows.append((f"{em} {scraper.capitalize()}", "⚪ never ran"))
            continue

        # Aggregate across categories
        any_running   = any(r['status'] == 'running' for r in cats)
        any_error     = any(r['status'] == 'error'   for r in cats)
        latest_start  = max((r['started_at']  for r in cats if r['started_at']),  default=None)
        latest_finish = max((r['finished_at'] for r in cats if r['finished_at']), default=None)
        total_new     = sum(r['new_records'] for r in cats)

        # Staleness check
        stale = False
        if latest_start:
            try:
                dt = datetime.fromisoformat(str(latest_start).replace('Z', '+00:00'))
                hours_old = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
                stale = hours_old > stale_h
            except Exception:
                pass

        if any_running:
            icon = "⚙️ "
            detail = f"running · started {_ago(latest_start)}"
        elif any_error:
            icon = "❌"
            detail = f"error · {_ago(latest_start)}"
        elif stale:
            icon = "⚠️ "
            detail = f"stale · last {_ago(latest_start)}"
        else:
            icon = "✅"
            dur = _duration(latest_start, latest_finish) if latest_finish else "—"
            detail = f"ok · {_ago(latest_start)} · {total_new:,} new · {dur}"

        rows.append((f"{em} {scraper.capitalize()}", f"{icon} {detail}"))
    return rows


def _ago(dt_str) -> str:
    """Return human '3h 12m ago' string from an ISO timestamp string."""
    if not dt_str:
        return 'never'
    try:
        if isinstance(dt_str, str):
            dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        else:
            dt = dt_str
        delta = datetime.now(timezone.utc) - dt.astimezone(timezone.utc)
        total = int(delta.total_seconds())
        if total < 60:
            return f"{total}s ago"
        if total < 3600:
            return f"{total // 60}m ago"
        h = total // 3600
        m = (total % 3600) // 60
        return f"{h}h {m}m ago" if m else f"{h}h ago"
    except Exception:
        return str(dt_str)[:16]


def _duration(started, finished) -> str:
    if not started or not finished:
        return '—'
    try:
        s = datetime.fromisoformat(str(started).replace('Z', '+00:00'))
        f = datetime.fromisoformat(str(finished).replace('Z', '+00:00'))
        sec = int((f - s).total_seconds())
        if sec < 60:
            return f"{sec}s"
        return f"{sec // 60}m {sec % 60}s"
    except Exception:
        return '—'


EMOJI = {
    'cars':        '🚗',
    'apartments':  '🏘',
    'electronics': '💻',
    'gpu':         '🎮',
    'iphone':      '📱',
    'macbook':     '💻',
    'mac':         '🖥',
    'ipad':        '📟',
}

STATUS_ICON = {
    'completed': '✅',
    'running':   '⚙️ ',
    'error':     '❌',
}


# ─────────────────────────────────────────────────────────────
# Message builder
# ─────────────────────────────────────────────────────────────

def build_status_message() -> str:
    runs   = _get_scraper_runs()
    health = _service_health()

    tz5 = timezone(timedelta(hours=5))
    now_str = datetime.now(tz5).strftime('%a %d %b · %H:%M UTC+5')

    lines = [
        "📡 *OLX DATA MONITOR*",
        f"_{now_str}_",
        "",
    ]

    # Group by scraper_name then category
    grouped: dict[str, list] = {}
    for r in runs:
        grouped.setdefault(r['scraper_name'], []).append(r)

    for scraper in ('cars', 'apartments', 'electronics'):
        cats = grouped.get(scraper, [])
        if not cats:
            lines.append(f"{EMOJI.get(scraper, '🔧')} *{scraper.upper()}* — no runs yet")
            lines.append("")
            continue

        if scraper in ('cars', 'apartments'):
            for r in cats:
                icon  = STATUS_ICON.get(r['status'], '❓')
                em    = EMOJI.get(scraper, '🔧')
                label = scraper.upper()
                if r['category']:
                    label += f" ({r['category']})"

                lines.append(f"{em} *{label}*")

                if r['status'] == 'running':
                    lines.append(f"  {icon} Running... (started {_ago(r['started_at'])})")
                else:
                    lines.append(f"  {icon} Last run: {_ago(r['started_at'])}")
                    lines.append(f"  ⏱ Duration: {_duration(r['started_at'], r['finished_at'])}")

                lines.append(f"  ✨ New ads: {r['new_records']:,}")
                lines.append(f"  📄 Pages scraped: {r['pages_scraped']}")

                if r.get('early_stopped'):
                    lines.append("  🛑 Early stop (DB up to date)")
                if r.get('error_msg'):
                    lines.append(f"  ⚠️ Error: {r['error_msg'][:80]}")
                lines.append("")

        else:  # electronics — show per-category summary
            lines.append(f"{EMOJI.get(scraper, '🔧')} *ELECTRONICS*")
            total_new = 0
            latest_start = None
            latest_finish = None
            any_running = False

            for r in cats:
                cat_em = EMOJI.get(r['category'] or '', '📦')
                icon   = STATUS_ICON.get(r['status'], '❓')
                lines.append(
                    f"  {cat_em} {(r['category'] or 'unknown').upper()}: "
                    f"{icon} {r['new_records']:,} new · {r['pages_scraped']}p"
                    + (" 🛑" if r.get('early_stopped') else "")
                )
                total_new += r['new_records']
                if r['status'] == 'running':
                    any_running = True
                if r['started_at']:
                    if not latest_start or r['started_at'] > latest_start:
                        latest_start = r['started_at']
                if r.get('finished_at'):
                    if not latest_finish or r['finished_at'] > latest_finish:
                        latest_finish = r['finished_at']

            if any_running:
                lines.append(f"  ⚙️  Still running... ({_ago(latest_start)})")
            else:
                lines.append(f"  📦 Total new: {total_new:,}")
                lines.append(f"  ⏱ Last run: {_ago(latest_start)}")
                if latest_start and latest_finish:
                    lines.append(f"  ⏳ Duration: {_duration(latest_start, latest_finish)}")
            lines.append("")

    lines.append("━━━━━━━━━━━━━━━━━━━━")

    # API services — shown as two-column pairs
    lines.append("🏥 *API SERVICES*")
    svc_pairs = list(health.items())
    for i in range(0, len(svc_pairs), 2):
        left  = svc_pairs[i]
        right = svc_pairs[i + 1] if i + 1 < len(svc_pairs) else None
        left_str  = f"{'✅' if left[1] else '❌'} {left[0]}"
        right_str = f"  {'✅' if right[1] else '❌'} {right[0]}" if right else ""
        lines.append(f"  {left_str}{right_str}")

    lines.append("")

    # Scraper instances — one per line with last-run health
    lines.append("🤖 *SCRAPERS*")
    for label, status in _scraper_health(runs):
        lines.append(f"  {label}: {status}")

    lines.append("━━━━━━━━━━━━━━━━━━━━")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# Access guard
# ─────────────────────────────────────────────────────────────

async def _check_access(update: Update) -> bool:
    """Return True if the user is allowed; send rejection and return False otherwise."""
    user_id = update.effective_user.id
    if not ALLOWED_IDS or user_id in ALLOWED_IDS:
        return True
    username = update.effective_user.username or update.effective_user.first_name or str(user_id)
    logger.warning("Rejected access from user %s (%s)", user_id, username)
    await update.message.reply_text(
        "⛔ Access denied.\n\n"
        "This is a private monitoring bot.\n"
        "Ask the administrator to add your Telegram ID to the access list."
    )
    return False


# ─────────────────────────────────────────────────────────────
# Handlers
# ─────────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_access(update):
        return
    chat_id = update.effective_chat.id
    context.bot_data.setdefault('monitor_chats', set()).add(chat_id)
    await update.message.reply_text(
        "👋 OLX Data Monitor bot started.\n\n"
        "Commands:\n"
        "  /status — scraper status + service health\n\n"
        "Auto-update: every 3 hours in this chat.",
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_access(update):
        return
    msg = build_status_message()
    await update.message.reply_text(msg, parse_mode='Markdown')


async def _cmd_electronics_report(update: Update, category: str, emoji: str, label: str):
    """Shared logic for all electronics price report commands."""
    try:
        r = requests.get(
            f"{DJANGO_URL}/api/electronics/report/?category={category}", timeout=12
        )
        r.raise_for_status()
        payload = r.json()
        models  = payload.get('models', [])
        broken  = payload.get('broken_listings', [])
    except Exception as e:
        await update.message.reply_text(f"⚠️ Could not fetch data: {e}")
        return

    if not models:
        await update.message.reply_text(f"{emoji} No {label} data in DB yet.")
        return

    tz5 = timezone(timedelta(hours=5))
    date_str = datetime.now(tz5).strftime('%d %b %Y')

    lines = [f"{emoji} *{label} prices — OLX.uz*",
             f"_{date_str} · {len(models)} models_", ""]
    for m in models:
        lo = int(m['min_usd'])
        hi = int(m['max_usd'])
        lines.append(f"`{m['model']:<26}` ${lo:,}–${hi:,}  ({m['cnt']})")

    if broken:
        lines += ["", "🔧 *For repair / parts:*"]
        for b in broken:
            lines.append(f"  `${b['price_usd']:,}` {b['title'][:48]}")

    await update.message.reply_text("\n".join(lines), parse_mode='Markdown')


async def cmd_report_iphone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_access(update):
        return
    await _cmd_electronics_report(update, 'iphone', '📱', 'iPhone')


async def cmd_report_macbook(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_access(update):
        return
    await _cmd_electronics_report(update, 'macbook', '💻', 'MacBook')


async def cmd_report_gpu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_access(update):
        return
    await _cmd_electronics_report(update, 'gpu', '🎮', 'GPU')


async def cmd_report_mac(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_access(update):
        return
    await _cmd_electronics_report(update, 'mac', '🖥', 'Mac')


# ─────────────────────────────────────────────────────────────
# Interactive electronics drill-down  (/report_electronics)
# ─────────────────────────────────────────────────────────────

LISTINGS_PAGE_SIZE = 5  # mirrors backend ElectronicsListings.PAGE_SIZE


async def _check_cb_access(update: Update) -> bool:
    """Access guard for callback queries."""
    user_id = update.callback_query.from_user.id
    if not ALLOWED_IDS or user_id in ALLOWED_IDS:
        return True
    await update.callback_query.answer("⛔ Access denied.", show_alert=True)
    return False


def _category_view() -> tuple[str, InlineKeyboardMarkup]:
    text = "🛒 *Electronics price reports*\n\nPick a category:"
    cats = list(ELEC_CATEGORIES.values())
    rows, row = [], []
    for c in cats:
        row.append(InlineKeyboardButton(c['label'], callback_data=f"e|per|{c['id']}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return text, InlineKeyboardMarkup(rows)


def _period_view(category: str) -> tuple[str, InlineKeyboardMarkup]:
    cat = ELEC_CATEGORIES.get(category, {})
    text = (f"{cat.get('emoji', '🛒')} *{cat.get('report_label', category)}*\n\n"
            "Pick a time period:")
    rows, row = [], []
    for p in ELEC_PERIODS:
        row.append(InlineKeyboardButton(p['label'], callback_data=f"e|rep|{category}|{p['id']}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("← New search", callback_data="e|cat")])
    return text, InlineKeyboardMarkup(rows)


def _scraped_age(scraped_at_iso: str | None) -> str:
    """Return human-readable age like 'today', 'yesterday', '3 days ago'."""
    if not scraped_at_iso:
        return ''
    try:
        dt = datetime.fromisoformat(scraped_at_iso.replace('Z', '+00:00'))
        days_old = (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).days
        if days_old == 0:
            return 'today'
        if days_old == 1:
            return 'yesterday'
        return f'{days_old}d ago'
    except Exception:
        return ''


def _fetch_report(category: str, days: int) -> dict | None:
    try:
        r = requests.get(
            f"{DJANGO_URL}/api/electronics/report/",
            params={'category': category, 'days': days}, timeout=12,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning("electronics report fetch failed: %s", e)
        return None


def _report_view(category: str, days: int) -> tuple[str, InlineKeyboardMarkup, list[dict]]:
    """Returns (text, keyboard, models). models is [] when no data / fetch error."""
    cat       = ELEC_CATEGORIES.get(category, {})
    emoji     = cat.get('emoji', '🛒')
    label     = cat.get('report_label', category)
    per_label = ELEC_PERIOD_LABEL.get(str(days), f"{days} days")

    payload = _fetch_report(category, days)
    if payload is None:
        text = f"{emoji} *{label}* — ⚠️ could not fetch data."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("← New search", callback_data="e|cat")]])
        return text, kb, []

    models = payload.get('models', [])
    broken = payload.get('broken_listings', [])

    if not models:
        text = f"{emoji} *{label}*\n_{per_label}_\n\nNo data for this period."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("← New search", callback_data="e|cat")]])
        return text, kb, []

    # Header text — keep it short, models are in the buttons
    header = f"{emoji} *{label} prices — OLX.uz*\n_{per_label} · {len(models)} models · tap to browse_"
    if broken:
        header += f"\n\n🔧 *For repair / parts:*"
        for b in broken[:3]:
            header += f"\n  `${b['price_usd']:,}` {b['title'][:45]}"

    # One full-width button per model: "Model Name   $lo–$hi  (N)"
    rows = []
    for i, m in enumerate(models):
        lo  = int(m['min_usd'])
        hi  = int(m['max_usd'])
        cnt = m['cnt']
        rows.append([InlineKeyboardButton(
            f"{m['model']}   ${lo:,}–${hi:,}  ({cnt})",
            callback_data=f"e|lst|{i}"
        )])
    rows.append([InlineKeyboardButton("← New search", callback_data="e|cat")])

    lines = [header]

    return "\n".join(lines), InlineKeyboardMarkup(rows), models


def _fetch_listings(category: str, model_label: str, days: int, page: int) -> dict | None:
    try:
        r = requests.get(
            f"{DJANGO_URL}/api/electronics/listings/",
            params={'category': category, 'model_label': model_label,
                    'days': days, 'page': page}, timeout=12,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.warning("electronics listings fetch failed: %s", e)
        return None


def _listings_view(category: str, model_label: str, days: int, page: int,
                   idx: int) -> tuple[str, InlineKeyboardMarkup, str]:
    cat   = ELEC_CATEGORIES.get(category, {})
    emoji = cat.get('emoji', '🛒')
    per_label = ELEC_PERIOD_LABEL.get(str(days), f"{days} days")

    payload = _fetch_listings(category, model_label, days, page)
    if payload is None:
        text = f"{emoji} <b>{model_label}</b> — ⚠️ could not fetch listings."
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("← Back to report", callback_data="e|back")]])
        return text, kb, 'HTML'

    listings = payload.get('listings', [])
    total    = payload.get('total', 0)
    page     = payload.get('page', page)
    pages    = payload.get('pages', 0)

    lines = [f"{emoji} <b>{model_label} — listings</b>"]
    if total:
        first = page * LISTINGS_PAGE_SIZE + 1
        last  = min(first + len(listings) - 1, total)
        lines.append(f"<i>{per_label} · showing {first}–{last} of {total}</i>")
    else:
        lines.append(f"<i>{per_label}</i>\n\nNo listings found.")
    lines.append("")

    def _esc(s: str) -> str:
        return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    for n, lst in enumerate(listings, start=page * LISTINGS_PAGE_SIZE + 1):
        title = _esc((lst.get('title') or '')[:60])
        price = lst.get('price_usd', 0)
        age   = _scraped_age(lst.get('scraped_at'))
        url   = lst.get('source_url') or ''
        if url:
            lines.append(f'{n}. <a href="{url}">{title}</a> — <b>${price:,}</b> <i>{age}</i>')
        else:
            lines.append(f'{n}. {title} — <b>${price:,}</b> <i>{age}</i>')

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀ Prev", callback_data=f"e|pg|{idx}|{page - 1}"))
    if page < pages - 1:
        nav.append(InlineKeyboardButton("▶ Next", callback_data=f"e|pg|{idx}|{page + 1}"))
    btn_rows = [nav] if nav else []
    btn_rows.append([InlineKeyboardButton("← Back to report", callback_data="e|back")])

    return "\n".join(lines), InlineKeyboardMarkup(btn_rows), 'HTML'


async def cmd_report_electronics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_access(update):
        return
    text, kb = _category_view()
    await update.message.reply_text(text, reply_markup=kb, parse_mode='Markdown')


async def handle_electronics_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _check_cb_access(update):
        return
    q = update.callback_query
    await q.answer()
    parts = q.data.split('|')
    action = parts[1] if len(parts) > 1 else 'cat'

    store  = context.user_data.setdefault('elec', {})
    msg_id = q.message.message_id
    state  = store.get(msg_id)

    async def _edit(text, kb, parse_mode='Markdown'):
        await q.edit_message_text(text, reply_markup=kb, parse_mode=parse_mode)

    if action == 'cat':
        store.pop(msg_id, None)
        text, kb = _category_view()
        await _edit(text, kb)
        return

    if action == 'per':
        category = parts[2]
        text, kb = _period_view(category)
        await _edit(text, kb)
        return

    if action == 'rep':
        category = parts[2]
        days = int(parts[3])
        text, kb, models = _report_view(category, days)
        store[msg_id] = {
            'category': category,
            'days': days,
            'models': [m['model'] for m in models],
        }
        await _edit(text, kb)
        return

    if action == 'back':
        if not state:
            text, kb = _category_view()
            await _edit(text, kb)
            return
        text, kb, models = _report_view(state['category'], state['days'])
        state['models'] = [m['model'] for m in models]
        await _edit(text, kb)
        return

    if action in ('lst', 'pg'):
        if not state or not state.get('models'):
            # state lost (e.g. bot restarted) — send user back to start
            text, kb = _category_view()
            await _edit(text, kb)
            return
        idx  = int(parts[2])
        page = int(parts[3]) if action == 'pg' else 0
        models = state['models']
        if idx < 0 or idx >= len(models):
            text, kb, refreshed = _report_view(state['category'], state['days'])
            state['models'] = [m['model'] for m in refreshed]
            await _edit(text, kb)
            return
        model_label = models[idx]
        text, kb, pm = _listings_view(state['category'], model_label,
                                     state['days'], page, idx)
        await _edit(text, kb, pm)
        return


async def auto_post(context: ContextTypes.DEFAULT_TYPE):
    chats: set = context.bot_data.get('monitor_chats', set())
    if not chats:
        return
    msg = build_status_message()
    for chat_id in list(chats):
        try:
            await context.bot.send_message(chat_id, msg, parse_mode='Markdown')
        except Exception as e:
            logger.warning("Auto-post to %s failed: %s", chat_id, e)


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

async def post_init(app: Application) -> None:
    await app.bot.set_my_commands([
        BotCommand("start",           "Start monitoring — subscribe to auto-updates"),
        BotCommand("status",          "Show scrapers + service health right now"),
        BotCommand("report_electronics", "Electronics price reports with drill-down"),
        BotCommand("report_iphone",   "iPhone prices: model · min–max · count"),
        BotCommand("report_macbook",  "MacBook prices: model · min–max · count"),
        BotCommand("report_mac",      "Mac mini/Studio/iMac prices: model · min–max · count"),
        BotCommand("report_gpu",      "GPU prices: model · min–max · count"),
    ])


def main():
    if not BOT_TOKEN:
        logger.error("OPS_BOT_TOKEN not set in .env — exiting")
        return

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start",          cmd_start))
    app.add_handler(CommandHandler("status",         cmd_status))
    app.add_handler(CommandHandler("report_iphone",  cmd_report_iphone))
    app.add_handler(CommandHandler("report_macbook", cmd_report_macbook))
    app.add_handler(CommandHandler("report_mac",     cmd_report_mac))
    app.add_handler(CommandHandler("report_gpu",     cmd_report_gpu))
    app.add_handler(CommandHandler("report_electronics", cmd_report_electronics))
    app.add_handler(CallbackQueryHandler(handle_electronics_callback, pattern=r'^e\|'))

    # Auto-post every AUTO_POST_INTERVAL seconds (default 3 h)
    app.job_queue.run_repeating(
        auto_post,
        interval=AUTO_POST_INTERVAL,
        first=60,
    )

    logger.info("OLX Monitor bot starting (auto-post every %ds)", AUTO_POST_INTERVAL)
    app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()
