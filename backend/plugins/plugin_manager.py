"""
Plugin Manager for the Grabby plugin system
Handles plugin discovery, loading, and execution
"""
import asyncio
import logging
import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Any, Optional, Type, Union
import json
import traceback

from .base_plugins import PostProcessor, Extractor, Notifier, PluginType, ProcessingContext, PluginMetadata

logger = logging.getLogger(__name__)

class PluginManager:
    """Manages all plugins in the system"""
    
    def __init__(self, plugin_dirs: Optional[List[Path]] = None):
        self.plugin_dirs = plugin_dirs or [
            Path(__file__).parent / "post_processors",
            Path(__file__).parent / "extractors", 
            Path(__file__).parent / "notifiers"
        ]
        
        # Plugin registries
        self.post_processors: Dict[str, PostProcessor] = {}
        self.extractors: Dict[str, Extractor] = {}
        self.notifiers: Dict[str, Notifier] = {}
        
        # Plugin configurations
        self.plugin_configs: Dict[str, Dict[str, Any]] = {}
        
        # Plugin execution order
        self.post_processor_order: List[str] = []
        self.enabled_plugins: Dict[str, bool] = {}
    
    async def initialize(self, config_path: Optional[Path] = None):
        """Initialize the plugin manager"""
        # Load configuration
        if config_path and config_path.exists():
            await self.load_config(config_path)
        
        # Discover and load plugins
        await self.discover_plugins()
        await self.load_plugins()
        
        logger.info(f"Loaded {len(self.post_processors)} post-processors, "
                   f"{len(self.extractors)} extractors, "
                   f"{len(self.notifiers)} notifiers")
    
    async def load_config(self, config_path: Path):
        """Load plugin configuration from file"""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            self.plugin_configs = config.get('plugin_configs', {})
            self.post_processor_order = config.get('post_processor_order', [])
            self.enabled_plugins = config.get('enabled_plugins', {})
            
        except Exception as e:
            logger.error(f"Failed to load plugin config: {e}")
    
    async def save_config(self, config_path: Path):
        """Save plugin configuration to file"""
        try:
            config = {
                'plugin_configs': self.plugin_configs,
                'post_processor_order': self.post_processor_order,
                'enabled_plugins': self.enabled_plugins
            }
            
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save plugin config: {e}")
    
    async def discover_plugins(self):
        """Discover available plugins in plugin directories"""
        for plugin_dir in self.plugin_dirs:
            if not plugin_dir.exists():
                continue
            
            for plugin_file in plugin_dir.glob("*.py"):
                if plugin_file.name.startswith("__"):
                    continue
                
                try:
                    # Import the plugin module
                    module_name = f"backend.plugins.{plugin_dir.name}.{plugin_file.stem}"
                    spec = importlib.util.spec_from_file_location(module_name, plugin_file)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Find plugin classes
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if (issubclass(obj, (PostProcessor, Extractor, Notifier)) and 
                            obj not in (PostProcessor, Extractor, Notifier)):
                            
                            logger.debug(f"Discovered plugin: {name} in {plugin_file}")
                            
                except Exception as e:
                    logger.error(f"Failed to discover plugins in {plugin_file}: {e}")
    
    async def load_plugins(self):
        """Load and instantiate discovered plugins"""
        # Load built-in plugins
        await self._load_builtin_plugins()
    
    async def _load_builtin_plugins(self):
        """Load built-in plugins"""
        # Import and register built-in plugins
        try:
            from .post_processors.thumbnail_extractor import ThumbnailExtractor
            from .post_processors.metadata_embedder import MetadataEmbedder
            from .post_processors.video_converter import VideoConverter
            from .notifiers.console_notifier import ConsoleNotifier
            from .notifiers.desktop_notifier import DesktopNotifier
            
            # Register post-processors
            await self.register_plugin(ThumbnailExtractor())
            await self.register_plugin(MetadataEmbedder())
            await self.register_plugin(VideoConverter())
            
            # Register notifiers
            await self.register_plugin(ConsoleNotifier())
            await self.register_plugin(DesktopNotifier())
            
        except ImportError as e:
            logger.warning(f"Some built-in plugins not available: {e}")
    
    async def register_plugin(self, plugin: Union[PostProcessor, Extractor, Notifier]):
        """Register a plugin instance"""
        try:
            metadata = plugin.get_metadata()
            plugin_name = metadata.name
            
            # Apply configuration if available
            if plugin_name in self.plugin_configs:
                plugin.config.update(self.plugin_configs[plugin_name])
            
            # Validate configuration
            if hasattr(plugin, 'validate_config'):
                if not await plugin.validate_config(plugin.config):
                    logger.error(f"Invalid configuration for plugin {plugin_name}")
                    return False
            
            # Register based on type
            if isinstance(plugin, PostProcessor):
                self.post_processors[plugin_name] = plugin
                if plugin_name not in self.post_processor_order:
                    self.post_processor_order.append(plugin_name)
            elif isinstance(plugin, Extractor):
                self.extractors[plugin_name] = plugin
            elif isinstance(plugin, Notifier):
                self.notifiers[plugin_name] = plugin
            
            # Enable by default if not configured
            if plugin_name not in self.enabled_plugins:
                self.enabled_plugins[plugin_name] = True
            
            logger.info(f"Registered plugin: {plugin_name} ({metadata.plugin_type.value})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register plugin {plugin.__class__.__name__}: {e}")
            return False
    
    async def process_file(self, context: ProcessingContext) -> bool:
        """Run all enabled post-processors on a file"""
        success = True
        
        for plugin_name in self.post_processor_order:
            if not self.enabled_plugins.get(plugin_name, True):
                continue
            
            if plugin_name not in self.post_processors:
                continue
            
            plugin = self.post_processors[plugin_name]
            
            try:
                logger.debug(f"Running post-processor: {plugin_name}")
                result = await plugin.process(context)
                
                if not result:
                    logger.warning(f"Post-processor {plugin_name} returned False")
                    success = False
                
            except Exception as e:
                logger.error(f"Post-processor {plugin_name} failed: {e}")
                logger.debug(traceback.format_exc())
                success = False
        
        return success
    
    async def extract_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Try to extract info using custom extractors"""
        for plugin_name, extractor in self.extractors.items():
            if not self.enabled_plugins.get(plugin_name, True):
                continue
            
            try:
                if extractor.can_extract(url):
                    logger.debug(f"Using extractor: {plugin_name}")
                    return await extractor.extract_info(url)
            except Exception as e:
                logger.error(f"Extractor {plugin_name} failed: {e}")
        
        return None
    
    async def get_download_url(self, url: str, quality: str = "best") -> Optional[str]:
        """Get direct download URL using custom extractors"""
        for plugin_name, extractor in self.extractors.items():
            if not self.enabled_plugins.get(plugin_name, True):
                continue
            
            try:
                if extractor.can_extract(url):
                    logger.debug(f"Using extractor for download URL: {plugin_name}")
                    return await extractor.extract_download_url(url, quality)
            except Exception as e:
                logger.error(f"Extractor {plugin_name} failed to get download URL: {e}")
        
        return None
    
    async def notify_download_started(self, url: str, metadata: Dict[str, Any]):
        """Notify all enabled notifiers of download start"""
        for plugin_name, notifier in self.notifiers.items():
            if not self.enabled_plugins.get(plugin_name, True):
                continue
            
            try:
                await notifier.notify_download_started(url, metadata)
            except Exception as e:
                logger.error(f"Notifier {plugin_name} failed: {e}")
    
    async def notify_download_completed(self, file_path: Path, metadata: Dict[str, Any]):
        """Notify all enabled notifiers of download completion"""
        for plugin_name, notifier in self.notifiers.items():
            if not self.enabled_plugins.get(plugin_name, True):
                continue
            
            try:
                await notifier.notify_download_completed(file_path, metadata)
            except Exception as e:
                logger.error(f"Notifier {plugin_name} failed: {e}")
    
    async def notify_download_failed(self, url: str, error: str, metadata: Dict[str, Any]):
        """Notify all enabled notifiers of download failure"""
        for plugin_name, notifier in self.notifiers.items():
            if not self.enabled_plugins.get(plugin_name, True):
                continue
            
            try:
                await notifier.notify_download_failed(url, error, metadata)
            except Exception as e:
                logger.error(f"Notifier {plugin_name} failed: {e}")
    
    async def notify_batch_completed(self, results: List[Dict[str, Any]]):
        """Notify all enabled notifiers of batch completion"""
        for plugin_name, notifier in self.notifiers.items():
            if not self.enabled_plugins.get(plugin_name, True):
                continue
            
            try:
                await notifier.notify_batch_completed(results)
            except Exception as e:
                logger.error(f"Notifier {plugin_name} failed: {e}")
    
    def get_plugin_info(self) -> Dict[str, Any]:
        """Get information about all loaded plugins"""
        info = {
            'post_processors': {},
            'extractors': {},
            'notifiers': {}
        }
        
        for name, plugin in self.post_processors.items():
            metadata = plugin.get_metadata()
            info['post_processors'][name] = {
                'metadata': metadata.__dict__,
                'enabled': self.enabled_plugins.get(name, True),
                'config': plugin.config
            }
        
        for name, plugin in self.extractors.items():
            metadata = plugin.get_metadata()
            info['extractors'][name] = {
                'metadata': metadata.__dict__,
                'enabled': self.enabled_plugins.get(name, True),
                'config': plugin.config
            }
        
        for name, plugin in self.notifiers.items():
            metadata = plugin.get_metadata()
            info['notifiers'][name] = {
                'metadata': metadata.__dict__,
                'enabled': self.enabled_plugins.get(name, True),
                'config': plugin.config
            }
        
        return info
    
    async def enable_plugin(self, plugin_name: str):
        """Enable a plugin"""
        self.enabled_plugins[plugin_name] = True
    
    async def disable_plugin(self, plugin_name: str):
        """Disable a plugin"""
        self.enabled_plugins[plugin_name] = False
    
    async def configure_plugin(self, plugin_name: str, config: Dict[str, Any]):
        """Configure a plugin"""
        self.plugin_configs[plugin_name] = config
        
        # Update plugin instance if loaded
        for plugin_dict in [self.post_processors, self.extractors, self.notifiers]:
            if plugin_name in plugin_dict:
                plugin_dict[plugin_name].config.update(config)
                break
    
    async def set_post_processor_order(self, order: List[str]):
        """Set the execution order for post-processors"""
        # Validate that all plugins exist
        valid_order = [name for name in order if name in self.post_processors]
        self.post_processor_order = valid_order
