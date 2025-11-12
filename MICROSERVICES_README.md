# 🐳 VidSense Microservices Architecture

Complete Docker-based microservices deployment with hot-reload for development.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   API Gateway (Nginx :80)                    │
└────────────┬─────────────────────────────────────────────────┘
             │
    ┌────────┼────────┬────────────┬─────────────┬────────────┐
    │        │        │            │             │            │
┌───▼──┐ ┌───▼──┐ ┌───▼────┐ ┌────▼─────┐ ┌────▼────┐ ┌─────▼────┐
│Ingest│ │Stream│ │ Search │ │Collection│ │Frontend │ │  Redis   │
│:8081 │ │:8083 │ │ :8082  │ │  :8084   │ │  :5173  │ │  :6379   │
└──┬───┘ └──┬───┘ └───┬────┘ └────┬─────┘ └─────────┘ └────┬─────┘
   │        │         │           │                         │
   └────────┴─────────┴───────────┴─────────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │  PostgreSQL        │
                    │  (External/Docker) │
                    └────────────────────┘
                              │
                    ┌─────────┴──────────┐
                    │                    │
            ┌───────▼────────┐  ┌───────▼─────────┐
            │ Transcription  │  │   Embedding     │
            │    Worker      │  │    Worker       │
            └────────────────┘  └─────────────────┘
```

## 📦 Services

| Service | Port | Description | Hot-Reload |
|---------|------|-------------|------------|
| **API Gateway** | 80 | Nginx reverse proxy | ✅ |
| **Ingestion** | 8081 | Video URL ingestion, metadata | ✅ |
| **Streaming** | 8083 | Video streaming & remuxing | ✅ |
| **Search** | 8082 | Semantic search, RAG, reranking | ✅ |
| **Collections** | 8084 | Save search history | ✅ |
| **Frontend** | 5173 | React UI | ✅ |
| **Transcription Worker** | - | Async transcription via Celery | ✅ |
| **Embedding Worker** | - | Async embedding generation | ✅ |
| **Redis** | 6379 | Message queue for workers | - |
| **PostgreSQL** | 5432 | Database + pgvector | External |

## 🚀 Quick Start

### Prerequisites

- Docker 20.10+
- Docker Compose 1.29+
- 8GB RAM (recommended)
- Existing PostgreSQL container: `2f2f5ac5192e`

### Automatic Setup (Recommended)

```bash
# Make scripts executable
chmod +x setup-microservices.sh migrate-to-microservices.sh

# Run setup (builds + starts everything)
./setup-microservices.sh
```

This script will:
1. ✅ Migrate code to microservices structure
2. ✅ Build all Docker images
3. ✅ Start all services
4. ✅ Display access URLs

### Manual Setup

```bash
# 1. Migrate code
chmod +x migrate-to-microservices.sh
./migrate-to-microservices.sh

# 2. Create .env file (if not exists)
cp .env.example .env
# Edit .env with your credentials

# 3. Build services
docker-compose build

# 4. Start services
docker-compose up -d

# 5. View logs
docker-compose logs -f
```

## 🔧 Configuration

### Environment Variables

Create `.env` in root directory:

```bash
# Database (using your existing container)
DATABASE_URL=postgresql+psycopg://tips:tips123@172.17.0.2:5432/tipsdb

# Gemini API
GEMINI_API_KEY=your_gemini_api_key_here

# yt-dlp
YTDLP_COOKIES=chrome
```

### Using Existing PostgreSQL Container

Your docker-compose is configured to connect to your existing PostgreSQL container `2f2f5ac5192e`.

**Option 1: Use External Container (Current Setup)**

```yaml
# In docker-compose.yml, services connect via:
DATABASE_URL=postgresql+psycopg://tips:tips123@<CONTAINER_IP>:5432/tipsdb
```

Get container IP:
```bash
docker inspect 2f2f5ac5192e | grep IPAddress
```

**Option 2: Connect via Docker Network**

```bash
# Add services to your PostgreSQL network
docker network connect <postgres_network> vidsense-ingestion
docker network connect <postgres_network> vidsense-streaming
# ... etc
```

## 💻 Development

### Hot-Reload Enabled

All source code is mounted as volumes:

```yaml
volumes:
  - ./services/ingestion/app:/app/app:ro  # Backend code
  - ./services/frontend/src:/app/src:ro   # Frontend code
```

**No rebuild needed!** Just edit files and changes reflect immediately.

### Editing Code

```bash
# Edit backend services
nano services/ingestion/app/routes_ingest.py

# Edit frontend
nano services/frontend/src/pages/SearchPage.tsx

# Changes apply instantly (hot-reload via uvicorn --reload)
```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f ingestion-service

# Last 50 lines
docker-compose logs --tail=50 search-service
```

### Restarting Services

```bash
# Restart specific service
docker-compose restart search-service

# Restart all
docker-compose restart

# Stop all
docker-compose down

# Start all
docker-compose up -d
```

### Scaling Workers

```bash
# Scale embedding workers to 3 instances
docker-compose up -d --scale embedding-worker=3

# Scale transcription workers
docker-compose up -d --scale transcription-worker=5
```

### Shell Access

```bash
# Access service shell
docker exec -it vidsense-ingestion /bin/bash
docker exec -it vidsense-search python
docker exec -it vidsense-redis redis-cli
```

## 🧪 Testing Services

### Health Checks

```bash
# API Gateway
curl http://localhost/health

# Individual services
curl http://localhost:8081/health  # Ingestion
curl http://localhost:8082/health  # Search
curl http://localhost:8083/health  # Streaming
curl http://localhost:8084/health  # Collections
```

### API Documentation

- Ingestion API: http://localhost:8081/docs
- Search API: http://localhost:8082/docs
- Streaming API: http://localhost:8083/docs
- Collections API: http://localhost:8084/docs

### Test Workflow

```bash
# 1. Ingest video
curl -X POST http://localhost:8081/videos/ingest_url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://instagram.com/p/xxx"}'

# 2. Search
curl -X POST http://localhost:8082/search/query \
  -H "Content-Type: application/json" \
  -d '{"query": "shoulder pain", "k_final": 10}'

# 3. Stream video
curl http://localhost:8083/videos/{video_id}/stream?clip=1
```

## 📊 Monitoring

### Service Status

```bash
# View running containers
docker-compose ps

# Resource usage
docker stats

# Disk usage
docker system df
```

### Worker Queues

```bash
# Redis CLI
docker exec -it vidsense-redis redis-cli

# Check queue length
> LLEN transcription_queue
> LLEN embedding_queue
```

## 🔍 Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose logs <service-name>

# Rebuild service
docker-compose build --no-cache <service-name>
docker-compose up -d <service-name>
```

### Database Connection Failed

```bash
# Check PostgreSQL container
docker ps -a | grep 2f2f5ac5192e

# Test connection
docker exec -it 2f2f5ac5192e psql -U tips -d tipsdb

# Get container IP
docker inspect 2f2f5ac5192e | grep IPAddress
```

### Hot-Reload Not Working

```bash
# Ensure volumes are mounted (check docker-compose ps)
docker-compose ps

# Restart with fresh mounts
docker-compose down
docker-compose up -d
```

### Models Not Loading

```bash
# Clear cache
docker volume rm vidsense-models

# Rebuild search/embedding services
docker-compose build search-service embedding-worker
docker-compose up -d
```

### Out of Memory

```bash
# Reduce worker concurrency
# Edit docker-compose.yml:
command: celery -A tasks worker --concurrency=1

# Or scale down
docker-compose up -d --scale embedding-worker=1
```

## 🗂️ Project Structure

```
.
├── docker-compose.yml              # Orchestration
├── .env                            # Environment variables
├── gateway/
│   └── nginx.conf                  # API Gateway config
│
├── services/
│   ├── ingestion/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── app/                    # ← Your backend code (volume mounted)
│   │       ├── main.py
│   │       ├── routes_ingest.py
│   │       ├── stream_utils.py
│   │       ├── metadata_extractors.py
│   │       └── transcribe/
│   │
│   ├── streaming/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── app/                    # ← Your streaming code
│   │       ├── main.py
│   │       └── stream_utils.py
│   │
│   ├── search/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── app/                    # ← Your search code
│   │       ├── main.py
│   │       ├── routes_search.py
│   │       ├── embeddings.py
│   │       └── reranker.py
│   │
│   ├── collections/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── app/                    # ← Your collections code
│   │       ├── main.py
│   │       └── routes_collections.py
│   │
│   ├── workers/
│   │   ├── transcription/
│   │   │   ├── Dockerfile
│   │   │   ├── requirements.txt
│   │   │   └── tasks.py           # ← Transcription worker
│   │   │
│   │   └── embedding/
│   │       ├── Dockerfile
│   │       ├── requirements.txt
│   │       └── tasks.py           # ← Embedding worker
│   │
│   └── frontend/
│       ├── Dockerfile
│       └── src/                    # ← Your React code (symlinked)
│
└── backend/                        # ← Original code (preserved)
    └── app/
```

## 🚀 Production Deployment

### Build for Production

```bash
# Production build (no hot-reload)
docker-compose -f docker-compose.prod.yml build

# Start production
docker-compose -f docker-compose.prod.yml up -d
```

### Scaling

```bash
# Scale horizontally
docker-compose up -d --scale search-service=3 --scale embedding-worker=5
```

### Resource Limits

Edit `docker-compose.yml`:

```yaml
services:
  search-service:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

## 📝 Migration Notes

### What Was Migrated

✅ **ALL code preserved** - no functionality lost
✅ **Volume mounted** - hot-reload works
✅ **Existing DB** - connects to your PostgreSQL `2f2f5ac5192e`
✅ **Model caching** - models downloaded once

### Original Code Location

Original code remains in `backend/` and `frontend/` directories. Services use copies/symlinks from `services/`.

## 🎯 Next Steps

1. ✅ Run `./setup-microservices.sh`
2. ✅ Access http://localhost
3. ✅ Test video ingestion
4. ✅ Test semantic search
5. ✅ Monitor worker logs
6. ✅ Scale as needed

## 🤝 Support

- 📖 View logs: `docker-compose logs -f`
- 🐛 Report issues: Check service logs
- 💬 Debug: Use `docker exec -it <container> /bin/bash`

---

**Built with ❤️ for scalable video search**
