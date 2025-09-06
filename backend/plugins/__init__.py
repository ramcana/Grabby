"""
Plugin system for Grabby Video Downloader
Enables extensible post-processing, custom extractors, and notifications
"""

from .plugin_manager import PluginManager
from .base_plugins import PostProcessor, Extractor, Notifier
from .post_processors import *
from .extractors import *
from .notifiers import *

__all__ = [
    'PluginManager',
    'PostProcessor', 
    'Extractor',
    'Notifier',
]
