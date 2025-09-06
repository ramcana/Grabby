"""
Unified Download Interface
Combines the original UniversalDownloader with the multi-engine system
"""
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime

from .downloader import UniversalDownloader
from .models import DownloadOptions, DownloadProgress, DownloadStatus
from .multi_engine_downloader import EnhancedMultiEngineDownloader, EngineConfig
from .queue_manager import QueuePriority
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from config.profile_manager import ProfileManager, DownloadProfile

logger = logging.getLogger(__name__)

class UnifiedDownloader:
    """
    Unified downloader that provides both legacy yt-dlp and multi-engine capabilities
    """
    
    def __init__(self, 
                 options: Optional[DownloadOptions] = None,
                 engine_config: Optional[EngineConfig] = None,
                 redis_url: Optional[str] = None,
                 use_multi_engine: bool = True,
                 profile_manager: Optional[ProfileManager] = None):
        
        self.options = options or DownloadOptions()
        self.use_multi_engine = use_multi_engine
        self.profile_manager = profile_manager
        self.current_profile: Optional[DownloadProfile] = None
        
        if use_multi_engine:
            # Use the enhanced multi-engine downloader
            self.downloader = EnhancedMultiEngineDownloader(
                download_options=options,
                engine_config=engine_config,
                redis_url=redis_url
            )
        else:
            # Use the original yt-dlp only downloader
            self.downloader = UniversalDownloader(options, redis_url)
        
        self.progress_callbacks = []
    
    async def initialize(self):
        """Initialize the unified downloader"""
        await self.downloader.initialize()
        
        # Set up progress forwarding
        def forward_progress(progress: DownloadProgress):
            for callback in self.progress_callbacks:
                try:
                    callback(progress)
                except Exception as e:
                    logger.error(f"Error in progress callback: {e}")
        
        self.downloader.add_progress_callback(forward_progress)
    
    def add_progress_callback(self, callback: Callable[[DownloadProgress], None]):
        """Add progress callback"""
        self.progress_callbacks.append(callback)
    
    async def set_profile(self, profile_name: str) -> bool:
        """Set the active download profile"""
        if not self.profile_manager:
            logger.warning("No profile manager available")
            return False
        
        profile = self.profile_manager.get_profile(profile_name)
        if not profile:
            logger.error(f"Profile not found: {profile_name}")
            return False
        
        self.current_profile = profile
        
        # Apply profile settings to downloader options
        await self._apply_profile_settings()
        
        logger.info(f"Set active profile to: {profile_name}")
        return True
    
    async def _apply_profile_settings(self):
        """Apply current profile settings to downloader"""
        if not self.current_profile:
            return
        
        profile = self.current_profile
        
        # Update download options
        self.options.output_path = profile.output_path
        self.options.concurrent_downloads = profile.concurrent_downloads
        self.options.max_retries = profile.max_retries
        self.options.timeout = profile.timeout
        
        # Apply to underlying downloader
        if hasattr(self.downloader, 'options'):
            self.downloader.options = self.options
        
        # Configure engine preferences for multi-engine
        if self.use_multi_engine and hasattr(self.downloader, 'configure_engine'):
            for engine_name, config in profile.engine_specific.items():
                self.downloader.configure_engine(engine_name, config)
    
    def get_profile_config_for_url(self, url: str) -> Dict[str, Any]:
        """Get profile configuration for a specific URL/platform"""
        if not self.current_profile:
            return {}
        
        # Detect platform from URL
        platform = self._detect_platform(url)
        
        if platform and platform in self.current_profile.platform_overrides:
            return self.current_profile.get_platform_config(platform)
        
        return self.current_profile.to_dict()
    
    def _detect_platform(self, url: str) -> Optional[str]:
        """Detect platform from URL"""
        url_lower = url.lower()
        
        if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            return 'youtube'
        elif 'twitch.tv' in url_lower:
            return 'twitch'
        elif 'instagram.com' in url_lower:
            return 'instagram'
        elif 'tiktok.com' in url_lower:
            return 'tiktok'
        elif 'vimeo.com' in url_lower:
            return 'vimeo'
        elif 'soundcloud.com' in url_lower:
            return 'soundcloud'
        
        return None
    
    async def download(self, url: str, priority: QueuePriority = QueuePriority.NORMAL, profile_name: Optional[str] = None) -> DownloadProgress:
        """Download a single URL"""
        # Apply profile if specified
        if profile_name:
            await self.set_profile(profile_name)
        
        if self.use_multi_engine:
            # Add to queue and process
            item_id = await self.downloader.add_to_queue(url, priority)
            if not item_id:
                return DownloadProgress(
                    url=url,
                    status=DownloadStatus.FAILED,
                    error_message="Failed to add to queue"
                )
            
            # Process the queue (will handle this item)
            await self.downloader.process_queue()
            
            # Get result from queue
            if item_id in self.downloader.queue_manager.items:
                item = self.downloader.queue_manager.items[item_id]
                return DownloadProgress(
                    url=item.url,
                    status=DownloadStatus(item.status.value),
                    started_at=item.started_at,
                    completed_at=item.completed_at,
                    error_message=item.error_message,
                    filename=item.metadata.get('title', '')
                )
        else:
            # Use original downloader
            return await self.downloader.download(url)
    
    async def download_batch(self, urls: List[str], priority: QueuePriority = QueuePriority.NORMAL, profile_name: Optional[str] = None) -> List[DownloadProgress]:
        """Download multiple URLs"""
        # Apply profile if specified
        if profile_name:
            await self.set_profile(profile_name)
        
        if self.use_multi_engine:
            return await self.downloader.download_batch(urls, priority)
        else:
            # Use original batch download
            results = []
            for url in urls:
                result = await self.downloader.download(url)
                results.append(result)
            return results
    
    async def add_to_queue(self, url: str, priority: QueuePriority = QueuePriority.NORMAL) -> Optional[str]:
        """Add URL to download queue"""
        return await self.downloader.add_to_queue(url, priority)
    
    async def process_queue(self):
        """Process the download queue"""
        await self.downloader.process_queue()
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get queue status"""
        return self.downloader.get_queue_status()
    
    async def cancel_download(self, url: str) -> bool:
        """Cancel a download"""
        return await self.downloader.cancel_download(url)
    
    async def pause_download(self, url: str) -> bool:
        """Pause a download"""
        if hasattr(self.downloader, 'pause_download'):
            return await self.downloader.pause_download(url)
        return False
    
    async def resume_download(self, url: str) -> bool:
        """Resume a download"""
        if hasattr(self.downloader, 'resume_download'):
            return await self.downloader.resume_download(url)
        return False
    
    def get_engine_status(self) -> Dict[str, Any]:
        """Get engine status (multi-engine only)"""
        if self.use_multi_engine and hasattr(self.downloader, 'get_engine_status'):
            return self.downloader.get_engine_status()
        return {'engines': ['yt-dlp'], 'multi_engine': False}
    
    async def get_optimal_engine(self, url: str) -> Optional[str]:
        """Get optimal engine for URL (multi-engine only)"""
        if self.use_multi_engine and hasattr(self.downloader, 'get_optimal_engine'):
            return await self.downloader.get_optimal_engine(url)
        return 'yt-dlp'
    
    def configure_engine(self, engine_name: str, config: Dict[str, Any]):
        """Configure engine (multi-engine only)"""
        if self.use_multi_engine and hasattr(self.downloader, 'configure_engine'):
            self.downloader.configure_engine(engine_name, config)
    
    async def clear_completed(self):
        """Clear completed downloads"""
        await self.downloader.clear_completed()

# Factory function for easy creation
def create_downloader(
    use_multi_engine: bool = True,
    output_path: str = "./downloads",
    concurrent_downloads: int = 3,
    redis_url: Optional[str] = None,
    engine_config: Optional[Dict[str, Any]] = None,
    profile_manager: Optional[ProfileManager] = None
) -> UnifiedDownloader:
    """
    Factory function to create a unified downloader
    
    Args:
        use_multi_engine: Whether to use multi-engine system (default: True)
        output_path: Download output directory
        concurrent_downloads: Max concurrent downloads
        redis_url: Redis URL for queue persistence (optional)
        engine_config: Engine-specific configuration
        profile_manager: Profile manager for download profiles (optional)
    
    Returns:
        Configured UnifiedDownloader instance
    """
    
    options = DownloadOptions(
        output_path=output_path,
        concurrent_downloads=concurrent_downloads
    )
    
    config = None
    if use_multi_engine and engine_config:
        config = EngineConfig(
            yt_dlp_aria2=engine_config.get('yt_dlp_aria2', {}),
            streamlink=engine_config.get('streamlink', {}),
            gallery_dl=engine_config.get('gallery_dl', {}),
            ripme=engine_config.get('ripme', {})
        )
    
    return UnifiedDownloader(
        options=options,
        engine_config=config,
        redis_url=redis_url,
        use_multi_engine=use_multi_engine,
        profile_manager=profile_manager
    )

# Example usage
async def main():
    """Example usage of unified downloader"""
    
    # Create multi-engine downloader
    downloader = create_downloader(
        use_multi_engine=True,
        output_path="./downloads",
        concurrent_downloads=4,
        engine_config={
            'yt_dlp_aria2': {
                'aria2': {
                    'max-concurrent-downloads': 8,
                    'max-connection-per-server': 16
                }
            }
        }
    )
    
    await downloader.initialize()
    
    # Add progress callback
    def progress_callback(progress: DownloadProgress):
        print(f"[{progress.status.value}] {progress.url}")
        if progress.status == DownloadStatus.DOWNLOADING:
            print(f"  Progress: {progress.progress_percent:.1f}% | Speed: {progress.speed}")
    
    downloader.add_progress_callback(progress_callback)
    
    # Test URLs
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.instagram.com/p/example/"
    ]
    
    # Show optimal engines
    for url in test_urls:
        engine = await downloader.get_optimal_engine(url)
        print(f"Optimal engine for {url}: {engine}")
    
    # Download batch
    print("\nStarting batch download...")
    results = await downloader.download_batch(test_urls)
    
    # Show results
    print("\nDownload Results:")
    for result in results:
        print(f"  {result.url} -> {result.status.value}")
        if result.error_message:
            print(f"    Error: {result.error_message}")
    
    # Show engine status
    status = downloader.get_engine_status()
    print(f"\nEngine Status: {status}")

if __name__ == "__main__":
    asyncio.run(main())
