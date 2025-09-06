"""
Enhanced Queue Management System with Redis/RAM
Priority queues, bandwidth management, auto-retry, and playlist intelligence
"""
import asyncio
import logging
import json
import time
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import re
from collections import defaultdict, deque
import heapq

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)

class QueuePriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

class QueueStatus(Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    PAUSED = "paused"

@dataclass
class QueueItem:
    """Individual download queue item"""
    id: str
    url: str
    priority: QueuePriority = QueuePriority.NORMAL
    status: QueueStatus = QueueStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    error_message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    download_options: Dict[str, Any] = field(default_factory=dict)
    
    # Bandwidth management
    bandwidth_limit: Optional[int] = None  # bytes per second
    estimated_size: Optional[int] = None
    
    # Playlist information
    playlist_id: Optional[str] = None
    playlist_index: Optional[int] = None
    
    def __lt__(self, other):
        """For priority queue ordering"""
        if self.priority.value != other.priority.value:
            return self.priority.value > other.priority.value  # Higher priority first
        return self.created_at < other.created_at  # FIFO for same priority

@dataclass
class BandwidthManager:
    """Manages bandwidth allocation across downloads"""
    total_limit: Optional[int] = None  # bytes per second
    allocated: int = 0
    active_downloads: Dict[str, int] = field(default_factory=dict)
    
    def can_allocate(self, item_id: str, requested: int) -> bool:
        """Check if bandwidth can be allocated"""
        if self.total_limit is None:
            return True
        
        current_usage = self.allocated - self.active_downloads.get(item_id, 0)
        return current_usage + requested <= self.total_limit
    
    def allocate(self, item_id: str, amount: int) -> bool:
        """Allocate bandwidth to a download"""
        if self.can_allocate(item_id, amount):
            self.active_downloads[item_id] = amount
            self.allocated = sum(self.active_downloads.values())
            return True
        return False
    
    def release(self, item_id: str):
        """Release bandwidth from a download"""
        if item_id in self.active_downloads:
            del self.active_downloads[item_id]
            self.allocated = sum(self.active_downloads.values())

class PlaylistDetector:
    """Detects and handles playlist URLs"""
    
    PLAYLIST_PATTERNS = {
        'youtube': [
            r'youtube\.com/playlist\?list=',
            r'youtube\.com/watch\?.*&list=',
        ],
        'spotify': [
            r'spotify\.com/playlist/',
            r'spotify\.com/album/',
        ],
        'soundcloud': [
            r'soundcloud\.com/.*/sets/',
        ]
    }
    
    @classmethod
    def detect_playlist(cls, url: str) -> Optional[str]:
        """Detect if URL is a playlist and return platform"""
        for platform, patterns in cls.PLAYLIST_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return platform
        return None
    
    @classmethod
    def extract_playlist_id(cls, url: str) -> Optional[str]:
        """Extract playlist ID from URL"""
        # YouTube playlist
        match = re.search(r'list=([^&]+)', url)
        if match:
            return match.group(1)
        
        # Spotify playlist/album
        match = re.search(r'/(playlist|album)/([^/?]+)', url)
        if match:
            return match.group(2)
        
        # SoundCloud set
        match = re.search(r'/sets/([^/?]+)', url)
        if match:
            return match.group(1)
        
        return None

class DuplicateDetector:
    """Detects duplicate downloads"""
    
    def __init__(self):
        self.url_hashes: Set[str] = set()
        self.title_hashes: Set[str] = set()
    
    def _hash_url(self, url: str) -> str:
        """Create hash of normalized URL"""
        # Normalize URL (remove tracking parameters, etc.)
        normalized = re.sub(r'[?&](utm_|ref|source)=[^&]*', '', url.lower())
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _hash_title(self, title: str) -> str:
        """Create hash of normalized title"""
        # Normalize title (remove special chars, lowercase)
        normalized = re.sub(r'[^\w\s]', '', title.lower()).strip()
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def is_duplicate_url(self, url: str) -> bool:
        """Check if URL is duplicate"""
        url_hash = self._hash_url(url)
        return url_hash in self.url_hashes
    
    def is_duplicate_title(self, title: str) -> bool:
        """Check if title is duplicate"""
        title_hash = self._hash_title(title)
        return title_hash in self.title_hashes
    
    def add_url(self, url: str):
        """Add URL to duplicate detection"""
        self.url_hashes.add(self._hash_url(url))
    
    def add_title(self, title: str):
        """Add title to duplicate detection"""
        self.title_hashes.add(self._hash_title(title))

class RetryManager:
    """Manages retry logic with exponential backoff"""
    
    def __init__(self, base_delay: float = 1.0, max_delay: float = 300.0):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.retry_times: Dict[str, datetime] = {}
    
    def should_retry(self, item: QueueItem) -> bool:
        """Check if item should be retried"""
        if item.retry_count >= item.max_retries:
            return False
        
        # Check if enough time has passed for retry
        if item.id in self.retry_times:
            next_retry = self.retry_times[item.id]
            return datetime.now() >= next_retry
        
        return True
    
    def schedule_retry(self, item: QueueItem):
        """Schedule next retry with exponential backoff"""
        delay = min(
            self.base_delay * (2 ** item.retry_count),
            self.max_delay
        )
        
        self.retry_times[item.id] = datetime.now() + timedelta(seconds=delay)
        item.retry_count += 1
        item.status = QueueStatus.RETRYING
        
        logger.info(f"Scheduled retry for {item.url} in {delay:.1f}s (attempt {item.retry_count})")

class EnhancedQueueManager:
    """
    Enhanced queue management system with Redis/RAM support
    """
    
    def __init__(self, 
                 redis_url: Optional[str] = None,
                 max_concurrent: int = 3,
                 bandwidth_limit: Optional[int] = None):
        
        self.max_concurrent = max_concurrent
        self.bandwidth_manager = BandwidthManager(total_limit=bandwidth_limit)
        self.duplicate_detector = DuplicateDetector()
        self.retry_manager = RetryManager()
        
        # Queue storage
        self.priority_queue: List[QueueItem] = []
        self.items: Dict[str, QueueItem] = {}
        self.active_downloads: Dict[str, QueueItem] = {}
        
        # Redis connection
        self.redis_client = None
        if redis_url and REDIS_AVAILABLE:
            self.redis_client = redis.from_url(redis_url)
        
        # Event callbacks
        self.status_callbacks: List[Callable[[QueueItem], None]] = []
        
        # Statistics
        self.stats = {
            'total_added': 0,
            'total_completed': 0,
            'total_failed': 0,
            'duplicates_skipped': 0,
            'bandwidth_used': 0
        }
    
    async def initialize(self):
        """Initialize the queue manager"""
        if self.redis_client:
            try:
                await self.redis_client.ping()
                logger.info("Connected to Redis for queue persistence")
                await self._load_from_redis()
            except Exception as e:
                logger.warning(f"Redis connection failed, using in-memory queue: {e}")
                self.redis_client = None
    
    def add_status_callback(self, callback: Callable[[QueueItem], None]):
        """Add callback for status updates"""
        self.status_callbacks.append(callback)
    
    def _notify_status_change(self, item: QueueItem):
        """Notify all callbacks of status change"""
        for callback in self.status_callbacks:
            try:
                callback(item)
            except Exception as e:
                logger.error(f"Error in status callback: {e}")
    
    async def add_item(self, 
                      url: str, 
                      priority: QueuePriority = QueuePriority.NORMAL,
                      download_options: Optional[Dict] = None,
                      skip_duplicates: bool = True) -> Optional[str]:
        """Add item to download queue"""
        
        # Check for duplicates
        if skip_duplicates and self.duplicate_detector.is_duplicate_url(url):
            self.stats['duplicates_skipped'] += 1
            logger.info(f"Skipping duplicate URL: {url}")
            return None
        
        # Generate unique ID
        item_id = hashlib.md5(f"{url}{time.time()}".encode()).hexdigest()[:12]
        
        # Detect playlist
        playlist_platform = PlaylistDetector.detect_playlist(url)
        playlist_id = PlaylistDetector.extract_playlist_id(url) if playlist_platform else None
        
        # Create queue item
        item = QueueItem(
            id=item_id,
            url=url,
            priority=priority,
            download_options=download_options or {},
            playlist_id=playlist_id
        )
        
        # Add to queue
        heapq.heappush(self.priority_queue, item)
        self.items[item_id] = item
        self.duplicate_detector.add_url(url)
        
        self.stats['total_added'] += 1
        
        # Persist to Redis
        if self.redis_client:
            await self._save_item_to_redis(item)
        
        self._notify_status_change(item)
        logger.info(f"Added to queue: {url} (ID: {item_id}, Priority: {priority.name})")
        
        return item_id
    
    async def add_playlist(self, 
                          playlist_url: str,
                          priority: QueuePriority = QueuePriority.NORMAL,
                          download_options: Optional[Dict] = None) -> List[str]:
        """Add playlist items to queue"""
        
        # This would integrate with the downloader to extract playlist items
        # For now, we'll simulate playlist detection
        playlist_id = PlaylistDetector.extract_playlist_id(playlist_url)
        if not playlist_id:
            # Treat as single item
            item_id = await self.add_item(playlist_url, priority, download_options)
            return [item_id] if item_id else []
        
        # TODO: Integrate with actual playlist extraction
        # For now, return single item
        item_id = await self.add_item(playlist_url, priority, download_options)
        return [item_id] if item_id else []
    
    async def get_next_item(self) -> Optional[QueueItem]:
        """Get next item for download"""
        
        # Check if we can start more downloads
        if len(self.active_downloads) >= self.max_concurrent:
            return None
        
        # Find next available item
        while self.priority_queue:
            item = heapq.heappop(self.priority_queue)
            
            # Skip if item was removed
            if item.id not in self.items:
                continue
            
            # Skip if already active
            if item.id in self.active_downloads:
                continue
            
            # Check retry timing
            if item.status == QueueStatus.RETRYING:
                if not self.retry_manager.should_retry(item):
                    # Put back in queue for later
                    heapq.heappush(self.priority_queue, item)
                    continue
            
            # Check bandwidth availability
            bandwidth_needed = item.bandwidth_limit or 1024 * 1024  # 1MB default
            if not self.bandwidth_manager.can_allocate(item.id, bandwidth_needed):
                # Put back in queue
                heapq.heappush(self.priority_queue, item)
                return None
            
            # Allocate bandwidth and mark as active
            self.bandwidth_manager.allocate(item.id, bandwidth_needed)
            self.active_downloads[item.id] = item
            item.status = QueueStatus.DOWNLOADING
            item.started_at = datetime.now()
            
            # Persist state
            if self.redis_client:
                await self._save_item_to_redis(item)
            
            self._notify_status_change(item)
            return item
        
        return None
    
    async def complete_item(self, item_id: str, success: bool = True, error_message: str = ""):
        """Mark item as completed or failed"""
        
        if item_id not in self.items:
            return
        
        item = self.items[item_id]
        
        # Release bandwidth
        self.bandwidth_manager.release(item_id)
        
        # Remove from active downloads
        if item_id in self.active_downloads:
            del self.active_downloads[item_id]
        
        if success:
            item.status = QueueStatus.COMPLETED
            item.completed_at = datetime.now()
            self.stats['total_completed'] += 1
            
            # Add title to duplicate detection if available
            if 'title' in item.metadata:
                self.duplicate_detector.add_title(item.metadata['title'])
                
        else:
            item.error_message = error_message
            
            # Try to retry
            if self.retry_manager.should_retry(item):
                self.retry_manager.schedule_retry(item)
                # Put back in queue
                heapq.heappush(self.priority_queue, item)
            else:
                item.status = QueueStatus.FAILED
                self.stats['total_failed'] += 1
        
        # Persist state
        if self.redis_client:
            await self._save_item_to_redis(item)
        
        self._notify_status_change(item)
    
    async def cancel_item(self, item_id: str):
        """Cancel a queued or active download"""
        
        if item_id not in self.items:
            return False
        
        item = self.items[item_id]
        
        # Release bandwidth if active
        if item_id in self.active_downloads:
            self.bandwidth_manager.release(item_id)
            del self.active_downloads[item_id]
        
        item.status = QueueStatus.CANCELLED
        item.completed_at = datetime.now()
        
        # Persist state
        if self.redis_client:
            await self._save_item_to_redis(item)
        
        self._notify_status_change(item)
        return True
    
    async def pause_item(self, item_id: str):
        """Pause a download"""
        if item_id in self.items:
            self.items[item_id].status = QueueStatus.PAUSED
            self._notify_status_change(self.items[item_id])
    
    async def resume_item(self, item_id: str):
        """Resume a paused download"""
        if item_id in self.items:
            item = self.items[item_id]
            if item.status == QueueStatus.PAUSED:
                item.status = QueueStatus.PENDING
                heapq.heappush(self.priority_queue, item)
                self._notify_status_change(item)
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        
        status_counts = defaultdict(int)
        for item in self.items.values():
            status_counts[item.status.value] += 1
        
        return {
            'total_items': len(self.items),
            'active_downloads': len(self.active_downloads),
            'queue_length': len(self.priority_queue),
            'status_breakdown': dict(status_counts),
            'bandwidth_usage': {
                'allocated': self.bandwidth_manager.allocated,
                'limit': self.bandwidth_manager.total_limit,
                'active_downloads': len(self.bandwidth_manager.active_downloads)
            },
            'statistics': self.stats.copy()
        }
    
    def get_items_by_status(self, status: QueueStatus) -> List[QueueItem]:
        """Get all items with specific status"""
        return [item for item in self.items.values() if item.status == status]
    
    async def clear_completed(self):
        """Remove completed items from queue"""
        completed_ids = [
            item_id for item_id, item in self.items.items()
            if item.status in [QueueStatus.COMPLETED, QueueStatus.FAILED, QueueStatus.CANCELLED]
        ]
        
        for item_id in completed_ids:
            del self.items[item_id]
            if self.redis_client:
                await self.redis_client.delete(f"queue_item:{item_id}")
    
    # Redis persistence methods
    async def _save_item_to_redis(self, item: QueueItem):
        """Save item to Redis"""
        if not self.redis_client:
            return
        
        try:
            data = asdict(item)
            # Convert datetime objects to ISO strings
            for key, value in data.items():
                if isinstance(value, datetime):
                    data[key] = value.isoformat() if value else None
            
            await self.redis_client.set(
                f"queue_item:{item.id}",
                json.dumps(data, default=str),
                ex=86400 * 7  # 7 days expiry
            )
        except Exception as e:
            logger.error(f"Failed to save item to Redis: {e}")
    
    async def _load_from_redis(self):
        """Load queue state from Redis"""
        if not self.redis_client:
            return
        
        try:
            keys = await self.redis_client.keys("queue_item:*")
            for key in keys:
                data = await self.redis_client.get(key)
                if data:
                    item_data = json.loads(data)
                    
                    # Convert ISO strings back to datetime
                    for key in ['created_at', 'started_at', 'completed_at']:
                        if item_data.get(key):
                            item_data[key] = datetime.fromisoformat(item_data[key])
                    
                    # Convert priority back to enum
                    item_data['priority'] = QueuePriority(item_data['priority'])
                    item_data['status'] = QueueStatus(item_data['status'])
                    
                    item = QueueItem(**item_data)
                    self.items[item.id] = item
                    
                    # Add to appropriate queue
                    if item.status == QueueStatus.PENDING:
                        heapq.heappush(self.priority_queue, item)
                    elif item.status == QueueStatus.DOWNLOADING:
                        self.active_downloads[item.id] = item
            
            logger.info(f"Loaded {len(self.items)} items from Redis")
            
        except Exception as e:
            logger.error(f"Failed to load from Redis: {e}")

# Example usage
async def main():
    """Example usage of enhanced queue manager"""
    
    # Initialize queue manager
    queue_manager = EnhancedQueueManager(
        max_concurrent=3,
        bandwidth_limit=10 * 1024 * 1024  # 10 MB/s
    )
    
    await queue_manager.initialize()
    
    # Add progress callback
    def on_status_change(item: QueueItem):
        print(f"Status update: {item.url} -> {item.status.value}")
    
    queue_manager.add_status_callback(on_status_change)
    
    # Add some test items
    urls = [
        "https://youtube.com/watch?v=example1",
        "https://youtube.com/watch?v=example2",
        "https://youtube.com/playlist?list=example",
    ]
    
    for i, url in enumerate(urls):
        priority = QueuePriority.HIGH if i == 0 else QueuePriority.NORMAL
        await queue_manager.add_item(url, priority=priority)
    
    # Process queue
    while True:
        item = await queue_manager.get_next_item()
        if not item:
            break
        
        print(f"Processing: {item.url}")
        
        # Simulate download
        await asyncio.sleep(1)
        
        # Mark as completed
        await queue_manager.complete_item(item.id, success=True)
    
    # Show final status
    status = queue_manager.get_queue_status()
    print(f"Queue status: {status}")

if __name__ == "__main__":
    asyncio.run(main())
