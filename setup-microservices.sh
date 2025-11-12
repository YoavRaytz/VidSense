#!/bin/bash
# VidSense Microservices Setup Script
# This script sets up the complete microservices architecture

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   VidSense Microservices Setup                    ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════════════╝${NC}"
echo ""

# ========================================
# Step 1: Check prerequisites
# ========================================
echo -e "${BLUE}📋 Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker first.${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose not found. Please install Docker Compose first.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker found: $(docker --version)${NC}"
echo -e "${GREEN}✓ Docker Compose found: $(docker-compose --version)${NC}"
echo ""

# ========================================
# Step 2: Migrate code to services
# ========================================
echo -e "${BLUE}📦 Migrating code to microservices structure...${NC}"

chmod +x migrate-to-microservices.sh
./migrate-to-microservices.sh

echo ""

# ========================================
# Step 3: Check .env file
# ========================================
echo -e "${BLUE}🔐 Checking environment variables...${NC}"

if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from backend/.env...${NC}"
    if [ -f "backend/.env" ]; then
        cp backend/.env .env
    else
        cp .env.example .env
        echo -e "${YELLOW}⚠️  Please edit .env and add your credentials${NC}"
    fi
fi

# Check for existing PostgreSQL container
POSTGRES_CONTAINER_ID="2f2f5ac5192e"
if docker ps -a --format '{{.ID}}' | grep -q "$POSTGRES_CONTAINER_ID"; then
    echo -e "${GREEN}✓ Found existing PostgreSQL container: ${POSTGRES_CONTAINER_ID}${NC}"
    echo -e "${YELLOW}ℹ️  Will use existing database${NC}"
    
    # Update docker-compose to use external network if needed
    # Get network of existing container
    POSTGRES_NETWORK=$(docker inspect $POSTGRES_CONTAINER_ID --format='{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}' | head -n1)
    echo -e "${BLUE}ℹ️  PostgreSQL network: ${POSTGRES_NETWORK}${NC}"
else
    echo -e "${YELLOW}⚠️  PostgreSQL container ${POSTGRES_CONTAINER_ID} not found${NC}"
    echo -e "${YELLOW}ℹ️  Docker Compose will create a new PostgreSQL instance${NC}"
fi

echo ""

# ========================================
# Step 4: Build services
# ========================================
echo -e "${BLUE}🏗️  Building Docker images...${NC}"
echo -e "${YELLOW}⏳ This may take 5-10 minutes on first run...${NC}"
echo ""

docker-compose build --parallel

echo ""
echo -e "${GREEN}✅ Build complete!${NC}"
echo ""

# ========================================
# Step 5: Start services
# ========================================
echo -e "${BLUE}🚀 Starting services...${NC}"
echo ""

docker-compose up -d

echo ""
echo -e "${GREEN}✅ Services started!${NC}"
echo ""

# ========================================
# Step 6: Wait for services to be healthy
# ========================================
echo -e "${BLUE}⏳ Waiting for services to be ready...${NC}"

sleep 10

# Check health
SERVICES=("gateway" "ingestion-service" "streaming-service" "search-service" "collections-service" "redis")

for service in "${SERVICES[@]}"; do
    if docker ps --format '{{.Names}}' | grep -q "vidsense-$service"; then
        echo -e "${GREEN}✓ $service is running${NC}"
    else
        echo -e "${RED}✗ $service is not running${NC}"
    fi
done

echo ""

# ========================================
# Step 7: Display access URLs
# ========================================
echo -e "${GREEN}╔═══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   🎉 VidSense Microservices Ready!               ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}🌐 Access URLs:${NC}"
echo -e "   Frontend:    ${GREEN}http://localhost${NC}"
echo -e "   API Gateway: ${GREEN}http://localhost/api${NC}"
echo -e "   Ingestion:   ${GREEN}http://localhost:8081${NC}"
echo -e "   Streaming:   ${GREEN}http://localhost:8083${NC}"
echo -e "   Search:      ${GREEN}http://localhost:8082${NC}"
echo -e "   Collections: ${GREEN}http://localhost:8084${NC}"
echo ""
echo -e "${BLUE}📊 Service Status:${NC}"
echo -e "   View logs:   ${YELLOW}docker-compose logs -f${NC}"
echo -e "   View status: ${YELLOW}docker-compose ps${NC}"
echo -e "   Stop all:    ${YELLOW}docker-compose down${NC}"
echo ""
echo -e "${BLUE}💡 Development Tips:${NC}"
echo -e "   • Source code is mounted with volumes (hot-reload enabled)"
echo -e "   • Edit files in services/* and changes reflect immediately"
echo -e "   • No rebuild needed for code changes!"
echo -e "   • Models cached in vidsense-models volume"
echo ""
echo -e "${BLUE}🔧 Useful Commands:${NC}"
echo -e "   Scale workers: ${YELLOW}docker-compose up -d --scale embedding-worker=3${NC}"
echo -e "   Restart:       ${YELLOW}docker-compose restart <service-name>${NC}"
echo -e "   Shell access:  ${YELLOW}docker exec -it vidsense-<service> /bin/bash${NC}"
echo ""

# Open browser
if command -v xdg-open &> /dev/null; then
    echo -e "${BLUE}🌐 Opening browser...${NC}"
    xdg-open http://localhost
elif command -v open &> /dev/null; then
    open http://localhost
fi

echo -e "${GREEN}✨ Setup complete! Happy coding! ✨${NC}"
