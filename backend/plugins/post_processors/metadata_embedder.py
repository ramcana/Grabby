"""
Metadata Embedder Plugin
Embeds metadata into downloaded video files
"""
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any
import subprocess
import shutil
import json

from ..base_plugins import PostProcessor, PluginMetadata, PluginType, ProcessingContext

logger = logging.getLogger(__name__)

class MetadataEmbedder(PostProcessor):
    """Embed metadata into downloaded video files"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="metadata_embedder",
            version="1.0.0",
            description="Embed metadata into video files using ffmpeg",
            author="Grabby Team",
            plugin_type=PluginType.POST_PROCESSOR,
            dependencies=["ffmpeg"],
            config_schema={
                "enabled": {"type": "boolean", "default": True},
                "embed_title": {"type": "boolean", "default": True},
                "embed_description": {"type": "boolean", "default": True},
                "embed_uploader": {"type": "boolean", "default": True},
                "embed_upload_date": {"type": "boolean", "default": True},
                "create_backup": {"type": "boolean", "default": False}
            }
        )
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration"""
        # Check if ffmpeg is available
        if not shutil.which("ffmpeg"):
            logger.warning("ffmpeg not found, metadata embedding will be disabled")
            return False
        
        return True
    
    async def process(self, context: ProcessingContext) -> bool:
        """Embed metadata into video file"""
        if not self.config.get("enabled", True):
            return True
        
        try:
            video_file = context.file_path
            if not video_file.exists():
                logger.error(f"Video file not found: {video_file}")
                return False
            
            # Check if we have metadata to embed
            metadata = context.metadata
            if not metadata:
                logger.info("No metadata available to embed")
                return True
            
            # Create backup if requested
            if self.config.get("create_backup", False):
                backup_path = video_file.with_suffix(f"{video_file.suffix}.backup")
                if not backup_path.exists():
                    shutil.copy2(video_file, backup_path)
            
            # Embed metadata using ffmpeg
            await self._embed_metadata(video_file, metadata)
            
            logger.info(f"Embedded metadata into: {video_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to embed metadata: {e}")
            return False
    
    async def _embed_metadata(self, video_path: Path, metadata: Dict[str, Any]):
        """Embed metadata using ffmpeg"""
        temp_path = video_path.with_suffix(f".temp{video_path.suffix}")
        
        cmd = [
            "ffmpeg",
            "-i", str(video_path),
            "-c", "copy",  # Copy streams without re-encoding
        ]
        
        # Add metadata options
        if self.config.get("embed_title", True) and metadata.get("title"):
            cmd.extend(["-metadata", f"title={metadata['title']}"])
        
        if self.config.get("embed_description", True) and metadata.get("description"):
            # Truncate description if too long
            description = metadata["description"][:500] + "..." if len(metadata["description"]) > 500 else metadata["description"]
            cmd.extend(["-metadata", f"comment={description}"])
        
        if self.config.get("embed_uploader", True) and metadata.get("uploader"):
            cmd.extend(["-metadata", f"artist={metadata['uploader']}"])
        
        if self.config.get("embed_upload_date", True) and metadata.get("upload_date"):
            cmd.extend(["-metadata", f"date={metadata['upload_date']}"])
        
        cmd.extend(["-y", str(temp_path)])  # Overwrite output file
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown ffmpeg error"
            if temp_path.exists():
                temp_path.unlink()
            raise Exception(f"ffmpeg failed: {error_msg}")
        
        # Replace original file with metadata-embedded version
        video_path.unlink()
        temp_path.rename(video_path)
    
    async def cleanup(self, context: ProcessingContext):
        """Clean up temporary files"""
        temp_path = context.file_path.with_suffix(f".temp{context.file_path.suffix}")
        if temp_path.exists():
            temp_path.unlink()
