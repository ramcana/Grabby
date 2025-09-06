#!/bin/bash

# Grabby Video Downloader Stop Script
# Stops all running services

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛑 Stopping Grabby Video Downloader services...${NC}"

# Stop API server
if [ -f ".api.pid" ]; then
    API_PID=$(cat .api.pid)
    if kill -0 $API_PID 2>/dev/null; then
        echo -e "${YELLOW}🔄 Stopping API server (PID: $API_PID)...${NC}"
        kill $API_PID
        rm .api.pid
    else
        echo -e "${YELLOW}⚠️  API server not running${NC}"
        rm -f .api.pid
    fi
fi

# Stop web frontend
if [ -f ".web.pid" ]; then
    WEB_PID=$(cat .web.pid)
    if kill -0 $WEB_PID 2>/dev/null; then
        echo -e "${YELLOW}🔄 Stopping web frontend (PID: $WEB_PID)...${NC}"
        kill $WEB_PID
        rm .web.pid
    else
        echo -e "${YELLOW}⚠️  Web frontend not running${NC}"
        rm -f .web.pid
    fi
fi

# Stop any remaining uvicorn processes
pkill -f "uvicorn.*fastapi_app" 2>/dev/null || true

# Stop any remaining npm processes for this project
pkill -f "npm.*start" 2>/dev/null || true

# Optional: Stop Redis and PostgreSQL if they were started by the script
if [ "$1" = "--all" ]; then
    echo -e "${YELLOW}🔄 Stopping Redis and PostgreSQL...${NC}"
    pkill redis-server 2>/dev/null || true
    sudo service postgresql stop 2>/dev/null || true
fi

echo -e "${GREEN}✅ All services stopped successfully!${NC}"

# Clean up any remaining PID files
rm -f .api.pid .web.pid

echo -e "${BLUE}💡 To start services again, run: scripts/start.sh${NC}"
