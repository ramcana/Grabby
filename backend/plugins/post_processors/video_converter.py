"""
Video Converter Plugin
Converts videos to different formats and qualities
"""
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any
import subprocess
import shutil

from ..base_plugins import PostProcessor, PluginMetadata, PluginType, ProcessingContext

logger = logging.getLogger(__name__)

class VideoConverter(PostProcessor):
    """Convert videos to different formats and qualities"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="video_converter",
            version="1.0.0",
            description="Convert videos to different formats using ffmpeg",
            author="Grabby Team",
            plugin_type=PluginType.POST_PROCESSOR,
            dependencies=["ffmpeg"],
            config_schema={
                "enabled": {"type": "boolean", "default": False},
                "output_format": {"type": "string", "default": "mp4", "enum": ["mp4", "mkv", "avi", "webm"]},
                "video_codec": {"type": "string", "default": "libx264", "enum": ["libx264", "libx265", "copy"]},
                "audio_codec": {"type": "string", "default": "aac", "enum": ["aac", "mp3", "copy"]},
                "quality": {"type": "string", "default": "medium", "enum": ["low", "medium", "high", "lossless"]},
                "max_resolution": {"type": "string", "default": "1080p", "enum": ["480p", "720p", "1080p", "1440p", "2160p"]},
                "keep_original": {"type": "boolean", "default": True}
            }
        )
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration"""
        if not shutil.which("ffmpeg"):
            logger.warning("ffmpeg not found, video conversion will be disabled")
            return False
        
        return True
    
    async def process(self, context: ProcessingContext) -> bool:
        """Convert video file"""
        if not self.config.get("enabled", False):
            return True
        
        try:
            video_file = context.file_path
            if not video_file.exists():
                logger.error(f"Video file not found: {video_file}")
                return False
            
            # Generate output filename
            output_format = self.config.get("output_format", "mp4")
            output_file = video_file.with_suffix(f".converted.{output_format}")
            
            # Skip if converted file already exists
            if output_file.exists():
                logger.info(f"Converted file already exists: {output_file}")
                return True
            
            # Convert video
            await self._convert_video(video_file, output_file)
            
            # Replace original if requested
            if not self.config.get("keep_original", True):
                video_file.unlink()
                output_file.rename(video_file)
                context.file_path = video_file
            else:
                context.file_path = output_file
            
            logger.info(f"Converted video: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to convert video: {e}")
            return False
    
    async def _convert_video(self, input_path: Path, output_path: Path):
        """Convert video using ffmpeg"""
        cmd = ["ffmpeg", "-i", str(input_path)]
        
        # Video codec
        video_codec = self.config.get("video_codec", "libx264")
        if video_codec != "copy":
            cmd.extend(["-c:v", video_codec])
            
            # Quality settings
            quality = self.config.get("quality", "medium")
            if video_codec in ["libx264", "libx265"]:
                crf_values = {"low": "28", "medium": "23", "high": "18", "lossless": "0"}
                cmd.extend(["-crf", crf_values[quality]])
        else:
            cmd.extend(["-c:v", "copy"])
        
        # Audio codec
        audio_codec = self.config.get("audio_codec", "aac")
        cmd.extend(["-c:a", audio_codec])
        
        # Resolution scaling
        max_resolution = self.config.get("max_resolution", "1080p")
        resolution_map = {
            "480p": "854:480",
            "720p": "1280:720", 
            "1080p": "1920:1080",
            "1440p": "2560:1440",
            "2160p": "3840:2160"
        }
        
        if max_resolution in resolution_map:
            scale = resolution_map[max_resolution]
            cmd.extend(["-vf", f"scale={scale}:force_original_aspect_ratio=decrease"])
        
        cmd.extend(["-y", str(output_path)])  # Overwrite output file
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown ffmpeg error"
            if output_path.exists():
                output_path.unlink()
            raise Exception(f"ffmpeg conversion failed: {error_msg}")
    
    async def cleanup(self, context: ProcessingContext):
        """Clean up temporary files"""
        pass
