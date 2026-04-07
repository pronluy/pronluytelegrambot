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
    document_handler,
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
# Silence noisy libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("chromadb").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def main() -> None:
    """Build the Application, register all handlers, and start polling."""

    logger.info("🚀 Starting Study Assistant Bot...")

    # Ensure the data directory exists for ChromaDB
    os.makedirs(os.path.join("data", "chroma_db"), exist_ok=True)

    # Build the Telegram application
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # ── Register Command Handlers ─────────────────────────────────────────────
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("schedule", schedule_handler))
    app.add_handler(CommandHandler("docs", docs_handler))
    app.add_handler(CommandHandler("clear", clear_handler))

    # ── Register Message Handlers ─────────────────────────────────────────────
    # PDF documents — must be registered BEFORE the generic text handler
    app.add_handler(MessageHandler(filters.Document.PDF, document_handler))

    # All regular text messages (excludes commands, which are handled above)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    # ── Global Error Handler ──────────────────────────────────────────────────
    app.add_error_handler(error_handler)

    # ── Start Polling ─────────────────────────────────────────────────────────
    logger.info("✅ Bot is running. Press Ctrl+C to stop.")
    app.run_polling(
        allowed_updates=["message"],   # Only process message updates
        drop_pending_updates=True,     # Ignore messages sent while bot was offline
    )


if __name__ == "__main__":
    main()
