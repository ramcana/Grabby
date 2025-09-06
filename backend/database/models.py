"""
Database models for Grabby Video Downloader
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from enum import Enum
import json

logger = logging.getLogger(__name__)

class DownloadStatus(Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"

class EngineType(Enum):
    YT_DLP = "yt-dlp"
    STREAMLINK = "streamlink"
    GALLERY_DL = "gallery-dl"
    RIPME = "ripme"
    ARIA2C = "aria2c"

@dataclass
class DownloadRecord:
    """Database model for download records"""
    id: Optional[int] = None
    url: str = ""
    title: str = ""
    description: str = ""
    uploader: str = ""
    upload_date: Optional[datetime] = None
    duration: Optional[int] = None  # seconds
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    
    # Download information
    status: DownloadStatus = DownloadStatus.PENDING
    engine_used: Optional[EngineType] = None
    file_path: str = ""
    file_size: Optional[int] = None  # bytes
    format_id: str = ""
    quality: str = ""
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Error information
    error_message: str = ""
    retry_count: int = 0
    
    # Metadata
    thumbnail_url: str = ""
    thumbnail_path: str = ""
    subtitles_path: str = ""
    info_json_path: str = ""
    
    # Playlist information
    playlist_id: Optional[int] = None
    playlist_index: Optional[int] = None
    
    # Additional metadata as JSON
    extra_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Download options used
    download_options: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        
        # Convert datetime objects to ISO strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat() if value else None
            elif isinstance(value, Enum):
                data[key] = value.value
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DownloadRecord':
        """Create from dictionary"""
        # Convert ISO strings back to datetime
        for key in ['created_at', 'started_at', 'completed_at', 'upload_date']:
            if data.get(key):
                data[key] = datetime.fromisoformat(data[key])
        
        # Convert enum strings back to enums
        if data.get('status'):
            data['status'] = DownloadStatus(data['status'])
        if data.get('engine_used'):
            data['engine_used'] = EngineType(data['engine_used'])
        
        return cls(**data)

@dataclass
class PlaylistRecord:
    """Database model for playlist records"""
    id: Optional[int] = None
    url: str = ""
    title: str = ""
    description: str = ""
    uploader: str = ""
    
    # Playlist information
    total_entries: int = 0
    downloaded_entries: int = 0
    failed_entries: int = 0
    
    # Status
    status: DownloadStatus = DownloadStatus.PENDING
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Metadata
    thumbnail_url: str = ""
    extra_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        
        # Convert datetime objects to ISO strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat() if value else None
            elif isinstance(value, Enum):
                data[key] = value.value
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlaylistRecord':
        """Create from dictionary"""
        # Convert ISO strings back to datetime
        for key in ['created_at', 'started_at', 'completed_at']:
            if data.get(key):
                data[key] = datetime.fromisoformat(data[key])
        
        # Convert enum strings back to enums
        if data.get('status'):
            data['status'] = DownloadStatus(data['status'])
        
        return cls(**data)

@dataclass
class UserSettings:
    """Database model for user settings"""
    id: Optional[int] = None
    key: str = ""
    value: str = ""
    value_type: str = "string"  # string, int, float, bool, json
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def get_typed_value(self) -> Any:
        """Get value with proper type conversion"""
        if self.value_type == "int":
            return int(self.value)
        elif self.value_type == "float":
            return float(self.value)
        elif self.value_type == "bool":
            return self.value.lower() in ("true", "1", "yes")
        elif self.value_type == "json":
            return json.loads(self.value)
        else:
            return self.value
    
    def set_typed_value(self, value: Any):
        """Set value with automatic type detection"""
        if isinstance(value, bool):
            self.value = str(value).lower()
            self.value_type = "bool"
        elif isinstance(value, int):
            self.value = str(value)
            self.value_type = "int"
        elif isinstance(value, float):
            self.value = str(value)
            self.value_type = "float"
        elif isinstance(value, (dict, list)):
            self.value = json.dumps(value)
            self.value_type = "json"
        else:
            self.value = str(value)
            self.value_type = "string"
        
        self.updated_at = datetime.now()

# SQL Schema definitions
DOWNLOAD_RECORDS_SCHEMA = """
CREATE TABLE IF NOT EXISTS download_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    title TEXT,
    description TEXT,
    uploader TEXT,
    upload_date TIMESTAMP,
    duration INTEGER,
    view_count INTEGER,
    like_count INTEGER,
    
    status TEXT NOT NULL DEFAULT 'pending',
    engine_used TEXT,
    file_path TEXT,
    file_size INTEGER,
    format_id TEXT,
    quality TEXT,
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    thumbnail_url TEXT,
    thumbnail_path TEXT,
    subtitles_path TEXT,
    info_json_path TEXT,
    
    playlist_id INTEGER,
    playlist_index INTEGER,
    
    extra_metadata TEXT,  -- JSON
    download_options TEXT,  -- JSON
    
    FOREIGN KEY (playlist_id) REFERENCES playlist_records (id)
);
"""

PLAYLIST_RECORDS_SCHEMA = """
CREATE TABLE IF NOT EXISTS playlist_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL UNIQUE,
    title TEXT,
    description TEXT,
    uploader TEXT,
    
    total_entries INTEGER DEFAULT 0,
    downloaded_entries INTEGER DEFAULT 0,
    failed_entries INTEGER DEFAULT 0,
    
    status TEXT NOT NULL DEFAULT 'pending',
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    thumbnail_url TEXT,
    extra_metadata TEXT  -- JSON
);
"""

USER_SETTINGS_SCHEMA = """
CREATE TABLE IF NOT EXISTS user_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL,
    value_type TEXT NOT NULL DEFAULT 'string',
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

# Indexes for better performance
INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_download_records_url ON download_records(url);",
    "CREATE INDEX IF NOT EXISTS idx_download_records_status ON download_records(status);",
    "CREATE INDEX IF NOT EXISTS idx_download_records_created_at ON download_records(created_at);",
    "CREATE INDEX IF NOT EXISTS idx_download_records_playlist_id ON download_records(playlist_id);",
    "CREATE INDEX IF NOT EXISTS idx_playlist_records_url ON playlist_records(url);",
    "CREATE INDEX IF NOT EXISTS idx_playlist_records_status ON playlist_records(status);",
    "CREATE INDEX IF NOT EXISTS idx_user_settings_key ON user_settings(key);"
]
