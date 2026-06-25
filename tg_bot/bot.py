import io
import json
import logging
import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import requests
from dotenv import load_dotenv
from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

from admin_panel import (
    admin_start, admin_check_password, admin_callback, ADMIN_AUTH,
)

load_dotenv()
BOT_TOKEN           = os.getenv("BOT_TOKEN")
ML_API_URL          = os.getenv("ML_API_URL",          "http://ml_api:8500")
DJANGO_URL          = os.getenv("DJANGO_URL",          "http://django:8000")
CAR_VISION_URL      = os.getenv("CAR_VISION_URL",      "http://car-vision-api:8600")
PHOTOS_IDLE_TIMEOUT = int(os.getenv("PHOTOS_IDLE_TIMEOUT", "30"))
CHECK_AUTO_TIMEOUT  = int(os.getenv("CHECK_AUTO_TIMEOUT",  "15"))

# ── States ───────────────────────────────────────────────────────────────────
BRAND, MODEL, YEAR, MILEAGE, GEAR, COLOR = range(6)
COLLECTING_PHOTOS = 6
COMPARE_KM, COMPARE_TAXI = 7, 8

# ── Depreciation rates by brand (annual, from real OLX data) ─────────────────
DEPRECIATION_RATES = {
    "Chevrolet": 0.089, "BYD": 0.311, "Hyundai": 0.252,
    "LADA": 0.034,      "Toyota": 0.12, "Kia": 0.15,
    "Daewoo": 0.10,     "Geely": 0.18,  "Haval": 0.20,
}
DEFAULT_DEPRECIATION = 0.15

# ── Fuel consumption L/100km by model keyword ─────────────────────────────────
FUEL_L_100 = {
    "Nexia": 8.0, "Cobalt": 8.0, "Matiz": 6.5, "Spark": 6.5,
    "Lacetti": 9.0, "Gentra": 8.5, "Malibu": 10.0, "Cruze": 9.5,
    "Trailblazer": 12.0, "Captiva": 11.0, "Tracker": 9.5,
    "Camry": 9.5, "Corolla": 7.5, "Land Cruiser": 14.0,
    "Tucson": 9.5, "Santa Fe": 11.0,
}
DEFAULT_FUEL_L_100 = 9.0
FUEL_PRICE_USD     = 0.65   # per liter, Uzbekistan 95 octane
MAINTENANCE_USD    = 30     # per month average

# ── Option maps (display label → DB value) ───────────────────────────────────
GEAR_OPTIONS = {
    "⚙️ Automatic": "AT",
    "🔧 Manual":    "MT",
    "🔩 DSG":       "DSG",
    "🔄 CVT":       "CVT",
}

COLOR_OPTIONS = {
    "⬜ White":  "white",
    "⬛ Black":  "black",
    "🔘 Silver": "silver",
    "🩶 Grey":   "grey",
    "🔵 Blue":   "blue",
    "🔴 Red":    "red",
    "🟢 Green":  "green",
    "🟡 Yellow": "yellow",
    "🎨 Other":  "other",
}

# ── Brand/model cache ────────────────────────────────────────────────────────
_brand_models: dict[str, list[str]] = {}


def load_brand_models() -> dict[str, list[str]]:
    global _brand_models
    if _brand_models:
        return _brand_models
    try:
        r = requests.get(f"{DJANGO_URL}/api/cars/brand-models/", timeout=8)
        r.raise_for_status()
        _brand_models = r.json()
        logger.info("Loaded %d brands", len(_brand_models))
    except Exception as e:
        logger.error("brand-models fetch failed: %s", e)
    return _brand_models


def build_keyboard(options: list[str], columns: int = 3) -> ReplyKeyboardMarkup:
    rows = [options[i : i + columns] for i in range(0, len(options), columns)]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)


# ── Job helpers ───────────────────────────────────────────────────────────────
def _ask_job(chat_id):  return f"ask_done_{chat_id}"
def _auto_job(chat_id): return f"auto_check_{chat_id}"


def _cancel_jobs(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    for name in [_ask_job(chat_id), _auto_job(chat_id)]:
        for job in context.job_queue.get_jobs_by_name(name):
            job.schedule_removal()


# ═══════════════════════════════════════════════════════════════════════════════
# PRICE PREDICTION  /start
# ═══════════════════════════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    brands = sorted(load_brand_models().keys())
    if not brands:
        await update.message.reply_text(
            "⚠️ Could not load brand list. Try again later.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END
    await update.message.reply_text(
        "🚗 *Car Price Prediction*\n\nChoose a brand:",
        parse_mode="Markdown",
        reply_markup=build_keyboard(brands),
    )
    return BRAND


async def get_brand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bm = load_brand_models()
    brand = update.message.text.strip()
    if brand not in bm:
        await update.message.reply_text(
            "❌ Select a brand from the keyboard:",
            reply_markup=build_keyboard(sorted(bm.keys())),
        )
        return BRAND
    context.user_data["brand"] = brand
    await update.message.reply_text(
        f"Select a model for *{brand}*:",
        parse_mode="Markdown",
        reply_markup=build_keyboard(sorted(bm[brand])),
    )
    return MODEL


async def get_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bm = load_brand_models()
    brand = context.user_data["brand"]
    model = update.message.text.strip()
    if model not in bm.get(brand, []):
        await update.message.reply_text(
            "❌ Select a model from the keyboard:",
            reply_markup=build_keyboard(sorted(bm[brand])),
        )
        return MODEL
    context.user_data["model"] = model
    await update.message.reply_text(
        "Enter car *year* (1990–2026):",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return YEAR


async def get_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        year = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Enter a valid year:")
        return YEAR
    if not (1990 <= year <= 2026):
        await update.message.reply_text("❌ Year must be 1990–2026:")
        return YEAR
    context.user_data["year"] = year
    await update.message.reply_text("Enter *mileage* in km:", parse_mode="Markdown")
    return MILEAGE


async def get_mileage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        mileage = int(update.message.text.strip().replace(",", "").replace(" ", ""))
    except ValueError:
        await update.message.reply_text("❌ Enter a valid mileage:")
        return MILEAGE
    if not (0 <= mileage <= 1_000_000):
        await update.message.reply_text("❌ Mileage must be 0–1,000,000:")
        return MILEAGE

    context.user_data["mileage"] = mileage
    await update.message.reply_text(
        "Select *transmission type*:",
        parse_mode="Markdown",
        reply_markup=build_keyboard(list(GEAR_OPTIONS.keys()), columns=2),
    )
    return GEAR


async def get_gear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    label = update.message.text.strip()
    if label not in GEAR_OPTIONS:
        await update.message.reply_text(
            "❌ Select transmission from the keyboard:",
            reply_markup=build_keyboard(list(GEAR_OPTIONS.keys()), columns=2),
        )
        return GEAR

    context.user_data["gear_type"] = GEAR_OPTIONS[label]
    await update.message.reply_text(
        "Select *car color*:",
        parse_mode="Markdown",
        reply_markup=build_keyboard(list(COLOR_OPTIONS.keys()), columns=3),
    )
    return COLOR


async def get_color(update: Update, context: ContextTypes.DEFAULT_TYPE):
    label = update.message.text.strip()
    if label not in COLOR_OPTIONS:
        await update.message.reply_text(
            "❌ Select color from the keyboard:",
            reply_markup=build_keyboard(list(COLOR_OPTIONS.keys()), columns=3),
        )
        return COLOR

    context.user_data["color"] = COLOR_OPTIONS[label]
    await _do_predict(update, context)
    return ConversationHandler.END


async def _do_predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    brand     = context.user_data["brand"]
    model     = context.user_data["model"]
    year      = context.user_data["year"]
    mileage   = context.user_data["mileage"]
    gear_type = context.user_data["gear_type"]
    color     = context.user_data["color"]

    gear_label  = next(k for k, v in GEAR_OPTIONS.items()  if v == gear_type)
    color_label = next(k for k, v in COLOR_OPTIONS.items() if v == color)

    price       = None
    source_line = ""
    range_line  = ""
    ml_low      = int(mileage * 0.75)
    ml_high     = int(mileage * 1.25)
    chart_low   = ml_low
    chart_high  = ml_high

    # ── 1. Real market data — tries progressively wider mileage bands ──
    try:
        r = requests.get(
            f"{DJANGO_URL}/api/cars/smart-price/",
            params={"brand": brand, "model": model, "year": year,
                    "gear_type": gear_type, "color": color, "mileage": mileage},
            timeout=8,
        )
        if r.status_code == 200:
            d = r.json()
            # Always capture the band returned (used for chart even on ML fallback)
            chart_low  = d.get("mileage_low",  ml_low)
            chart_high = d.get("mileage_high", ml_high)
            if d.get("price"):
                price       = d["price"]
                count       = d["count"]
                period      = d["period"]
                band        = d.get("mileage_band", "")
                source_line = f"📊 *{count} real listings* · {period} · {band}"
                range_line  = f"Range: ${d['min']:,} – ${d['max']:,}"
                logger.info("Market price: $%d median, %d listings (%s, %s)",
                            price, count, period, band)
    except Exception as e:
        logger.warning("smart-price failed: %s", e)

    # ── 2. ML fallback only when no market data ──
    if price is None:
        try:
            r = requests.post(
                f"{ML_API_URL}/predict2",
                headers={"Content-Type": "application/json"},
                data=json.dumps({"year": year, "mileage": mileage,
                                 "brand": brand, "model": model,
                                 "gear_type": gear_type, "color": color}),
                timeout=10,
            )
            if r.status_code == 200:
                price = round(r.json().get("predicted_price", 0) / 100) * 100
                source_line = "🤖 ML estimate _(not enough recent listings)_"
                logger.info("ML fallback price: $%d", price)
            else:
                logger.error("predict2 %d: %s", r.status_code, r.text)
        except Exception as e:
            logger.error("predict2 error: %s", e)

    if price is None:
        await update.message.reply_text("⚠️ Could not estimate price. Try again.")
        return

    text = (
        f"💰 *Current market price: {int(price):,} USD*\n\n"
        f"🚗 {brand} {model} · {year}\n"
        f"⚙️ {gear_label}  🎨 {color_label}\n"
    )
    if range_line:
        text += f"📉 {range_line}\n"
    text += f"\n{source_line}\n\nType /start for a new prediction."

    context.user_data["last_price"] = price   # used by /compare and /forecast

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup(
            [["/compare", "/forecast"], ["/start", "/cancel"]],
            resize_keyboard=True,
        ),
    )
    await _send_price_chart(update, context, brand, model, year, gear_type, color, mileage)


def _fetch_chart_data(brand, model, year, gear_type, color, mileage):
    """Fetch hedonic price history.  Falls back to relaxed filters if sparse."""
    # Primary: hedonic mode — all data, pooled slope adjustment
    attempts = [
        {"gear_type": gear_type, "color": color, "mileage": mileage},
        {"gear_type": gear_type, "mileage": mileage},
        {"mileage": mileage},
    ]
    for params in attempts:
        r = requests.get(
            f"{DJANGO_URL}/api/cars/price-history/",
            params={"brand": brand, "model": model, "year": year, **params},
            timeout=10,
        )
        if r.status_code != 200:
            continue
        resp = r.json()
        data = resp.get("data", []) if isinstance(resp, dict) else resp
        hedonic = resp.get("hedonic", False) if isinstance(resp, dict) else False
        slope   = resp.get("pooled_slope", 0) if isinstance(resp, dict) else 0
        months_with_data = [d for d in data if d.get("count", 0) >= 3]
        if len(months_with_data) >= 2:
            return data, hedonic, slope
    return [], False, 0


async def _send_price_chart(update: Update, context: ContextTypes.DEFAULT_TYPE,
                             brand: str, model: str, year: int,
                             gear_type: str, color: str, mileage: int):
    try:
        data, hedonic, slope = _fetch_chart_data(
            brand, model, year, gear_type, color, mileage)

        # Keep only months with ≥3 listings for stability
        data = [d for d in data if d.get("count", 0) >= 3]

        if len(data) < 2:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="📊 Not enough historical data for a price trend chart.",
            )
            return

        months = [datetime.strptime(d['month'], '%Y-%m') for d in data]
        counts = [d['count'] for d in data]
        total  = sum(counts)

        gear_label  = next((k for k, v in GEAR_OPTIONS.items()  if v == gear_type), gear_type)
        color_label = next((k for k, v in COLOR_OPTIONS.items() if v == color),     color)

        fig, ax = plt.subplots(figsize=(10, 5))

        if hedonic and all('price_at_mileage' in d for d in data):
            # Main line: your car's estimated value (mileage-adjusted)
            adj_prices = [d['price_at_mileage'] for d in data]
            avg_prices = [d['avg_price'] for d in data]

            ax.plot(months, avg_prices, linewidth=1.2, linestyle='--',
                    color='#90CAF9', alpha=0.7, label='Market avg (all km)', zorder=2)
            ax.plot(months, adj_prices, marker='o', linewidth=2.5,
                    color='#1976D2', markersize=7, zorder=3,
                    label=f'Your car ({mileage:,} km)')
            ax.fill_between(months, adj_prices, alpha=0.10, color='#1976D2')

            for m, p in zip(months, adj_prices):
                ax.annotate(f'${p:,}', xy=(m, p), xytext=(0, 10),
                            textcoords='offset points', ha='center',
                            fontsize=8, color='#1565C0', fontweight='bold')

            all_vals = adj_prices + avg_prices
            ax.set_ylim(min(all_vals) * 0.92, max(all_vals) * 1.08)
            ax.legend(fontsize=8, loc='upper right')
            slope_note = f" · ${abs(slope):.4f}/km price sensitivity"
            ax.set_xlabel(
                f'Based on {total:,} listings over {len(months)} months{slope_note}',
                fontsize=8, color='grey'
            )
            title_suffix = f"\nYour car value at {mileage:,} km (hedonic adjusted)"
        else:
            prices = [d['avg_price'] for d in data]
            ax.plot(months, prices, marker='o', linewidth=2.5,
                    color='#1976D2', markersize=7, zorder=3)
            ax.fill_between(months, prices, alpha=0.12, color='#1976D2')
            for m, p in zip(months, prices):
                ax.annotate(f'${p:,}', xy=(m, p), xytext=(0, 10),
                            textcoords='offset points', ha='center',
                            fontsize=8, color='#1976D2')
            ax.set_ylim(min(prices) * 0.92, max(prices) * 1.08)
            ax.set_xlabel(
                f'Based on {total:,} listings over {len(months)} months',
                fontsize=8, color='grey'
            )
            title_suffix = "\nMarket Price Trend"

        ax.set_title(
            f'{brand} {model} {year} · {gear_label} · {color_label}{title_suffix}',
            fontsize=12, fontweight='bold'
        )
        ax.set_ylabel('Price (USD)', fontsize=10)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        plt.xticks(rotation=40, ha='right', fontsize=9)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${x:,.0f}'))
        ax.grid(True, alpha=0.25, linestyle='--')

        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)

        caption = f"📈 {brand} {model} {year} · {gear_label} · {color_label} — {len(months)}-month trend"
        if hedonic:
            caption += f" (adjusted to {mileage:,} km)"
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=buf,
            caption=caption,
        )
        logger.info("Sent price chart for %s %s (%d months, hedonic=%s)", brand, model, len(months), hedonic)
    except Exception as e:
        logger.error("Chart generation failed: %s", e)


# ═══════════════════════════════════════════════════════════════════════════════
# PHOTO ANALYSIS  /fotos → photos → /check
# ═══════════════════════════════════════════════════════════════════════════════

async def fotos_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["pending_photos"] = []
    _cancel_jobs(context, update.effective_chat.id)
    await update.message.reply_text(
        "📸 Send car photos one by one.\n"
        "Type /check when done — or just wait, I'll ask you.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return COLLECTING_PHOTOS


async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    _cancel_jobs(context, chat_id)

    photo_obj = update.message.photo[-1]            # largest size
    tg_file   = await context.bot.get_file(photo_obj.file_id)
    data      = bytes(await tg_file.download_as_bytearray())

    photos = context.user_data.setdefault("pending_photos", [])
    photos.append(data)

    await update.message.reply_text(f"📷 Photo {len(photos)} received. Send more or /check.")

    # Ask "That's all?" after PHOTOS_IDLE_TIMEOUT seconds of silence
    context.job_queue.run_once(
        _ask_done_job,
        when=PHOTOS_IDLE_TIMEOUT,
        chat_id=chat_id,
        user_id=update.effective_user.id,
        name=_ask_job(chat_id),
    )
    return COLLECTING_PHOTOS


async def _ask_done_job(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    photos  = context.user_data.get("pending_photos", [])
    if not photos:
        return

    msg = await context.bot.send_message(
        chat_id,
        f"📸 {len(photos)} photo(s) queued. That's all?",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Check it", callback_data="check_now"),
        ]]),
    )
    context.user_data["ask_msg_id"] = msg.message_id

    # Auto-check if the button isn't pressed within CHECK_AUTO_TIMEOUT seconds
    context.job_queue.run_once(
        _auto_check_job,
        when=CHECK_AUTO_TIMEOUT,
        chat_id=chat_id,
        user_id=context.job.user_id,
        name=_auto_job(chat_id),
    )


async def _auto_check_job(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(context.job.chat_id, "⏱ Auto-checking now…")
    await _run_check(context.job.chat_id, context)


async def check_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat.id
    _cancel_jobs(context, chat_id)
    await _run_check(chat_id, context)
    return ConversationHandler.END


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    _cancel_jobs(context, chat_id)
    await _run_check(chat_id, context)
    return ConversationHandler.END


# ── Analysis aggregation ──────────────────────────────────────────────────────

COND_EMOJI = {
    "ideal": "🟢", "good": "🟡", "normal": "🟠",
    "damaged": "🔴", "needs_repair": "⛔", "unknown": "⚪",
}
# worst = lowest index
COND_ORDER = ["needs_repair", "damaged", "normal", "good", "ideal", "unknown"]


async def _run_check(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    photos = context.user_data.pop("pending_photos", [])
    if not photos:
        await context.bot.send_message(chat_id, "⚠️ No photos to analyze.")
        return

    await context.bot.send_message(chat_id, f"🔍 Analyzing {len(photos)} photo(s)…")

    results = []
    for i, photo_bytes in enumerate(photos):
        try:
            r = requests.post(
                f"{CAR_VISION_URL}/analyze",
                files={"file": (f"photo_{i + 1}.jpg", photo_bytes, "image/jpeg")},
                timeout=30,
            )
            if r.status_code == 200:
                results.append(r.json())
                logger.info("Photo %d: %s", i + 1, r.json().get("condition"))
            else:
                logger.error("Vision API photo %d → %d %s", i + 1, r.status_code, r.text)
        except Exception as e:
            logger.error("Vision API photo %d exception: %s", i + 1, e)

    if not results:
        await context.bot.send_message(chat_id, "⚠️ Could not analyze photos. Try again.")
        return

    # Best exterior shot → brand/model/year/color/body_type
    exterior = [r for r in results if r.get("photo_type") == "exterior"]
    best = exterior[0] if exterior else results[0]

    # Worst condition across all photos (index 0 in COND_ORDER = worst)
    worst = min(
        results,
        key=lambda r: COND_ORDER.index(r.get("condition", "unknown"))
        if r.get("condition", "unknown") in COND_ORDER else 99,
    )

    # Deduplicated damage areas
    damage = list(dict.fromkeys(
        area for r in results for area in r.get("damage_areas", [])
    ))

    brand     = best.get("brand")         or "Unknown"
    model     = best.get("model")         or "Unknown"
    year_est  = best.get("year_estimate") or "—"
    color     = best.get("color")         or "—"
    body      = best.get("body_type")     or "—"
    condition = worst.get("condition",         "unknown")
    score     = worst.get("condition_score",   0)
    details   = worst.get("condition_details", "")
    emoji     = COND_EMOJI.get(condition, "⚪")

    text = (
        f"🚗 *{brand} {model}*\n"
        f"📅 {year_est}  🎨 {color}  🏎 {body}\n\n"
        f"{emoji} *Condition: {condition.replace('_', ' ').title()}* ({score}/5)\n"
        f"_{details}_\n"
    )
    if damage:
        text += f"\n⚠️ *Damage areas:* {', '.join(damage)}\n"

    summaries = [r.get("summary", "") for r in results if r.get("summary")]
    if summaries:
        text += f"\n📝 {summaries[0]}"

    await context.bot.send_message(chat_id, text, parse_mode="Markdown")


# ═══════════════════════════════════════════════════════════════════════════════
# /compare  — Own car vs Taxi calculator
# ═══════════════════════════════════════════════════════════════════════════════

async def compare_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    car = _last_car(context)
    if not car:
        await update.message.reply_text(
            "⚠️ Please run /start first to identify your car, then use /compare.",
        )
        return ConversationHandler.END
    context.user_data["compare_car"] = car
    await update.message.reply_text(
        f"🚗 Comparing *{car['brand']} {car['model']} {car['year']}*\n\n"
        "How many km do you drive per day on average?\n"
        "_Example: 30_",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return COMPARE_KM


async def compare_get_km(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        km = float(update.message.text.strip().replace(",", "."))
        if not (1 <= km <= 1000):
            raise ValueError
    except ValueError:
        await update.message.reply_text("Please enter a number between 1 and 1000:")
        return COMPARE_KM
    context.user_data["compare_daily_km"] = km
    await update.message.reply_text(
        "🚕 What does 1 km cost in a taxi in your city? (USD)\n\n"
        "Tashkent Yandex.Taxi ≈ *0.10–0.12 USD/km*\n"
        "_Just send 0.12 to use the default_",
        parse_mode="Markdown",
    )
    return COMPARE_TAXI


async def compare_get_taxi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        taxi = float(update.message.text.strip().replace(",", "."))
        if not (0.01 <= taxi <= 5.0):
            raise ValueError
    except ValueError:
        await update.message.reply_text("Please enter a price like 0.10 or 0.12:")
        return COMPARE_TAXI

    car      = context.user_data["compare_car"]
    daily_km = context.user_data["compare_daily_km"]
    await update.message.reply_text("⏳ Calculating…", reply_markup=ReplyKeyboardRemove())
    await _do_compare(update, context, car, daily_km, taxi)
    return ConversationHandler.END


def _last_car(context) -> dict | None:
    """Return the car from last /start session, or None."""
    ud = context.user_data
    if all(k in ud for k in ("brand", "model", "year", "mileage", "gear_type", "color")):
        return {k: ud[k] for k in ("brand", "model", "year", "mileage", "gear_type", "color",
                                    "last_price")}
    return None


async def _do_compare(update, context, car, daily_km, taxi_per_km):
    brand = car["brand"]
    model = car["model"]
    price = car.get("last_price", 10000)

    depr_rate    = DEPRECIATION_RATES.get(brand, DEFAULT_DEPRECIATION)
    fuel_l100    = next((v for k, v in FUEL_L_100.items() if k.lower() in model.lower()),
                        DEFAULT_FUEL_L_100)
    monthly_km   = daily_km * 30

    monthly_depr  = price * depr_rate / 12
    monthly_fuel  = monthly_km * (fuel_l100 / 100) * FUEL_PRICE_USD
    monthly_maint = MAINTENANCE_USD
    monthly_car   = monthly_depr + monthly_fuel + monthly_maint

    monthly_taxi  = monthly_km * taxi_per_km

    winner = "🚗 Own car" if monthly_car < monthly_taxi else "🚕 Taxi"
    saving = abs(monthly_car - monthly_taxi)

    # 3-year cumulative
    months   = list(range(37))
    cum_car  = [price + m * monthly_car for m in months]    # includes initial capital
    cum_taxi = [m * monthly_taxi        for m in months]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.patch.set_facecolor('#FAFAFA')

    # Left: monthly cost breakdown (stacked bars)
    ax = axes[0]
    ax.set_facecolor('#FAFAFA')
    cats     = ["Own Car", "Taxi"]
    bottoms  = [0, 0]
    segments = [
        ("Depreciation", [monthly_depr, 0],       '#1565C0'),
        ("Fuel",         [monthly_fuel, 0],        '#42A5F5'),
        ("Maintenance",  [monthly_maint, 0],       '#90CAF9'),
        ("Taxi fare",    [0, monthly_taxi],        '#FF8F00'),
    ]
    for label, vals, color in segments:
        ax.bar(cats, vals, bottom=bottoms, color=color, label=label, width=0.45)
        bottoms = [bottoms[i] + vals[i] for i in range(2)]

    ax.set_ylabel("USD / month", fontsize=10)
    ax.set_title("Monthly cost breakdown", fontsize=11, fontweight='bold')
    ax.legend(fontsize=8, loc='upper right')
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${x:,.0f}'))
    for i, total in enumerate([monthly_car, monthly_taxi]):
        ax.text(i, total + 5, f'${total:,.0f}', ha='center', fontsize=10, fontweight='bold')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Right: 3-year cumulative
    ax2 = axes[1]
    ax2.set_facecolor('#FAFAFA')
    ax2.plot(months, cum_car,  linewidth=2.5, color='#1565C0', label='Own car (total spent)')
    ax2.plot(months, cum_taxi, linewidth=2.5, color='#FF8F00', label='Taxi (total spent)')
    ax2.fill_between(months, cum_car, cum_taxi,
                     where=[c < t for c, t in zip(cum_car, cum_taxi)],
                     alpha=0.12, color='#1565C0', label='Car cheaper zone')
    ax2.fill_between(months, cum_car, cum_taxi,
                     where=[t < c for c, t in zip(cum_car, cum_taxi)],
                     alpha=0.12, color='#FF8F00', label='Taxi cheaper zone')
    ax2.set_xlabel("Months", fontsize=10)
    ax2.set_ylabel("Total USD spent", fontsize=10)
    ax2.set_title("3-year cumulative cost", fontsize=11, fontweight='bold')
    ax2.legend(fontsize=8)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${x:,.0f}'))
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    fig.suptitle(
        f"{brand} {model} {car['year']}  ·  {daily_km:.0f} km/day  ·  Taxi ${taxi_per_km}/km",
        fontsize=12, fontweight='bold'
    )
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#FAFAFA')
    buf.seek(0)
    plt.close(fig)

    text = (
        f"📊 *Own Car vs Taxi — {brand} {model} {car['year']}*\n\n"
        f"🛣 Daily km: *{daily_km:.0f} km* ({monthly_km:,.0f} km/month)\n\n"
        f"🚗 *Own car:* ${monthly_car:,.0f}/month\n"
        f"  └ Depreciation: ${monthly_depr:,.0f}  ·  Fuel: ${monthly_fuel:,.0f}  ·  Maint: ${monthly_maint}\n\n"
        f"🚕 *Taxi ({taxi_per_km} USD/km):* ${monthly_taxi:,.0f}/month\n\n"
        f"{'✅' if winner == '🚗 Own car' else '💡'} *{winner} saves ${saving:,.0f}/month* (${saving*12:,.0f}/year)\n\n"
        f"_Depreciation rate: {depr_rate*100:.1f}%/year · Fuel: {fuel_l100}L/100km @ ${FUEL_PRICE_USD}/L_\n\n"
        "Type /start for a new prediction."
    )
    await update.message.reply_text(
        text, parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["/start", "/forecast", "/cancel"]], resize_keyboard=True),
    )
    await context.bot.send_photo(
        chat_id=update.effective_chat.id, photo=buf,
        caption=f"📊 {brand} {model} · {daily_km:.0f} km/day · own car vs taxi",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# /forecast  — Car value 3-year projection
# ═══════════════════════════════════════════════════════════════════════════════

async def forecast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    car = _last_car(context)
    if not car:
        await update.message.reply_text(
            "⚠️ Please run /start first to identify your car, then /forecast.",
        )
        return

    brand   = car["brand"]
    model   = car["model"]
    year    = car["year"]
    mileage = car["mileage"]
    price   = car.get("last_price")

    if not price:
        await update.message.reply_text("⚠️ No price data from last prediction. Run /start first.")
        return

    await update.message.reply_text("⏳ Building forecast from real market data…")

    # Get real monthly depreciation from DB
    monthly_rate = None
    try:
        r = requests.get(
            f"{DJANGO_URL}/api/cars/price-history/",
            params={"brand": brand, "model": model, "year": year,
                    "gear_type": car["gear_type"], "color": car["color"],
                    "mileage": mileage},
            timeout=10,
        )
        if r.status_code == 200:
            data = [d for d in r.json().get("data", []) if d.get("count", 0) >= 3
                    and d.get("price_at_mileage")]
            if len(data) >= 3:
                prices_hist = [d["price_at_mileage"] for d in data]
                n = len(prices_hist)
                x_mean = (n - 1) / 2
                y_mean = sum(prices_hist) / n
                slope  = sum((i - x_mean) * (p - y_mean) for i, p in enumerate(prices_hist)) / \
                         sum((i - x_mean) ** 2 for i in range(n))
                monthly_rate = slope / price   # fraction per month
    except Exception as e:
        logger.warning("Forecast history fetch failed: %s", e)

    if monthly_rate is None:
        ann_rate     = DEPRECIATION_RATES.get(brand, DEFAULT_DEPRECIATION)
        monthly_rate = -(ann_rate / 12)

    monthly_rate = max(-0.05, min(0, monthly_rate))  # cap: -5%/month max

    months    = list(range(37))
    projected = [round(price * (1 + monthly_rate) ** m) for m in months]
    ann_pct   = monthly_rate * 12 * 100

    # Chart
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor('#FAFAFA')
    ax.set_facecolor('#FAFAFA')

    ax.plot(months, projected, linewidth=2.5, color='#1565C0', zorder=3)
    ax.fill_between(months, projected, alpha=0.10, color='#1565C0')

    milestones = [6, 12, 24, 36]
    for m in milestones:
        val = projected[m]
        ax.scatter([m], [val], color='#1565C0', s=60, zorder=4)
        ax.annotate(f'${val:,}', xy=(m, val), xytext=(0, 12),
                    textcoords='offset points', ha='center',
                    fontsize=8.5, color='#1565C0', fontweight='bold')

    ax.axhline(price * 0.5, color='#C62828', linewidth=1, linestyle=':', alpha=0.5)
    ax.text(36.2, price * 0.5, '50% value', va='center', fontsize=7.5, color='#C62828')

    ax.set_xlabel("Months from today", fontsize=10)
    ax.set_ylabel("Estimated value (USD)", fontsize=10)
    ax.set_title(
        f"{brand} {model} {year} · Value Forecast\n"
        f"Based on {abs(ann_pct):.1f}% annual depreciation (real market data)",
        fontsize=11, fontweight='bold'
    )
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'${x:,.0f}'))
    ax.set_xlim(0, 38)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(True, alpha=0.2, linestyle='--')

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='#FAFAFA')
    buf.seek(0)
    plt.close(fig)

    val_1y = projected[12]
    val_2y = projected[24]
    val_3y = projected[36]
    loss_1y = price - val_1y

    text = (
        f"📉 *{brand} {model} {year} — Value Forecast*\n\n"
        f"💰 Today:      *${price:,}*\n"
        f"📅 6 months:  ${projected[6]:,}  (−${price - projected[6]:,})\n"
        f"📅 1 year:     ${val_1y:,}  (−${loss_1y:,}, {ann_pct:.1f}%)\n"
        f"📅 2 years:    ${val_2y:,}  (−${price - val_2y:,})\n"
        f"📅 3 years:    ${val_3y:,}  (−${price - val_3y:,})\n\n"
        f"📊 Annual depreciation: *{abs(ann_pct):.1f}%* "
        f"({'real data' if monthly_rate != -DEPRECIATION_RATES.get(brand, DEFAULT_DEPRECIATION)/12 else 'brand estimate'})\n\n"
        f"💡 Losing *${loss_1y:,}/year* — use /compare to see if taxi saves money."
    )
    await update.message.reply_text(
        text, parse_mode="Markdown",
        reply_markup=ReplyKeyboardMarkup([["/start", "/compare", "/cancel"]], resize_keyboard=True),
    )
    await context.bot.send_photo(
        chat_id=update.effective_chat.id, photo=buf,
        caption=f"📉 {brand} {model} {year} · 3-year value forecast",
    )


# ─────────────────────────────────────────────────────────────────────────────

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _cancel_jobs(context, update.effective_chat.id)
    await update.message.reply_text("❌ Cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# ─────────────────────────────────────────────────────────────────────────────

async def post_init(app):
    await app.bot.set_my_commands([
        BotCommand("start",    "🚗 Predict car price"),
        BotCommand("compare",  "🚕 Own car vs Taxi calculator"),
        BotCommand("forecast", "📉 3-year value forecast"),
        BotCommand("fotos",    "📸 Analyze car photos"),
        BotCommand("check",    "✅ Submit photos for analysis"),
        BotCommand("admin",    "🔧 Admin panel (auth required)"),
        BotCommand("cancel",   "❌ Cancel"),
    ])


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    price_conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            BRAND:   [MessageHandler(filters.TEXT & ~filters.COMMAND, get_brand)],
            MODEL:   [MessageHandler(filters.TEXT & ~filters.COMMAND, get_model)],
            YEAR:    [MessageHandler(filters.TEXT & ~filters.COMMAND, get_year)],
            MILEAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_mileage)],
            GEAR:    [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gear)],
            COLOR:   [MessageHandler(filters.TEXT & ~filters.COMMAND, get_color)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    photo_conv = ConversationHandler(
        entry_points=[CommandHandler("fotos", fotos_start)],
        states={
            COLLECTING_PHOTOS: [
                MessageHandler(filters.PHOTO, receive_photo),
                CommandHandler("check", check_command),
                CallbackQueryHandler(check_button, pattern="^check_now$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    compare_conv = ConversationHandler(
        entry_points=[CommandHandler("compare", compare_start)],
        states={
            COMPARE_KM:   [MessageHandler(filters.TEXT & ~filters.COMMAND, compare_get_km)],
            COMPARE_TAXI: [MessageHandler(filters.TEXT & ~filters.COMMAND, compare_get_taxi)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    admin_conv = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_start)],
        states={
            ADMIN_AUTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_check_password)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(price_conv)
    app.add_handler(photo_conv)
    app.add_handler(compare_conv)
    app.add_handler(admin_conv)
    app.add_handler(CommandHandler("forecast", forecast))
    # Catch "Check it" presses that arrive outside an active conversation
    app.add_handler(CallbackQueryHandler(check_button, pattern="^check_now$"))
    # Admin panel inline button callbacks
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^adm_"))

    logger.info("Bot started — polling.")
    app.run_polling()


if __name__ == "__main__":
    main()
