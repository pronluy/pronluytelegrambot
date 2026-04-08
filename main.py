# main.py
# ─────────────────────────────────────────────────────────────────────────────
# Entry point. Wires all handlers to the Telegram Application and starts
# the polling loop. Run with:  python main.py
# ─────────────────────────────────────────────────────────────────────────────

import logging
import os

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

from config.settings import TELEGRAM_BOT_TOKEN
from bot.handlers import (
    start_handler,
    help_handler,
    schedule_handler,
    docs_handler,
    clear_handler,
    handle_any_file, # <--- នាំចូលឈ្មោះថ្មី
    message_handler,
    error_handler,
)

# ── Logging Setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),                    
        logging.FileHandler("study_bot.log", encoding="utf-8"), 
    ],
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

def main() -> None:
    logger.info("🚀 Starting Study Assistant Bot...")

    os.makedirs(os.path.join("data", "chroma_db"), exist_ok=True)

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # ── Register Command Handlers ─────────────────────────────────────────────
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("schedule", schedule_handler))
    app.add_handler(CommandHandler("docs", docs_handler))
    app.add_handler(CommandHandler("clear", clear_handler))

    # ── Register Message Handlers ─────────────────────────────────────────────
    # Universal handler for ANY document or photo
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, handle_any_file))

    # All regular text messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    # ── Global Error Handler ──────────────────────────────────────────────────
    app.add_error_handler(error_handler)

    # ── Start Polling ─────────────────────────────────────────────────────────
    logger.info("✅ Bot is running. Press Ctrl+C to stop.")
    app.run_polling(
        allowed_updates=["message"],
        drop_pending_updates=True,
    )

if __name__ == "__main__":
    main()