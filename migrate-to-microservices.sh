#!/bin/bash
# Migration script: Move code to microservices structure
# This preserves ALL your existing code without loss

set -e

echo "🚀 Starting VidSense microservices migration..."
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ========================================
# 1. INGESTION SERVICE
# ========================================
echo -e "${BLUE}📦 Setting up Ingestion Service...${NC}"

# Copy shared files
cp backend/app/__init__.py services/ingestion/app/
cp backend/app/db.py services/ingestion/app/
cp backend/app/models.py services/ingestion/app/
cp backend/app/schemas.py services/ingestion/app/

# Copy ingestion-specific files
cp backend/app/routes_ingest.py services/ingestion/app/
cp backend/app/stream_utils.py services/ingestion/app/
cp backend/app/metadata_extractors.py services/ingestion/app/

# Copy transcription module
cp -r backend/app/transcribe services/ingestion/app/

echo -e "${GREEN}✓ Ingestion service files copied${NC}"

# ========================================
# 2. STREAMING SERVICE
# ========================================
echo -e "${BLUE}📦 Setting up Streaming Service...${NC}"

# Copy shared files
cp backend/app/__init__.py services/streaming/app/
cp backend/app/db.py services/streaming/app/
cp backend/app/models.py services/streaming/app/
cp backend/app/schemas.py services/streaming/app/

# Copy streaming-specific files
cp backend/app/stream_utils.py services/streaming/app/

echo -e "${GREEN}✓ Streaming service files copied${NC}"

# ========================================
# 3. SEARCH SERVICE
# ========================================
echo -e "${BLUE}📦 Setting up Search Service...${NC}"

# Copy shared files
cp backend/app/__init__.py services/search/app/
cp backend/app/db.py services/search/app/
cp backend/app/models.py services/search/app/
cp backend/app/schemas.py services/search/app/

# Copy search-specific files
cp backend/app/routes_search.py services/search/app/
cp backend/app/embeddings.py services/search/app/
cp backend/app/reranker.py services/search/app/

# Copy transcription for RAG
cp -r backend/app/transcribe services/search/app/

echo -e "${GREEN}✓ Search service files copied${NC}"

# ========================================
# 4. COLLECTIONS SERVICE
# ========================================
echo -e "${BLUE}📦 Setting up Collections Service...${NC}"

# Copy shared files
cp backend/app/__init__.py services/collections/app/
cp backend/app/db.py services/collections/app/
cp backend/app/models.py services/collections/app/
cp backend/app/schemas.py services/collections/app/

# Copy collections-specific files
cp backend/app/routes_collections.py services/collections/app/

echo -e "${GREEN}✓ Collections service files copied${NC}"

# ========================================
# 5. WORKERS
# ========================================
echo -e "${BLUE}📦 Setting up Workers...${NC}"

# Transcription worker
cp backend/app/db.py services/workers/transcription/
cp backend/app/models.py services/workers/transcription/
cp -r backend/app/transcribe services/workers/transcription/

# Embedding worker
cp backend/app/db.py services/workers/embedding/
cp backend/app/models.py services/workers/embedding/
cp backend/app/embeddings.py services/workers/embedding/

echo -e "${GREEN}✓ Worker files copied${NC}"

# ========================================
# 6. FRONTEND
# ========================================
echo -e "${BLUE}📦 Setting up Frontend...${NC}"

# Create symlinks instead of copying (so changes reflect immediately)
ln -sf ../../frontend/src services/frontend/src
ln -sf ../../frontend/index.html services/frontend/index.html
ln -sf ../../frontend/vite.config.ts services/frontend/vite.config.ts
ln -sf ../../frontend/package.json services/frontend/package.json
ln -sf ../../frontend/package-lock.json services/frontend/package-lock.json
ln -sf ../../frontend/tsconfig.json services/frontend/tsconfig.json

echo -e "${GREEN}✓ Frontend symlinks created${NC}"

echo ""
echo -e "${GREEN}✅ Migration complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Review .env file and update if needed"
echo "2. Build and start services: docker-compose up --build"
echo "3. Access application at http://localhost"
