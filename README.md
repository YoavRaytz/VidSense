Got it 👍 — here’s a **concise, correct, copy-ready `README.md`** for your current repo.
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

## ⚙️ Setup

### 1️⃣ Backend (FastAPI)

**Requirements**
- Python ≥ 3.10  
- PostgreSQL (local or container)
- [`yt-dlp`](https://github.com/yt-dlp/yt-dlp) installed  
- `gst-launch-1.0` (GStreamer)  
- Gemini API key (`GEMINI_API_KEY`)

**Setup**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp env.example .env
````

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
PYTHONPATH="$PWD/.." WATCHFILES_FORCE_POLLING=true \
uvicorn app.main:app --reload --reload-dir app --port 8080
```

API: [http://127.0.0.1:8080](http://127.0.0.1:8080)

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

## 🧩 Main Flow

1. Paste a video link
2. Click **Open** → fetch stream via `yt-dlp`
3. Click **Get Transcript** → remux video + transcribe with Gemini
4. Edit the text
5. Click **Save to DB**

---

## 🧠 Endpoints (used by frontend)

| Method | Endpoint                           | Description                 |
| ------ | ---------------------------------- | --------------------------- |
| `POST` | `/videos/ingest_url`               | Register a new video by URL |
| `GET`  | `/videos/{id}/stream`              | Get a playable MP4 link     |
| `POST` | `/videos/{id}:generate_transcript` | Run Gemini transcription    |
| `GET`  | `/videos/{id}/transcript`          | Get transcript text         |
| `PUT`  | `/videos/{id}/transcript`          | Update transcript text      |

---

## 🧱 Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── routes_ingest.py
│   │   ├── stream_utils.py
│   │   ├── transcribe/gemini_client.py
│   │   ├── models.py, db.py, schemas.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/IngestPage.tsx
│   │   ├── api.ts, App.tsx, main.tsx
│   ├── vite.config.ts
│   └── package.json
└── docker-compose.yml (optional)
```

---

## 🧰 Troubleshooting

* **Empty MP4 after remux:**
  Ensure GStreamer is installed and Instagram cookies are valid.

* **Gemini errors:**
  Check `GEMINI_API_KEY` in `.env`.

* **DB connection refused:**
  Make sure PostgreSQL is running and matches `DATABASE_URL`.

---

## 🪄 Notes

* Temporary files live in `/tmp/app-videos`
* `.env` and media files are ignored via `.gitignore`
* Future updates will add description + multi-clip (carousel) support

---

## 📜 License

MIT © 2025
Developed by Yoav Raytsfeld

```

---

✅ You can copy this directly into your root `README.md`.  
It’s short, accurate to your current code, and GitHub-ready.
```
