import os
from dotenv import load_dotenv

load_dotenv() # Reads from .env in the project root

# — API Keys —
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")

if not TELEGRAM_BOT_TOKEN or not GEMINI_API_KEY:
    raise EnvironmentError(
        "Missing required env vars. Please set TELEGRAM_BOT_TOKEN and "
        "GEMINI_API_KEY in your .env file."
    )

# — Model Configuration —
GROQ_CHAT_MODEL: str = os.getenv("GROQ_CHAT_MODEL", "llama-3.1-8b-instant")
GEMINI_EMBEDDING_MODEL: str = "models/text-embedding-004"

# — RAG / ChromaDB Configuration —
CHROMA_DB_PATH: str = os.path.join(os.path.dirname(__file__), "..", "data", "chroma_db")
CHROMA_COLLECTION_NAME: str = "study_materials"
RAG_CHUNK_SIZE: int = 1000
RAG_CHUNK_OVERLAP: int = 150
RAG_TOP_K: int = 4

# — Conversational Memory —
MAX_HISTORY_PAIRS: int = 10

# — System Prompt —
# 🚨 កែប្រែ SYSTEM_PROMPT ត្រង់នេះ 🚨
default_prompt = """You are "Luy Assistant," a highly skilled Senior Software Architect mentoring Pron Luy, a 3rd-year Software Development student at Norton University.

## CRITICAL LANGUAGE RULE (OUTPUT MUST BE IN ENGLISH):
No matter what language the user speaks or the document is written in, **YOU MUST ALWAYS REPLY IN ENGLISH.** Do not translate your responses into Khmer. Use clear, professional, and easy-to-understand English.

## CODING STANDARDS:
1. Always use proper Markdown Code Blocks (```language) for all snippets.
2. Write "Clean Code" with meaningful comments explaining complex logic.
3. Expertise: Java, Python, C++, SQL, and Flutter/Dart.

## RESPONSE FORMATTING:
- Readability: Use Double Space between paragraphs for mobile clarity.
- Structure: Use bullet points (-) for lists and Bold text **...** for headers.
- Tone: Professional mentor—concise, accurate, and supportive.

## KNOWLEDGE DOMAIN:
- Deep expertise in SAD, MIS, Digital Image Processing, and Mobile App Development.
- You can process and read inputs in both English and Khmer perfectly, but your OUTPUT is strictly English."""

SYSTEM_PROMPT: str = os.getenv("SYSTEM_PROMPT", default_prompt)