"""
Core download engine - The foundation everything else builds on
"""
import asyncio
import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import yt_dlp

from .queue_manager import EnhancedQueueManager, QueuePriority, QueueStatus, QueueItem
from .models import DownloadStatus, DownloadProgress, DownloadOptions

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UniversalDownloader:
    """
    Core download engine that handles video downloads from multiple platforms
    Enhanced with queue management system
    """
    
    def __init__(self, options: Optional[DownloadOptions] = None, redis_url: Optional[str] = None):
        self.options = options or DownloadOptions()
        self.active_downloads: Dict[str, DownloadProgress] = {}
        self.progress_callbacks: List[Callable[[DownloadProgress], None]] = []
        self.semaphore = asyncio.Semaphore(self.options.concurrent_downloads)
        
        # Enhanced queue manager
        self.queue_manager = EnhancedQueueManager(
            redis_url=redis_url,
            max_concurrent=self.options.concurrent_downloads
        )
        
        # Ensure output directory exists
        Path(self.options.output_path).mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Initialize the downloader and queue manager"""
        await self.queue_manager.initialize()
        
        # Set up queue status callback
        def on_queue_status_change(item: QueueItem):
            # Convert queue item to download progress for compatibility
            progress = DownloadProgress(
                url=item.url,
                status=DownloadStatus(item.status.value),
                started_at=item.started_at,
                completed_at=item.completed_at
            )
            if item.metadata:
                progress.filename = item.metadata.get('title', '')
            
            self._notify_progress(progress)
        
        self.queue_manager.add_status_callback(on_queue_status_change)
        
    def add_progress_callback(self, callback: Callable[[DownloadProgress], None]):
        """Add a callback to receive progress updates"""
        self.progress_callbacks.append(callback)
    
    def _notify_progress(self, progress: DownloadProgress):
        """Notify all registered callbacks of progress updates"""
        for callback in self.progress_callbacks:
            try:
                callback(progress)
            except Exception as e:
                logger.error(f"Error in progress callback: {e}")
    
    def _create_ydl_opts(self, url: str) -> Dict[str, Any]:
        """Create yt-dlp options for download"""
        progress = self.active_downloads.get(url)
        
        def progress_hook(d):
            if not progress:
                return
                
            if d['status'] == 'downloading':
                progress.status = DownloadStatus.DOWNLOADING
                progress.filename = d.get('filename', '')
                progress.downloaded_bytes = d.get('downloaded_bytes', 0)
                progress.total_bytes = d.get('total_bytes', 0)
                progress.speed = d.get('_speed_str', '0 B/s')
                progress.eta = d.get('_eta_str', 'Unknown')
                
                if progress.total_bytes > 0:
                    progress.progress_percent = (progress.downloaded_bytes / progress.total_bytes) * 100
                
                self._notify_progress(progress)
                
            elif d['status'] == 'finished':
                progress.status = DownloadStatus.COMPLETED
                progress.progress_percent = 100.0
                progress.completed_at = datetime.now()
                progress.filename = d.get('filename', '')
                self._notify_progress(progress)
        
        ydl_opts = {
            'outtmpl': f"{self.options.output_path}/%(title)s.%(ext)s",
            'format': self.options.format_selector,
            'writesubtitles': self.options.write_subtitles,
            'writethumbnail': self.options.write_thumbnail,
            'writeinfojson': self.options.write_info_json,
            'progress_hooks': [progress_hook],
            'no_warnings': False,
            'extractaudio': self.options.extract_audio,
            'audioformat': self.options.audio_format if self.options.extract_audio else None,
        }
        
        if self.options.custom_headers:
            ydl_opts['http_headers'] = self.options.custom_headers
            
        return ydl_opts
    
    async def get_video_info(self, url: str) -> Dict[str, Any]:
        """Extract video information without downloading"""
        try:
            loop = asyncio.get_event_loop()
            
            def extract_info():
                with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                    return ydl.extract_info(url, download=False)
            
            info = await loop.run_in_executor(None, extract_info)
            return info
            
        except Exception as e:
            logger.error(f"Failed to extract info for {url}: {e}")
            raise
    
    async def download_single(self, url: str) -> DownloadProgress:
        """Download a single video"""
        async with self.semaphore:
            # Initialize progress tracking
            progress = DownloadProgress(url=url, started_at=datetime.now())
            self.active_downloads[url] = progress
            self._notify_progress(progress)
            
            try:
                # Get video info first
                info = await self.get_video_info(url)
                progress.filename = info.get('title', 'Unknown')
                self._notify_progress(progress)
                
                # Download the video
                loop = asyncio.get_event_loop()
                ydl_opts = self._create_ydl_opts(url)
                
                def download():
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([url])
                
                await loop.run_in_executor(None, download)
                
                if progress.status != DownloadStatus.COMPLETED:
                    progress.status = DownloadStatus.COMPLETED
                    progress.completed_at = datetime.now()
                    self._notify_progress(progress)
                
                return progress
                
            except Exception as e:
                progress.status = DownloadStatus.FAILED
                progress.error_message = str(e)
                progress.completed_at = datetime.now()
                self._notify_progress(progress)
                logger.error(f"Download failed for {url}: {e}")
                raise
            
            finally:
                # Clean up active downloads
                if url in self.active_downloads:
                    del self.active_downloads[url]
    
    async def add_to_queue(self, 
                          url: str, 
                          priority: QueuePriority = QueuePriority.NORMAL) -> Optional[str]:
        """Add URL to download queue"""
        download_options = {
            'output_path': self.options.output_path,
            'format_selector': self.options.format_selector,
            'extract_audio': self.options.extract_audio,
            'write_subtitles': self.options.write_subtitles,
            'write_thumbnail': self.options.write_thumbnail,
        }
        
        return await self.queue_manager.add_item(
            url=url,
            priority=priority,
            download_options=download_options
        )
    
    async def add_playlist_to_queue(self, 
                                   playlist_url: str,
                                   priority: QueuePriority = QueuePriority.NORMAL) -> List[str]:
        """Add playlist to download queue"""
        download_options = {
            'output_path': self.options.output_path,
            'format_selector': self.options.format_selector,
            'extract_audio': self.options.extract_audio,
            'write_subtitles': self.options.write_subtitles,
            'write_thumbnail': self.options.write_thumbnail,
        }
        
        return await self.queue_manager.add_playlist(
            playlist_url=playlist_url,
            priority=priority,
            download_options=download_options
        )
    
    async def process_queue(self):
        """Process items in the download queue"""
        while True:
            item = await self.queue_manager.get_next_item()
            if not item:
                break
            
            try:
                # Update item metadata with video info
                info = await self.get_video_info(item.url)
                item.metadata.update({
                    'title': info.get('title', 'Unknown'),
                    'uploader': info.get('uploader', 'Unknown'),
                    'duration': info.get('duration'),
                    'view_count': info.get('view_count'),
                })
                
                # Perform the actual download
                await self._download_queue_item(item)
                
                # Mark as completed
                await self.queue_manager.complete_item(item.id, success=True)
                
            except Exception as e:
                logger.error(f"Download failed for {item.url}: {e}")
                await self.queue_manager.complete_item(
                    item.id, 
                    success=False, 
                    error_message=str(e)
                )
    
    async def _download_queue_item(self, item: QueueItem):
        """Download a single queue item"""
        # Create yt-dlp options from queue item
        ydl_opts = self._create_ydl_opts_from_item(item)
        
        # Download the video
        loop = asyncio.get_event_loop()
        
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([item.url])
        
        await loop.run_in_executor(None, download)
    
    def _create_ydl_opts_from_item(self, item: QueueItem) -> Dict[str, Any]:
        """Create yt-dlp options from queue item"""
        options = item.download_options
        
        def progress_hook(d):
            if d['status'] == 'downloading':
                # Update item metadata with progress
                item.metadata.update({
                    'downloaded_bytes': d.get('downloaded_bytes', 0),
                    'total_bytes': d.get('total_bytes', 0),
                    'speed': d.get('_speed_str', '0 B/s'),
                    'eta': d.get('_eta_str', 'Unknown'),
                })
                
                # Create progress object for callbacks
                progress = DownloadProgress(
                    url=item.url,
                    status=DownloadStatus.DOWNLOADING,
                    downloaded_bytes=d.get('downloaded_bytes', 0),
                    total_bytes=d.get('total_bytes', 0),
                    speed=d.get('_speed_str', '0 B/s'),
                    eta=d.get('_eta_str', 'Unknown'),
                    filename=d.get('filename', ''),
                    started_at=item.started_at
                )
                
                if progress.total_bytes > 0:
                    progress.progress_percent = (progress.downloaded_bytes / progress.total_bytes) * 100
                
                self._notify_progress(progress)
        
        ydl_opts = {
            'outtmpl': f"{options.get('output_path', './downloads')}/%(title)s.%(ext)s",
            'format': options.get('format_selector', 'best'),
            'writesubtitles': options.get('write_subtitles', False),
            'writethumbnail': options.get('write_thumbnail', False),
            'writeinfojson': options.get('write_info_json', False),
            'progress_hooks': [progress_hook],
            'no_warnings': False,
            'extractaudio': options.get('extract_audio', False),
            'audioformat': options.get('audio_format', 'best') if options.get('extract_audio') else None,
        }
        
        return ydl_opts

    async def download_batch(self, urls: List[str]) -> List[DownloadProgress]:
        """Download multiple videos using the queue system"""
        # Add all URLs to queue
        item_ids = []
        for url in urls:
            item_id = await self.add_to_queue(url)
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
                    error_message=item.error_message
                )
                if item.metadata:
                    progress.filename = item.metadata.get('title', '')
                results.append(progress)
        
        return results
    
    def get_active_downloads(self) -> Dict[str, DownloadProgress]:
        """Get currently active downloads from queue manager"""
        active_items = self.queue_manager.get_items_by_status(QueueStatus.DOWNLOADING)
        active_downloads = {}
        
        for item in active_items:
            progress = DownloadProgress(
                url=item.url,
                status=DownloadStatus.DOWNLOADING,
                started_at=item.started_at,
                filename=item.metadata.get('title', ''),
                downloaded_bytes=item.metadata.get('downloaded_bytes', 0),
                total_bytes=item.metadata.get('total_bytes', 0),
                speed=item.metadata.get('speed', '0 B/s'),
                eta=item.metadata.get('eta', 'Unknown')
            )
            
            if progress.total_bytes > 0:
                progress.progress_percent = (progress.downloaded_bytes / progress.total_bytes) * 100
            
            active_downloads[item.url] = progress
        
        return active_downloads
    
    async def cancel_download(self, url: str) -> bool:
        """Cancel an active download"""
        # Find item by URL
        for item_id, item in self.queue_manager.items.items():
            if item.url == url:
                return await self.queue_manager.cancel_item(item_id)
        return False
    
    async def cancel_all_downloads(self):
        """Cancel all active downloads"""
        active_items = self.queue_manager.get_items_by_status(QueueStatus.DOWNLOADING)
        for item in active_items:
            await self.queue_manager.cancel_item(item.id)
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get queue status information"""
        return self.queue_manager.get_queue_status()
    
    async def pause_download(self, url: str) -> bool:
        """Pause a download"""
        for item_id, item in self.queue_manager.items.items():
            if item.url == url:
                await self.queue_manager.pause_item(item_id)
                return True
        return False
    
    async def resume_download(self, url: str) -> bool:
        """Resume a paused download"""
        for item_id, item in self.queue_manager.items.items():
            if item.url == url:
                await self.queue_manager.resume_item(item_id)
                return True
        return False

# Example usage and testing
async def main():
    """Example usage of the download engine"""
    
    def progress_callback(progress: DownloadProgress):
        print(f"[{progress.status.value}] {progress.url}")
        if progress.status == DownloadStatus.DOWNLOADING:
            print(f"  Progress: {progress.progress_percent:.1f}% | Speed: {progress.speed} | ETA: {progress.eta}")
        elif progress.status == DownloadStatus.COMPLETED:
            print(f"  ✓ Completed: {progress.filename}")
        elif progress.status == DownloadStatus.FAILED:
            print(f"  ✗ Failed: {progress.error_message}")
    
    # Configure download options
    options = DownloadOptions(
        output_path="./downloads",
        format_selector="best[height<=720]",  # Lower quality for testing
        write_thumbnail=True,
        concurrent_downloads=2
    )
    
    # Create downloader instance
    downloader = UniversalDownloader(options)
    downloader.add_progress_callback(progress_callback)
    
    # Test with a sample URL (replace with actual URL for testing)
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Roll for testing
    ]
    
    try:
        print("Starting downloads...")
        results = await downloader.download_batch(test_urls)
        
        print("\nDownload Summary:")
        for result in results:
            print(f"  {result.url}: {result.status.value}")
            if result.error_message:
                print(f"    Error: {result.error_message}")
                
    except Exception as e:
        print(f"Error during download: {e}")

if __name__ == "__main__":
    asyncio.run(main())
