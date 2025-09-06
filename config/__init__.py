"""
Configuration system for Grabby Video Downloader
Handles profiles, settings, and user preferences
"""

from .profile_manager import ProfileManager, DownloadProfile
from .settings_manager import SettingsManager

__all__ = [
    'ProfileManager',
    'DownloadProfile', 
    'SettingsManager'
]
