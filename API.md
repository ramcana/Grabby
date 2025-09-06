# 📡 Grabby API Documentation

Complete API reference for the Grabby video downloader REST API and WebSocket interface.

## 🌐 Base Information

- **Base URL**: `http://localhost:8000`
- **API Version**: v1
- **Content Type**: `application/json`
- **Authentication**: JWT Bearer tokens (optional)

## 📋 Quick Reference

### Core Endpoints
```
POST   /download           # Start new download
GET    /downloads          # List all downloads
GET    /downloads/{id}     # Get download status
DELETE /downloads/{id}     # Cancel download
POST   /video-info         # Extract video information
GET    /queue              # Get download queue
POST   /queue              # Add to queue
GET    /profiles           # List profiles
GET    /settings           # Get settings
GET    /stats              # System statistics
GET    /health             # Health check
WS     /ws                 # WebSocket connection
```

## 🔽 Download Management

### Start Download
```http
POST /download
Content-Type: application/json

{
  "urls": ["https://youtube.com/watch?v=example"],
  "quality": "720p",
  "profile": "default",
  "output_path": "./downloads",
  "extract_audio": false,
  "subtitles": true,
  "thumbnail": true
}
```

**Response**:
```json
{
  "download_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "Download added to queue"
}
```

### Get Download Status
```http
GET /downloads/550e8400-e29b-41d4-a716-446655440000
```

**Response**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "url": "https://youtube.com/watch?v=example",
  "title": "Example Video",
  "status": "downloading",
  "progress": 45.2,
  "speed": "1.2MB/s",
  "eta": "00:02:30",
  "file_size": 52428800,
  "downloaded": 23592960,
  "quality": "720p",
  "format": "mp4",
  "created_at": "2025-09-03T20:00:00Z",
  "started_at": "2025-09-03T20:00:05Z",
  "file_path": "./downloads/example_video.mp4"
}
```

### List Downloads
```http
GET /downloads?status=completed&limit=50&offset=0
```

**Query Parameters**:
- `status`: Filter by status (queued, downloading, completed, failed, paused)
- `limit`: Number of results (default: 50, max: 100)
- `offset`: Pagination offset (default: 0)
- `search`: Search in titles and URLs

**Response**:
```json
{
  "downloads": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "url": "https://youtube.com/watch?v=example",
      "title": "Example Video",
      "status": "completed",
      "progress": 100.0,
      "file_size": 52428800,
      "quality": "720p",
      "created_at": "2025-09-03T20:00:00Z",
      "completed_at": "2025-09-03T20:03:15Z"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

### Cancel Download
```http
DELETE /downloads/550e8400-e29b-41d4-a716-446655440000
```

**Response**:
```json
{
  "message": "Download cancelled successfully",
  "status": "cancelled"
}
```

## 📋 Queue Management

### Get Queue
```http
GET /queue
```

**Response**:
```json
{
  "queue": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "url": "https://youtube.com/watch?v=example2",
      "priority": 5,
      "status": "pending",
      "position": 1,
      "estimated_start": "2025-09-03T20:05:00Z"
    }
  ],
  "active_downloads": 2,
  "queue_size": 5,
  "max_concurrent": 3
}
```

### Add to Queue
```http
POST /queue
Content-Type: application/json

{
  "url": "https://youtube.com/watch?v=example",
  "priority": 5,
  "profile": "high_quality",
  "scheduled_time": "2025-09-03T22:00:00Z"
}
```

### Update Queue Item
```http
PATCH /queue/550e8400-e29b-41d4-a716-446655440001
Content-Type: application/json

{
  "priority": 10,
  "status": "paused"
}
```

### Remove from Queue
```http
DELETE /queue/550e8400-e29b-41d4-a716-446655440001
```

## 📹 Video Information

### Extract Video Info
```http
POST /video-info
Content-Type: application/json

{
  "url": "https://youtube.com/watch?v=example"
}
```

**Response**:
```json
{
  "title": "Example Video Title",
  "description": "Video description...",
  "uploader": "Channel Name",
  "duration": 300,
  "view_count": 1000000,
  "upload_date": "2025-09-01",
  "thumbnail": "https://img.youtube.com/vi/example/maxresdefault.jpg",
  "formats": [
    {
      "format_id": "137",
      "ext": "mp4",
      "height": 1080,
      "width": 1920,
      "filesize": 104857600,
      "fps": 30
    },
    {
      "format_id": "136",
      "ext": "mp4", 
      "height": 720,
      "width": 1280,
      "filesize": 52428800,
      "fps": 30
    }
  ],
  "subtitles": ["en", "es", "fr"],
  "chapters": [
    {
      "title": "Introduction",
      "start_time": 0,
      "end_time": 30
    }
  ]
}
```

## 👤 Profile Management

### List Profiles
```http
GET /profiles
```

**Response**:
```json
{
  "profiles": [
    {
      "name": "default",
      "description": "Default download settings",
      "quality": "best",
      "format": "mp4",
      "extract_audio": false,
      "subtitles": false,
      "thumbnail": true
    },
    {
      "name": "audio_only",
      "description": "Audio extraction only",
      "quality": "best",
      "format": "mp3",
      "extract_audio": true,
      "subtitles": false,
      "thumbnail": false
    }
  ]
}
```

### Get Profile
```http
GET /profiles/audio_only
```

### Create Profile
```http
POST /profiles
Content-Type: application/json

{
  "name": "custom_profile",
  "description": "Custom settings",
  "quality": "1080p",
  "format": "mp4",
  "extract_audio": false,
  "subtitles": true,
  "thumbnail": true,
  "output_template": "%(uploader)s - %(title)s.%(ext)s"
}
```

### Update Profile
```http
PUT /profiles/custom_profile
Content-Type: application/json

{
  "quality": "720p",
  "subtitles": false
}
```

### Delete Profile
```http
DELETE /profiles/custom_profile
```

## ⚙️ Settings Management

### Get Settings
```http
GET /settings
```

**Response**:
```json
{
  "download": {
    "max_concurrent": 3,
    "default_quality": "720p",
    "output_path": "./downloads",
    "retry_attempts": 3
  },
  "interface": {
    "theme": "dark",
    "language": "en",
    "notifications": true
  },
  "network": {
    "proxy_url": null,
    "user_agent": "Grabby/1.5.0",
    "timeout": 30,
    "rate_limit": null
  }
}
```

### Update Settings
```http
PUT /settings
Content-Type: application/json

{
  "download": {
    "max_concurrent": 5,
    "default_quality": "1080p"
  },
  "interface": {
    "theme": "light"
  }
}
```

## 📊 Statistics & Monitoring

### System Statistics
```http
GET /stats
```

**Response**:
```json
{
  "downloads": {
    "total": 1250,
    "completed": 1180,
    "failed": 45,
    "active": 3,
    "queued": 22
  },
  "storage": {
    "total_size": 52428800000,
    "available_space": 104857600000,
    "download_path": "./downloads"
  },
  "performance": {
    "average_speed": "2.5MB/s",
    "success_rate": 94.4,
    "uptime": "5d 12h 30m"
  },
  "system": {
    "cpu_usage": 15.2,
    "memory_usage": 45.8,
    "disk_usage": 67.3
  }
}
```

### Health Check
```http
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-09-03T20:00:00Z",
  "version": "1.5.0",
  "services": {
    "database": "connected",
    "redis": "connected",
    "download_engines": "available"
  }
}
```

## 🔌 WebSocket Interface

### Connection
```javascript
const socket = io('ws://localhost:8000/ws');
```

### Event Types

#### Download Progress
```json
{
  "type": "download.progress",
  "data": {
    "download_id": "550e8400-e29b-41d4-a716-446655440000",
    "progress": 45.2,
    "speed": "1.2MB/s",
    "eta": "00:02:30",
    "downloaded": 23592960,
    "total": 52428800
  }
}
```

#### Download Completed
```json
{
  "type": "download.completed",
  "data": {
    "download_id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "Example Video",
    "file_path": "./downloads/example_video.mp4",
    "file_size": 52428800,
    "duration": "00:03:15"
  }
}
```

#### Queue Updated
```json
{
  "type": "queue.updated",
  "data": {
    "queue_size": 5,
    "active_downloads": 2,
    "next_item": {
      "id": "550e8400-e29b-41d4-a716-446655440001",
      "url": "https://youtube.com/watch?v=example2"
    }
  }
}
```

#### System Status
```json
{
  "type": "system.status",
  "data": {
    "cpu_usage": 15.2,
    "memory_usage": 45.8,
    "active_downloads": 2,
    "queue_size": 5
  }
}
```

### Client Events

#### Subscribe to Download
```json
{
  "type": "subscribe",
  "data": {
    "download_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

#### Unsubscribe
```json
{
  "type": "unsubscribe",
  "data": {
    "download_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

## 🚨 Error Handling

### Error Response Format
```json
{
  "error": {
    "code": "INVALID_URL",
    "message": "The provided URL is not valid or supported",
    "details": {
      "url": "invalid-url",
      "supported_sites": ["youtube.com", "vimeo.com", "..."]
    }
  },
  "timestamp": "2025-09-03T20:00:00Z",
  "request_id": "req_123456789"
}
```

### Common Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| `INVALID_URL` | URL format is invalid | 400 |
| `UNSUPPORTED_SITE` | Site not supported | 400 |
| `DOWNLOAD_NOT_FOUND` | Download ID not found | 404 |
| `QUEUE_FULL` | Download queue is full | 429 |
| `INSUFFICIENT_SPACE` | Not enough disk space | 507 |
| `NETWORK_ERROR` | Network connectivity issue | 502 |
| `EXTRACTION_FAILED` | Video info extraction failed | 422 |
| `DOWNLOAD_FAILED` | Download process failed | 500 |

## 🔐 Authentication

### JWT Authentication (Optional)

#### Login
```http
POST /auth/login
Content-Type: application/json

{
  "username": "admin",
  "password": "password"
}
```

**Response**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

#### Using Token
```http
GET /downloads
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

## 📝 Rate Limiting

- **Default**: 100 requests per minute per IP
- **Authenticated**: 1000 requests per minute per user
- **Download**: 10 concurrent downloads per user
- **WebSocket**: 1 connection per user

### Rate Limit Headers
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1693766400
```

## 🧪 Testing

### Example cURL Commands

```bash
# Health check
curl http://localhost:8000/health

# Get video info
curl -X POST http://localhost:8000/video-info \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtube.com/watch?v=example"}'

# Start download
curl -X POST http://localhost:8000/download \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://youtube.com/watch?v=example"], "quality": "720p"}'

# Check download status
curl http://localhost:8000/downloads/550e8400-e29b-41d4-a716-446655440000
```

### Python Client Example

```python
import requests
import socketio

# REST API client
class GrabbyClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def download(self, url, quality="720p"):
        response = self.session.post(f"{self.base_url}/download", json={
            "urls": [url],
            "quality": quality
        })
        return response.json()
    
    def get_status(self, download_id):
        response = self.session.get(f"{self.base_url}/downloads/{download_id}")
        return response.json()

# WebSocket client
sio = socketio.Client()

@sio.on('download.progress')
def on_progress(data):
    print(f"Progress: {data['progress']:.1f}%")

sio.connect('http://localhost:8000')
```

---

**Last Updated**: 2025-09-03  
**Version**: 1.5.0
