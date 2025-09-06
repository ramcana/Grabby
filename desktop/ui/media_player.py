"""
Media Player Widget for Advanced Desktop UI
"""
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSlider,
    QLabel, QGroupBox, QListWidget, QListWidgetItem, QSplitter,
    QFileDialog, QMessageBox, QProgressBar, QComboBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QUrl
from PyQt6.QtGui import QPixmap, QFont
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

class MediaPlayerWidget(QWidget):
    """Advanced media player widget for previewing downloaded content"""
    
    media_loaded = pyqtSignal(str)  # file_path
    playback_started = pyqtSignal()
    playback_paused = pyqtSignal()
    playback_stopped = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_file = None
        self.playlist = []
        self.current_index = -1
        
        self.init_ui()
        self.setup_media_player()
    
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        
        # Create splitter for main content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side: Video/Audio display
        media_widget = self.create_media_display()
        splitter.addWidget(media_widget)
        
        # Right side: Playlist and controls
        controls_widget = self.create_controls_panel()
        splitter.addWidget(controls_widget)
        
        # Set splitter proportions (70% media, 30% controls)
        splitter.setSizes([700, 300])
        
        layout.addWidget(splitter)
        
        # Bottom: Transport controls
        transport_widget = self.create_transport_controls()
        layout.addWidget(transport_widget)
        
        self.setLayout(layout)
    
    def create_media_display(self) -> QWidget:
        """Create media display area"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Video display
        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumSize(400, 300)
        self.video_widget.setStyleSheet("background-color: black;")
        layout.addWidget(self.video_widget)
        
        # Media info display
        info_group = QGroupBox("Media Information")
        info_layout = QVBoxLayout()
        
        self.media_info_label = QLabel("No media loaded")
        self.media_info_label.setWordWrap(True)
        self.media_info_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        info_layout.addWidget(self.media_info_label)
        
        info_group.setLayout(info_layout)
        info_group.setMaximumHeight(120)
        layout.addWidget(info_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_controls_panel(self) -> QWidget:
        """Create controls panel"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # File operations
        file_group = QGroupBox("File Operations")
        file_layout = QVBoxLayout()
        
        open_btn = QPushButton("📁 Open File")
        open_btn.clicked.connect(self.open_file)
        file_layout.addWidget(open_btn)
        
        open_folder_btn = QPushButton("📂 Open Folder")
        open_folder_btn.clicked.connect(self.open_folder)
        file_layout.addWidget(open_folder_btn)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Playlist
        playlist_group = QGroupBox("Playlist")
        playlist_layout = QVBoxLayout()
        
        self.playlist_widget = QListWidget()
        self.playlist_widget.itemDoubleClicked.connect(self.play_selected_item)
        playlist_layout.addWidget(self.playlist_widget)
        
        # Playlist controls
        playlist_controls = QHBoxLayout()
        
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_playlist)
        playlist_controls.addWidget(clear_btn)
        
        shuffle_btn = QPushButton("🔀")
        shuffle_btn.setToolTip("Shuffle")
        shuffle_btn.clicked.connect(self.shuffle_playlist)
        playlist_controls.addWidget(shuffle_btn)
        
        repeat_btn = QPushButton("🔁")
        repeat_btn.setToolTip("Repeat")
        repeat_btn.setCheckable(True)
        playlist_controls.addWidget(repeat_btn)
        
        playlist_layout.addLayout(playlist_controls)
        playlist_group.setLayout(playlist_layout)
        layout.addWidget(playlist_group)
        
        # Playback settings
        settings_group = QGroupBox("Playback Settings")
        settings_layout = QVBoxLayout()
        
        # Volume control
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(QLabel("Volume:"))
        
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.valueChanged.connect(self.set_volume)
        volume_layout.addWidget(self.volume_slider)
        
        self.volume_label = QLabel("50%")
        volume_layout.addWidget(self.volume_label)
        
        settings_layout.addLayout(volume_layout)
        
        # Playback speed
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Speed:"))
        
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.25x", "0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "2.0x"])
        self.speed_combo.setCurrentText("1.0x")
        self.speed_combo.currentTextChanged.connect(self.set_playback_speed)
        speed_layout.addWidget(self.speed_combo)
        
        settings_layout.addLayout(speed_layout)
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_transport_controls(self) -> QWidget:
        """Create transport controls"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Progress bar
        progress_layout = QHBoxLayout()
        
        self.current_time_label = QLabel("00:00")
        progress_layout.addWidget(self.current_time_label)
        
        self.progress_slider = QSlider(Qt.Orientation.Horizontal)
        self.progress_slider.sliderPressed.connect(self.on_progress_pressed)
        self.progress_slider.sliderReleased.connect(self.on_progress_released)
        progress_layout.addWidget(self.progress_slider)
        
        self.total_time_label = QLabel("00:00")
        progress_layout.addWidget(self.total_time_label)
        
        layout.addLayout(progress_layout)
        
        # Transport buttons
        transport_layout = QHBoxLayout()
        
        self.prev_btn = QPushButton("⏮️")
        self.prev_btn.setToolTip("Previous")
        self.prev_btn.clicked.connect(self.previous_track)
        transport_layout.addWidget(self.prev_btn)
        
        self.play_pause_btn = QPushButton("▶️")
        self.play_pause_btn.setToolTip("Play/Pause")
        self.play_pause_btn.clicked.connect(self.toggle_playback)
        transport_layout.addWidget(self.play_pause_btn)
        
        self.stop_btn = QPushButton("⏹️")
        self.stop_btn.setToolTip("Stop")
        self.stop_btn.clicked.connect(self.stop_playback)
        transport_layout.addWidget(self.stop_btn)
        
        self.next_btn = QPushButton("⏭️")
        self.next_btn.setToolTip("Next")
        self.next_btn.clicked.connect(self.next_track)
        transport_layout.addWidget(self.next_btn)
        
        transport_layout.addStretch()
        
        # Additional controls
        self.mute_btn = QPushButton("🔊")
        self.mute_btn.setToolTip("Mute")
        self.mute_btn.setCheckable(True)
        self.mute_btn.clicked.connect(self.toggle_mute)
        transport_layout.addWidget(self.mute_btn)
        
        self.fullscreen_btn = QPushButton("⛶")
        self.fullscreen_btn.setToolTip("Fullscreen")
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        transport_layout.addWidget(self.fullscreen_btn)
        
        layout.addLayout(transport_layout)
        widget.setLayout(layout)
        return widget
    
    def setup_media_player(self):
        """Setup media player components"""
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        
        # Connect media player to video widget and audio output
        self.media_player.setVideoOutput(self.video_widget)
        self.media_player.setAudioOutput(self.audio_output)
        
        # Connect signals
        self.media_player.positionChanged.connect(self.update_position)
        self.media_player.durationChanged.connect(self.update_duration)
        self.media_player.playbackStateChanged.connect(self.on_playback_state_changed)
        self.media_player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.media_player.errorOccurred.connect(self.on_media_error)
        
        # Setup timer for UI updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(100)  # Update every 100ms
    
    def open_file(self):
        """Open a single media file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Media File", "",
            "Media Files (*.mp4 *.mkv *.avi *.webm *.mp3 *.m4a *.wav *.flac);;All Files (*)"
        )
        
        if file_path:
            self.load_media(file_path)
    
    def open_folder(self):
        """Open a folder and add all media files to playlist"""
        folder_path = QFileDialog.getExistingDirectory(self, "Select Media Folder")
        
        if folder_path:
            self.load_folder(folder_path)
    
    def load_media(self, file_path: str):
        """Load a media file"""
        try:
            self.current_file = file_path
            
            # Set media source
            media_url = QUrl.fromLocalFile(file_path)
            self.media_player.setSource(media_url)
            
            # Add to playlist if not already there
            if file_path not in self.playlist:
                self.playlist.append(file_path)
                self.update_playlist_widget()
            
            # Update current index
            self.current_index = self.playlist.index(file_path)
            self.highlight_current_item()
            
            # Update media info
            self.update_media_info(file_path)
            
            self.media_loaded.emit(file_path)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load media: {e}")
    
    def load_folder(self, folder_path: str):
        """Load all media files from a folder"""
        try:
            folder = Path(folder_path)
            media_extensions = {'.mp4', '.mkv', '.avi', '.webm', '.mp3', '.m4a', '.wav', '.flac'}
            
            media_files = []
            for file_path in folder.rglob('*'):
                if file_path.suffix.lower() in media_extensions:
                    media_files.append(str(file_path))
            
            if media_files:
                self.playlist.extend([f for f in media_files if f not in self.playlist])
                self.update_playlist_widget()
                
                # Load first file
                if media_files:
                    self.load_media(media_files[0])
                
                QMessageBox.information(self, "Success", f"Added {len(media_files)} media files to playlist")
            else:
                QMessageBox.information(self, "No Media", "No media files found in the selected folder")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load folder: {e}")
    
    def update_playlist_widget(self):
        """Update the playlist widget"""
        self.playlist_widget.clear()
        
        for file_path in self.playlist:
            file_name = Path(file_path).name
            item = QListWidgetItem(file_name)
            item.setData(Qt.ItemDataRole.UserRole, file_path)
            self.playlist_widget.addItem(item)
    
    def highlight_current_item(self):
        """Highlight the currently playing item"""
        if self.current_index >= 0 and self.current_index < self.playlist_widget.count():
            self.playlist_widget.setCurrentRow(self.current_index)
    
    def play_selected_item(self, item: QListWidgetItem):
        """Play the selected playlist item"""
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if file_path:
            self.load_media(file_path)
            self.play_media()
    
    def update_media_info(self, file_path: str):
        """Update media information display"""
        try:
            file_path_obj = Path(file_path)
            
            info_text = f"File: {file_path_obj.name}\n"
            info_text += f"Size: {self.format_file_size(file_path_obj.stat().st_size)}\n"
            info_text += f"Path: {file_path_obj.parent}\n"
            
            # Additional metadata would be added here in a full implementation
            # This would require a media metadata library like mutagen or ffprobe
            
            self.media_info_label.setText(info_text)
            
        except Exception as e:
            self.media_info_label.setText(f"Error reading file info: {e}")
    
    def format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
    
    def toggle_playback(self):
        """Toggle play/pause"""
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.pause_media()
        else:
            self.play_media()
    
    def play_media(self):
        """Start playback"""
        if self.current_file:
            self.media_player.play()
            self.playback_started.emit()
    
    def pause_media(self):
        """Pause playback"""
        self.media_player.pause()
        self.playback_paused.emit()
    
    def stop_playback(self):
        """Stop playback"""
        self.media_player.stop()
        self.playback_stopped.emit()
    
    def previous_track(self):
        """Play previous track"""
        if self.current_index > 0:
            self.current_index -= 1
            self.load_media(self.playlist[self.current_index])
            self.play_media()
    
    def next_track(self):
        """Play next track"""
        if self.current_index < len(self.playlist) - 1:
            self.current_index += 1
            self.load_media(self.playlist[self.current_index])
            self.play_media()
    
    def set_volume(self, volume: int):
        """Set playback volume"""
        self.audio_output.setVolume(volume / 100.0)
        self.volume_label.setText(f"{volume}%")
    
    def toggle_mute(self, muted: bool):
        """Toggle mute"""
        self.audio_output.setMuted(muted)
        self.mute_btn.setText("🔇" if muted else "🔊")
    
    def set_playback_speed(self, speed_text: str):
        """Set playback speed"""
        try:
            speed = float(speed_text.replace('x', ''))
            self.media_player.setPlaybackRate(speed)
        except ValueError:
            pass
    
    def clear_playlist(self):
        """Clear the playlist"""
        self.playlist.clear()
        self.playlist_widget.clear()
        self.current_index = -1
    
    def shuffle_playlist(self):
        """Shuffle the playlist"""
        import random
        if self.playlist:
            current_file = self.current_file
            random.shuffle(self.playlist)
            self.update_playlist_widget()
            
            # Update current index
            if current_file and current_file in self.playlist:
                self.current_index = self.playlist.index(current_file)
                self.highlight_current_item()
    
    def toggle_fullscreen(self):
        """Toggle fullscreen video"""
        if self.video_widget.isFullScreen():
            self.video_widget.setFullScreen(False)
            self.fullscreen_btn.setText("⛶")
        else:
            self.video_widget.setFullScreen(True)
            self.fullscreen_btn.setText("🗗")
    
    def update_position(self, position: int):
        """Update playback position"""
        self.progress_slider.setValue(position)
        self.current_time_label.setText(self.format_time(position))
    
    def update_duration(self, duration: int):
        """Update media duration"""
        self.progress_slider.setRange(0, duration)
        self.total_time_label.setText(self.format_time(duration))
    
    def format_time(self, milliseconds: int) -> str:
        """Format time in MM:SS format"""
        seconds = milliseconds // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    def on_progress_pressed(self):
        """Handle progress slider press"""
        self.media_player.pause()
    
    def on_progress_released(self):
        """Handle progress slider release"""
        position = self.progress_slider.value()
        self.media_player.setPosition(position)
        self.media_player.play()
    
    def on_playback_state_changed(self, state):
        """Handle playback state changes"""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_pause_btn.setText("⏸️")
            self.play_pause_btn.setToolTip("Pause")
        else:
            self.play_pause_btn.setText("▶️")
            self.play_pause_btn.setToolTip("Play")
    
    def on_media_status_changed(self, status):
        """Handle media status changes"""
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            # Auto-play next track
            self.next_track()
    
    def on_media_error(self, error):
        """Handle media errors"""
        error_messages = {
            QMediaPlayer.Error.NoError: "No error",
            QMediaPlayer.Error.ResourceError: "Resource error",
            QMediaPlayer.Error.FormatError: "Format error",
            QMediaPlayer.Error.NetworkError: "Network error",
            QMediaPlayer.Error.AccessDeniedError: "Access denied"
        }
        
        error_msg = error_messages.get(error, "Unknown error")
        QMessageBox.critical(self, "Media Error", f"Playback error: {error_msg}")
    
    def update_ui(self):
        """Update UI elements"""
        # This method can be used for periodic UI updates
        pass
    
    def load_downloaded_file(self, file_path: str):
        """Load a downloaded file for preview"""
        if Path(file_path).exists():
            self.load_media(file_path)
        else:
            QMessageBox.warning(self, "File Not Found", f"File not found: {file_path}")
    
    def get_current_media_info(self) -> Optional[Dict[str, Any]]:
        """Get information about currently loaded media"""
        if not self.current_file:
            return None
        
        return {
            'file_path': self.current_file,
            'duration': self.media_player.duration(),
            'position': self.media_player.position(),
            'state': self.media_player.playbackState(),
            'volume': self.audio_output.volume(),
            'muted': self.audio_output.isMuted()
        }
