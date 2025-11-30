# 🚀 VidSense Microservices - Quick Reference

## 🎯 Quick Start

```bash
# One command to rule them all
./setup-microservices.sh
```

Then open: **http://localhost**

---

## 📝 Common Commands

### Starting & Stopping

```bash
# Start everything
docker-compose up -d

# Stop everything
docker-compose down

# Restart specific service
docker-compose restart search-service

# View status
docker-compose ps
```

### Viewing Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f ingestion-service

# Last 100 lines
docker-compose logs --tail=100 search-service
```

### Rebuilding

```bash
# Rebuild specific service
docker-compose build search-service
docker-compose up -d search-service

# Rebuild everything
docker-compose build
docker-compose up -d
```

### Scaling Workers

```bash
# More embedding workers
docker-compose up -d --scale embedding-worker=5

# More transcription workers
docker-compose up -d --scale transcription-worker=3
```

---

## 🔧 Development

### Editing Code (No Rebuild Needed!)

```bash
# Backend services
nano services/ingestion/app/routes_ingest.py
nano services/search/app/routes_search.py

# Frontend
nano services/frontend/src/pages/SearchPage.tsx

# Changes apply instantly via hot-reload
```

### Accessing Containers

```bash
# Shell access
docker exec -it vidsense-ingestion /bin/bash
docker exec -it vidsense-search /bin/bash

# Python REPL
docker exec -it vidsense-search python

# Redis CLI
docker exec -it vidsense-redis redis-cli
```

### Database Access

```bash
# Connect to PostgreSQL
docker exec -it 2f2f5ac5192e psql -U tips -d tipsdb

# Or if using new instance
docker exec -it vidsense-postgres psql -U tips -d tipsdb
```

---

## 🌐 Service URLs

| Service | URL | Docs |
|---------|-----|------|
| **Frontend** | http://localhost | - |
| **API Gateway** | http://localhost/api | - |
| **Ingestion** | http://localhost:8081 | /docs |
| **Streaming** | http://localhost:8083 | /docs |
| **Search** | http://localhost:8082 | /docs |
| **Collections** | http://localhost:8084 | /docs |

---

## 🐛 Troubleshooting

### Service won't start
```bash
docker-compose logs <service-name>
docker-compose restart <service-name>
```

### Database connection failed
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Get IP address
docker inspect 2f2f5ac5192e | grep IPAddress

# Test connection
docker exec -it 2f2f5ac5192e psql -U tips -d tipsdb
```

### Models not loading
```bash
# Check models volume
docker volume inspect vidsense-models

# Clear and re-download
docker volume rm vidsense-models
docker-compose up -d search-service embedding-worker
```

### Out of memory
```bash
# Check usage
docker stats

# Reduce workers
docker-compose up -d --scale embedding-worker=1 --scale transcription-worker=1
```

---

## 📊 Monitoring

### Resource Usage
```bash
docker stats
```

### Worker Queues
```bash
docker exec -it vidsense-redis redis-cli
> LLEN transcription
> LLEN embedding
```

### Service Health
```bash
curl http://localhost/health
curl http://localhost:8081/health
curl http://localhost:8082/health
```

---

## 🧹 Cleanup

### Remove everything (keep data)
```bash
docker-compose down
```

### Remove everything (including data)
```bash
docker-compose down -v
```

### Clean Docker system
```bash
docker system prune -a
```

---

## 📦 Architecture

```
Gateway:80 → Frontend:5173
           → Ingestion:8081 → Workers → PostgreSQL
           → Streaming:8083 →         → Redis
           → Search:8082    →
           → Collections:8084
```

---

## ⚡ Performance Tips

1. **Scale workers** for parallel processing
2. **Use SSD** for model cache volume
3. **Allocate 4GB+ RAM** per ML service
4. **Monitor** with `docker stats`
5. **Hot-reload** avoids rebuilds

---

## 🎓 Learn More

- Full docs: `MICROSERVICES_README.md`
- Original setup: `README.md`
- Docker Compose: `docker-compose.yml`
- Gateway config: `gateway/nginx.conf`

---

**Need help?** Check logs first: `docker-compose logs -f`
