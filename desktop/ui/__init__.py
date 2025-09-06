"""
Advanced Desktop UI Components for Grabby
"""

from .download_config_dialog import DownloadConfigDialog
from .queue_management_widget import QueueManagementWidget
from .settings_panel import SettingsPanel
from .download_scheduler import DownloadScheduler
from .media_player import MediaPlayerWidget

__all__ = [
    'DownloadConfigDialog',
    'QueueManagementWidget', 
    'SettingsPanel',
    'DownloadScheduler',
    'MediaPlayerWidget'
]
