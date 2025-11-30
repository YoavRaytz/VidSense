#!/bin/bash
# VidSense Docker Compose Restart Script
# This script ensures the external database container (2f) is properly connected
# to the VidSense network before starting services

set -e  # Exit on any error

echo "=========================================="
echo "VidSense Docker Compose Restart Script"
echo "=========================================="
echo ""

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
DB_CONTAINER="pgvector"
NETWORK_NAME="vidsense_vidsense-network"
DB_ALIASES="postgres pgvector database"

# Step 1: Stop all VidSense services
echo -e "${YELLOW}[1/5]${NC} Stopping VidSense services..."
sudo docker-compose down --remove-orphans 2>/dev/null || true
echo -e "${GREEN}✓${NC} Services stopped"
echo ""

# Step 2: Check if database container exists
echo -e "${YELLOW}[2/5]${NC} Checking database container '${DB_CONTAINER}'..."
if ! sudo docker ps -a --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
    echo -e "${RED}✗${NC} Container '${DB_CONTAINER}' not found!"
    echo "Please ensure the database container is running."
    exit 1
fi

# Check if container is running
if ! sudo docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
    echo -e "${YELLOW}!${NC} Container '${DB_CONTAINER}' is not running."
    echo "Fixing broken network references..."
    
    # Stop the container if it's in a bad state
    sudo docker stop "${DB_CONTAINER}" 2>/dev/null || true
    
    # Get the container ID for direct manipulation
    CONTAINER_ID=$(sudo docker ps -a --filter "name=^${DB_CONTAINER}$" --format "{{.ID}}")
    
    # Disconnect from ALL networks including broken ones
    echo "Clearing ALL network connections (including broken ones)..."
    
    # Get all network names the container thinks it's connected to
    NETWORKS=$(sudo docker inspect "${CONTAINER_ID}" --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}} {{end}}' 2>/dev/null || echo "")
    
    for net in $NETWORKS; do
        echo "  Disconnecting from: $net"
        sudo docker network disconnect -f "$net" "${CONTAINER_ID}" 2>/dev/null || true
    done
    
    # Also try to disconnect from common networks by name
    sudo docker network disconnect -f bridge "${CONTAINER_ID}" 2>/dev/null || true
    sudo docker network disconnect -f vidsense_vidsense-network "${CONTAINER_ID}" 2>/dev/null || true
    sudo docker network disconnect -f vidsense-network "${CONTAINER_ID}" 2>/dev/null || true
    
    # Now start it fresh - it will connect to default bridge network
    echo "Starting container on default bridge network..."
    sudo docker start "${CONTAINER_ID}"
    
    # Wait for container to be fully started
    echo "Waiting for database to be ready..."
    for i in {1..10}; do
        if sudo docker exec "${CONTAINER_ID}" pg_isready -U tips 2>/dev/null; then
            echo -e "${GREEN}✓${NC} Database is ready"
            break
        fi
        echo "  Waiting... ($i/10)"
        sleep 2
    done
fi
echo -e "${GREEN}✓${NC} Database container is running"
echo ""

# Step 3: Disconnect from network (ignore errors if not connected)
echo -e "${YELLOW}[3/5]${NC} Disconnecting database from VidSense network..."
sudo docker network disconnect "${NETWORK_NAME}" "${DB_CONTAINER}" 2>/dev/null || true
echo -e "${GREEN}✓${NC} Disconnected (or was not connected)"
echo ""

# Step 4: Create network if it doesn't exist and connect with proper aliases
echo -e "${YELLOW}[4/5]${NC} Connecting database to VidSense network with aliases..."
# Create network if it doesn't exist
sudo docker network inspect "${NETWORK_NAME}" >/dev/null 2>&1 || sudo docker network create "${NETWORK_NAME}"

# Connect with all aliases
sudo docker network connect \
    --alias postgres \
    --alias pgvector \
    --alias database \
    "${NETWORK_NAME}" \
    "${DB_CONTAINER}"

echo -e "${GREEN}✓${NC} Connected with aliases: postgres, pgvector, database"
echo ""

# Step 5: Verify docker-compose.yml uses correct hostname
echo -e "${YELLOW}[5/5]${NC} Verifying docker-compose.yml configuration..."
if grep -q "DATABASE_URL=.*@postgres:5432" docker-compose.yml; then
    echo -e "${GREEN}✓${NC} docker-compose.yml is configured correctly"
else
    echo -e "${YELLOW}!${NC} Updating docker-compose.yml to use @postgres hostname..."
    # Replace any other hostname with postgres
    sed -i 's|@pgvector:5432|@postgres:5432|g' docker-compose.yml
    sed -i 's|@172\.20\.0\.[0-9]*:5432|@postgres:5432|g' docker-compose.yml
    sed -i 's|@database:5432|@postgres:5432|g' docker-compose.yml
    echo -e "${GREEN}✓${NC} docker-compose.yml updated"
fi
echo ""

# Step 6: Start VidSense services
echo -e "${YELLOW}[6/6]${NC} Starting VidSense services..."
sudo docker-compose up -d
echo -e "${GREEN}✓${NC} Services started"
echo ""

# Step 7: Wait for services to be ready
echo "Waiting for services to initialize..."
sleep 5

# Step 8: Show service status
echo ""
echo "=========================================="
echo "Service Status:"
echo "=========================================="
sudo docker-compose ps
echo ""

# Step 9: Test database connectivity
echo "=========================================="
echo "Testing Database Connectivity:"
echo "=========================================="
echo "Testing from ingestion service..."

# Wait a bit more for services to fully start
sleep 3

# Test connection using a simpler method
if sudo docker-compose exec -T ingestion-service python3 -c "
import psycopg
try:
    conn = psycopg.connect('host=postgres port=5432 dbname=tipsdb user=tips password=tips123')
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM videos')
    count = cur.fetchone()[0]
    print(f'✓ Successfully connected! Videos in database: {count}')
    cur.close()
    conn.close()
except Exception as e:
    print(f'✗ Connection failed: {e}')
    exit(1)
" 2>/dev/null; then
    echo -e "${GREEN}✓${NC} Database connectivity verified!"
else
    echo -e "${YELLOW}!${NC} Could not verify database connection (services may still be starting)"
    echo "You can manually test with: sudo docker-compose exec ingestion-service python3 -c \"import psycopg; conn = psycopg.connect('host=postgres port=5432 dbname=tipsdb user=tips password=tips123'); print('Connected!')\""
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✓ Restart complete!${NC}"
echo "=========================================="
echo ""
echo "VidSense is now running at:"
echo "  - Frontend: http://localhost:5173"
echo "  - Gateway:  http://localhost:80"
echo ""
echo "To view logs: sudo docker-compose logs -f [service-name]"
echo "To stop:      sudo docker-compose down"
echo ""
