"""
Thumbnail Extractor Plugin
Extracts and saves video thumbnails
"""
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any
import subprocess
import shutil

from ..base_plugins import PostProcessor, PluginMetadata, PluginType, ProcessingContext

logger = logging.getLogger(__name__)

class ThumbnailExtractor(PostProcessor):
    """Extract thumbnails from downloaded videos"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="thumbnail_extractor",
            version="1.0.0",
            description="Extract thumbnails from downloaded videos using ffmpeg",
            author="Grabby Team",
            plugin_type=PluginType.POST_PROCESSOR,
            dependencies=["ffmpeg"],
            config_schema={
                "enabled": {"type": "boolean", "default": True},
                "timestamp": {"type": "string", "default": "00:00:05"},
                "format": {"type": "string", "default": "jpg", "enum": ["jpg", "png"]},
                "quality": {"type": "integer", "default": 2, "min": 1, "max": 31},
                "size": {"type": "string", "default": "320x240"}
            }
        )
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration"""
        # Check if ffmpeg is available
        if not shutil.which("ffmpeg"):
            logger.warning("ffmpeg not found, thumbnail extraction will be disabled")
            return False
        
        return True
    
    async def process(self, context: ProcessingContext) -> bool:
        """Extract thumbnail from video file"""
        if not self.config.get("enabled", True):
            return True
        
        try:
            video_file = context.file_path
            if not video_file.exists():
                logger.error(f"Video file not found: {video_file}")
                return False
            
            # Generate thumbnail filename
            thumbnail_name = f"{video_file.stem}_thumbnail.{self.config.get('format', 'jpg')}"
            thumbnail_path = video_file.parent / thumbnail_name
            
            # Skip if thumbnail already exists
            if thumbnail_path.exists():
                logger.info(f"Thumbnail already exists: {thumbnail_path}")
                return True
            
            # Extract thumbnail using ffmpeg
            await self._extract_thumbnail(video_file, thumbnail_path)
            
            # Update metadata
            context.metadata["thumbnail_path"] = str(thumbnail_path)
            
            logger.info(f"Extracted thumbnail: {thumbnail_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to extract thumbnail: {e}")
            return False
    
    async def _extract_thumbnail(self, video_path: Path, thumbnail_path: Path):
        """Extract thumbnail using ffmpeg"""
        timestamp = self.config.get("timestamp", "00:00:05")
        quality = self.config.get("quality", 2)
        size = self.config.get("size", "320x240")
        
        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-ss", timestamp,
            "-vframes", "1",
            "-q:v", str(quality),
            "-s", size,
            "-y",  # Overwrite output file
            str(thumbnail_path)
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown ffmpeg error"
            raise Exception(f"ffmpeg failed: {error_msg}")
    
    async def cleanup(self, context: ProcessingContext):
        """Clean up temporary files if needed"""
        pass
