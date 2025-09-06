# 🎬 Grabby - Universal Video Downloader

A powerful, feature-complete video downloader with multiple interfaces supporting YouTube, TikTok, Instagram, and 1000+ platforms.

## ✨ Features Overview

- **🎯 Multi-Interface**: CLI, Desktop GUI, Web UI, REST API, and Interactive TUI
- **🚀 Smart Download Engine**: Multi-engine support with intelligent routing
- **📊 Real-time Updates**: WebSocket integration for live progress tracking
- **🎨 Modern UI**: React web frontend and advanced PyQt6 desktop interface
- **🤖 Smart Automation**: Rules engine for intelligent download management
- **📁 Profile System**: Customizable download profiles with YAML configuration
- **🔄 Queue Management**: Advanced queue with priority, scheduling, and retry logic
- **🔌 Plugin Architecture**: Extensible system for custom extractors and processors

## 🚀 Quick Start

### Automated Installation
```bash
# Run the installation script
./scripts/install.sh

# Start all services
./scripts/start.sh
```

### Manual Installation
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy configuration
cp .env.example .env
```

### Usage Options

#### 1. Web Interface (Recommended)
```bash
# Start all services
./scripts/start.sh

# Access web UI at http://localhost:3000
# API documentation at http://localhost:8000/docs
```

#### 2. Interactive TUI
```bash
# Launch modern terminal interface
python -m cli.tui_app
```

#### 3. Command Line Interface
```bash
# Basic download
python -m cli.main download "https://youtube.com/watch?v=example"

# Download with profile
python -m cli.main download "https://youtube.com/watch?v=example" --profile audio_only

# Interactive TUI mode
python -m cli.tui_app
```

#### 4. Desktop GUI
```bash
# Launch advanced desktop application
python desktop/main.py
```

#### 5. Docker Deployment
```bash
# Start with Docker Compose
docker-compose up -d

# Access web UI at http://localhost:3000
```

## 🎯 Features

### Core Download Engine
- **Universal platform support** - YouTube, TikTok, Instagram, and more
- **Async downloads** - Multiple concurrent downloads
- **Smart retry logic** - Automatic retry with exponential backoff
- **Progress tracking** - Real-time download progress
- **Quality selection** - Choose video quality and format

### CLI Interface
- **Rich terminal UI** - Beautiful progress bars and formatting
- **Batch downloads** - Multiple URLs at once
- **Quick presets** - Audio-only, HD, etc.
- **Status monitoring** - Check download history and stats

### Desktop GUI
- **Modern PyQt6 interface** - Clean, intuitive design
- **Drag & drop support** - Easy URL input
- **Real-time progress** - Live download tracking
- **System tray integration** - Minimize to tray
- **Download history** - Track all downloads

### REST API
- **FastAPI backend** - High-performance async API
- **WebSocket support** - Real-time progress updates
- **OpenAPI documentation** - Auto-generated docs
- **CORS enabled** - Web interface ready

## 📁 Project Structure

```
grabby/
├── backend/
│   ├── core/
│   │   └── downloader.py      # Core download engine
│   └── api/
│       └── fastapi_app.py     # REST API
├── cli/
│   └── main.py                # CLI interface
├── desktop/
│   └── main.py                # Desktop GUI
├── main.py                    # Main entry point
├── requirements.txt           # Dependencies
└── README.md                  # This file
```

## 🔧 Configuration

### Download Options
- **Output path** - Where to save downloads
- **Quality settings** - Video resolution and format
- **Audio extraction** - MP3, M4A, etc.
- **Subtitles** - Download subtitle files
- **Thumbnails** - Save video thumbnails
- **Concurrent downloads** - Number of simultaneous downloads

### Quality Presets
- `best` - Highest available quality
- `1080p` - Full HD
- `720p` - HD
- `480p` - Standard definition
- `audio` - Audio only

## 🌐 API Endpoints

### Core Endpoints
- `POST /download` - Start new download
- `GET /downloads` - List all downloads
- `GET /downloads/{id}` - Get download status
- `DELETE /downloads/{id}` - Cancel download
- `POST /video-info` - Get video information
- `GET /ws` - WebSocket for real-time updates

### Example API Usage
```python
import requests

# Start download
response = requests.post('http://localhost:8000/download', json={
    'urls': ['https://youtube.com/watch?v=example'],
    'quality': '720p',
    'output_path': './downloads'
})

download_id = response.json()['download_id']

# Check progress
progress = requests.get(f'http://localhost:8000/downloads/{download_id}')
print(progress.json())
```

## 🎨 Desktop GUI Features

### Main Interface
- **URL input** - Paste multiple URLs
- **Quality selection** - Choose download quality
- **Options panel** - Subtitles, thumbnails, etc.
- **Progress tracking** - Real-time download progress
- **Download log** - Detailed activity log

### System Integration
- **System tray** - Minimize to system tray
- **Notifications** - Download completion alerts
- **File browser** - Easy output directory selection
- **Clipboard integration** - Paste URLs from clipboard

## 🛠️ Development

### Running in Development
```bash
# CLI development
python main.py --help

# API development
uvicorn backend.api.fastapi_app:app --reload

# Desktop development
python desktop/main.py
```

### Adding New Extractors
The core engine uses yt-dlp, which supports 1000+ sites out of the box. Custom extractors can be added to the plugin system.

## 📊 Monitoring

### CLI Status
```bash
python main.py status
```

### API Health Check
```bash
curl http://localhost:8000/health
```

### API Statistics
```bash
curl http://localhost:8000/stats
```

## 🔒 Security Notes

- The API runs on localhost by default
- For production deployment, configure proper authentication
- CORS is enabled for development - restrict in production
- File paths are validated to prevent directory traversal

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is open source. Please respect the terms of service of the platforms you download from.

## 🆘 Troubleshooting

### Common Issues

**"yt-dlp not found"**
```bash
pip install yt-dlp
```

**"PyQt6 not available"**
```bash
pip install PyQt6 PyQt6-WebEngine
```

**"Permission denied"**
- Check output directory permissions
- Run with appropriate user privileges

**"Download failed"**
- Check internet connection
- Verify URL is valid and accessible
- Some platforms may require authentication

### Getting Help
- Check the API documentation at `/docs`
- Use `python main.py --help` for CLI options
- Enable debug logging for detailed error information

---

Built with ❤️ using Python, FastAPI, PyQt6, and yt-dlp
