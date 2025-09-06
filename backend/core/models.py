"""
Shared models and data classes for the download system
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Optional


class DownloadStatus(Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DownloadProgress:
    """Progress tracking for downloads"""
    url: str
    status: DownloadStatus = DownloadStatus.PENDING
    progress_percent: float = 0.0
    speed: str = "0 B/s"
    eta: str = "Unknown"
    downloaded_bytes: int = 0
    total_bytes: int = 0
    filename: str = ""
    error_message: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class DownloadOptions:
    """Configuration options for downloads"""
    output_path: str = "./downloads"
    format_selector: str = "best[height<=1080]"
    audio_format: str = "best"
    extract_audio: bool = False
    write_subtitles: bool = False
    write_thumbnail: bool = False
    write_info_json: bool = False
    concurrent_downloads: int = 3
    max_retries: int = 3
    custom_headers: Dict[str, str] = field(default_factory=dict)
