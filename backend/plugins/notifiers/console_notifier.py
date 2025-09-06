"""
Console Notifier Plugin
Sends notifications to console/terminal
"""
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from ..base_plugins import Notifier, PluginMetadata, PluginType

logger = logging.getLogger(__name__)

class ConsoleNotifier(Notifier):
    """Send notifications to console output"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="console_notifier",
            version="1.0.0",
            description="Send download notifications to console/terminal",
            author="Grabby Team",
            plugin_type=PluginType.NOTIFIER,
            config_schema={
                "enabled": {"type": "boolean", "default": True},
                "show_timestamps": {"type": "boolean", "default": True},
                "show_file_size": {"type": "boolean", "default": True},
                "show_duration": {"type": "boolean", "default": True}
            }
        )
    
    async def notify_download_started(self, url: str, metadata: Dict[str, Any]):
        """Notify when download starts"""
        if not self.config.get("enabled", True):
            return
        
        timestamp = self._get_timestamp() if self.config.get("show_timestamps", True) else ""
        title = metadata.get("title", "Unknown")
        uploader = metadata.get("uploader", "Unknown")
        
        message = f"{timestamp}🚀 Started downloading: {title}"
        if uploader != "Unknown":
            message += f" by {uploader}"
        message += f" ({url})"
        
        print(message)
        logger.info(f"Download started: {title}")
    
    async def notify_download_completed(self, file_path: Path, metadata: Dict[str, Any]):
        """Notify when download completes"""
        if not self.config.get("enabled", True):
            return
        
        timestamp = self._get_timestamp() if self.config.get("show_timestamps", True) else ""
        title = metadata.get("title", file_path.name)
        
        message = f"{timestamp}✅ Completed: {title}"
        
        # Add file size if available and enabled
        if self.config.get("show_file_size", True) and file_path.exists():
            size_mb = file_path.stat().st_size / (1024 * 1024)
            message += f" ({size_mb:.1f} MB)"
        
        # Add duration if available and enabled
        if self.config.get("show_duration", True) and metadata.get("duration"):
            duration = metadata["duration"]
            if isinstance(duration, (int, float)):
                mins, secs = divmod(int(duration), 60)
                message += f" [{mins:02d}:{secs:02d}]"
        
        message += f" -> {file_path}"
        
        print(message)
        logger.info(f"Download completed: {title}")
    
    async def notify_download_failed(self, url: str, error: str, metadata: Dict[str, Any]):
        """Notify when download fails"""
        if not self.config.get("enabled", True):
            return
        
        timestamp = self._get_timestamp() if self.config.get("show_timestamps", True) else ""
        title = metadata.get("title", "Unknown")
        
        message = f"{timestamp}❌ Failed: {title} - {error}"
        
        print(message)
        logger.error(f"Download failed: {title} - {error}")
    
    async def notify_batch_completed(self, results: List[Dict[str, Any]]):
        """Notify when batch download completes"""
        if not self.config.get("enabled", True):
            return
        
        timestamp = self._get_timestamp() if self.config.get("show_timestamps", True) else ""
        
        total = len(results)
        successful = sum(1 for r in results if r.get("status") == "completed")
        failed = total - successful
        
        message = f"{timestamp}📊 Batch completed: {successful}/{total} successful"
        if failed > 0:
            message += f", {failed} failed"
        
        print(message)
        logger.info(f"Batch download completed: {successful}/{total} successful")
    
    def _get_timestamp(self) -> str:
        """Get formatted timestamp"""
        return f"[{datetime.now().strftime('%H:%M:%S')}] "
