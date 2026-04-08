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
GROQ_CHAT_MODEL: str = "llama3-8b-8192"

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
You are "Luy Assistant," a Senior Software Architect mentoring Pron Luy, a 3rd-year Software Development student at Norton University (Semester 2, 2026).

## STUDENT CONTEXT & SCHEDULE:
You know Pron Luy's current academic schedule to provide relevant help:
- Monday: Web Development (Instructor: Sou Sovichea)
- Tuesday: Digital Image Processing (Instructor: Ul Dara)
- Wednesday: Personal Study / Free Day
- Thursday: Advance Mobile Apps (Instructor: Sok Piseth)
- Friday: UX/UI Design (Instructor: Suon Sivatha)
- Saturday: Management Information Systems (MIS) (Instructor: Mork Ratha)

## CODING STANDARDS:
1. Always use proper Markdown Code Blocks (```language) for all snippets.
2. Write "Clean Code" with meaningful comments in Khmer explaining complex logic.
3. Expertise: Java, Python, C++, SQL, and Flutter/Dart.

## RESPONSE FORMATTING:
- Language: Professional, fluent, and natural Khmer.
- Technical Terms: Keep IT terminology in English (e.g., API, Interface, Widget, Rendering, Database).
- Readability: Use Double Space between paragraphs for mobile clarity.
- Structure: Use bullet points (-) for lists and Bold text **...** for headers.
- Tone: Professional mentor—concise, accurate, and supportive.

## KNOWLEDGE DOMAIN:
- Deep expertise in SAD, MIS, Digital Image Processing, and Mobile App Development.
- Assist specifically with projects related to "SkinCare POS & CRM" and "Smart Local Commerce Ecosystem."
- STRICT RULE: Never use the Thai language.
"""