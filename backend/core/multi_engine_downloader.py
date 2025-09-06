"""
Multi-Engine Download Manager Integration
Integrates the multi-engine system with our existing queue and plugin architecture
"""
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import sys

# Import the multi-engine system
sys.path.append(str(Path(__file__).parent.parent.parent))
from multi_engine_downloader import (
    MultiEngineDownloader, DownloadRequest as MultiEngineRequest, 
    EngineType, YtDlpAria2Engine, StreamlinkEngine, GalleryDlEngine, RipmeEngine
)

# Import our existing systems
from .models import DownloadOptions, DownloadProgress, DownloadStatus
from .queue_manager import EnhancedQueueManager, QueuePriority, QueueStatus, QueueItem

logger = logging.getLogger(__name__)

@dataclass
class EngineConfig:
    """Configuration for multi-engine system"""
    yt_dlp_aria2: Dict[str, Any] = None
    streamlink: Dict[str, Any] = None
    gallery_dl: Dict[str, Any] = None
    ripme: Dict[str, Any] = None
    
    def __post_init__(self):
        self.yt_dlp_aria2 = self.yt_dlp_aria2 or {
            'aria2': {
                'max-concurrent-downloads': 8,
                'max-connection-per-server': 16,
                'split': 16,
                'min-split-size': '1M',
                'continue': True,
                'max-tries': 5,
                'retry-wait': 3
            }
        }
        self.streamlink = self.streamlink or {}
        self.gallery_dl = self.gallery_dl or {}
        self.ripme = self.ripme or {'jar_path': './ripme.jar'}

class EnhancedMultiEngineDownloader:
    """
    Enhanced downloader that combines multi-engine routing with queue management
    """
    
    def __init__(self, 
                 download_options: Optional[DownloadOptions] = None,
                 engine_config: Optional[EngineConfig] = None,
                 redis_url: Optional[str] = None):
        
        self.download_options = download_options or DownloadOptions()
        self.engine_config = engine_config or EngineConfig()
        
        # Initialize multi-engine downloader
        config = {
            'yt-dlp-aria2': self.engine_config.yt_dlp_aria2,
            'streamlink': self.engine_config.streamlink,
            'gallery-dl': self.engine_config.gallery_dl,
            'ripme': self.engine_config.ripme
        }
        
        self.multi_engine = MultiEngineDownloader(config)
        
        # Initialize queue manager
        self.queue_manager = EnhancedQueueManager(
            redis_url=redis_url,
            max_concurrent=self.download_options.concurrent_downloads
        )
        
        # Progress callbacks
        self.progress_callbacks = []
        
        # Engine availability status
        self.engine_status = {}
        
    async def initialize(self):
        """Initialize the enhanced multi-engine downloader"""
        await self.queue_manager.initialize()
        
        # Check engine availability
        self.engine_status = {
            'yt-dlp+aria2c': self.multi_engine.engines[EngineType.YT_DLP_ARIA2].is_available,
            'streamlink': self.multi_engine.engines[EngineType.STREAMLINK].is_available,
            'gallery-dl': self.multi_engine.engines[EngineType.GALLERY_DL].is_available,
            'ripme': self.multi_engine.engines[EngineType.RIPME].is_available
        }
        
        logger.info(f"Engine availability: {self.engine_status}")
        
        # Set up queue status callback
        def on_queue_status_change(item: QueueItem):
            progress = DownloadProgress(
                url=item.url,
                status=DownloadStatus(item.status.value),
                started_at=item.started_at,
                completed_at=item.completed_at,
                filename=item.metadata.get('title', ''),
                downloaded_bytes=item.metadata.get('downloaded_bytes', 0),
                total_bytes=item.metadata.get('total_bytes', 0),
                speed=item.metadata.get('speed', '0 B/s'),
                eta=item.metadata.get('eta', 'Unknown'),
                error_message=item.error_message
            )
            
            if progress.total_bytes > 0:
                progress.progress_percent = (progress.downloaded_bytes / progress.total_bytes) * 100
            
            self._notify_progress(progress)
        
        self.queue_manager.add_status_callback(on_queue_status_change)
    
    def add_progress_callback(self, callback):
        """Add progress callback"""
        self.progress_callbacks.append(callback)
    
    def _notify_progress(self, progress: DownloadProgress):
        """Notify progress callbacks"""
        for callback in self.progress_callbacks:
            try:
                callback(progress)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
    
    async def add_to_queue(self, 
                          url: str, 
                          priority: QueuePriority = QueuePriority.NORMAL,
                          preferred_engine: Optional[EngineType] = None) -> Optional[str]:
        """Add URL to download queue with engine selection"""
        
        # Determine best engine for this URL
        selected_engine = self.multi_engine.select_engine(url, preferred_engine or EngineType.AUTO)
        if not selected_engine:
            logger.error(f"No suitable engine found for URL: {url}")
            return None
        
        engine_name = selected_engine.__class__.__name__
        
        # Create download options with engine info
        download_options = {
            'output_path': self.download_options.output_path,
            'format_selector': self.download_options.format_selector,
            'extract_audio': self.download_options.extract_audio,
            'write_subtitles': self.download_options.write_subtitles,
            'write_thumbnail': self.download_options.write_thumbnail,
            'engine_type': engine_name,
            'engine_config': self._get_engine_config(engine_name)
        }
        
        return await self.queue_manager.add_item(
            url=url,
            priority=priority,
            download_options=download_options
        )
    
    def _get_engine_config(self, engine_name: str) -> Dict[str, Any]:
        """Get configuration for specific engine"""
        config_map = {
            'YtDlpAria2Engine': self.engine_config.yt_dlp_aria2,
            'StreamlinkEngine': self.engine_config.streamlink,
            'GalleryDlEngine': self.engine_config.gallery_dl,
            'RipmeEngine': self.engine_config.ripme
        }
        return config_map.get(engine_name, {})
    
    async def process_queue(self):
        """Process items in the download queue using multi-engine system"""
        while True:
            item = await self.queue_manager.get_next_item()
            if not item:
                break
            
            try:
                # Create multi-engine request
                engine_type = self._get_engine_type_from_name(
                    item.download_options.get('engine_type', 'YtDlpAria2Engine')
                )
                
                # Create progress callback for this item
                async def progress_callback(progress_data):
                    # Update item metadata with progress
                    item.metadata.update({
                        'downloaded_bytes': progress_data.get('downloaded', 0),
                        'total_bytes': progress_data.get('total', 0),
                        'speed': progress_data.get('speed', '0 B/s'),
                        'eta': progress_data.get('eta', 'Unknown'),
                        'percentage': progress_data.get('percentage', 0)
                    })
                    
                    # Create progress object for callbacks
                    progress = DownloadProgress(
                        url=item.url,
                        status=DownloadStatus.DOWNLOADING,
                        downloaded_bytes=progress_data.get('downloaded', 0),
                        total_bytes=progress_data.get('total', 0),
                        speed=progress_data.get('speed', '0 B/s'),
                        eta=progress_data.get('eta', 'Unknown'),
                        progress_percent=progress_data.get('percentage', 0),
                        filename=item.metadata.get('title', ''),
                        started_at=item.started_at
                    )
                    
                    self._notify_progress(progress)
                
                # Create completion callback
                async def completion_callback(result):
                    if result.get('status') == 'success':
                        # Update metadata with result info
                        item.metadata.update({
                            'title': result.get('title', ''),
                            'output_path': str(result.get('output_path', '')),
                            'engine_used': result.get('engine', ''),
                            'duration': result.get('duration'),
                            'downloaded_files': result.get('downloaded_files', []),
                            'file_count': result.get('count', 1)
                        })
                
                # Create multi-engine request
                request = MultiEngineRequest(
                    url=item.url,
                    output_dir=Path(item.download_options.get('output_path', './downloads')),
                    quality=item.download_options.get('format_selector', 'best'),
                    engine=engine_type,
                    options=item.download_options.get('engine_config', {}),
                    progress_callback=progress_callback,
                    completion_callback=completion_callback
                )
                
                # Perform download using multi-engine system
                result = await self.multi_engine.download(request)
                
                # Mark as completed based on result
                success = result.get('status') == 'success'
                error_message = result.get('message', '') if not success else ''
                
                await self.queue_manager.complete_item(
                    item.id, 
                    success=success, 
                    error_message=error_message
                )
                
            except Exception as e:
                logger.error(f"Download failed for {item.url}: {e}")
                await self.queue_manager.complete_item(
                    item.id, 
                    success=False, 
                    error_message=str(e)
                )
    
    def _get_engine_type_from_name(self, engine_name: str) -> EngineType:
        """Convert engine class name to EngineType enum"""
        engine_map = {
            'YtDlpAria2Engine': EngineType.YT_DLP_ARIA2,
            'StreamlinkEngine': EngineType.STREAMLINK,
            'GalleryDlEngine': EngineType.GALLERY_DL,
            'RipmeEngine': EngineType.RIPME
        }
        return engine_map.get(engine_name, EngineType.AUTO)
    
    async def download_batch(self, urls: List[str], priority: QueuePriority = QueuePriority.NORMAL) -> List[DownloadProgress]:
        """Download multiple URLs using the queue system"""
        # Add all URLs to queue
        item_ids = []
        for url in urls:
            item_id = await self.add_to_queue(url, priority)
            if item_id:
                item_ids.append(item_id)
        
        # Process the queue
        await self.process_queue()
        
        # Return results
        results = []
        for item_id in item_ids:
            if item_id in self.queue_manager.items:
                item = self.queue_manager.items[item_id]
                progress = DownloadProgress(
                    url=item.url,
                    status=DownloadStatus(item.status.value),
                    started_at=item.started_at,
                    completed_at=item.completed_at,
                    error_message=item.error_message,
                    filename=item.metadata.get('title', '')
                )
                results.append(progress)
        
        return results
    
    def get_engine_status(self) -> Dict[str, Any]:
        """Get status of all engines"""
        return {
            'available_engines': list(self.multi_engine.available_engines.keys()),
            'engine_status': self.engine_status,
            'queue_status': self.queue_manager.get_queue_status()
        }
    
    async def get_optimal_engine(self, url: str) -> Optional[str]:
        """Get the optimal engine for a given URL"""
        engine = self.multi_engine.select_engine(url)
        return engine.__class__.__name__ if engine else None
    
    def configure_engine(self, engine_name: str, config: Dict[str, Any]):
        """Configure a specific engine"""
        if engine_name == 'yt-dlp-aria2':
            self.engine_config.yt_dlp_aria2.update(config)
        elif engine_name == 'streamlink':
            self.engine_config.streamlink.update(config)
        elif engine_name == 'gallery-dl':
            self.engine_config.gallery_dl.update(config)
        elif engine_name == 'ripme':
            self.engine_config.ripme.update(config)
    
    # Delegate queue management methods
    async def cancel_download(self, url: str) -> bool:
        """Cancel a download by URL"""
        for item_id, item in self.queue_manager.items.items():
            if item.url == url:
                return await self.queue_manager.cancel_item(item_id)
        return False
    
    async def pause_download(self, url: str) -> bool:
        """Pause a download"""
        for item_id, item in self.queue_manager.items.items():
            if item.url == url:
                await self.queue_manager.pause_item(item_id)
                return True
        return False
    
    async def resume_download(self, url: str) -> bool:
        """Resume a download"""
        for item_id, item in self.queue_manager.items.items():
            if item.url == url:
                await self.queue_manager.resume_item(item_id)
                return True
        return False
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get queue status"""
        return self.queue_manager.get_queue_status()
    
    async def clear_completed(self):
        """Clear completed downloads"""
        await self.queue_manager.clear_completed()

# Example usage
async def main():
    """Example usage of enhanced multi-engine downloader"""
    
    # Configure engines
    engine_config = EngineConfig(
        yt_dlp_aria2={
            'aria2': {
                'max-concurrent-downloads': 8,
                'max-connection-per-server': 16,
                'split': 16
            }
        }
    )
    
    # Create downloader
    downloader = EnhancedMultiEngineDownloader(
        download_options=DownloadOptions(output_path="./downloads"),
        engine_config=engine_config
    )
    
    await downloader.initialize()
    
    # Add progress callback
    def progress_callback(progress: DownloadProgress):
        print(f"[{progress.status.value}] {progress.url}")
        if progress.status == DownloadStatus.DOWNLOADING:
            print(f"  Progress: {progress.progress_percent:.1f}% | Speed: {progress.speed}")
    
    downloader.add_progress_callback(progress_callback)
    
    # Test URLs for different engines
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # yt-dlp+aria2c
        "https://www.instagram.com/p/example/",          # gallery-dl
    ]
    
    # Check optimal engines
    for url in test_urls:
        engine = await downloader.get_optimal_engine(url)
        print(f"Optimal engine for {url}: {engine}")
    
    # Download batch
    results = await downloader.download_batch(test_urls)
    
    # Show results
    for result in results:
        print(f"Result: {result.url} -> {result.status.value}")
    
    # Show engine status
    status = downloader.get_engine_status()
    print(f"Engine status: {status}")

if __name__ == "__main__":
    asyncio.run(main())
