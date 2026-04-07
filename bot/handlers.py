# bot/handlers.py
# ─────────────────────────────────────────────────────────────────────────────
# All Telegram Update handlers. Each handler corresponds to one user action:
#   /start        → welcome message
#   /help         → command reference
#   /clear        → wipe conversation memory
#   /schedule     → show the student's timetable
#   /docs         → list memorised PDFs
#   PDF upload    → trigger RAG ingestion pipeline
#   Text message  → route to Gemini chat (with RAG if docs exist)
# ─────────────────────────────────────────────────────────────────────────────

import os
import logging
import asyncio
import tempfile

import aiofiles
from telegram import Update, Document
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction

from core.gemini_client import chat, clear_history
from core.rag_pipeline import ingest_pdf, list_ingested_documents

logger = logging.getLogger(__name__)


# ── /start ────────────────────────────────────────────────────────────────────
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a rich welcome message explaining the bot's capabilities."""
    user_name = update.effective_user.first_name or "there"
    welcome_text = (
        f"👋 Hey {user_name}! I'm your personal **Study Assistant & Coding Tutor**.\n\n"
        "Here's what I can do:\n\n"
        "📚 **Study Q&A** — Ask me anything about your courses\n"
        "💻 **Code Help** — Explain, debug, or write code with you\n"
        "📄 **PDF Memory** — Send me a PDF and I'll memorise it for future Q&A\n"
        "🗓 **Schedule Aware** — I know your university timetable\n\n"
        "**Commands:**\n"
        "/help — Show all commands\n"
        "/schedule — View your timetable\n"
        "/docs — List memorised documents\n"
        "/clear — Reset our conversation\n\n"
        "Just send me a message or drop a PDF to get started! 🚀"
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)


# ── /help ─────────────────────────────────────────────────────────────────────
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "🤖 **Study Assistant — Command Reference**\n\n"
        "/start — Welcome message & overview\n"
        "/help — This help message\n"
        "/schedule — Display your university timetable\n"
        "/docs — Show all PDFs I've memorised\n"
        "/clear — Wipe conversation memory (fresh start)\n\n"
        "**How to use PDF RAG:**\n"
        "1️⃣ Send any PDF file in this chat\n"
        "2️⃣ Wait for the ✅ confirmation\n"
        "3️⃣ Ask questions — I'll answer from the document!\n\n"
        "**Tips:**\n"
        "• Be specific in your questions for better answers\n"
        "• I remember our last 10 exchanges per session\n"
        "• Re-uploading a PDF refreshes its content in memory"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


# ── /schedule ─────────────────────────────────────────────────────────────────
async def schedule_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the hardcoded timetable in a readable format."""
    schedule_text = (
        "🗓 **Your University Schedule**\n\n"
        "```\n"
        "MON  08:00-10:00  Data Structures & Algorithms\n"
        "MON  13:00-15:00  Database Systems\n"
        "TUE  10:00-12:00  Operating Systems\n"
        "WED  08:00-10:00  Data Structures & Algorithms\n"
        "WED  14:00-16:00  Web Development (Frontend)\n"
        "THU  10:00-12:00  Machine Learning Fundamentals\n"
        "THU  13:00-15:00  Database Systems\n"
        "FRI  09:00-11:00  Software Engineering Principles\n"
        "```\n\n"
        "💡 I keep this schedule in mind when helping you study!"
    )
    await update.message.reply_text(schedule_text, parse_mode=ParseMode.MARKDOWN)


# ── /docs ─────────────────────────────────────────────────────────────────────
async def docs_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all documents currently stored in ChromaDB."""
    docs = list_ingested_documents()
    if not docs:
        await update.message.reply_text(
            "📭 No documents memorised yet.\n\n"
            "Send me a PDF file and I'll ingest it into my knowledge base!"
        )
    else:
        doc_list = "\n".join(f"  • {doc}" for doc in docs)
        await update.message.reply_text(
            f"📚 **Memorised Documents ({len(docs)} total):**\n\n{doc_list}\n\n"
            "Ask me anything about these materials!",
            parse_mode=ParseMode.MARKDOWN,
        )


# ── /clear ────────────────────────────────────────────────────────────────────
async def clear_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clear conversation history for this user."""
    user_id = update.effective_user.id
    clear_history(user_id)
    await update.message.reply_text(
        "🧹 Conversation memory cleared!\n\n"
        "I've forgotten our chat history but still remember all your uploaded PDFs. "
        "What would you like to study?"
    )


# ── PDF Upload Handler ────────────────────────────────────────────────────────
async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle PDF file uploads from the user.

    Flow:
      1. Validate the file is a PDF.
      2. Send a "processing" status message to the user.
      3. Download the file from Telegram's servers to a temp directory.
      4. Run the RAG ingestion pipeline (extract → chunk → embed → store).
      5. Clean up the temp file.
      6. Report success or failure back to the user.
    """
    doc: Document = update.message.document

    # Step 1: Validate file type
    if doc.mime_type != "application/pdf":
        await update.message.reply_text(
            "⚠️ I can only process **PDF** files.\n"
            "Please convert your document to PDF and send it again.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    file_name = doc.file_name or f"document_{doc.file_id}.pdf"
    # Sanitise the filename for use as a ChromaDB source identifier
    source_name = os.path.splitext(file_name)[0].replace(" ", "_")

    # Step 2: Acknowledge receipt
    status_msg = await update.message.reply_text(
        f"📥 Received **{file_name}**\n\n"
        "⏳ Processing... I'm reading and memorising this document. "
        "This may take 30-60 seconds depending on file size.",
        parse_mode=ParseMode.MARKDOWN,
    )

    # Show "typing" action while we work
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING,
    )

    # Step 3: Download from Telegram to a temporary file
    tmp_path = None
    try:
        # Create a named temp file that persists until we explicitly delete it
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name

        telegram_file = await context.bot.get_file(doc.file_id)
        await telegram_file.download_to_drive(custom_path=tmp_path)
        logger.info(f"Downloaded '{file_name}' to {tmp_path}")

        # Step 4: Run ingestion pipeline (blocking — run in thread to avoid
        # blocking the asyncio event loop during embedding API calls)
        chunk_count = await asyncio.get_event_loop().run_in_executor(
            None, ingest_pdf, tmp_path, source_name
        )

        # Step 5: Success feedback
        await status_msg.edit_text(
            f"✅ **{file_name}** memorised!\n\n"
            f"📊 Processed into **{chunk_count} searchable chunks**.\n\n"
            "You can now ask me questions about this document and I'll answer "
            "directly from its content. Try it!",
            parse_mode=ParseMode.MARKDOWN,
        )
        logger.info(f"Successfully ingested '{source_name}' ({chunk_count} chunks)")

    except ValueError as ve:
        # PDF text extraction failed (e.g. scanned image PDF)
        logger.error(f"Ingestion ValueError for '{file_name}': {ve}")
        await status_msg.edit_text(
            f"❌ **Could not read '{file_name}'**\n\n"
            f"Reason: {str(ve)}\n\n"
            "This usually happens with scanned/image-only PDFs. "
            "Try a text-based PDF instead.",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logger.error(f"Unexpected error ingesting '{file_name}': {e}", exc_info=True)
        await status_msg.edit_text(
            f"❌ An unexpected error occurred while processing **{file_name}**.\n"
            "Please try again or contact support.",
            parse_mode=ParseMode.MARKDOWN,
        )
    finally:
        # Step 6: Always clean up the temp file
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
            logger.info(f"Cleaned up temp file: {tmp_path}")


# ── Text Message Handler ──────────────────────────────────────────────────────
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle all regular text messages — the main chat interface.

    Sends a "typing" action, calls Gemini (with automatic RAG lookup),
    and returns the formatted response.
    """
    user_id = update.effective_user.id
    user_message = update.message.text.strip()

    if not user_message:
        return

    # Show typing indicator while waiting for Gemini
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING,
    )

    logger.info(f"User {user_id}: '{user_message[:80]}...'")

    # Get AI response (RAG is automatically triggered inside chat() if relevant)
    reply = await chat(user_id, user_message)

    # Send the response — use Markdown for code blocks, bold, etc.
    # Split long messages if they exceed Telegram's 4096 char limit
   # Send the response — with a fallback for Telegram Markdown errors
    if len(reply) <= 4096:
        try:
            await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            # បើ Telegram អាន Markdown មិនដាច់ វាទម្លាក់មកជាអក្សរធម្មតាវិញ
            await update.message.reply_text(reply)
    else:
        # សម្រាប់សារដែលវែងពេក
        for i in range(0, len(reply), 4000):
            chunk = reply[i:i + 4000]
            try:
                await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
            except Exception:
                await update.message.reply_text(chunk)

# ── Error Handler ─────────────────────────────────────────────────────────────
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log all unhandled exceptions so they don't silently disappear."""
    logger.error(f"Unhandled exception: {context.error}", exc_info=context.error)
    if isinstance(update, Update) and update.message:
        await update.message.reply_text(
            "⚠️ Something went wrong on my end. Please try again!"
        )
