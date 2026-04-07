# config/settings.py
# ─────────────────────────────────────────────────────────────────────────────
# Central configuration: API keys, model names, RAG tuning, and the all-
# important SYSTEM PROMPT that injects your university schedule + persona.
# ─────────────────────────────────────────────────────────────────────────────

import os
from dotenv import load_dotenv

load_dotenv()  # Reads from .env in the project root

# ── API Keys ──────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "") # បន្ថែមបន្ទាត់នេះ

if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
    raise EnvironmentError(
        "Missing required env vars. Please set TELEGRAM_BOT_TOKEN and "
        "GEMINI_API_KEY in your .env file."
    )

# ── Model Configuration ───────────────────────────────────────────────────────
# gemini-2.5-flash is the latest model for chat
# យើងប្រើ Llama 3 70B ដែលជា Model កំពូលនិងឆ្លាតបំផុតរបស់ Meta
GROQ_CHAT_MODEL: str = "llama-3.3-70b-versatile"

# text-embedding-004 is Google's best free embedding model (768 dimensions)
GEMINI_EMBEDDING_MODEL: str = "models/text-embedding-004"

# ── RAG / ChromaDB Configuration ─────────────────────────────────────────────
CHROMA_DB_PATH: str = os.path.join(os.path.dirname(__file__), "..", "data", "chroma_db")
CHROMA_COLLECTION_NAME: str = "study_materials"

# Chunk size in characters — 1000 chars ≈ ~250 tokens, good balance for study docs
RAG_CHUNK_SIZE: int = 1000
# Overlap ensures context isn't lost at chunk boundaries
RAG_CHUNK_OVERLAP: int = 150
# How many chunks to retrieve for each query
RAG_TOP_K: int = 4

# ── Conversational Memory ─────────────────────────────────────────────────────
# Maximum number of past message PAIRS (user + assistant) to keep in memory.
# Prevents the context window from overflowing on long sessions.
MAX_HISTORY_PAIRS: int = 10

# ── System Prompt ─────────────────────────────────────────────────────────────
# This is injected into every conversation. Edit the SCHEDULE section freely.
# The {rag_context} placeholder is filled at runtime when relevant docs exist.
# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
You are 'Luy Assistant', a professional Software Mentor. Your goal is to provide responses that follow a CLEAN, PROFESSIONAL, and DOCUMENTATION-STYLE format.

## FORMATTING STANDARDS (CRITICAL)
1. HEADERS: Use # for Main Titles and ## for Sub-titles. 
2. ICON USAGE: Place ONLY ONE relevant icon at the start of each Header (e.g., # 🚀 Getting Started). DO NOT use icons inside the body text or lists.
3. BOLDING: Use **double asterisks** to highlight key technical terms or important notes.
4. CLEAN LISTS: 
   - Use Numbers (1., 2., 3.) for step-by-step instructions or sequences.
   - Use Simple Dashes (-) for general bullet points or features.
   - NO emojis as bullet points.
5. CODE BLOCKS: Use ```language blocks for all code. Provide full, working examples with comments.
6. LANGUAGE: Respond in a professional mix of Khmer and English. Use Khmer for explanations and English for technical terms.

## UNIVERSITY SCHEDULE (NORTON UNIVERSITY)
Monday: Web Development (Sou Sovichea)
Tuesday: Digital Image Processing (Ul Dara)
Wednesday: Free Day
Thursday: Advance Mobile Apps (Sok Piseth)
Friday: UX/UI Design (Suon Sivatha)
Saturday: MIS (Mork Ratha)

## TONE
- Be professional, structured, and clear. 
- Write like a Senior Developer documenting a project for a Junior.
"""