# core/rag_pipeline.py
# ─────────────────────────────────────────────────────────────────────────────
# The RAG (Retrieval-Augmented Generation) pipeline has two distinct phases:
#
#  PHASE 1 — INGESTION (triggered when user sends a PDF)
#  ┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌───────────┐
#  │  PDF File   │───▶│ Text Extract │───▶│ Chunk / Split│───▶│ Embed &   │
#  │  on disk    │    │ (pdfplumber) │    │ (LangChain)  │    │ Store in  │
#  └─────────────┘    └──────────────┘    └──────────────┘    │ ChromaDB  │
#                                                              └───────────┘
#
#  PHASE 2 — RETRIEVAL (triggered on every user question)
#  ┌─────────────┐    ┌──────────────┐    ┌──────────────┐    ┌───────────┐
#  │ User Query  │───▶│ Embed Query  │───▶│ Similarity   │───▶│ Top-K     │
#  │             │    │ (Gemini)     │    │ Search       │    │ Chunks    │
#  └─────────────┘    └──────────────┘    │ (ChromaDB)   │    │ returned  │
#                                         └──────────────┘    └───────────┘
# ─────────────────────────────────────────────────────────────────────────────

import os
import logging
from typing import Optional

import pdfplumber
import PyPDF2
import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain.text_splitter import RecursiveCharacterTextSplitter

from core.embeddings import GeminiEmbeddings
from config.settings import (
    CHROMA_DB_PATH,
    CHROMA_COLLECTION_NAME,
    RAG_CHUNK_SIZE,
    RAG_CHUNK_OVERLAP,
    RAG_TOP_K,
)

logger = logging.getLogger(__name__)


# ── ChromaDB Client (singleton, persistent on disk) ───────────────────────────
def _get_chroma_client() -> chromadb.PersistentClient:
    """
    Returns a persistent ChromaDB client whose data survives bot restarts.
    The DB files live in data/chroma_db/ relative to the project root.
    """
    os.makedirs(CHROMA_DB_PATH, exist_ok=True)
    return chromadb.PersistentClient(
        path=CHROMA_DB_PATH,
        settings=ChromaSettings(anonymized_telemetry=False),
    )


# ── Text Extraction ───────────────────────────────────────────────────────────
def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract all text from a PDF file.

    Strategy:
      1. Try pdfplumber first — handles tables, multi-column layouts better.
      2. Fall back to PyPDF2 if pdfplumber yields nothing (e.g. scanned PDFs).
    """
    text = ""

    # Attempt 1: pdfplumber
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
        logger.info(f"pdfplumber extracted {len(text)} chars from {pdf_path}")
    except Exception as e:
        logger.warning(f"pdfplumber failed: {e}")

    # Attempt 2: PyPDF2 fallback
    if not text.strip():
        logger.info("Falling back to PyPDF2...")
        try:
            with open(pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n\n"
            logger.info(f"PyPDF2 extracted {len(text)} chars")
        except Exception as e:
            logger.error(f"PyPDF2 also failed: {e}")

    return text.strip()


# ── Document Ingestion (PHASE 1) ──────────────────────────────────────────────
def ingest_pdf(pdf_path: str, source_name: str) -> int:
    """
    Full ingestion pipeline for a single PDF file.

    Steps:
      1. Extract raw text from PDF.
      2. Split into overlapping chunks using LangChain's RecursiveCharacterTextSplitter.
         Recursive splitting tries to split on paragraph breaks → sentences →
         words → characters, keeping semantically coherent chunks.
      3. Embed each chunk using Gemini text-embedding-004.
      4. Store vectors + metadata in ChromaDB.

    Returns the number of chunks stored.
    Raises ValueError if no text could be extracted.
    """
    # Step 1: Extract text
    raw_text = extract_text_from_pdf(pdf_path)
    if not raw_text:
        raise ValueError(f"Could not extract any text from {pdf_path}. "
                         "The file may be a scanned image PDF.")

    # Step 2: Split into chunks
    # RecursiveCharacterTextSplitter is preferred for study material because:
    # - It respects natural paragraph/sentence boundaries
    # - Overlap ensures no fact is split awkwardly between two chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=RAG_CHUNK_SIZE,
        chunk_overlap=RAG_CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],  # Priority order of split points
    )
    chunks = splitter.split_text(raw_text)
    logger.info(f"Split '{source_name}' into {len(chunks)} chunks")

    if not chunks:
        raise ValueError("Text splitting produced no chunks.")

    # Step 3 & 4: Embed and store in ChromaDB
    embeddings_model = GeminiEmbeddings()
    client = _get_chroma_client()

    # get_or_create_collection is idempotent — safe to call on every ingestion
    collection = client.get_or_create_collection(
        name=CHROMA_COLLECTION_NAME,
        # cosine similarity is best for text semantic search
        metadata={"hnsw:space": "cosine"},
    )

    # Generate unique IDs for each chunk: "<source_name>_chunk_<index>"
    # Using the source name in the ID lets us delete a document's chunks later
    ids = [f"{source_name}_chunk_{i}" for i in range(len(chunks))]

    # Attach metadata to each chunk so we can cite the source in answers
    metadatas = [{"source": source_name, "chunk_index": i} for i in range(len(chunks))]

    # Compute embeddings for all chunks (batch)
    logger.info("Embedding chunks... (this may take a moment)")
    vectors = embeddings_model.embed_documents(chunks)

    # Upsert: add new or overwrite if same ID already exists
    # This means re-sending the same PDF is safe — it just refreshes the data
    collection.upsert(
        ids=ids,
        embeddings=vectors,
        documents=chunks,
        metadatas=metadatas,
    )

    logger.info(f"Stored {len(chunks)} chunks for '{source_name}' in ChromaDB")
    return len(chunks)


# ── Retrieval (PHASE 2) ───────────────────────────────────────────────────────
def retrieve_context(query: str) -> Optional[str]:
    """
    Retrieve the most relevant document chunks for a given user query.

    Steps:
      1. Embed the query using Gemini (task_type="retrieval_query").
      2. Run cosine-similarity search against all stored chunk vectors.
      3. Return the top-K chunks formatted as a context block for the LLM.

    Returns None if the ChromaDB collection is empty (no PDFs ingested yet).
    """
    client = _get_chroma_client()

    # Check if any documents have been ingested
    try:
        collection = client.get_collection(name=CHROMA_COLLECTION_NAME)
    except Exception:
        # Collection doesn't exist yet — no PDFs have been uploaded
        return None

    if collection.count() == 0:
        return None

    # Embed the user query
    embeddings_model = GeminiEmbeddings()
    query_vector = embeddings_model.embed_query(query)

    # Search ChromaDB for the top-K most similar chunks
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=min(RAG_TOP_K, collection.count()),  # Don't ask for more than we have
        include=["documents", "metadatas", "distances"],
    )

    if not results["documents"] or not results["documents"][0]:
        return None

    # Format retrieved chunks into a clean context block for the LLM prompt
    context_parts = []
    for i, (doc, meta) in enumerate(
        zip(results["documents"][0], results["metadatas"][0])
    ):
        source = meta.get("source", "Unknown")
        chunk_idx = meta.get("chunk_index", "?")
        context_parts.append(
            f"[Source: {source} | Chunk {chunk_idx}]\n{doc}"
        )

    context_block = "\n\n---\n\n".join(context_parts)
    logger.info(f"Retrieved {len(context_parts)} chunks for query: '{query[:60]}...'")
    return context_block


# ── Utility ───────────────────────────────────────────────────────────────────
def list_ingested_documents() -> list[str]:
    """
    Returns a deduplicated list of all document source names stored in ChromaDB.
    Used by the /docs command to show the user what's been memorised.
    """
    client = _get_chroma_client()
    try:
        collection = client.get_collection(name=CHROMA_COLLECTION_NAME)
    except Exception:
        return []

    if collection.count() == 0:
        return []

    # Fetch all metadata and extract unique source names
    all_items = collection.get(include=["metadatas"])
    sources = {meta["source"] for meta in all_items["metadatas"] if "source" in meta}
    return sorted(sources)
