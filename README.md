# 📚 Study Assistant Telegram Bot

A **100% free** intelligent Telegram Bot that acts as your personal Study Assistant and Coding Tutor, powered by Google Gemini and a local RAG pipeline.

---

## ✨ Features

| Feature | Technology |
|---|---|
| Conversational Memory | Sliding-window history (in-process) |
| LLM Reasoning | Google Gemini 1.5 Flash (free tier) |
| PDF Memorisation | pdfplumber + ChromaDB RAG |
| Embeddings | Google text-embedding-004 (free) |
| Vector Search | ChromaDB (local, persistent) |
| Telegram Interface | python-telegram-bot v21 |

---

## 🗂 Project Structure

```
study_assistant_bot/
├── bot/
│   ├── __init__.py
│   └── handlers.py          # All Telegram command & message handlers
├── core/
│   ├── __init__.py
│   ├── gemini_client.py     # Gemini API + conversation memory
│   ├── rag_pipeline.py      # PDF ingestion + ChromaDB retrieval
│   └── embeddings.py        # Google Embeddings wrapper
├── config/
│   ├── __init__.py
│   └── settings.py          # Config, API keys, system prompt & schedule
├── data/
│   └── chroma_db/           # Auto-created persistent vector store
├── main.py                  # Entry point
├── requirements.txt
├── .env.example             # Copy to .env and fill in
└── study_bot.log            # Auto-created log file
```

---

## 🚀 Setup & Installation

### 1. Get Your API Keys (Both Free)

**Telegram Bot Token:**
1. Open Telegram and message [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the prompts
3. Copy the token provided

**Gemini API Key:**
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click "Create API Key"
3. Copy the key (free tier gives 15 RPM / 1M tokens/day for Flash)

### 2. Clone & Install

```bash
git clone <your-repo>
cd study_assistant_bot

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your keys
nano .env
```

```env
TELEGRAM_BOT_TOKEN=123456789:ABCdef...
GEMINI_API_KEY=AIzaSy...
```

### 4. Customise Your Schedule

Open `config/settings.py` and edit the markdown table in `SYSTEM_PROMPT` to match your actual timetable.

### 5. Run the Bot

```bash
python main.py
```

You should see:
```
2024-xx-xx | INFO     | __main__ — 🚀 Starting Study Assistant Bot...
2024-xx-xx | INFO     | __main__ — ✅ Bot is running. Press Ctrl+C to stop.
```

---

## 💬 Bot Commands

| Command | Description |
|---|---|
| `/start` | Welcome message and overview |
| `/help` | Show all commands |
| `/schedule` | View your university timetable |
| `/docs` | List all memorised PDFs |
| `/clear` | Reset conversation memory |

**PDF Upload:** Simply send any PDF file to the bot — it will automatically ingest it!

---

## 🔍 How the RAG Pipeline Works

```
User uploads PDF
      │
      ▼
┌─────────────────┐
│ Text Extraction │  pdfplumber (primary) → PyPDF2 (fallback)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Text Chunking   │  RecursiveCharacterTextSplitter
│                 │  chunk_size=1000, overlap=150
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Embeddings    │  Google text-embedding-004
│                 │  task_type="retrieval_document"
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    ChromaDB     │  Cosine similarity index
│  (local disk)   │  Persistent across restarts
└─────────────────┘

User asks a question
      │
      ▼
┌─────────────────┐
│  Embed Query    │  task_type="retrieval_query"
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Similarity      │  Top-4 most relevant chunks
│ Search          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Gemini + RAG    │  System Prompt + Context + History + Question
│ Context         │
└─────────────────┘
```

---

## ⚙️ Configuration Reference (`config/settings.py`)

| Setting | Default | Description |
|---|---|---|
| `GEMINI_CHAT_MODEL` | `gemini-1.5-flash` | LLM for conversation |
| `GEMINI_EMBEDDING_MODEL` | `text-embedding-004` | Embedding model |
| `RAG_CHUNK_SIZE` | `1000` | Characters per chunk |
| `RAG_CHUNK_OVERLAP` | `150` | Overlap between chunks |
| `RAG_TOP_K` | `4` | Chunks retrieved per query |
| `MAX_HISTORY_PAIRS` | `10` | Conversation turns remembered |

---

## 🔧 Troubleshooting

**"Could not extract text from PDF"**
→ The PDF is likely a scanned image. Use a text-layer PDF or run OCR first (e.g. Adobe Acrobat, OCRmyPDF).

**"Missing required env vars"**
→ Ensure your `.env` file exists in the project root and contains both keys.

**Bot not responding**
→ Check `study_bot.log` for errors. Common causes: expired API key, network issues.

**Gemini rate limit errors**
→ Free tier allows 15 requests/minute. If hit frequently, add a `time.sleep(1)` between rapid queries.

---

## 🆓 Cost Breakdown

| Service | Free Tier |
|---|---|
| Gemini 1.5 Flash | 15 RPM, 1M tokens/day, 1500 RPD |
| text-embedding-004 | 100 requests/minute |
| ChromaDB | Fully local, unlimited |
| python-telegram-bot | Free, open-source |

**Total monthly cost: $0.00** ✅
