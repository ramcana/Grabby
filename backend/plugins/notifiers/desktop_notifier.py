"""
Desktop Notifier Plugin
Sends native desktop notifications
"""
import logging
from pathlib import Path
from typing import Dict, Any, List
import asyncio

from ..base_plugins import Notifier, PluginMetadata, PluginType

logger = logging.getLogger(__name__)

class DesktopNotifier(Notifier):
    """Send native desktop notifications"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="desktop_notifier",
            version="1.0.0",
            description="Send native desktop notifications",
            author="Grabby Team",
            plugin_type=PluginType.NOTIFIER,
            dependencies=["plyer"],
            config_schema={
                "enabled": {"type": "boolean", "default": True},
                "show_on_start": {"type": "boolean", "default": False},
                "show_on_complete": {"type": "boolean", "default": True},
                "show_on_failure": {"type": "boolean", "default": True},
                "timeout": {"type": "integer", "default": 5}
            }
        )
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration"""
        try:
            import plyer
            return True
        except ImportError:
            logger.warning("plyer not available, desktop notifications will be disabled")
            return False
    
    async def notify_download_started(self, url: str, metadata: Dict[str, Any]):
        """Notify when download starts"""
        if not self.config.get("enabled", True) or not self.config.get("show_on_start", False):
            return
        
        title = metadata.get("title", "Download Started")
        message = f"Started downloading: {title[:50]}..."
        
        await self._send_notification("Grabby - Download Started", message)
    
    async def notify_download_completed(self, file_path: Path, metadata: Dict[str, Any]):
        """Notify when download completes"""
        if not self.config.get("enabled", True) or not self.config.get("show_on_complete", True):
            return
        
        title = metadata.get("title", file_path.name)
        message = f"Successfully downloaded: {title[:50]}"
        
        if file_path.exists():
            size_mb = file_path.stat().st_size / (1024 * 1024)
            message += f" ({size_mb:.1f} MB)"
        
        await self._send_notification("Grabby - Download Complete", message)
    
    async def notify_download_failed(self, url: str, error: str, metadata: Dict[str, Any]):
        """Notify when download fails"""
        if not self.config.get("enabled", True) or not self.config.get("show_on_failure", True):
            return
        
        title = metadata.get("title", "Unknown")
        message = f"Failed to download: {title[:30]}... - {error[:50]}"
        
        await self._send_notification("Grabby - Download Failed", message)
    
    async def notify_batch_completed(self, results: List[Dict[str, Any]]):
        """Notify when batch download completes"""
        if not self.config.get("enabled", True):
            return
        
        total = len(results)
        successful = sum(1 for r in results if r.get("status") == "completed")
        failed = total - successful
        
        message = f"Batch completed: {successful}/{total} successful"
        if failed > 0:
            message += f", {failed} failed"
        
        await self._send_notification("Grabby - Batch Complete", message)
    
    async def _send_notification(self, title: str, message: str):
        """Send desktop notification"""
        try:
            import plyer
            
            def send_notification():
                plyer.notification.notify(
                    title=title,
                    message=message,
                    app_name="Grabby",
                    timeout=self.config.get("timeout", 5)
                )
            
            # Run in thread to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, send_notification)
            
        except Exception as e:
            logger.error(f"Failed to send desktop notification: {e}")
