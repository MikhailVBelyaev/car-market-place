"""Admin panel for @MVehicleBot — channel post manager."""
import os
import logging
import requests

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

logger = logging.getLogger(__name__)

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
DJANGO_URL     = os.getenv("DJANGO_URL", "http://django:8000")

ADMIN_AUTH = 11  # ConversationHandler state

POST_REGISTRY = [
    ("brand_ranking",        "📊", "Brand Ranking",        "Mon 09:00"),
    ("price_movers",         "📉", "Price Movers",         "Wed 09:00"),
    ("weekly_digest",        "📋", "Weekly Digest",        "Fri 09:00"),
    ("color_premium",        "🎨", "Color Premium",        "Monthly"),
    ("gear_premium",         "⚙️", "Gear Premium",        "Monthly"),
    ("age_depreciation",     "📅", "Age Depreciation",     "Monthly"),
    ("best_value",           "💎", "Best Value Deals",     "Weekly"),
    ("seasonal_trends",      "🌡", "Seasonal Trends",      "Monthly"),
    ("market_breadth",       "📦", "Market Breadth",       "Monthly"),
    ("mileage_depreciation", "🚗", "Mileage Depreciation", "Monthly"),
]

# Map post_type to its analytics URL path
ANALYTICS_URLS = {
    "brand_ranking":        "/api/cars/analytics/brand-ranking/",
    "price_movers":         "/api/cars/analytics/price-movers/",
    "weekly_digest":        "/api/cars/analytics/weekly-digest/",
    "color_premium":        "/api/cars/analytics/color-premium/",
    "gear_premium":         "/api/cars/analytics/gear-premium/",
    "age_depreciation":     "/api/cars/analytics/age-depreciation/",
    "best_value":           "/api/cars/analytics/best-value/",
    "seasonal_trends":      "/api/cars/analytics/seasonal-trends/",
    "market_breadth":       "/api/cars/analytics/market-breadth/",
    "mileage_depreciation": "/api/cars/analytics/mileage-depreciation/",
}


def _get_configs():
    try:
        r = requests.get(f"{DJANGO_URL}/api/cars/post-config/", timeout=5)
        r.raise_for_status()
        return {item["post_type"]: item["enabled"] for item in r.json()}
    except Exception as e:
        logger.warning("PostConfig fetch failed: %s", e)
        return {}


def _toggle(post_type, enabled):
    try:
        r = requests.patch(
            f"{DJANGO_URL}/api/cars/post-config/{post_type}/",
            json={"enabled": enabled}, timeout=5)
        r.raise_for_status()
        return True
    except Exception as e:
        logger.warning("Toggle failed: %s", e)
        return False


def _build_keyboard(configs):
    rows = []
    for pt, emoji, name, schedule in POST_REGISTRY:
        enabled = configs.get(pt, False)
        status  = "✅" if enabled else "⬜"
        rows.append([
            InlineKeyboardButton(
                f"{status} {emoji} {name}  [{schedule}]",
                callback_data=f"adm_toggle_{pt}",
            ),
            InlineKeyboardButton("👁", callback_data=f"adm_preview_{pt}"),
        ])
    rows.append([
        InlineKeyboardButton("🔄 Refresh", callback_data="adm_refresh"),
        InlineKeyboardButton("❌ Close",   callback_data="adm_close"),
    ])
    return InlineKeyboardMarkup(rows)


async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if context.user_data.get("admin_authed"):
        configs = _get_configs()
        kb = _build_keyboard(configs)
        await update.message.reply_text(
            "📡 *CHANNEL POST MANAGER*\n\n"
            "Tap a post name to toggle on/off\nTap 👁 to preview data from DB",
            parse_mode="Markdown", reply_markup=kb,
        )
        return ConversationHandler.END

    if not ADMIN_PASSWORD:
        await update.message.reply_text("⚠️ ADMIN_PASSWORD not set.")
        return ConversationHandler.END

    await update.message.reply_text("🔐 Enter admin password:")
    return ADMIN_AUTH


async def admin_check_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text or ""
    try:
        await update.message.delete()
    except Exception:
        pass

    if text == ADMIN_PASSWORD:
        context.user_data["admin_authed"] = True
        configs = _get_configs()
        kb = _build_keyboard(configs)
        await update.message.reply_text(
            "✅ Authenticated!\n\n"
            "📡 *CHANNEL POST MANAGER*\n\n"
            "Tap a post name to toggle on/off\nTap 👁 to preview data",
            parse_mode="Markdown", reply_markup=kb,
        )
    else:
        await update.message.reply_text("❌ Wrong password.")
    return ConversationHandler.END


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if not context.user_data.get("admin_authed"):
        await q.answer("Session expired — use /admin", show_alert=True)
        return

    data = q.data

    if data == "adm_refresh":
        configs = _get_configs()
        kb = _build_keyboard(configs)
        try:
            await q.edit_message_reply_markup(reply_markup=kb)
        except Exception:
            pass
        return

    if data == "adm_close":
        try:
            await q.message.delete()
        except Exception:
            pass
        return

    if data.startswith("adm_toggle_"):
        pt      = data[len("adm_toggle_"):]
        configs = _get_configs()
        current = configs.get(pt, False)
        _toggle(pt, not current)
        configs[pt] = not current  # optimistic update
        kb = _build_keyboard(configs)
        try:
            await q.edit_message_reply_markup(reply_markup=kb)
        except Exception:
            pass
        return

    if data.startswith("adm_preview_"):
        pt = data[len("adm_preview_"):]
        await _send_preview(q, pt)
        return


async def _send_preview(q, post_type):
    url_path = ANALYTICS_URLS.get(post_type)
    if not url_path:
        await q.message.reply_text(f"⚠️ No analytics URL for {post_type}")
        return
    try:
        r = requests.get(f"{DJANGO_URL}{url_path}", timeout=10)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        await q.message.reply_text(f"⚠️ Data fetch failed: {e}")
        return

    text = _format_preview(post_type, data)
    await q.message.reply_text(text, parse_mode="Markdown")


def _format_preview(post_type, data):
    registry_map = {pt: (emoji, name) for pt, emoji, name, _ in POST_REGISTRY}
    emoji, name = registry_map.get(post_type, ("📊", post_type))
    lines = [f"{emoji} *{name} — DATA PREVIEW*\n"]

    try:
        if post_type == "brand_ranking":
            for b in data.get("brands", [])[:5]:
                chg = f" ({b['pct_change']:+.1f}% w/w)" if b.get('pct_change') is not None else ""
                lines.append(f"  {b['brand']} — {b['count']:,} listings{chg}")

        elif post_type == "price_movers":
            lines.append("📈 Risers:")
            for m in data.get("risers", [])[:3]:
                lines.append(f"  {m['brand']} {m['model']}: +{m['change_pct']:.1f}%")
            lines.append("📉 Fallers:")
            for m in data.get("fallers", [])[:3]:
                lines.append(f"  {m['brand']} {m['model']}: {m['change_pct']:.1f}%")

        elif post_type == "weekly_digest":
            lines.append(f"Total listings: {data.get('total_listings', 0):,}")
            for b in data.get("top_brands", [])[:3]:
                lines.append(f"  {b['brand']}: {b['count']:,} · avg ${b['avg_price']:,}")

        elif post_type == "color_premium":
            lines.append(f"Market avg: ${data.get('market_avg', 0):,}")
            for c in data.get("colors", [])[:6]:
                s = "+" if c["vs_market_pct"] >= 0 else ""
                lines.append(f"  {c['color']}: avg ${c['avg_price']:,}  ({s}{c['vs_market_pct']:.1f}% vs market)")

        elif post_type == "gear_premium":
            for b in data.get("brands", [])[:5]:
                lines.append(f"  {b['brand']}: AT ${b['at_price']:,} vs MT ${b['mt_price']:,} (+{b['premium_pct']:.1f}%)")

        elif post_type == "age_depreciation":
            for b in data.get("brands", []):
                yrs = b.get("years", [])
                if len(yrs) >= 2:
                    lines.append(f"\n{b['brand']}: {yrs[0]['year']} → {yrs[-1]['year']}")
                    for y in yrs[-4:]:
                        lines.append(f"  {y['year']}: avg ${y['avg_price']:,}  ({y['count']} listings)")

        elif post_type == "best_value":
            lst = data.get("listings", [])
            lines.append(f"Found {len(lst)} underpriced listings this week:")
            for l in lst[:5]:
                lines.append(
                    f"  {l['brand']} {l['model']} {l['year']}: ${l['price']:,}"
                    f"  (market avg ${l['avg_price']:,}, -{l['discount_pct']:.0f}%)")

        elif post_type == "seasonal_trends":
            for b in data.get("brands", []):
                months = b.get("months", [])
                if len(months) >= 2:
                    lo = min(months, key=lambda m: m['avg_price'])
                    hi = max(months, key=lambda m: m['avg_price'])
                    lines.append(f"\n{b['brand']} ({len(months)} months):")
                    lines.append(f"  Cheapest: {lo['month']} → ${lo['avg_price']:,}")
                    lines.append(f"  Priciest: {hi['month']} → ${hi['avg_price']:,}")

        elif post_type == "market_breadth":
            lines.append(f"Total this week: {data.get('total', 0):,}")
            for band in data.get("bands", []):
                lines.append(f"  {band['label']}: {band['count']:,}  ({band['pct']:.0f}%)")

        elif post_type == "mileage_depreciation":
            lines.append("Price loss per 10,000 km:")
            for m in data.get("models", []):
                lines.append(
                    f"  {m['brand']} {m['model']}: ${abs(m['price_per_10k_km']):,.0f} / 10k km"
                    f"  ({m['count']} listings)")

        else:
            lines.append(str(data)[:400])

    except Exception as e:
        lines.append(f"⚠️ Format error: {e}")

    return "\n".join(lines)
