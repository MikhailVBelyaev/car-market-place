# Telegram Bot for Car Price Prediction
# This bot predicts the price of a Chevrolet Lacetti white based on year and mileage using a model hosted on Databricks.
# It uses the Telegram Bot API to interact with users and handle commands.
# Requirements:
# - Python 3.7+
# - python-telegram-bot library
# - requests library        
import os
import logging
import requests
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
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

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    chat_id = update.effective_chat.id

    context.user_data["brand"] = "Chevrolet"
    context.user_data["model"] = "Lacetti"

    logger.info(f"Start triggered for user {chat_id}")
    keyboard = ReplyKeyboardMarkup([['/start', '/cancel']], resize_keyboard=True)
    await update.message.reply_text(
        "🛠 In MVP version, we only support Chevrolet Lacetti white.\n\n🔝 Enter car year:",
        reply_markup=keyboard
    )
    return YEAR

async def get_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        year = int(update.message.text)
        logger.info(f"User {update.effective_chat.id} raw year input: {update.message.text}")
        if not (2000 <= year <= 2025):
            await update.message.reply_text("❌ Year must be between 2000 and 2025.")
            return YEAR

        context.user_data["year"] = year
        logger.info(f"User {update.effective_chat.id} entered year: {year}")
        await update.message.reply_text("Enter car mileage:")
        logger.debug(f"Transitioning to MILEAGE state for user {update.effective_chat.id}")
        return MILEAGE
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid year:")
        return YEAR

async def get_mileage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        mileage = int(update.message.text)
        logger.info(f"User {update.effective_chat.id} raw mileage input: {update.message.text}")
        if not (0 <= mileage <= 500000):
            await update.message.reply_text("❌ Mileage must be between 0 and 500000.")
            return MILEAGE

        context.user_data["mileage"] = mileage
        logger.info(f"User {update.effective_chat.id} entered mileage: {mileage}")

        payload = {
            "inputs": [
                {"year": context.user_data["year"], "mileage": mileage}
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

            await update.message.reply_text(
                f"💰 Predicted price: {int(rounded_price)} USD\n\nYou can type /start to make a new prediction.",
                reply_markup=ReplyKeyboardMarkup([['/start', '/cancel']], resize_keyboard=True)
            )
        else:
            logger.error(f"Databricks error: {response.text}")
            await update.message.reply_text("⚠️ Model error or still starting. Try again soon.")
        logger.debug(f"ConversationHandler.END for user {update.effective_chat.id}")
        return ConversationHandler.END
    except ValueError:
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
    context.user_data.clear()
    context.user_data["brand"] = "Chevrolet"
    context.user_data["model"] = "Lacetti"

    logger.info(f"New prediction requested via button by user {chat_id}")
    logger.info(f"Resetting conversation for user {chat_id}. Prompting for year again.")
    await context.bot.send_message(
        chat_id=chat_id,
        text="✅ Prediction completed. You can type /start to begin a new prediction.",
        reply_markup=ReplyKeyboardMarkup([['/start', '/cancel']], resize_keyboard=True)
    )
    return ConversationHandler.END

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
