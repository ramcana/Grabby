"""
Enhanced CLI with TUI (Text User Interface) for Grabby
"""
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Header, Footer, Input, Button, DataTable, Log, Static, 
    ProgressBar, Tabs, TabPane, Tree, ListView, ListItem,
    Label, Switch, Select, Collapsible
)
from textual.binding import Binding
from textual.reactive import reactive
from textual.message import Message
from textual.screen import Screen
from textual import events
from rich.text import Text
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

import sys
sys.path.append(str(Path(__file__).parent.parent))

from backend.core.unified_downloader import create_downloader
from backend.core.queue_manager import QueueManager, QueueStatus, QueuePriority
from config.profile_manager import ProfileManager
from backend.core.event_bus import get_event_bus

class DownloadScreen(Screen):
    """Screen for adding new downloads"""
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("Add New Download", classes="title"),
            Input(placeholder="Enter video URL...", id="url_input"),
            Horizontal(
                Select(
                    [("Default", "default"), ("High Quality", "high_quality"), 
                     ("Audio Only", "audio_only"), ("Mobile", "mobile")],
                    value="default",
                    id="profile_select"
                ),
                Select(
                    [("Best", "best"), ("1080p", "best[height<=1080]"), 
                     ("720p", "best[height<=720]"), ("480p", "best[height<=480]")],
                    value="best[height<=1080]",
                    id="quality_select"
                ),
                classes="controls"
            ),
            Horizontal(
                Switch(value=False, id="audio_only"),
                Label("Audio Only"),
                Switch(value=True, id="subtitles"),
                Label("Subtitles"),
                classes="switches"
            ),
            Button("Start Download", variant="primary", id="start_download"),
            Button("Get Video Info", variant="default", id="get_info"),
            Static("", id="video_info"),
            classes="download_form"
        )
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start_download":
            self.start_download()
        elif event.button.id == "get_info":
            self.get_video_info()
    
    def start_download(self):
        url_input = self.query_one("#url_input", Input)
        profile_select = self.query_one("#profile_select", Select)
        quality_select = self.query_one("#quality_select", Select)
        
        url = url_input.value.strip()
        if not url:
            self.notify("Please enter a URL", severity="error")
            return
        
        # Add to download queue
        self.app.add_download(url, profile_select.value, quality_select.value)
        url_input.value = ""
        self.notify("Download added to queue", severity="information")
    
    def get_video_info(self):
        url_input = self.query_one("#url_input", Input)
        url = url_input.value.strip()
        
        if not url:
            self.notify("Please enter a URL", severity="error")
            return
        
        # Get video info asynchronously
        asyncio.create_task(self.fetch_video_info(url))
    
    async def fetch_video_info(self, url: str):
        try:
            # This would use the actual downloader to get info
            info = {"title": "Sample Video", "duration": "5:30", "uploader": "Sample Channel"}
            
            info_widget = self.query_one("#video_info", Static)
            info_text = f"Title: {info['title']}\nDuration: {info['duration']}\nUploader: {info['uploader']}"
            info_widget.update(info_text)
            
        except Exception as e:
            self.notify(f"Failed to get video info: {e}", severity="error")

class QueueScreen(Screen):
    """Screen for managing download queue"""
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("Download Queue", classes="title"),
            Horizontal(
                Button("Pause All", id="pause_all"),
                Button("Resume All", id="resume_all"),
                Button("Clear Completed", id="clear_completed"),
                classes="queue_controls"
            ),
            DataTable(id="queue_table"),
            classes="queue_screen"
        )
        yield Footer()
    
    def on_mount(self) -> None:
        table = self.query_one("#queue_table", DataTable)
        table.add_columns("Status", "Title", "Progress", "Speed", "ETA", "Priority")
        self.refresh_queue()
    
    def refresh_queue(self):
        table = self.query_one("#queue_table", DataTable)
        table.clear()
        
        # Get queue items from app
        queue_items = self.app.get_queue_items()
        
        for item in queue_items:
            status_text = Text(item['status'], style=self.get_status_style(item['status']))
            progress_text = f"{item.get('progress', 0):.1f}%"
            
            table.add_row(
                status_text,
                item.get('title', item['url'][:50]),
                progress_text,
                item.get('speed', '-'),
                item.get('eta', '-'),
                item.get('priority', 'medium')
            )
    
    def get_status_style(self, status: str) -> str:
        styles = {
            'downloading': 'blue',
            'completed': 'green',
            'failed': 'red',
            'paused': 'yellow',
            'pending': 'white'
        }
        return styles.get(status, 'white')
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "pause_all":
            self.app.pause_all_downloads()
        elif event.button.id == "resume_all":
            self.app.resume_all_downloads()
        elif event.button.id == "clear_completed":
            self.app.clear_completed_downloads()
        
        self.refresh_queue()

class HistoryScreen(Screen):
    """Screen for viewing download history"""
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("Download History", classes="title"),
            Input(placeholder="Search history...", id="search_input"),
            DataTable(id="history_table"),
            classes="history_screen"
        )
        yield Footer()
    
    def on_mount(self) -> None:
        table = self.query_one("#history_table", DataTable)
        table.add_columns("Date", "Title", "Status", "Size", "Duration")
        self.refresh_history()
    
    def refresh_history(self):
        table = self.query_one("#history_table", DataTable)
        table.clear()
        
        # Get history items from app
        history_items = self.app.get_history_items()
        
        for item in history_items:
            status_text = Text(item['status'], style=self.get_status_style(item['status']))
            
            table.add_row(
                item.get('date', ''),
                item.get('title', item['url'][:50]),
                status_text,
                item.get('size', '-'),
                item.get('duration', '-')
            )
    
    def get_status_style(self, status: str) -> str:
        return 'green' if status == 'completed' else 'red'

class SettingsScreen(Screen):
    """Screen for application settings"""
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield ScrollableContainer(
            Static("Settings", classes="title"),
            Collapsible(
                Vertical(
                    Input(value="./downloads", id="download_path"),
                    Label("Download Path"),
                    Select(
                        [("1", 1), ("2", 2), ("3", 3), ("5", 5), ("10", 10)],
                        value=3,
                        id="concurrent_downloads"
                    ),
                    Label("Max Concurrent Downloads"),
                    Switch(value=True, id="auto_subtitles"),
                    Label("Auto-download subtitles"),
                    Switch(value=False, id="audio_only_default"),
                    Label("Audio-only by default"),
                ),
                title="Download Settings",
                collapsed=False
            ),
            Collapsible(
                Vertical(
                    Select(
                        [("Auto", "auto"), ("yt-dlp", "yt-dlp"), ("Streamlink", "streamlink")],
                        value="auto",
                        id="preferred_engine"
                    ),
                    Label("Preferred Engine"),
                    Switch(value=True, id="engine_fallback"),
                    Label("Enable engine fallback"),
                    Input(placeholder="Rate limit (e.g., 1M)", id="rate_limit"),
                    Label("Rate Limit"),
                ),
                title="Engine Settings",
                collapsed=True
            ),
            Collapsible(
                Vertical(
                    Switch(value=True, id="notifications"),
                    Label("Show notifications"),
                    Switch(value=True, id="auto_refresh"),
                    Label("Auto-refresh queue"),
                    Select(
                        [("Dark", "dark"), ("Light", "light")],
                        value="dark",
                        id="theme"
                    ),
                    Label("Theme"),
                ),
                title="Interface Settings",
                collapsed=True
            ),
            Button("Save Settings", variant="primary", id="save_settings"),
            classes="settings_screen"
        )
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save_settings":
            self.save_settings()
    
    def save_settings(self):
        # Collect all settings and save them
        settings = {
            'download_path': self.query_one("#download_path", Input).value,
            'concurrent_downloads': self.query_one("#concurrent_downloads", Select).value,
            'auto_subtitles': self.query_one("#auto_subtitles", Switch).value,
            'audio_only_default': self.query_one("#audio_only_default", Switch).value,
            'preferred_engine': self.query_one("#preferred_engine", Select).value,
            'engine_fallback': self.query_one("#engine_fallback", Switch).value,
            'rate_limit': self.query_one("#rate_limit", Input).value,
            'notifications': self.query_one("#notifications", Switch).value,
            'auto_refresh': self.query_one("#auto_refresh", Switch).value,
            'theme': self.query_one("#theme", Select).value,
        }
        
        self.app.save_settings(settings)
        self.notify("Settings saved successfully", severity="information")

class ProfilesScreen(Screen):
    """Screen for managing download profiles"""
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("Download Profiles", classes="title"),
            Horizontal(
                ListView(id="profiles_list"),
                Vertical(
                    Static("Profile Details", classes="subtitle"),
                    Input(placeholder="Profile name", id="profile_name"),
                    Input(placeholder="Description", id="profile_description"),
                    Select(
                        [("Best", "best"), ("1080p", "best[height<=1080]"), 
                         ("720p", "best[height<=720]")],
                        value="best[height<=1080]",
                        id="profile_quality"
                    ),
                    Switch(value=False, id="profile_audio_only"),
                    Label("Audio Only"),
                    Switch(value=True, id="profile_subtitles"),
                    Label("Subtitles"),
                    Horizontal(
                        Button("Save Profile", variant="primary", id="save_profile"),
                        Button("Delete Profile", variant="error", id="delete_profile"),
                    ),
                    classes="profile_editor"
                ),
                classes="profiles_container"
            ),
            classes="profiles_screen"
        )
        yield Footer()
    
    def on_mount(self) -> None:
        self.refresh_profiles()
    
    def refresh_profiles(self):
        profiles_list = self.query_one("#profiles_list", ListView)
        profiles_list.clear()
        
        # Get profiles from app
        profiles = self.app.get_profiles()
        
        for profile in profiles:
            profiles_list.append(ListItem(Label(profile['name'])))
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save_profile":
            self.save_profile()
        elif event.button.id == "delete_profile":
            self.delete_profile()
    
    def save_profile(self):
        profile_data = {
            'name': self.query_one("#profile_name", Input).value,
            'description': self.query_one("#profile_description", Input).value,
            'quality': self.query_one("#profile_quality", Select).value,
            'audio_only': self.query_one("#profile_audio_only", Switch).value,
            'subtitles': self.query_one("#profile_subtitles", Switch).value,
        }
        
        if not profile_data['name']:
            self.notify("Please enter a profile name", severity="error")
            return
        
        self.app.save_profile(profile_data)
        self.refresh_profiles()
        self.notify("Profile saved successfully", severity="information")
    
    def delete_profile(self):
        # Implementation for deleting selected profile
        self.notify("Profile deleted", severity="information")

class GrabbyTUI(App):
    """Main TUI application for Grabby"""
    
    CSS_PATH = "tui_styles.css"
    TITLE = "Grabby - Video Downloader TUI"
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("d", "show_downloads", "Downloads"),
        Binding("u", "show_queue", "Queue"),
        Binding("h", "show_history", "History"),
        Binding("s", "show_settings", "Settings"),
        Binding("p", "show_profiles", "Profiles"),
        Binding("r", "refresh", "Refresh"),
    ]
    
    def __init__(self):
        super().__init__()
        self.downloader = None
        self.queue_manager = None
        self.profile_manager = None
        self.event_bus = get_event_bus()
        self.queue_items = []
        self.history_items = []
        self.settings = {}
        self.profiles = []
    
    async def on_mount(self) -> None:
        """Initialize the application"""
        try:
            # Initialize components
            self.downloader = create_downloader()
            self.queue_manager = QueueManager()
            self.profile_manager = ProfileManager()
            
            # Load initial data
            await self.load_profiles()
            await self.load_settings()
            
            # Set up event listeners
            self.setup_event_listeners()
            
            # Start with download screen
            await self.push_screen(DownloadScreen())
            
        except Exception as e:
            self.notify(f"Failed to initialize: {e}", severity="error")
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Tabs(
                TabPane("Downloads", DownloadScreen(), id="downloads"),
                TabPane("Queue", QueueScreen(), id="queue"),
                TabPane("History", HistoryScreen(), id="history"),
                TabPane("Settings", SettingsScreen(), id="settings"),
                TabPane("Profiles", ProfilesScreen(), id="profiles"),
            ),
            id="main_tabs"
        )
        yield Footer()
    
    def setup_event_listeners(self):
        """Set up event bus listeners"""
        self.event_bus.subscribe('download.started', self.on_download_started)
        self.event_bus.subscribe('download.progress', self.on_download_progress)
        self.event_bus.subscribe('download.completed', self.on_download_completed)
        self.event_bus.subscribe('download.failed', self.on_download_failed)
    
    async def on_download_started(self, event):
        """Handle download started event"""
        self.notify(f"Download started: {event.data.get('title', 'Unknown')}")
    
    async def on_download_progress(self, event):
        """Handle download progress event"""
        # Update queue display
        pass
    
    async def on_download_completed(self, event):
        """Handle download completed event"""
        self.notify(f"Download completed: {event.data.get('title', 'Unknown')}", severity="information")
    
    async def on_download_failed(self, event):
        """Handle download failed event"""
        self.notify(f"Download failed: {event.data.get('error', 'Unknown error')}", severity="error")
    
    # Action methods
    def action_show_downloads(self) -> None:
        """Show downloads screen"""
        self.push_screen(DownloadScreen())
    
    def action_show_queue(self) -> None:
        """Show queue screen"""
        self.push_screen(QueueScreen())
    
    def action_show_history(self) -> None:
        """Show history screen"""
        self.push_screen(HistoryScreen())
    
    def action_show_settings(self) -> None:
        """Show settings screen"""
        self.push_screen(SettingsScreen())
    
    def action_show_profiles(self) -> None:
        """Show profiles screen"""
        self.push_screen(ProfilesScreen())
    
    def action_refresh(self) -> None:
        """Refresh current screen"""
        self.notify("Refreshed", severity="information")
    
    # Data methods
    def add_download(self, url: str, profile: str, quality: str):
        """Add a download to the queue"""
        try:
            # Create download item
            download_item = {
                'url': url,
                'profile': profile,
                'quality': quality,
                'status': 'pending',
                'progress': 0,
                'speed': '-',
                'eta': '-',
                'priority': 'medium',
                'title': url  # Will be updated when info is fetched
            }
            
            self.queue_items.append(download_item)
            
            # Start actual download
            asyncio.create_task(self.start_download(download_item))
            
        except Exception as e:
            self.notify(f"Failed to add download: {e}", severity="error")
    
    async def start_download(self, item: Dict[str, Any]):
        """Start downloading an item"""
        try:
            if self.downloader:
                # This would use the actual downloader
                item['status'] = 'downloading'
                
                # Simulate download progress
                for progress in range(0, 101, 10):
                    item['progress'] = progress
                    await asyncio.sleep(0.5)
                
                item['status'] = 'completed'
                self.history_items.append(item.copy())
                
        except Exception as e:
            item['status'] = 'failed'
            self.notify(f"Download failed: {e}", severity="error")
    
    def get_queue_items(self) -> List[Dict[str, Any]]:
        """Get current queue items"""
        return self.queue_items
    
    def get_history_items(self) -> List[Dict[str, Any]]:
        """Get history items"""
        return self.history_items
    
    def pause_all_downloads(self):
        """Pause all active downloads"""
        for item in self.queue_items:
            if item['status'] == 'downloading':
                item['status'] = 'paused'
    
    def resume_all_downloads(self):
        """Resume all paused downloads"""
        for item in self.queue_items:
            if item['status'] == 'paused':
                item['status'] = 'downloading'
    
    def clear_completed_downloads(self):
        """Clear completed downloads from queue"""
        self.queue_items = [item for item in self.queue_items if item['status'] != 'completed']
    
    async def load_profiles(self):
        """Load download profiles"""
        try:
            if self.profile_manager:
                profile_names = self.profile_manager.list_profiles()
                self.profiles = [{'name': name} for name in profile_names]
        except Exception as e:
            self.notify(f"Failed to load profiles: {e}", severity="error")
    
    def get_profiles(self) -> List[Dict[str, Any]]:
        """Get available profiles"""
        return self.profiles
    
    def save_profile(self, profile_data: Dict[str, Any]):
        """Save a download profile"""
        try:
            # This would save to profile manager
            self.profiles.append(profile_data)
        except Exception as e:
            self.notify(f"Failed to save profile: {e}", severity="error")
    
    async def load_settings(self):
        """Load application settings"""
        self.settings = {
            'download_path': './downloads',
            'concurrent_downloads': 3,
            'auto_subtitles': True,
            'audio_only_default': False,
            'preferred_engine': 'auto',
            'engine_fallback': True,
            'rate_limit': '',
            'notifications': True,
            'auto_refresh': True,
            'theme': 'dark',
        }
    
    def save_settings(self, settings: Dict[str, Any]):
        """Save application settings"""
        self.settings.update(settings)

def run_tui():
    """Run the TUI application"""
    app = GrabbyTUI()
    app.run()

if __name__ == "__main__":
    run_tui()
