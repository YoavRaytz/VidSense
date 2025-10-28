# 🎥 VidSense - AI-Powered Video Search & RAG System

A powerful FastAPI + React application for semantic video search with AI-generated answers. Ingest videos from social media, generate transcripts, and search with state-of-the-art retrieval and reranking.

## ✨ Features

### 🎬 Video Management
- **Multi-platform video ingestion** via `yt-dlp` (Instagram, YouTube, TikTok, etc.)
- **Automatic transcription** using Gemini 2.0 Flash
- **Video streaming** with adaptive quality and clip support
- **Transcript editing** with live preview

### � Advanced Search
- **Semantic search** using sentence-transformers embeddings (384-dim)
- **Two-stage retrieval**: Fast ANN search + Cross-encoder reranking
- **pgvector** for efficient vector similarity search
- **Cross-encoder reranking** with `ms-marco-MiniLM-L-6-v2`
- **Softmax score normalization** for interpretable relevance scores

### 🤖 RAG (Retrieval-Augmented Generation)
- **AI-powered answers** using Gemini with source citations
- **Markdown-formatted responses** with bold text, lists, and formatting
- **Clickable citations** that scroll to source videos
- **Context-aware answers** using top reranked resultsre’s a **concise, correct, copy-ready `README.md`** for your current repo.
It explains what it does, how to run it, and how to use it — without extra fluff or made-up parts.

---

````markdown
# 🎥 Video Search & Transcript Tool

A lightweight FastAPI + React app that lets you:

- Paste an Instagram (or any video) URL  
- Preview and play the video  
- Generate a transcript using **Gemini**  
- Edit and save the transcript to a **PostgreSQL** database  

---

## 🏗️ Architecture

### Backend Stack
- **FastAPI** - High-performance async API
- **PostgreSQL** with **pgvector** - Vector database for embeddings
- **sentence-transformers** - Embedding generation (`all-MiniLM-L6-v2`)
- **transformers** - Cross-encoder reranking (`ms-marco-MiniLM-L-6-v2`)
- **Gemini API** - Transcription & answer generation
- **yt-dlp** - Multi-platform video download
- **GStreamer** - Video remuxing & processing

### Frontend Stack
- **React + TypeScript** - Type-safe UI components
- **Vite** - Fast development & building
- **react-markdown** - Rich text formatting for AI answers

### Search Pipeline
1. **Query Embedding**: Convert search query to 384-dim vector
2. **ANN Search**: Fast approximate nearest neighbor search (k=20-50)
3. **Reranking**: Cross-encoder scores query-document pairs
4. **Softmax Normalization**: Convert logits to probabilities
5. **RAG Generation**: Gemini generates answer with citations

---

## ⚙️ Setup

### 1️⃣ Backend (FastAPI)

**Requirements**
- Python ≥ 3.10  
- PostgreSQL 15+ with **pgvector extension**
- [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) installed  
- `gst-launch-1.0` (GStreamer)  
- Gemini API key (`GEMINI_API_KEY`)

**Install pgvector**
```bash
# Ubuntu/Debian
sudo apt install postgresql-15-pgvector

# macOS
brew install pgvector

# Then in psql:
CREATE EXTENSION vector;
```

**Setup**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp env.example .env
```

**Example `.env`**

```
DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/video_db
GEMINI_API_KEY=your_gemini_key
YTDLP_BIN=yt-dlp
YTDLP_COOKIES=chrome:Default
GST_BIN=gst-launch-1.0
TMP_DIR=/tmp/app-videos
```

**Run**

```bash
cd backend
PYTHONPATH="$PWD/.." uvicorn app.main:app --reload --reload-dir app --port 8080 --env-file ../.env
```

API: [http://127.0.0.1:8080](http://127.0.0.1:8080)  
API Docs: [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs)

---

### 2️⃣ Frontend (React + Vite)

**Requirements**

* Node ≥ 18

**Setup**

```bash
cd frontend
npm install
npm run dev -- --host --port 5173
```

App: [http://localhost:5173](http://localhost:5173)

---

## 🧩 Main Workflows

### 1️⃣ Video Ingestion
1. Navigate to **Ingest** page
2. Paste video URL (Instagram, YouTube, etc.)
3. Click **Open** → fetch & preview video
4. Click **Get Transcript** → AI generates transcript
5. Edit transcript if needed
6. Click **Save to DB** → stores with embeddings

### 2️⃣ Semantic Search
1. Navigate to **Search** page
2. Enter natural language query (e.g., "shoulder pain exercises")
3. View ranked results with relevance scores
4. Click any result to view full video + transcript

### 3️⃣ RAG Question Answering
1. Enter question in search box
2. Click **Generate AI Answer**
3. View markdown-formatted answer with citations
4. Click citations `[1]`, `[2]` to jump to source videos
5. Watch source videos and read transcripts

---

## 🧠 API Endpoints

### Video Management
| Method | Endpoint                           | Description                    |
| ------ | ---------------------------------- | ------------------------------ |
| `POST` | `/videos/ingest_url`               | Register new video by URL      |
| `GET`  | `/videos/`                         | List all videos                |
| `GET`  | `/videos/{id}/meta`                | Get video metadata             |
| `GET`  | `/videos/{id}/stream`              | Stream video (MP4)             |
| `POST` | `/videos/{id}:generate_transcript` | Generate transcript w/ Gemini  |
| `GET`  | `/videos/{id}/transcript`          | Get transcript text            |
| `PUT`  | `/videos/{id}/transcript`          | Update transcript text         |

### Search & RAG
| Method | Endpoint         | Description                           |
| ------ | ---------------- | ------------------------------------- |
| `POST` | `/search/query`  | Semantic search with reranking        |
| `POST` | `/search/rag`    | RAG: Search + generate answer         |
| `POST` | `/embeddings`    | Generate embeddings for text          |

---

## 🧱 Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py                      # FastAPI app & router setup
│   │   ├── routes_ingest.py             # Video ingestion endpoints
│   │   ├── routes_search.py             # Search & RAG endpoints
│   │   ├── embeddings.py                # Sentence-transformers embeddings
│   │   ├── reranker.py                  # Cross-encoder reranking
│   │   ├── stream_utils.py              # Video processing & streaming
│   │   ├── transcribe/gemini_client.py  # Gemini API client
│   │   ├── models.py                    # SQLAlchemy models
│   │   ├── db.py                        # Database connection
│   │   ├── schemas.py                   # Pydantic schemas
│   │   └── sql/
│   │       └── create_vector_indexes.sql
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── IngestPage.tsx           # Video upload & transcription
│   │   │   ├── SearchPage.tsx           # Search & RAG interface
│   │   │   └── VideosPage.tsx           # Video library
│   │   ├── components/
│   │   │   ├── VideoPlayer.tsx          # Video playback
│   │   │   └── TranscriptViewer.tsx     # Transcript display/edit
│   │   ├── api.ts                       # API client
│   │   ├── App.tsx                      # Main app & routing
│   │   └── main.tsx                     # Entry point
│   ├── vite.config.ts
│   └── package.json
└── README.md
```

---

## 🔬 Technical Details

### Embedding Model
- **Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Dimensions**: 384
- **Approach**: Mean pooling of token embeddings
- **Storage**: pgvector with cosine distance

### Reranking Model
- **Model**: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **Type**: BERT-based sequence classification
- **Output**: Raw logits (typically -15 to +15)
- **Normalization**: Softmax for probability distribution
- **Context**: Combines title + description + transcript
- **Smart extraction**: Finds query terms, sends 4000-char windows

### RAG Pipeline
1. **Retrieve**: Get top-k documents via ANN + reranking
2. **Context**: Combine titles, descriptions, transcripts
3. **Prompt**: System prompt + context + user query
4. **Generate**: Gemini 2.0 Flash with temperature 0.3
5. **Citations**: Parse and link `[1]`, `[2]` references

---

## 🧰 Troubleshooting

### Video Issues
* **Empty MP4 after remux:**  
  Ensure GStreamer is installed: `sudo apt install gstreamer1.0-tools gstreamer1.0-plugins-good`

* **Instagram videos fail:**  
  Update cookies: `YTDLP_COOKIES=chrome:Default` or export cookies.txt

* **Video won't play:**  
  Check browser console. Some videos need specific codecs.

### Search Issues
* **Poor search results:**  
  - Ensure embeddings are generated (check `transcript_embedding` column)
  - Try different query phrasing
  - Check pgvector indexes are created

* **Reranker errors:**  
  - First run downloads model (~90MB) - check internet connection
  - Ensure sufficient memory for transformer models

* **Citations broken:**  
  - Check that `ragResponse.sources` matches citation numbers
  - Verify Gemini returns proper `[1]`, `[2]` format

### Database Issues
* **pgvector extension missing:**  
  ```sql
  CREATE EXTENSION IF NOT EXISTS vector;
  ```

* **Connection refused:**  
  Verify `DATABASE_URL` in `.env` matches PostgreSQL config

* **Slow vector search:**  
  Create HNSW index (automatically done on startup):
  ```sql
  CREATE INDEX IF NOT EXISTS transcript_embedding_idx 
  ON transcripts USING hnsw (embedding vector_cosine_ops);
  ```

---

## 🚀 Performance Tips

1. **ANN Search**: Adjust `k_ann` (default 50) for speed/accuracy tradeoff
2. **Reranking**: Adjust `k_final` (default 10) for final results
3. **Embeddings**: Batch generate for multiple videos
4. **Caching**: Models are lazy-loaded and cached with `@lru_cache`
5. **Database**: Use connection pooling for concurrent requests

---

## 🪄 Future Enhancements

- [ ] Multi-modal search (visual + text)
- [ ] Video carousel/clip support
- [ ] User accounts & saved searches
- [ ] Custom embedding models
- [ ] Hybrid search (keyword + semantic)
- [ ] Real-time transcription
- [ ] Video summarization
- [ ] Export search results

---

## � Example Queries

**Search Examples:**
- "shoulder pain exercises"
- "LinkedIn tips for software engineers"
- "what makes my ear hurt"
- "productivity advice"

**RAG Examples:**
- "How can I improve my LinkedIn profile?"
- "What exercises help with shoulder pain?"
- "Give me tips for better sleep"

---

## 🤝 Contributing

Contributions welcome! Areas of interest:
- New embedding models
- Alternative reranking strategies
- UI/UX improvements
- Performance optimizations
- Documentation

---

## �📜 License

MIT © 2025  
Developed by Yoav Raytsfeld

---

## 🙏 Acknowledgments

- **sentence-transformers** - Embedding models
- **Hugging Face** - Cross-encoder models
- **pgvector** - Vector database extension
- **Gemini API** - Transcription & generation
- **yt-dlp** - Universal video downloader

```

---

✅ You can copy this directly into your root `README.md`.  
It’s short, accurate to your current code, and GitHub-ready.
```
