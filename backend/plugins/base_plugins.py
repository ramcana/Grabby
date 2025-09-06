"""
Base plugin classes for the Grabby plugin system
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class PluginType(Enum):
    POST_PROCESSOR = "post_processor"
    EXTRACTOR = "extractor"
    NOTIFIER = "notifier"

@dataclass
class PluginMetadata:
    """Metadata for a plugin"""
    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    dependencies: List[str] = None
    config_schema: Dict[str, Any] = None

@dataclass
class ProcessingContext:
    """Context passed to plugins during processing"""
    file_path: Path
    metadata: Dict[str, Any]
    download_options: Dict[str, Any]
    temp_dir: Path
    output_dir: Path
    
class PostProcessor(ABC):
    """Base class for post-processing plugins"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.metadata = self.get_metadata()
    
    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata"""
        pass
    
    @abstractmethod
    async def process(self, context: ProcessingContext) -> bool:
        """
        Process the downloaded file
        
        Args:
            context: Processing context with file path, metadata, etc.
            
        Returns:
            bool: True if processing was successful
        """
        pass
    
    async def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration"""
        return True
    
    async def cleanup(self, context: ProcessingContext):
        """Clean up any temporary files or resources"""
        pass

class Extractor(ABC):
    """Base class for custom video extractors"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.metadata = self.get_metadata()
    
    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata"""
        pass
    
    @abstractmethod
    def can_extract(self, url: str) -> bool:
        """Check if this extractor can handle the given URL"""
        pass
    
    @abstractmethod
    async def extract_info(self, url: str) -> Dict[str, Any]:
        """Extract video information without downloading"""
        pass
    
    @abstractmethod
    async def extract_download_url(self, url: str, quality: str = "best") -> str:
        """Extract direct download URL"""
        pass

class Notifier(ABC):
    """Base class for notification plugins"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.metadata = self.get_metadata()
    
    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """Return plugin metadata"""
        pass
    
    @abstractmethod
    async def notify_download_started(self, url: str, metadata: Dict[str, Any]):
        """Notify when download starts"""
        pass
    
    @abstractmethod
    async def notify_download_completed(self, file_path: Path, metadata: Dict[str, Any]):
        """Notify when download completes"""
        pass
    
    @abstractmethod
    async def notify_download_failed(self, url: str, error: str, metadata: Dict[str, Any]):
        """Notify when download fails"""
        pass
    
    async def notify_batch_completed(self, results: List[Dict[str, Any]]):
        """Notify when batch download completes"""
        pass
