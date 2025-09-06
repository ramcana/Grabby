#!/bin/bash

# Setup script for Grabby Video Downloader

echo "🎬 Setting up Grabby Video Downloader..."

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install core dependencies first
echo "📥 Installing core dependencies..."
pip install yt-dlp aiohttp asyncio-mqtt pydantic python-dotenv

# Install CLI dependencies
echo "🖥️ Installing CLI dependencies..."
pip install click rich textual

# Install API dependencies
echo "🌐 Installing API dependencies..."
pip install fastapi uvicorn websockets

# Install database dependencies
echo "🗄️ Installing database dependencies..."
pip install sqlalchemy aiosqlite alembic

# Install optional GUI dependencies (may fail on headless systems)
echo "🖼️ Installing GUI dependencies (optional)..."
pip install PyQt6 PyQt6-WebEngine || echo "⚠️ GUI dependencies failed - desktop interface won't be available"

# Install remaining utilities
echo "🔧 Installing utilities..."
pip install pathlib2 httpx python-multipart jinja2

echo "✅ Setup complete!"
echo ""
echo "🚀 Quick start:"
echo "  source venv/bin/activate"
echo "  python main.py --help"
echo ""
echo "🌐 Start API server:"
echo "  python backend/api/fastapi_app.py"
echo ""
echo "🖥️ Launch desktop GUI:"
echo "  python desktop/main.py"
