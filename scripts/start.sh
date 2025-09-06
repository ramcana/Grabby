#!/bin/bash

# Grabby Video Downloader Startup Script
# Starts all services in development mode

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Grabby Video Downloader...${NC}"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Virtual environment not found. Run scripts/install.sh first.${NC}"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from example...${NC}"
    cp .env.example .env
fi

# Function to check if a port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null ; then
        return 0
    else
        return 1
    fi
}

# Start Redis if not running
if ! pgrep redis-server > /dev/null; then
    echo -e "${YELLOW}🔄 Starting Redis...${NC}"
    redis-server --daemonize yes --port 6379
    sleep 2
fi

# Start PostgreSQL if not running (optional)
if command -v pg_ctl &> /dev/null && ! pgrep postgres > /dev/null; then
    echo -e "${YELLOW}🔄 Starting PostgreSQL...${NC}"
    sudo service postgresql start 2>/dev/null || echo "PostgreSQL may already be running"
fi

# Start API server
if check_port 8000; then
    echo -e "${YELLOW}⚠️  Port 8000 is already in use${NC}"
else
    echo -e "${GREEN}🌐 Starting API server on port 8000...${NC}"
    uvicorn backend.api.fastapi_app:app --reload --host 0.0.0.0 --port 8000 &
    API_PID=$!
    echo $API_PID > .api.pid
fi

# Start web frontend if available
if [ -d "web" ] && [ -f "web/package.json" ]; then
    if check_port 3000; then
        echo -e "${YELLOW}⚠️  Port 3000 is already in use${NC}"
    else
        echo -e "${GREEN}🎨 Starting web frontend on port 3000...${NC}"
        cd web
        npm start &
        WEB_PID=$!
        echo $WEB_PID > ../.web.pid
        cd ..
    fi
fi

# Wait a moment for services to start
sleep 3

echo ""
echo -e "${GREEN}✅ Services started successfully!${NC}"
echo ""
echo -e "${BLUE}Available interfaces:${NC}"
echo -e "  🌐 Web UI:     http://localhost:3000"
echo -e "  📡 API:       http://localhost:8000"
echo -e "  📖 API Docs:  http://localhost:8000/docs"
echo -e "  💻 CLI:       python -m cli.main --help"
echo -e "  🖥️  Desktop:   python desktop/main.py"
echo -e "  📺 TUI:       python -m cli.tui_app"
echo ""
echo -e "${YELLOW}To stop services, run: scripts/stop.sh${NC}"
echo -e "${YELLOW}To view logs: tail -f logs/grabby.log${NC}"
