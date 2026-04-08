# bot/handlers.py
# ─────────────────────────────────────────────────────────────────────────────
# All Telegram Update handlers.
# ─────────────────────────────────────────────────────────────────────────────

import os
import io
import logging
import PyPDF2

from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode, ChatAction

from core.gemini_client import chat, clear_history
from core.rag_pipeline import list_ingested_documents

logger = logging.getLogger(__name__)

# ── /start ────────────────────────────────────────────────────────────────────
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_name = update.effective_user.first_name or "there"
    welcome_text = (
        f"👋 សួស្ដី {user_name}! ខ្ញុំជា **Study Assistant & Coding Tutor** របស់អ្នក។\n\n"
        "អ្វីដែលខ្ញុំអាចជួយបាន:\n\n"
        "📚 **Study Q&A** — សួរខ្ញុំពីមេរៀននានា\n"
        "💻 **Code Help** — ពន្យល់ និងសរសេរកូដ (Java, Python, Flutter)\n"
        "📄 **File Reader** — ផ្ញើ File (PDF, TXT, កូដ) ឬរូបភាពមក ខ្ញុំអាចអានបាន\n"
        "🗓 **Schedule Aware** — ខ្ញុំចងចាំកាលវិភាគរៀនរបស់អ្នក\n\n"
        "**Commands:**\n"
        "/help — មើលបញ្ជាផ្សេងៗ\n"
        "/clear — លុបការចងចាំចោល (Restart Chat)\n\n"
        "ផ្ញើសារ ឬទម្លាក់ File មកដើម្បីចាប់ផ្ដើម! 🚀"
    )
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)

# ── /help ─────────────────────────────────────────────────────────────────────
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "🤖 **Study Assistant — Command Reference**\n\n"
        "/start — ស្វាគមន៍\n"
        "/help — ជំនួយ\n"
        "/schedule — មើលកាលវិភាគរៀន\n"
        "/clear — លុបប្រវត្តិជជែក (Fresh start)\n\n"
        "**របៀបឱ្យខ្ញុំអាន File:**\n"
        "1️⃣ Forward ឬ ផ្ញើ File/រូបភាពចូលទីនេះ\n"
        "2️⃣ រង់ចាំខ្ញុំអាន (In-Memory) មួយភ្លែត\n"
        "3️⃣ សួរសំណួរទាក់ទងនឹង File នោះបានតែម្ដង!\n"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

# ── /schedule ─────────────────────────────────────────────────────────────────
async def schedule_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
        "💡 ខ្ញុំចាំកាលវិភាគនេះជានិច្ច!"
    )
    await update.message.reply_text(schedule_text, parse_mode=ParseMode.MARKDOWN)

# ── /docs ─────────────────────────────────────────────────────────────────────
async def docs_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    docs = list_ingested_documents()
    if not docs:
        await update.message.reply_text("📭 មិនមានឯកសារចាស់ៗក្នុង Database ទេ។")
    else:
        doc_list = "\n".join(f"  • {doc}" for doc in docs)
        await update.message.reply_text(
            f"📚 **ឯកសារក្នុង Database ({len(docs)}):**\n\n{doc_list}\n",
            parse_mode=ParseMode.MARKDOWN,
        )

# ── /clear ────────────────────────────────────────────────────────────────────
async def clear_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    clear_history(user_id)
    # លុបឯកសារ In-Memory ចោលដែរ
    if 'current_document' in context.user_data:
        del context.user_data['current_document']
        del context.user_data['doc_name']
        
    await update.message.reply_text("🧹 ខ្ញុំបានលុបការចងចាំ និង File លើអាកាសចោលអស់ហើយ!")

# ── Universal File Handler (In-Memory Processing) ─────────────────────────────
async def handle_any_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle ALL files & photos. Read them in-memory without saving to hard disk.
    """
    loading_msg = await update.message.reply_text("⏳ កំពុងវិភាគ File/រូបភាព លើអាកាស...")
    
    # Check if it's a document or a photo
    attachment = update.message.document or (update.message.photo[-1] if update.message.photo else None)
    
    if not attachment:
        await loading_msg.edit_text("❌ រកមិនឃើញ File ទេ។")
        return

    # Extract name and extension
    file_name = getattr(attachment, 'file_name', 'image.jpg')
    file_extension = file_name.split('.')[-1].lower()

    try:
        # Show "typing" action
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action=ChatAction.TYPING,
        )

        # Download to Memory (RAM)
        telegram_file = await context.bot.get_file(attachment.file_id)
        file_bytes = await telegram_file.download_as_bytearray()
        file_stream = io.BytesIO(file_bytes)
        
        extracted_text = ""

        # 1. Handle PDF
        if file_extension == 'pdf':
            reader = PyPDF2.PdfReader(file_stream)
            for page in reader.pages:
                text = page.extract_text()
                if text: 
                    extracted_text += text + "\n"

        # 2. Handle Text-based files
        elif file_extension in ['txt', 'csv', 'json', 'py', 'dart', 'html', 'md', 'sql']:
            extracted_text = file_bytes.decode('utf-8')
            
        # 3. Handle Images (Placeholder for future OCR)
        elif file_extension in ['jpg', 'jpeg', 'png']:
            extracted_text = "[ប្រព័ន្ធ OCR ចាប់អក្សរពីរូបភាព កំពុងស្ថិតក្នុងការអភិវឌ្ឍ។ ខ្ញុំឃើញថាវាជារូបភាព ប៉ុន្តែមិនទាន់អាចអានអក្សរលើវាបានទេឥឡូវនេះ។]"
            
        else:
            await loading_msg.edit_text(f"❌ បច្ចុប្បន្នខ្ញុំមិនទាន់គាំទ្រ File ប្រភេទ (.{file_extension}) ទេ។")
            return

        # Save to User's temporary context
        context.user_data['current_document'] = extracted_text
        context.user_data['doc_name'] = file_name

        await loading_msg.edit_text(
            f"✅ អាន File **{file_name}** ជោគជ័យ! (ទំហំអត្ថបទ: {len(extracted_text)} តួអក្សរ)\n\n"
            f"ឥឡូវប្អូនអាចសួរខ្ញុំពីទិន្នន័យនៅក្នុង File នេះបានហើយ។\n"
            f"*(បញ្ជាក់៖ File នេះស្ថិតនៅលើអាកាស បើផ្ញើ File ថ្មីមក វានឹងលុបអាលុបចាស់ចោល)*",
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info(f"In-Memory loaded '{file_name}' for user {update.effective_user.id}")

    except Exception as e:
        logger.error(f"Error reading file '{file_name}': {e}", exc_info=True)
        await loading_msg.edit_text(f"❌ មានបញ្ហាក្នុងការអាន File:\n{e}")

# ── Text Message Handler ──────────────────────────────────────────────────────
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_message = update.message.text.strip()

    if not user_message:
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING,
    )

    logger.info(f"User {user_id}: '{user_message[:80]}...'")

    # Combine user message with In-Memory Document if it exists
    final_prompt = user_message
    if 'current_document' in context.user_data:
        doc_text = context.user_data['current_document']
        doc_name = context.user_data.get('doc_name', 'Document')
        # Limit document text to ~15000 chars to avoid token limits
        final_prompt = f"យោងតាមឯកសារ '{doc_name}':\n{doc_text[:15000]}\n\nសូមឆ្លើយសំណួរខាងក្រោមផ្អែកលើឯកសារនេះ: {user_message}"

    # Get AI response
    reply = await chat(user_id, final_prompt)

    # Send the response safely
    if len(reply) <= 4096:
        try:
            await update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            await update.message.reply_text(reply)
    else:
        for i in range(0, len(reply), 4000):
            chunk = reply[i:i + 4000]
            try:
                await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
            except Exception:
                await update.message.reply_text(chunk)

# ── Error Handler ─────────────────────────────────────────────────────────────
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Unhandled exception: {context.error}", exc_info=context.error)
    if isinstance(update, Update) and update.message:
        await update.message.reply_text("⚠️ សូមអភ័យទោស! មានបញ្ហាបច្ចេកទេសបន្តិចបន្តួច។")