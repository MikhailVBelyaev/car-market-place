import os
import logging
import requests
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
    CallbackQueryHandler
)

# --- Logging Setup ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Environment Variables ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABRICKS_URL = os.getenv("DATABRICKS_URL")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")

YEAR, MILEAGE = range(2)
user_data = {}

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Handle both command and callback cases
    if update.message:
        chat_id = update.effective_chat.id
    elif update.callback_query:
        chat_id = update.callback_query.message.chat.id
    else:
        logger.error("Unknown update type in start()")
        return ConversationHandler.END

    user_data[chat_id] = {
        "brand": "Chevrolet",
        "model": "Lacetti"
    }
    logger.info(f"Start triggered for user {chat_id}")
    await context.bot.send_message(
        chat_id=chat_id,
        text="🛠 In MVP version, we only support Chevrolet Lacetti.\n\n👉 Enter car year:"
    )
    return YEAR

async def get_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        year = int(update.message.text)
        user_data[update.effective_chat.id]["year"] = year
        logger.info(f"User {update.effective_chat.id} entered year: {year}")
        await update.message.reply_text("Enter car mileage:")
        return MILEAGE
    except ValueError:
        logger.warning(f"Invalid year input from user {update.effective_chat.id}")
        await update.message.reply_text("❌ Please enter a valid year:")
        return YEAR

async def get_mileage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        mileage = int(update.message.text)
        data = user_data[update.effective_chat.id]
        data["mileage"] = mileage
        logger.info(f"User {update.effective_chat.id} entered mileage: {mileage}")

        payload = {
            "inputs": [
                {"year": data["year"], "mileage": data["mileage"]}
            ]
        }
        headers = {
            "Authorization": f"Bearer {DATABRICKS_TOKEN}",
            "Content-Type": "application/json"
        }

        logger.debug(f"Sending request to Databricks: {payload}")
        response = requests.post(DATABRICKS_URL, json=payload, headers=headers)

        if response.status_code == 200:
            prediction = response.json()["predictions"][0]
            rounded_price = round(prediction, -2)
            logger.info(f"Predicted price: {rounded_price} for user {update.effective_chat.id}")

            keyboard = [[InlineKeyboardButton("🔁 New Prediction", callback_data="new_prediction")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"💰 Predicted price: {int(rounded_price)} USD",
                reply_markup=reply_markup
            )
        else:
            logger.error(f"Databricks error: {response.text}")
            await update.message.reply_text("⚠️ Model error or still starting. Try again soon.")
        return ConversationHandler.END
    except ValueError:
        logger.warning(f"Invalid mileage input from user {update.effective_chat.id}")
        await update.message.reply_text("❌ Please enter a valid mileage:")
        return MILEAGE

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.effective_chat.id} canceled the conversation.")
    await update.message.reply_text("❌ Cancelled.")
    return ConversationHandler.END

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat.id
    user_data[chat_id] = {
        "brand": "Chevrolet",
        "model": "Lacetti"
    }

    logger.info(f"New prediction requested via button by user {chat_id}")
    await context.bot.send_message(
        chat_id=chat_id,
        text="🛠 In MVP version, we only support Chevrolet Lacetti.\n\n👉 Enter car year:"
    )

    # ✅ This line is critical to restart the conversation flow
    return YEAR

# --- Main ---
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            YEAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_year)],
            MILEAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_mileage)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )

    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(button_handler, pattern="new_prediction"))
    logger.info("Bot started.")
    app.run_polling()

if __name__ == "__main__":
    main()