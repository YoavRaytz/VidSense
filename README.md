# 🎥 VidSense - AI-Powered Video Search & RAG System# 🎥 VidSense - AI-Powered Video Search & RAG System



A powerful FastAPI + React application for semantic video search with AI-generated answers. Ingest videos from social media, generate transcripts, and search with state-of-the-art retrieval and reranking.A powerful FastAPI + React application for semantic video search with AI-generated answers. Ingest videos from social media, generate transcripts, and search with state-of-the-art retrieval and reranking.



## ✨ Features## ✨ Features



### 🎬 Video Management### 🎬 Video Management

- **Multi-platform video ingestion** via `yt-dlp` (Instagram, YouTube, TikTok, etc.)- **Multi-platform video ingestion** via `yt-dlp` (Instagram, YouTube, TikTok, etc.)

- **Automatic transcription** using Gemini 2.0 Flash- **Automatic transcription** using Gemini 2.0 Flash

- **Video streaming** with adaptive quality and clip support- **Video streaming** with adaptive quality and clip support

- **Transcript editing** with live preview- **Transcript editing** with live preview



### 🔍 Advanced Search### � Advanced Search

- **Semantic search** using sentence-transformers embeddings (384-dim)- **Semantic search** using sentence-transformers embeddings (384-dim)

- **Two-stage retrieval**: Fast ANN search + Cross-encoder reranking- **Two-stage retrieval**: Fast ANN search + Cross-encoder reranking

- **pgvector** for efficient vector similarity search- **pgvector** for efficient vector similarity search

- **Cross-encoder reranking** with `ms-marco-MiniLM-L-6-v2`- **Cross-encoder reranking** with `ms-marco-MiniLM-L-6-v2`

- **Softmax score normalization** for interpretable relevance scores- **Softmax score normalization** for interpretable relevance scores



### 🤖 RAG (Retrieval-Augmented Generation)### 🤖 RAG (Retrieval-Augmented Generation)

- **AI-powered answers** using Gemini with source citations- **AI-powered answers** using Gemini with source citations

- **Markdown-formatted responses** with bold text, lists, and formatting- **Markdown-formatted responses** with bold text, lists, and formatting

- **Clickable citations** that scroll to source videos- **Clickable citations** that scroll to source videos

- **Context-aware answers** using top reranked results- **Context-aware answers** using top reranked resultsre’s a **concise, correct, copy-ready `README.md`** for your current repo.

It explains what it does, how to run it, and how to use it — without extra fluff or made-up parts.

---

---

## 🏗️ Architecture

````markdown

### Backend Stack# 🎥 Video Search & Transcript Tool

- **FastAPI** - High-performance async API

- **PostgreSQL** with **pgvector** - Vector database for embeddingsA lightweight FastAPI + React app that lets you:

- **sentence-transformers** - Embedding generation (`all-MiniLM-L6-v2`)

- **transformers** - Cross-encoder reranking (`ms-marco-MiniLM-L-6-v2`)- Paste an Instagram (or any video) URL  

- **Gemini API** - Transcription & answer generation- Preview and play the video  

- **yt-dlp** - Multi-platform video download- Generate a transcript using **Gemini**  

- **GStreamer** - Video remuxing & processing- Edit and save the transcript to a **PostgreSQL** database  



### Frontend Stack---

- **React + TypeScript** - Type-safe UI components

- **Vite** - Fast development & building## 🏗️ Architecture

- **react-markdown** - Rich text formatting for AI answers

### Backend Stack

### Search Pipeline- **FastAPI** - High-performance async API

1. **Query Embedding**: Convert search query to 384-dim vector- **PostgreSQL** with **pgvector** - Vector database for embeddings

2. **ANN Search**: Fast approximate nearest neighbor search (k=20-50)- **sentence-transformers** - Embedding generation (`all-MiniLM-L6-v2`)

3. **Reranking**: Cross-encoder scores query-document pairs- **transformers** - Cross-encoder reranking (`ms-marco-MiniLM-L-6-v2`)

4. **Softmax Normalization**: Convert logits to probabilities- **Gemini API** - Transcription & answer generation

5. **RAG Generation**: Gemini generates answer with citations- **yt-dlp** - Multi-platform video download

- **GStreamer** - Video remuxing & processing

---

### Frontend Stack

## ⚙️ Setup- **React + TypeScript** - Type-safe UI components

- **Vite** - Fast development & building

### 1️⃣ Backend (FastAPI)- **react-markdown** - Rich text formatting for AI answers



**Requirements**### Search Pipeline

- Python ≥ 3.10  1. **Query Embedding**: Convert search query to 384-dim vector

- PostgreSQL 15+ with **pgvector extension**2. **ANN Search**: Fast approximate nearest neighbor search (k=20-50)

- [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) installed  3. **Reranking**: Cross-encoder scores query-document pairs

- `gst-launch-1.0` (GStreamer)  4. **Softmax Normalization**: Convert logits to probabilities

- Gemini API key5. **RAG Generation**: Gemini generates answer with citations



**Install pgvector**---

```bash

# Ubuntu/Debian## ⚙️ Setup

sudo apt install postgresql-15-pgvector

### 1️⃣ Backend (FastAPI)

# macOS

brew install pgvector**Requirements**

- Python ≥ 3.10  

# Then in psql:- PostgreSQL 15+ with **pgvector extension**

CREATE EXTENSION vector;- [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) installed  

```- `gst-launch-1.0` (GStreamer)  

- Gemini API key (`GEMINI_API_KEY`)

**Setup**

```bash**Install pgvector**

cd backend```bash

python -m venv venv# Ubuntu/Debian

source venv/bin/activatesudo apt install postgresql-15-pgvector

pip install -r requirements.txt

# macOS

cp env.example .envbrew install pgvector

```

# Then in psql:

**Example `.env`**CREATE EXTENSION vector;

```bash```

DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/video_db

GEMINI_API_KEY=your_gemini_api_key_here**Setup**

YTDLP_BIN=yt-dlp```bash

YTDLP_COOKIES=chrome:Defaultcd backend

GST_BIN=gst-launch-1.0python -m venv venv

TMP_DIR=/tmp/app-videossource venv/bin/activate

```pip install -r requirements.txt



**Run**cp env.example .env

```bash```

cd backend

PYTHONPATH="$PWD/.." uvicorn app.main:app --reload --reload-dir app --port 8080 --env-file ../.env**Example `.env`**

```

```

- API: [http://127.0.0.1:8080](http://127.0.0.1:8080)  DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/video_db

- API Docs: [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs)GEMINI_API_KEY=your_gemini_key

YTDLP_BIN=yt-dlp

---YTDLP_COOKIES=chrome:Default

GST_BIN=gst-launch-1.0

### 2️⃣ Frontend (React + Vite)TMP_DIR=/tmp/app-videos

```

**Requirements**

- Node.js ≥ 18**Run**



**Setup**```bash

```bashcd backend

cd frontendPYTHONPATH="$PWD/.." uvicorn app.main:app --reload --reload-dir app --port 8080 --env-file ../.env

npm install```

npm run dev -- --host --port 5173

```API: [http://127.0.0.1:8080](http://127.0.0.1:8080)  

API Docs: [http://127.0.0.1:8080/docs](http://127.0.0.1:8080/docs)

- App: [http://localhost:5173](http://localhost:5173)

---

---

### 2️⃣ Frontend (React + Vite)

## 🧩 Main Workflows

**Requirements**

### 1️⃣ Video Ingestion

1. Navigate to **Ingest** page* Node ≥ 18

2. Paste video URL (Instagram, YouTube, TikTok, etc.)

3. Click **Open** → fetch & preview video**Setup**

4. Click **Get Transcript** → AI generates transcript with Gemini

5. Edit transcript if needed```bash

6. Click **Save to DB** → stores video with embeddingscd frontend

npm install

### 2️⃣ Semantic Searchnpm run dev -- --host --port 5173

1. Navigate to **Search** page```

2. Enter natural language query (e.g., "shoulder pain exercises")

3. View ranked results with relevance scores (%)App: [http://localhost:5173](http://localhost:5173)

4. Click any result to view full video + transcript

---

### 3️⃣ RAG Question Answering

1. Enter question in search box## 🧩 Main Workflows

2. Click **Generate AI Answer**

3. View markdown-formatted answer with citations### 1️⃣ Video Ingestion

4. Click citations `[1]`, `[2]` to jump to source videos1. Navigate to **Ingest** page

5. Watch source videos and read full transcripts2. Paste video URL (Instagram, YouTube, etc.)

3. Click **Open** → fetch & preview video

---4. Click **Get Transcript** → AI generates transcript

5. Edit transcript if needed

## 🧠 API Endpoints6. Click **Save to DB** → stores with embeddings



### Video Management### 2️⃣ Semantic Search

| Method | Endpoint                           | Description                    |1. Navigate to **Search** page

| ------ | ---------------------------------- | ------------------------------ |2. Enter natural language query (e.g., "shoulder pain exercises")

| `POST` | `/videos/ingest_url`               | Register new video by URL      |3. View ranked results with relevance scores

| `GET`  | `/videos/`                         | List all videos                |4. Click any result to view full video + transcript

| `GET`  | `/videos/{id}/meta`                | Get video metadata             |

| `GET`  | `/videos/{id}/stream`              | Stream video (MP4)             |### 3️⃣ RAG Question Answering

| `POST` | `/videos/{id}:generate_transcript` | Generate transcript w/ Gemini  |1. Enter question in search box

| `GET`  | `/videos/{id}/transcript`          | Get transcript text            |2. Click **Generate AI Answer**

| `PUT`  | `/videos/{id}/transcript`          | Update transcript text         |3. View markdown-formatted answer with citations

4. Click citations `[1]`, `[2]` to jump to source videos

### Search & RAG5. Watch source videos and read transcripts

| Method | Endpoint         | Description                           |

| ------ | ---------------- | ------------------------------------- |---

| `POST` | `/search/query`  | Semantic search with reranking        |

| `POST` | `/search/rag`    | RAG: Search + generate answer         |## 🧠 API Endpoints

| `POST` | `/embeddings`    | Generate embeddings for text          |

### Video Management

---| Method | Endpoint                           | Description                    |

| ------ | ---------------------------------- | ------------------------------ |

## 🧱 Project Structure| `POST` | `/videos/ingest_url`               | Register new video by URL      |

| `GET`  | `/videos/`                         | List all videos                |

```| `GET`  | `/videos/{id}/meta`                | Get video metadata             |

.| `GET`  | `/videos/{id}/stream`              | Stream video (MP4)             |

├── backend/| `POST` | `/videos/{id}:generate_transcript` | Generate transcript w/ Gemini  |

│   ├── app/| `GET`  | `/videos/{id}/transcript`          | Get transcript text            |

│   │   ├── main.py                      # FastAPI app & router setup| `PUT`  | `/videos/{id}/transcript`          | Update transcript text         |

│   │   ├── routes_ingest.py             # Video ingestion endpoints

│   │   ├── routes_search.py             # Search & RAG endpoints### Search & RAG

│   │   ├── embeddings.py                # Sentence-transformers embeddings| Method | Endpoint         | Description                           |

│   │   ├── reranker.py                  # Cross-encoder reranking| ------ | ---------------- | ------------------------------------- |

│   │   ├── stream_utils.py              # Video processing & streaming| `POST` | `/search/query`  | Semantic search with reranking        |

│   │   ├── transcribe/gemini_client.py  # Gemini API client| `POST` | `/search/rag`    | RAG: Search + generate answer         |

│   │   ├── models.py                    # SQLAlchemy models| `POST` | `/embeddings`    | Generate embeddings for text          |

│   │   ├── db.py                        # Database connection

│   │   ├── schemas.py                   # Pydantic schemas---

│   │   └── sql/

│   │       └── create_vector_indexes.sql## 🧱 Project Structure

│   └── requirements.txt

├── frontend/```

│   ├── src/.

│   │   ├── pages/├── backend/

│   │   │   ├── IngestPage.tsx           # Video upload & transcription│   ├── app/

│   │   │   ├── SearchPage.tsx           # Search & RAG interface│   │   ├── main.py                      # FastAPI app & router setup

│   │   │   └── VideosPage.tsx           # Video library│   │   ├── routes_ingest.py             # Video ingestion endpoints

│   │   ├── components/│   │   ├── routes_search.py             # Search & RAG endpoints

│   │   │   ├── VideoPlayer.tsx          # Video playback│   │   ├── embeddings.py                # Sentence-transformers embeddings

│   │   │   └── TranscriptViewer.tsx     # Transcript display/edit│   │   ├── reranker.py                  # Cross-encoder reranking

│   │   ├── api.ts                       # API client│   │   ├── stream_utils.py              # Video processing & streaming

│   │   ├── App.tsx                      # Main app & routing│   │   ├── transcribe/gemini_client.py  # Gemini API client

│   │   └── main.tsx                     # Entry point│   │   ├── models.py                    # SQLAlchemy models

│   ├── vite.config.ts│   │   ├── db.py                        # Database connection

│   └── package.json│   │   ├── schemas.py                   # Pydantic schemas

└── README.md│   │   └── sql/

```│   │       └── create_vector_indexes.sql

│   └── requirements.txt

---├── frontend/

│   ├── src/

## 🔬 Technical Details│   │   ├── pages/

│   │   │   ├── IngestPage.tsx           # Video upload & transcription

### Embedding Model│   │   │   ├── SearchPage.tsx           # Search & RAG interface

- **Model**: `sentence-transformers/all-MiniLM-L6-v2`│   │   │   └── VideosPage.tsx           # Video library

- **Dimensions**: 384│   │   ├── components/

- **Approach**: Mean pooling of token embeddings│   │   │   ├── VideoPlayer.tsx          # Video playback

- **Storage**: pgvector with cosine distance operator│   │   │   └── TranscriptViewer.tsx     # Transcript display/edit

│   │   ├── api.ts                       # API client

### Reranking Model│   │   ├── App.tsx                      # Main app & routing

- **Model**: `cross-encoder/ms-marco-MiniLM-L-6-v2`│   │   └── main.tsx                     # Entry point

- **Type**: BERT-based sequence classification│   ├── vite.config.ts

- **Output**: Raw logits (typically -15 to +15)│   └── package.json

- **Normalization**: Softmax for probability distribution└── README.md

- **Context**: Combines title + description + transcript```

- **Smart extraction**: Finds query terms, extracts relevant 4000-char windows

---

### RAG Pipeline

1. **Retrieve**: Get top-k documents via ANN + reranking## 🔬 Technical Details

2. **Context**: Combine titles, descriptions, and transcripts

3. **Prompt**: System prompt + context + user query### Embedding Model

4. **Generate**: Gemini 2.0 Flash (temperature 0.3)- **Model**: `sentence-transformers/all-MiniLM-L6-v2`

5. **Citations**: Parse and link `[1]`, `[2]` references- **Dimensions**: 384

- **Approach**: Mean pooling of token embeddings

---- **Storage**: pgvector with cosine distance



## 🧰 Troubleshooting### Reranking Model

- **Model**: `cross-encoder/ms-marco-MiniLM-L-6-v2`

### Video Issues- **Type**: BERT-based sequence classification

**Empty MP4 after remux:**  - **Output**: Raw logits (typically -15 to +15)

Ensure GStreamer is installed:- **Normalization**: Softmax for probability distribution

```bash- **Context**: Combines title + description + transcript

sudo apt install gstreamer1.0-tools gstreamer1.0-plugins-good- **Smart extraction**: Finds query terms, sends 4000-char windows

```

### RAG Pipeline

**Instagram videos fail:**  1. **Retrieve**: Get top-k documents via ANN + reranking

Update cookies in `.env`:2. **Context**: Combine titles, descriptions, transcripts

```bash3. **Prompt**: System prompt + context + user query

YTDLP_COOKIES=chrome:Default4. **Generate**: Gemini 2.0 Flash with temperature 0.3

```5. **Citations**: Parse and link `[1]`, `[2]` references

Or export cookies.txt from your browser.

---

**Video won't play:**  

Check browser console for codec errors. Some videos may need specific codecs.## 🧰 Troubleshooting



### Search Issues### Video Issues

**Poor search results:**  * **Empty MP4 after remux:**  

- Ensure embeddings are generated (check `transcript_embedding` column in database)  Ensure GStreamer is installed: `sudo apt install gstreamer1.0-tools gstreamer1.0-plugins-good`

- Try different query phrasing

- Verify pgvector indexes are created* **Instagram videos fail:**  

  Update cookies: `YTDLP_COOKIES=chrome:Default` or export cookies.txt

**Reranker errors:**  

- First run downloads model (~90MB) - check internet connection* **Video won't play:**  

- Ensure sufficient RAM for transformer models (min 2GB)  Check browser console. Some videos need specific codecs.



**Citations broken:**  ### Search Issues

- Check that `ragResponse.sources` array matches citation numbers* **Poor search results:**  

- Verify Gemini returns proper `[1]`, `[2]` citation format  - Ensure embeddings are generated (check `transcript_embedding` column)

  - Try different query phrasing

### Database Issues  - Check pgvector indexes are created

**pgvector extension missing:**  

```sql* **Reranker errors:**  

CREATE EXTENSION IF NOT EXISTS vector;  - First run downloads model (~90MB) - check internet connection

```  - Ensure sufficient memory for transformer models



**Connection refused:**  * **Citations broken:**  

Verify `DATABASE_URL` in `.env` matches your PostgreSQL configuration.  - Check that `ragResponse.sources` matches citation numbers

  - Verify Gemini returns proper `[1]`, `[2]` format

**Slow vector search:**  

Ensure HNSW index is created (automatically on startup):### Database Issues

```sql* **pgvector extension missing:**  

CREATE INDEX IF NOT EXISTS transcript_embedding_idx   ```sql

ON transcripts USING hnsw (embedding vector_cosine_ops);  CREATE EXTENSION IF NOT EXISTS vector;

```  ```



---* **Connection refused:**  

  Verify `DATABASE_URL` in `.env` matches PostgreSQL config

## 🚀 Performance Tips

* **Slow vector search:**  

1. **ANN Search**: Adjust `k_ann` parameter (default 50) for speed/accuracy tradeoff  Create HNSW index (automatically done on startup):

2. **Reranking**: Adjust `k_final` parameter (default 10) for number of final results  ```sql

3. **Embeddings**: Batch generate embeddings for multiple videos  CREATE INDEX IF NOT EXISTS transcript_embedding_idx 

4. **Caching**: Models are lazy-loaded and cached with `@lru_cache`  ON transcripts USING hnsw (embedding vector_cosine_ops);

5. **Database**: Use connection pooling for concurrent requests  ```



------



## 📊 Example Queries## 🚀 Performance Tips



**Search Examples:**1. **ANN Search**: Adjust `k_ann` (default 50) for speed/accuracy tradeoff

- "shoulder pain exercises"2. **Reranking**: Adjust `k_final` (default 10) for final results

- "LinkedIn tips for software engineers"3. **Embeddings**: Batch generate for multiple videos

- "what makes my ear hurt"4. **Caching**: Models are lazy-loaded and cached with `@lru_cache`

- "productivity advice"5. **Database**: Use connection pooling for concurrent requests



**RAG Examples:**---

- "How can I improve my LinkedIn profile?"

- "What exercises help with shoulder pain?"## 🪄 Future Enhancements

- "Give me tips for better sleep"

- [ ] Multi-modal search (visual + text)

---- [ ] Video carousel/clip support

- [ ] User accounts & saved searches

## 🪄 Future Enhancements- [ ] Custom embedding models

- [ ] Hybrid search (keyword + semantic)

- [ ] Multi-modal search (visual + text)- [ ] Real-time transcription

- [ ] Video carousel/clip support- [ ] Video summarization

- [ ] User accounts & saved searches- [ ] Export search results

- [ ] Custom embedding models

- [ ] Hybrid search (keyword + semantic)---

- [ ] Real-time transcription

- [ ] Video summarization## � Example Queries

- [ ] Export search results

**Search Examples:**

---- "shoulder pain exercises"

- "LinkedIn tips for software engineers"

## 🤝 Contributing- "what makes my ear hurt"

- "productivity advice"

Contributions welcome! Areas of interest:

- New embedding models**RAG Examples:**

- Alternative reranking strategies- "How can I improve my LinkedIn profile?"

- UI/UX improvements- "What exercises help with shoulder pain?"

- Performance optimizations- "Give me tips for better sleep"

- Documentation

---

---

## 🤝 Contributing

## 📜 License

Contributions welcome! Areas of interest:

MIT © 2025  - New embedding models

Developed by Yoav Raytsfeld- Alternative reranking strategies

- UI/UX improvements

---- Performance optimizations

- Documentation

## 🙏 Acknowledgments

---

- **sentence-transformers** - Embedding models

- **Hugging Face** - Cross-encoder models## �📜 License

- **pgvector** - Vector database extension

- **Gemini API** - Transcription & generationMIT © 2025  

- **yt-dlp** - Universal video downloaderDeveloped by Yoav Raytsfeld


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
