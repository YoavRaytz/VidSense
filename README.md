# 🎥 VidSense - AI-Powered Video Search & RAG System

A powerful FastAPI + React application for semantic video search with AI-generated answers. Ingest videos from social media, generate transcripts, and search with state-of-the-art retrieval and reranking.

---

## ��️ Microservices Architecture

VidSense now uses a **microservices architecture** with Docker Compose orchestration for improved scalability, maintainability, and development workflow.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│                     Vite Dev Server :5173                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                    API Gateway (Nginx)                       │
│                    Routes: /api/* :80                        │
└──┬────────┬─────────┬──────────┬──────────┬────────────────┘
   │        │         │          │          │
   │        │         │          │          │
┌──▼────┐ ┌▼─────┐  ┌▼──────┐  ┌▼──────┐  ┌▼──────────┐
│Ingest │ │Search│  │Stream │  │Collec │  │Transcribe │
│:8081  │ │:8082 │  │:8083  │  │:8084  │  │Worker     │
└───┬───┘ └──┬───┘  └───┬───┘  └───┬───┘  └─────┬─────┘
    │        │          │          │             │
    └────────┴──────────┴──────────┴─────────────┤
                                                  │
    ┌─────────────────────────────────────────────┤
    │                                             │
┌───▼────────┐  ┌──────────┐  ┌─────────────┐   │
│PostgreSQL  │  │  Redis   │  │  Embedding  │   │
│+pgvector   │  │  :6379   │  │  Worker     │◄──┘
│:5432       │  │          │  │             │
└────────────┘  └──────────┘  └─────────────┘
```

### Services Overview

#### **Frontend Service** (Port 5173)
- React + TypeScript + Vite with HMR
- Proxies API requests to gateway

#### **API Gateway** (Port 80)
- Nginx reverse proxy
- Routes `/api/*` to appropriate microservices

#### **Ingestion Service** (Port 8081)
- Video URL ingestion and metadata extraction
- Video download, remuxing, and storage
- Coordinates transcript generation

#### **Search Service** (Port 8082)
- Semantic search with pgvector
- Cross-encoder reranking
- RAG answer generation with Gemini

#### **Streaming Service** (Port 8083)
- Video streaming with range requests
- Multi-clip playback support

#### **Collections Service** (Port 8084)
- Manage saved search collections
- CRUD operations for collections

#### **Transcription Worker** (Celery)
- Async video transcription with Gemini
- Background task processing

#### **Embedding Worker** (Celery)
- Vector embedding generation
- Batch processing for search indexing

#### **Redis** (Port 6379)
- Celery task queue and broker

#### **PostgreSQL + pgvector** (Port 5432)
- Stores video metadata, transcripts, embeddings
- Vector similarity search

### Docker Compose Quick Start

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# View specific service
docker-compose logs -f ingestion-service

# Restart a service
docker-compose restart search-service

# Rebuild after code changes
docker-compose up --build ingestion-service

# Stop all services
docker-compose down
```

### Environment Configuration

Create a `.env` file in the root:

```bash
# Database
DATABASE_URL=postgresql+psycopg://tips:tips123@postgres:5432/tipsdb

# Gemini API
GEMINI_API_KEY=your_gemini_api_key_here

# Redis
REDIS_URL=redis://redis:6379/0

# Models (optional - defaults provided)
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
GEMINI_MODEL=gemini-2.0-flash-exp

# yt-dlp cookies (optional)
# YTDLP_COOKIES=chrome
```

### Access Points

- **Frontend**: http://localhost:5173
- **API Gateway**: http://localhost/api/*
- **Ingestion API**: http://localhost:8081
- **Search API**: http://localhost:8082
- **Streaming API**: http://localhost:8083
- **Collections API**: http://localhost:8084

---

## ✨ Features

### 🎬 Video Management
- **Multi-platform video ingestion** via `yt-dlp` (Instagram, YouTube, TikTok, etc.)
- **Automatic transcription** using Gemini 2.0 Flash
- **Video streaming** with adaptive quality and clip support
- **Transcript editing** with live preview
- **Metadata extraction** (author, description, hashtags, likes, views, comments)

### 🔍 Advanced Search
- **Semantic search** using sentence-transformers embeddings (384-dim)
- **Two-stage retrieval**: Fast ANN search + Cross-encoder reranking
- **pgvector** for efficient vector similarity search
- **Cross-encoder reranking** with `ms-marco-MiniLM-L-6-v2`
- **Softmax score normalization** for interpretable relevance scores

### 🤖 RAG (Retrieval-Augmented Generation)
- **AI-powered answers** using Gemini with source citations
- **Markdown-formatted responses** with bold text, lists, and formatting
- **Clickable citations** that scroll to source videos
- **Context-aware answers** using top reranked results

### 📦 Collections
- **Save search results** as reusable collections
- **AI-generated summaries** for each collection
- **Persistent storage** with metadata and video references

---

## 🏗️ Traditional Architecture (Legacy)

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
- Gemini API key

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
```bash
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
- Node ≥ 18

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
├── docker-compose.yml           # Microservices orchestration
├── gateway/
│   └── nginx.conf              # API gateway configuration
├── services/
│   ├── frontend/               # React frontend
│   │   ├── src/
│   │   │   ├── api.ts
│   │   │   ├── pages/
│   │   │   └── components/
│   │   ├── Dockerfile
│   │   └── vite.config.ts
│   ├── ingestion/              # Video ingestion service
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── routes_ingest.py
│   │   │   ├── stream_utils.py
│   │   │   └── transcribe/
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── search/                 # Search & RAG service
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── routes_search.py
│   │   │   └── embeddings.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── streaming/              # Video streaming service
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   └── routes_streaming.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── collections/            # Collections management
│       ├── app/
│       │   ├── main.py
│       │   └── routes_collections.py
│       ├── Dockerfile
│       └── requirements.txt
├── services/workers/
│   ├── transcription/          # Transcription worker
│   │   ├── tasks.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── embedding/              # Embedding worker
│       ├── tasks.py
│       ├── Dockerfile
│       └── requirements.txt
└── backend/                    # Legacy monolithic structure
    ├── app/
    │   ├── main.py
    │   ├── routes_ingest.py
    │   ├── routes_search.py
    │   ├── embeddings.py
    │   ├── reranker.py
    │   ├── stream_utils.py
    │   ├── transcribe/gemini_client.py
    │   ├── models.py
    │   ├── db.py
    │   ├── schemas.py
    │   └── sql/
    │       └── create_vector_indexes.sql
    └── requirements.txt
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

### Docker/Microservices Issues
* **Services not starting:**  
  ```bash
  docker-compose logs -f
  netstat -tulpn | grep -E '80|5173|8081|8082|8083|8084|6379|5432'
  docker-compose down && docker-compose up -d
  ```

* **Database connection issues:**  
  ```bash
  # Check PostgreSQL is running
  docker ps | grep postgres
  
  # Reconnect to network
  docker network connect vidsense_vidsense-network <postgres-container> --alias postgres
  ```

* **Worker not processing tasks:**  
  ```bash
  # Check Redis
  docker exec -it vidsense-redis redis-cli ping
  
  # Check worker logs
  docker-compose logs -f transcription-worker embedding-worker
  
  # Restart workers
  docker-compose restart transcription-worker embedding-worker
  ```

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

## 📊 Example Queries

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

## 🤝 Contributing

Contributions welcome! Areas of interest:
- New embedding models
- Alternative reranking strategies
- UI/UX improvements
- Performance optimizations
- Documentation

---

## 📜 License

MIT © 2025  
Developed by Yoav Raytsfeld

---

## 🙏 Acknowledgments

- **sentence-transformers** - Embedding models
- **Hugging Face** - Cross-encoder models
- **pgvector** - Vector database extension
- **Gemini API** - Transcription & generation
- **yt-dlp** - Universal video downloader
- **FastAPI** - High-performance APIs
- **React** - Frontend framework
