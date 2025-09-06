#!/bin/bash

# Grabby Video Downloader Installation Script
# This script sets up the complete Grabby environment

set -e

echo "🚀 Installing Grabby Video Downloader..."

# Check if Python 3.10+ is available
python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
if [[ $(echo "$python_version >= 3.10" | bc -l) -eq 0 ]]; then
    echo "❌ Python 3.10+ is required. Current version: $python_version"
    exit 1
fi

echo "✅ Python $python_version detected"

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
echo "📥 Installing Python dependencies..."
pip install -r requirements.txt

# Install system dependencies
echo "🔧 Installing system dependencies..."
if command -v apt-get &> /dev/null; then
    # Ubuntu/Debian
    sudo apt-get update
    sudo apt-get install -y ffmpeg aria2 nodejs npm redis-server postgresql postgresql-contrib
elif command -v yum &> /dev/null; then
    # CentOS/RHEL
    sudo yum install -y ffmpeg aria2 nodejs npm redis postgresql postgresql-server
elif command -v brew &> /dev/null; then
    # macOS
    brew install ffmpeg aria2 node redis postgresql
else
    echo "⚠️  Please install ffmpeg, aria2, nodejs, npm, redis, and postgresql manually"
fi

# Setup directories
echo "📁 Creating directories..."
mkdir -p downloads logs config/profiles

# Copy example configuration
if [ ! -f .env ]; then
    cp .env.example .env
    echo "📝 Created .env file - please configure it before running"
fi

# Install web frontend dependencies
if [ -d "web" ]; then
    echo "🌐 Installing web frontend dependencies..."
    cd web
    
    # Install Node.js if not available
    if ! command -v node &> /dev/null; then
        echo "📦 Installing Node.js..."
        curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
        sudo apt-get install -y nodejs
    fi
    
    npm install
    cd ..
fi

# Setup database (if PostgreSQL is available)
if command -v psql &> /dev/null; then
    echo "🗄️  Setting up database..."
    sudo -u postgres createdb grabby 2>/dev/null || echo "Database may already exist"
    python -c "from backend.database.database_manager import DatabaseManager; import asyncio; asyncio.run(DatabaseManager().initialize())" 2>/dev/null || echo "Database initialization will happen on first run"
fi

# Create systemd service (optional)
if [ -d "/etc/systemd/system" ] && [ "$EUID" -eq 0 ]; then
    echo "⚙️  Creating systemd service..."
    cat > /etc/systemd/system/grabby.service << EOF
[Unit]
Description=Grabby Video Downloader API
After=network.target redis.service postgresql.service

[Service]
Type=simple
User=$SUDO_USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/uvicorn backend.api.fastapi_app:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    echo "✅ Systemd service created. Enable with: sudo systemctl enable grabby"
fi

echo ""
echo "🎉 Installation complete!"
echo ""
echo "Next steps:"
echo "1. Configure .env file with your settings"
echo "2. Start the services:"
echo "   - API: uvicorn backend.api.fastapi_app:app --reload"
echo "   - Web: cd web && npm start"
echo "   - CLI: python -m cli.main --help"
echo "   - Desktop: python desktop/main.py"
echo "   - TUI: python -m cli.tui_app"
echo ""
echo "3. Or use Docker: docker-compose up -d"
echo ""
echo "📚 Check README.md for detailed usage instructions"
