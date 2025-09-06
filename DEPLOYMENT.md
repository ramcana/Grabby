# 🚀 Grabby Deployment Guide

Complete deployment guide for the Grabby video downloader across different environments.

## 📋 Prerequisites

### System Requirements
- **OS**: Linux (Ubuntu 20.04+), macOS, or Windows with WSL2
- **Python**: 3.10 or higher
- **Node.js**: 18+ (for web frontend)
- **Memory**: 2GB RAM minimum, 4GB recommended
- **Storage**: 10GB free space minimum
- **Network**: Internet connection for video downloads

### External Dependencies
- **ffmpeg** - Video/audio processing
- **aria2** - High-speed downloads (optional)
- **Redis** - Queue management (optional, uses in-memory fallback)
- **PostgreSQL** - Database (optional, uses SQLite fallback)

## 🎯 Deployment Options

### 1. Quick Start (Recommended)

```bash
# Clone and setup
git clone <repository-url> grabby
cd grabby

# Automated installation
./scripts/install.sh

# Start all services
./scripts/start.sh
```

**Access Points:**
- Web UI: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 2. Docker Deployment

```bash
# Start with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

**Services Included:**
- API server (port 8000)
- Web frontend (port 3000)
- Redis cache
- PostgreSQL database
- Celery worker

### 3. Manual Installation

#### Step 1: Environment Setup
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install Python dependencies
pip install -r requirements.txt
```

#### Step 2: System Dependencies
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y ffmpeg aria2 nodejs npm redis-server postgresql

# macOS (with Homebrew)
brew install ffmpeg aria2 node redis postgresql

# Windows (with Chocolatey)
choco install ffmpeg aria2 nodejs redis postgresql
```

#### Step 3: Configuration
```bash
# Copy environment configuration
cp .env.example .env

# Edit configuration (see Configuration section below)
nano .env
```

#### Step 4: Database Setup (Optional)
```bash
# PostgreSQL setup
sudo -u postgres createdb grabby
sudo -u postgres createuser grabby

# Or use SQLite (default)
# No additional setup required
```

#### Step 5: Web Frontend
```bash
cd web
npm install
npm run build
cd ..
```

#### Step 6: Start Services
```bash
# Start API server
uvicorn backend.api.fastapi_app:app --host 0.0.0.0 --port 8000

# Start web server (in another terminal)
cd web && npm start

# Or use the start script
./scripts/start.sh
```

## ⚙️ Configuration

### Environment Variables (.env)

```bash
# Database Configuration
DATABASE_URL=sqlite:///./grabby.db
# DATABASE_URL=postgresql://grabby:password@localhost:5432/grabby

# Redis Configuration (optional)
REDIS_URL=redis://localhost:6379

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
SECRET_KEY=your-secret-key-here

# Download Configuration
DOWNLOAD_DIR=./downloads
MAX_CONCURRENT_DOWNLOADS=3
MAX_QUEUE_SIZE=100

# Engine Configuration
DEFAULT_ENGINE=yt-dlp
ENABLE_MULTI_ENGINE=true

# Security
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
ALLOWED_HOSTS=localhost,127.0.0.1

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/grabby.log
```

### Download Profiles

Profiles are stored in `config/profiles/` as YAML files:

```yaml
# config/profiles/high_quality.yaml
name: "High Quality"
quality: "1080p"
format: "mp4"
extract_audio: false
subtitles: true
thumbnail: true
output_template: "%(uploader)s - %(title)s.%(ext)s"
```

### Rules Configuration

Smart rules are stored in `config/rules.json`:

```json
{
  "rules": [
    {
      "name": "Music Videos",
      "enabled": true,
      "conditions": [
        {"type": "title", "operator": "contains", "value": "music"}
      ],
      "actions": [
        {"type": "set_profile", "value": "audio_only"}
      ]
    }
  ]
}
```

## 🐳 Docker Configuration

### docker-compose.yml Customization

```yaml
version: '3.8'
services:
  api:
    environment:
      - MAX_CONCURRENT_DOWNLOADS=5
      - DOWNLOAD_DIR=/app/downloads
    volumes:
      - ./downloads:/app/downloads
      - ./config:/app/config
    ports:
      - "8000:8000"
```

### Custom Docker Build

```dockerfile
# Custom API Dockerfile
FROM python:3.11-slim

# Add custom dependencies
RUN apt-get update && apt-get install -y \
    your-custom-package

# Copy custom configuration
COPY custom-config/ /app/config/
```

## 🔒 Production Security

### SSL/TLS Setup

```nginx
# nginx configuration
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:3000;
    }
    
    location /api/ {
        proxy_pass http://localhost:8000/;
    }
}
```

### Authentication Setup

```python
# Add to .env
ENABLE_AUTH=true
JWT_SECRET_KEY=your-jwt-secret
ADMIN_USERNAME=admin
ADMIN_PASSWORD=secure-password
```

### Firewall Configuration

```bash
# Ubuntu UFW
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw deny 8000   # Block direct API access
sudo ufw enable
```

## 📊 Monitoring & Logging

### Log Configuration

```bash
# Create log directory
mkdir -p logs

# Configure log rotation
sudo nano /etc/logrotate.d/grabby
```

### Health Monitoring

```bash
# Health check script
#!/bin/bash
curl -f http://localhost:8000/health || exit 1
curl -f http://localhost:3000 || exit 1
```

### Performance Monitoring

```bash
# Run performance tests
python tests/test_performance.py

# Monitor system resources
htop
iotop
```

## 🔧 Maintenance

### Backup Procedures

```bash
# Backup database
pg_dump grabby > backup_$(date +%Y%m%d).sql

# Backup configuration
tar -czf config_backup.tar.gz config/ .env

# Backup downloads (optional)
rsync -av downloads/ /backup/location/
```

### Updates

```bash
# Update codebase
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade
cd web && npm update && cd ..

# Restart services
./scripts/stop.sh
./scripts/start.sh
```

### Cleanup

```bash
# Clean old downloads
find downloads/ -mtime +30 -delete

# Clean logs
find logs/ -name "*.log" -mtime +7 -delete

# Clean Docker
docker system prune -f
```

## 🚨 Troubleshooting

### Common Issues

**Port already in use:**
```bash
# Find process using port
lsof -i :8000
kill -9 <PID>
```

**Permission denied:**
```bash
# Fix permissions
chmod +x scripts/*.sh
chown -R $USER:$USER downloads/
```

**Database connection failed:**
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Reset database
dropdb grabby && createdb grabby
```

**Out of disk space:**
```bash
# Check disk usage
df -h
du -sh downloads/

# Clean up
./scripts/cleanup.sh
```

### Performance Issues

**High memory usage:**
- Reduce `MAX_CONCURRENT_DOWNLOADS`
- Enable Redis for queue management
- Monitor with `htop`

**Slow downloads:**
- Check network connection
- Enable aria2 engine
- Adjust quality settings

**API timeouts:**
- Increase timeout values
- Check system resources
- Review error logs

## 📞 Support

### Log Analysis

```bash
# View API logs
tail -f logs/grabby.log

# View system logs
journalctl -u grabby -f

# View Docker logs
docker-compose logs -f api
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with debug
python -m backend.api.fastapi_app --debug
```

### Getting Help

1. Check logs for error messages
2. Review configuration files
3. Run diagnostic tests: `./scripts/test.sh`
4. Check system resources: `htop`, `df -h`
5. Verify network connectivity

---

**Last Updated**: 2025-09-03  
**Version**: 1.5.0
