# core/gemini_client.py
# ─────────────────────────────────────────────────────────────────────────────
# Manages:
#   1. The Groq API connection (replaces Gemini for faster, unlimited chatting)
#   2. Per-user conversational memory (sliding window of last N turns)
#   3. Prompt assembly — stitches together System Prompt + RAG context +
#      conversation history + current user message before each API call
# ─────────────────────────────────────────────────────────────────────────────

import logging
from typing import Optional
from groq import AsyncGroq # ប្រើប្រាស់ Library ថ្មីរបស់ Groq (Asynchronous)

from config.settings import (
    GROQ_API_KEY,      # ទាញយក Key ថ្មីពី settings
    GROQ_CHAT_MODEL,   # ទាញយកឈ្មោះ Model ថ្មី (llama3-70b-8192)
    SYSTEM_PROMPT,
    MAX_HISTORY_PAIRS,
)
from core.rag_pipeline import retrieve_context

logger = logging.getLogger(__name__)

# Initialize the Groq SDK with our API key
client = AsyncGroq(api_key=GROQ_API_KEY)

# ── Per-user memory store ─────────────────────────────────────────────────────
# Structure: { telegram_user_id (int) : [ {"role": str, "content": str}, ... ] }
# Each entry is a Groq-formatted message dict.
_conversation_histories: dict[int, list[dict]] = {}


def _get_history(user_id: int) -> list[dict]:
    """Return (or initialise) the conversation history for a user."""
    if user_id not in _conversation_histories:
        _conversation_histories[user_id] = []
    return _conversation_histories[user_id]


def _trim_history(history: list[dict]) -> list[dict]:
    """
    Keep only the most recent MAX_HISTORY_PAIRS message pairs.
    """
    max_messages = MAX_HISTORY_PAIRS * 2
    if len(history) > max_messages:
        return history[-max_messages:]
    return history


def clear_history(user_id: int) -> None:
    """Wipe conversation memory for a user (used by /clear command)."""
    _conversation_histories[user_id] = []
    logger.info(f"Cleared history for user {user_id}")


# ── Core Chat Function ────────────────────────────────────────────────────────
async def chat(user_id: int, user_message: str) -> str:
    """
    Send a message to Groq and return the assistant's reply.
    """
    history = _get_history(user_id)

    # ── Step 1: Check ChromaDB for relevant context ───────────────────────────
    rag_context = retrieve_context(user_message)

    # ── Step 2: Build the full prompt for this turn ───────────────────────────
    if rag_context:
        # RAG mode: inject document context
        full_user_message = (
            f"## RETRIEVED DOCUMENT CONTEXT\n"
            f"The following excerpts from your study materials are relevant "
            f"to the question. Use them as your primary source.\n\n"
            f"{rag_context}\n\n"
            f"---\n\n"
            f"## STUDENT'S QUESTION\n{user_message}"
        )
        logger.info(f"RAG context injected for user {user_id}")
    else:
        full_user_message = user_message

    # ── Step 3: Assemble message list for Groq ────────────────────────────────
    # Groq supports the "system" role natively!
    system_message = {"role": "system", "content": SYSTEM_PROMPT}

    # Build the full message list
    messages = [system_message] + history + [
        {"role": "user", "content": full_user_message}
    ]

    # ── Step 4: Call Groq ─────────────────────────────────────────────────────
    try:
        # Call the Groq chat completion API asynchronously
        chat_completion = await client.chat.completions.create(
            messages=messages,
            model=GROQ_CHAT_MODEL,
            temperature=0.7, # ធ្វើឱ្យចម្លើយមានភាពរស់រវើកនិងច្នៃប្រឌិត
        )
        reply = chat_completion.choices[0].message.content

    except Exception as e:
        logger.error(f"Groq API error for user {user_id}: {e}")
        reply = (
            "⚠️ I encountered an error connecting to the AI model. "
            "Please try again in a moment. If this persists, check your "
            "GROQ_API_KEY in the .env file."
        )

    # ── Step 5: Update conversation history ───────────────────────────────────
    # Save purely if it wasn't an error
    if "⚠️" not in reply:
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": reply}) # Groq uses 'assistant' not 'model'
        
        # Trim and save
        _conversation_histories[user_id] = _trim_history(history)

    return reply