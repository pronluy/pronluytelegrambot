# core/embeddings.py
# ─────────────────────────────────────────────────────────────────────────────
# Wraps Google's free text-embedding-004 model in a LangChain-compatible
# interface so ChromaDB can call it transparently during both ingestion
# (storing document chunks) and retrieval (embedding the user's query).
# ─────────────────────────────────────────────────────────────────────────────

import google.generativeai as genai
from langchain_core.embeddings import Embeddings
from typing import List
from config.settings import GEMINI_API_KEY, GEMINI_EMBEDDING_MODEL

# Configure the Gemini SDK once at module import time
genai.configure(api_key=GEMINI_API_KEY)


class GeminiEmbeddings(Embeddings):
    """
    LangChain-compatible embedding class backed by Google's text-embedding-004.

    text-embedding-004 produces 768-dimensional vectors and supports two
    task types we use here:
      - "retrieval_document"  → used when indexing PDF chunks into ChromaDB
      - "retrieval_query"     → used when embedding the user's search query
    Using the correct task type measurably improves retrieval accuracy.
    """

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a list of document chunks for storage in ChromaDB.
        Called once during PDF ingestion.
        """
        embeddings = []
        for text in texts:
            # task_type="retrieval_document" tells the model these are
            # passages to be stored, optimising their vector representation
            result = genai.embed_content(
                model=GEMINI_EMBEDDING_MODEL,
                content=text,
                task_type="retrieval_document",
            )
            embeddings.append(result["embedding"])
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single user query for similarity search against stored chunks.
        Called on every RAG-enabled question.
        """
        # task_type="retrieval_query" optimises the vector for search
        result = genai.embed_content(
            model=GEMINI_EMBEDDING_MODEL,
            content=text,
            task_type="retrieval_query",
        )
        return result["embedding"]
