# 🏗️ Grabby Architecture Documentation

Comprehensive technical architecture documentation for the Grabby video downloader system.

## 🎯 System Overview

Grabby is a multi-interface video downloader built with a modular, event-driven architecture supporting multiple engines and deployment scenarios.

### Core Principles
- **Modularity**: Loosely coupled components with clear interfaces
- **Scalability**: Horizontal scaling through queue-based architecture
- **Extensibility**: Plugin system for custom extractors and processors
- **Reliability**: Robust error handling and retry mechanisms
- **Performance**: Async operations and concurrent processing

## 📐 Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interfaces                          │
├─────────────┬─────────────┬─────────────┬─────────────────┤
│   Web UI    │  Desktop    │     CLI     │      TUI        │
│  (React)    │  (PyQt6)    │  (Click)    │   (Textual)     │
└─────────────┴─────────────┴─────────────┴─────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    API Layer                                │
├─────────────────────────────────────────────────────────────┤
│              FastAPI REST API + WebSocket                   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                  Core Services                              │
├─────────────┬─────────────┬─────────────┬─────────────────┤
│   Unified   │    Queue    │    Event    │     Rules       │
│ Downloader  │   Manager   │     Bus     │    Engine       │
└─────────────┴─────────────┴─────────────┴─────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                Download Engines                             │
├─────────────┬─────────────┬─────────────┬─────────────────┤
│   yt-dlp    │   aria2c    │ streamlink  │   gallery-dl    │
└─────────────┴─────────────┴─────────────┴─────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                 Data Layer                                  │
├─────────────┬─────────────┬─────────────┬─────────────────┤
│ PostgreSQL/ │    Redis    │    File     │    Config       │
│   SQLite    │   Cache     │   Storage   │   Profiles      │
└─────────────┴─────────────┴─────────────┴─────────────────┘
```

## 🔧 Core Components

### 1. Unified Downloader (`backend/core/unified_downloader.py`)

**Purpose**: Central download orchestration and engine selection

**Key Features**:
- Multi-engine support with intelligent routing
- Unified interface for all download operations
- Engine fallback and error handling
- Progress tracking and callbacks

**Engine Selection Logic**:
```python
def select_engine(url: str) -> str:
    if "youtube.com" in url or "youtu.be" in url:
        return "yt-dlp"  # Best for YouTube
    elif "twitch.tv" in url:
        return "streamlink"  # Live streams
    elif "instagram.com" in url:
        return "gallery-dl"  # Social media
    else:
        return "yt-dlp"  # Default fallback
```

### 2. Queue Manager (`backend/core/queue_manager.py`)

**Purpose**: Advanced queue management with priority and scheduling

**Architecture**:
- Priority-based queue with multiple levels
- Redis persistence for durability
- Bandwidth management and rate limiting
- Duplicate detection and deduplication
- Retry logic with exponential backoff

**Queue States**:
```
pending → processing → completed
    ↓         ↓           ↓
  paused → failed → retrying
```

### 3. Event Bus (`backend/core/event_bus.py`)

**Purpose**: Decoupled communication between components

**Event Flow**:
```
Component A → Event Bus → [Event Handlers] → Component B,C,D
```

**Event Categories**:
- Download lifecycle events
- Queue management events
- Plugin system events
- System status events
- Error and notification events

### 4. Rules Engine (`backend/core/rules_engine.py`)

**Purpose**: Intelligent automation and download management

**Rule Structure**:
```yaml
rule:
  name: "High Priority Music"
  conditions:
    - type: "title"
      operator: "contains"
      value: "music"
  actions:
    - type: "set_priority"
      value: 10
```

**Evaluation Pipeline**:
1. Rule matching against download metadata
2. Condition evaluation (AND/OR logic)
3. Action execution in priority order
4. Result aggregation and application

## 🌐 API Architecture

### FastAPI Application (`backend/api/fastapi_app.py`)

**Design Patterns**:
- RESTful API design
- Async/await for non-blocking operations
- WebSocket for real-time updates
- Dependency injection for services
- Automatic OpenAPI documentation

**Endpoint Categories**:
```
/downloads/*    - Download management
/queue/*        - Queue operations
/profiles/*     - Profile management
/settings/*     - Configuration
/stats          - System statistics
/health         - Health checks
/ws             - WebSocket endpoint
```

**WebSocket Events**:
```json
{
  "type": "download.progress",
  "data": {
    "download_id": "uuid",
    "progress": 45.2,
    "speed": "1.2MB/s",
    "eta": "00:02:30"
  }
}
```

## 🎨 Frontend Architecture

### Web Frontend (`web/src/`)

**Technology Stack**:
- React 18 with TypeScript
- Material-UI for components
- React Query for data fetching
- Socket.io for WebSocket communication
- React Router for navigation

**Component Hierarchy**:
```
App
├── Navbar
├── Dashboard
│   ├── DownloadForm
│   ├── RecentDownloads
│   └── SystemStats
├── Downloads
├── Queue
├── History
└── Settings
```

**State Management**:
- React Query for server state
- React Context for WebSocket connection
- Local state for UI interactions
- Persistent settings in localStorage

### Desktop GUI (`desktop/main.py`)

**Architecture**:
- PyQt6 with modern styling
- Worker threads for async operations
- System tray integration
- Drag-and-drop support

**UI Components**:
```
MainWindow
├── DownloadTab
├── QueueTab
├── HistoryTab
├── SettingsTab
└── LogTab
```

## 🔌 Plugin System

### Plugin Architecture (`backend/plugins/`)

**Plugin Types**:
1. **Extractors**: Custom site support
2. **Post-processors**: File manipulation
3. **Notifiers**: Alert systems

**Plugin Interface**:
```python
class BasePlugin:
    def __init__(self, config: dict):
        pass
    
    async def process(self, data: dict) -> dict:
        pass
    
    def get_info(self) -> dict:
        return {
            "name": "Plugin Name",
            "version": "1.0.0",
            "description": "Plugin description"
        }
```

**Plugin Discovery**:
- Automatic scanning of plugin directories
- Dynamic loading and registration
- Configuration management
- Enable/disable functionality

## 💾 Data Architecture

### Database Schema

**Core Tables**:
```sql
-- Downloads table
CREATE TABLE downloads (
    id UUID PRIMARY KEY,
    url TEXT NOT NULL,
    title TEXT,
    status VARCHAR(20),
    progress FLOAT,
    file_path TEXT,
    created_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Queue table
CREATE TABLE queue_items (
    id UUID PRIMARY KEY,
    url TEXT NOT NULL,
    priority INTEGER,
    status VARCHAR(20),
    retry_count INTEGER,
    scheduled_at TIMESTAMP
);

-- Profiles table
CREATE TABLE profiles (
    name VARCHAR(50) PRIMARY KEY,
    config JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Configuration Management

**Profile System**:
- YAML-based configuration files
- Hierarchical inheritance
- Platform-specific overrides
- Validation and schema checking

**Settings Hierarchy**:
```
System Defaults → User Profiles → Runtime Options
```

## 🚀 Deployment Architecture

### Container Architecture

**Multi-Service Setup**:
```yaml
services:
  api:        # FastAPI backend
  web:        # React frontend
  worker:     # Celery background tasks
  redis:      # Cache and queue
  postgres:   # Primary database
```

**Scaling Strategy**:
- Horizontal scaling of API and worker services
- Load balancing with nginx
- Database connection pooling
- Redis clustering for high availability

### Process Architecture

**Development Mode**:
```
Process 1: FastAPI (uvicorn)
Process 2: React Dev Server (npm start)
Process 3: Redis Server
Process 4: PostgreSQL (optional)
```

**Production Mode**:
```
Process 1: Gunicorn + FastAPI workers
Process 2: Nginx (static files + proxy)
Process 3: Celery workers
Process 4: Redis cluster
Process 5: PostgreSQL cluster
```

## 🔄 Data Flow

### Download Workflow

1. **Request Initiation**:
   ```
   User Interface → API → Unified Downloader
   ```

2. **Engine Selection**:
   ```
   URL Analysis → Engine Router → Selected Engine
   ```

3. **Queue Processing**:
   ```
   Queue Manager → Priority Sort → Worker Assignment
   ```

4. **Progress Tracking**:
   ```
   Engine Progress → Event Bus → WebSocket → UI Update
   ```

5. **Completion**:
   ```
   Download Complete → Database Update → Notification
   ```

### Event Flow

```
Component Action → Event Emission → Event Bus → Handler Registration → Handler Execution → Side Effects
```

## 🛡️ Security Architecture

### Authentication & Authorization

**API Security**:
- JWT token-based authentication
- Role-based access control (RBAC)
- Rate limiting per user/IP
- CORS configuration

**File System Security**:
- Path traversal prevention
- Download directory restrictions
- File type validation
- Quarantine for suspicious files

### Network Security

**API Protection**:
- HTTPS enforcement
- Request validation
- SQL injection prevention
- XSS protection headers

**External Requests**:
- User-Agent rotation
- Proxy support
- Request timeout limits
- Retry with backoff

## 📊 Performance Architecture

### Optimization Strategies

**Async Operations**:
- Non-blocking I/O throughout
- Connection pooling
- Batch operations
- Lazy loading

**Caching Strategy**:
```
L1: In-memory cache (application)
L2: Redis cache (distributed)
L3: Database cache (query optimization)
```

**Resource Management**:
- Connection limits per engine
- Memory usage monitoring
- Disk space management
- CPU throttling options

### Monitoring & Observability

**Metrics Collection**:
- Download success/failure rates
- Queue processing times
- System resource usage
- API response times

**Logging Strategy**:
- Structured logging (JSON)
- Log levels and filtering
- Centralized log aggregation
- Error tracking and alerting

## 🔮 Future Architecture

### Planned Enhancements

**Microservices Migration**:
- Service decomposition
- API gateway implementation
- Service mesh integration
- Independent scaling

**Advanced Features**:
- Machine learning for quality prediction
- Blockchain-based content verification
- Edge computing for global distribution
- Real-time collaboration features

---

**Last Updated**: 2025-09-03  
**Version**: 1.5.0
