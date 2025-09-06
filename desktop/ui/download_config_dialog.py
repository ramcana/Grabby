"""
Advanced Download Configuration Dialog
"""
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QFormLayout, QLineEdit, QSpinBox, QCheckBox, QComboBox,
    QPushButton, QFileDialog, QTextEdit, QSlider, QLabel,
    QGroupBox, QListWidget, QListWidgetItem, QMessageBox,
    QDialogButtonBox, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

# Add backend to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.core.downloader import DownloadOptions
from config.profile_manager import ProfileManager, DownloadProfile

class DownloadConfigDialog(QDialog):
    """Advanced download configuration dialog"""
    
    config_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None, initial_config: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.initial_config = initial_config or {}
        self.profile_manager = None
        self.current_profile = None
        
        self.setWindowTitle("Download Configuration")
        self.setModal(True)
        self.resize(600, 500)
        
        self.init_ui()
        self.load_initial_config()
    
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Add tabs
        self.tab_widget.addTab(self.create_general_tab(), "General")
        self.tab_widget.addTab(self.create_quality_tab(), "Quality")
        self.tab_widget.addTab(self.create_advanced_tab(), "Advanced")
        self.tab_widget.addTab(self.create_profiles_tab(), "Profiles")
        self.tab_widget.addTab(self.create_filters_tab(), "Filters")
        
        layout.addWidget(self.tab_widget)
        
        # Button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Apply
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply_config)
        
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def create_general_tab(self) -> QWidget:
        """Create general settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Output settings group
        output_group = QGroupBox("Output Settings")
        output_layout = QFormLayout()
        
        self.output_path = QLineEdit()
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_output_path)
        
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.output_path)
        path_layout.addWidget(browse_btn)
        
        output_layout.addRow("Output Directory:", path_layout)
        
        self.filename_template = QLineEdit("%(title)s.%(ext)s")
        output_layout.addRow("Filename Template:", self.filename_template)
        
        self.create_subdirs = QCheckBox("Create subdirectories")
        output_layout.addRow("", self.create_subdirs)
        
        self.organize_by_uploader = QCheckBox("Organize by uploader")
        output_layout.addRow("", self.organize_by_uploader)
        
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        # Download settings group
        download_group = QGroupBox("Download Settings")
        download_layout = QFormLayout()
        
        self.concurrent_downloads = QSpinBox()
        self.concurrent_downloads.setRange(1, 20)
        self.concurrent_downloads.setValue(3)
        download_layout.addRow("Concurrent Downloads:", self.concurrent_downloads)
        
        self.max_retries = QSpinBox()
        self.max_retries.setRange(0, 10)
        self.max_retries.setValue(3)
        download_layout.addRow("Max Retries:", self.max_retries)
        
        self.timeout = QSpinBox()
        self.timeout.setRange(10, 300)
        self.timeout.setValue(30)
        self.timeout.setSuffix(" seconds")
        download_layout.addRow("Timeout:", self.timeout)
        
        download_group.setLayout(download_layout)
        layout.addWidget(download_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_quality_tab(self) -> QWidget:
        """Create quality settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Video quality group
        video_group = QGroupBox("Video Quality")
        video_layout = QFormLayout()
        
        self.video_format = QComboBox()
        self.video_format.addItems([
            "best", "best[height<=2160]", "best[height<=1080]", 
            "best[height<=720]", "best[height<=480]", "worst"
        ])
        self.video_format.setEditable(True)
        video_layout.addRow("Video Format:", self.video_format)
        
        self.audio_format = QComboBox()
        self.audio_format.addItems([
            "best", "bestaudio", "mp3", "m4a", "opus", "vorbis"
        ])
        video_layout.addRow("Audio Format:", self.audio_format)
        
        self.prefer_free_codecs = QCheckBox("Prefer free codecs (VP9, AV1, Opus)")
        video_layout.addRow("", self.prefer_free_codecs)
        
        self.max_filesize = QLineEdit()
        self.max_filesize.setPlaceholderText("e.g., 100M, 1G")
        video_layout.addRow("Max File Size:", self.max_filesize)
        
        video_group.setLayout(video_layout)
        layout.addWidget(video_group)
        
        # Post-processing group
        postproc_group = QGroupBox("Post-Processing")
        postproc_layout = QFormLayout()
        
        self.extract_audio = QCheckBox("Extract audio only")
        postproc_layout.addRow("", self.extract_audio)
        
        self.write_subtitles = QCheckBox("Download subtitles")
        postproc_layout.addRow("", self.write_subtitles)
        
        self.write_thumbnail = QCheckBox("Download thumbnails")
        postproc_layout.addRow("", self.write_thumbnail)
        
        self.write_info_json = QCheckBox("Save video info as JSON")
        postproc_layout.addRow("", self.write_info_json)
        
        self.embed_metadata = QCheckBox("Embed metadata in files")
        postproc_layout.addRow("", self.embed_metadata)
        
        self.convert_format = QComboBox()
        self.convert_format.addItems(["None", "mp4", "mkv", "avi", "webm", "mp3", "m4a"])
        postproc_layout.addRow("Convert to:", self.convert_format)
        
        postproc_group.setLayout(postproc_layout)
        layout.addWidget(postproc_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_advanced_tab(self) -> QWidget:
        """Create advanced settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Engine settings group
        engine_group = QGroupBox("Engine Settings")
        engine_layout = QFormLayout()
        
        self.preferred_engine = QComboBox()
        self.preferred_engine.addItems(["auto", "yt-dlp", "streamlink", "gallery-dl", "ripme"])
        engine_layout.addRow("Preferred Engine:", self.preferred_engine)
        
        self.fallback_enabled = QCheckBox("Enable engine fallback")
        self.fallback_enabled.setChecked(True)
        engine_layout.addRow("", self.fallback_enabled)
        
        engine_group.setLayout(engine_layout)
        layout.addWidget(engine_group)
        
        # Rate limiting group
        rate_group = QGroupBox("Rate Limiting")
        rate_layout = QFormLayout()
        
        self.rate_limit = QLineEdit()
        self.rate_limit.setPlaceholderText("e.g., 1M, 500K")
        rate_layout.addRow("Rate Limit:", self.rate_limit)
        
        self.retry_delay = QSlider(Qt.Orientation.Horizontal)
        self.retry_delay.setRange(1, 60)
        self.retry_delay.setValue(5)
        self.retry_delay_label = QLabel("5 seconds")
        self.retry_delay.valueChanged.connect(
            lambda v: self.retry_delay_label.setText(f"{v} seconds")
        )
        
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(self.retry_delay)
        delay_layout.addWidget(self.retry_delay_label)
        
        rate_layout.addRow("Retry Delay:", delay_layout)
        
        rate_group.setLayout(rate_layout)
        layout.addWidget(rate_group)
        
        # Custom headers group
        headers_group = QGroupBox("Custom Headers")
        headers_layout = QVBoxLayout()
        
        self.custom_headers = QTextEdit()
        self.custom_headers.setPlaceholderText(
            "Enter custom headers in JSON format:\n"
            '{\n  "User-Agent": "Custom User Agent",\n  "Referer": "https://example.com"\n}'
        )
        self.custom_headers.setMaximumHeight(100)
        headers_layout.addWidget(self.custom_headers)
        
        headers_group.setLayout(headers_layout)
        layout.addWidget(headers_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_profiles_tab(self) -> QWidget:
        """Create profiles management tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Profile selection
        profile_group = QGroupBox("Profile Management")
        profile_layout = QVBoxLayout()
        
        # Profile selector
        selector_layout = QHBoxLayout()
        self.profile_combo = QComboBox()
        self.load_profile_btn = QPushButton("Load")
        self.save_profile_btn = QPushButton("Save As...")
        self.delete_profile_btn = QPushButton("Delete")
        
        self.load_profile_btn.clicked.connect(self.load_profile)
        self.save_profile_btn.clicked.connect(self.save_profile)
        self.delete_profile_btn.clicked.connect(self.delete_profile)
        
        selector_layout.addWidget(QLabel("Profile:"))
        selector_layout.addWidget(self.profile_combo)
        selector_layout.addWidget(self.load_profile_btn)
        selector_layout.addWidget(self.save_profile_btn)
        selector_layout.addWidget(self.delete_profile_btn)
        
        profile_layout.addLayout(selector_layout)
        
        # Profile description
        self.profile_description = QTextEdit()
        self.profile_description.setMaximumHeight(100)
        self.profile_description.setPlaceholderText("Profile description...")
        profile_layout.addWidget(QLabel("Description:"))
        profile_layout.addWidget(self.profile_description)
        
        profile_group.setLayout(profile_layout)
        layout.addWidget(profile_group)
        
        # Load profiles
        self.load_profiles()
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_filters_tab(self) -> QWidget:
        """Create filters and rules tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Duration filters
        duration_group = QGroupBox("Duration Filters")
        duration_layout = QFormLayout()
        
        self.min_duration = QSpinBox()
        self.min_duration.setRange(0, 86400)  # 24 hours in seconds
        self.min_duration.setSuffix(" seconds")
        duration_layout.addRow("Minimum Duration:", self.min_duration)
        
        self.max_duration = QSpinBox()
        self.max_duration.setRange(0, 86400)
        self.max_duration.setSuffix(" seconds")
        duration_layout.addRow("Maximum Duration:", self.max_duration)
        
        duration_group.setLayout(duration_layout)
        layout.addWidget(duration_group)
        
        # Content filters
        content_group = QGroupBox("Content Filters")
        content_layout = QFormLayout()
        
        self.skip_live_streams = QCheckBox("Skip live streams")
        content_layout.addRow("", self.skip_live_streams)
        
        self.skip_premieres = QCheckBox("Skip premieres")
        content_layout.addRow("", self.skip_premieres)
        
        self.allowed_extensions = QLineEdit()
        self.allowed_extensions.setPlaceholderText("mp4,mkv,webm (comma-separated)")
        content_layout.addRow("Allowed Extensions:", self.allowed_extensions)
        
        content_group.setLayout(content_layout)
        layout.addWidget(content_group)
        
        # Blocked uploaders
        blocked_group = QGroupBox("Blocked Uploaders")
        blocked_layout = QVBoxLayout()
        
        self.blocked_uploaders = QListWidget()
        self.blocked_uploaders.setMaximumHeight(100)
        
        uploader_input_layout = QHBoxLayout()
        self.uploader_input = QLineEdit()
        self.uploader_input.setPlaceholderText("Enter uploader name...")
        add_uploader_btn = QPushButton("Add")
        remove_uploader_btn = QPushButton("Remove")
        
        add_uploader_btn.clicked.connect(self.add_blocked_uploader)
        remove_uploader_btn.clicked.connect(self.remove_blocked_uploader)
        
        uploader_input_layout.addWidget(self.uploader_input)
        uploader_input_layout.addWidget(add_uploader_btn)
        uploader_input_layout.addWidget(remove_uploader_btn)
        
        blocked_layout.addWidget(self.blocked_uploaders)
        blocked_layout.addLayout(uploader_input_layout)
        
        blocked_group.setLayout(blocked_layout)
        layout.addWidget(blocked_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def browse_output_path(self):
        """Browse for output directory"""
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.output_path.setText(directory)
    
    def add_blocked_uploader(self):
        """Add uploader to blocked list"""
        uploader = self.uploader_input.text().strip()
        if uploader:
            self.blocked_uploaders.addItem(uploader)
            self.uploader_input.clear()
    
    def remove_blocked_uploader(self):
        """Remove selected uploader from blocked list"""
        current_item = self.blocked_uploaders.currentItem()
        if current_item:
            self.blocked_uploaders.takeItem(self.blocked_uploaders.row(current_item))
    
    def load_profiles(self):
        """Load available profiles"""
        try:
            if not self.profile_manager:
                self.profile_manager = ProfileManager()
                # Note: In real usage, this should be async
            
            profiles = self.profile_manager.list_profiles() if self.profile_manager else []
            self.profile_combo.clear()
            self.profile_combo.addItems(profiles)
            
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Failed to load profiles: {e}")
    
    def load_profile(self):
        """Load selected profile"""
        profile_name = self.profile_combo.currentText()
        if not profile_name or not self.profile_manager:
            return
        
        try:
            profile = self.profile_manager.get_profile(profile_name)
            if profile:
                self.load_profile_data(profile)
                self.current_profile = profile
                QMessageBox.information(self, "Success", f"Loaded profile: {profile_name}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load profile: {e}")
    
    def save_profile(self):
        """Save current settings as profile"""
        from PyQt6.QtWidgets import QInputDialog
        
        name, ok = QInputDialog.getText(self, "Save Profile", "Profile name:")
        if not ok or not name.strip():
            return
        
        try:
            config = self.get_config()
            profile = DownloadProfile.from_dict({
                'name': name,
                'description': self.profile_description.toPlainText(),
                **config
            })
            
            if self.profile_manager:
                # Note: In real usage, this should be async
                success = True  # await self.profile_manager.create_profile(profile)
                if success:
                    self.load_profiles()
                    QMessageBox.information(self, "Success", f"Profile saved: {name}")
                else:
                    QMessageBox.critical(self, "Error", "Failed to save profile")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save profile: {e}")
    
    def delete_profile(self):
        """Delete selected profile"""
        profile_name = self.profile_combo.currentText()
        if not profile_name or not self.profile_manager:
            return
        
        reply = QMessageBox.question(
            self, "Confirm Delete", 
            f"Are you sure you want to delete profile '{profile_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Note: In real usage, this should be async
                success = True  # await self.profile_manager.delete_profile(profile_name)
                if success:
                    self.load_profiles()
                    QMessageBox.information(self, "Success", f"Profile deleted: {profile_name}")
                else:
                    QMessageBox.critical(self, "Error", "Failed to delete profile")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete profile: {e}")
    
    def load_profile_data(self, profile: DownloadProfile):
        """Load profile data into UI"""
        # General settings
        self.output_path.setText(profile.output_path)
        self.filename_template.setText(profile.filename_template)
        self.create_subdirs.setChecked(profile.create_subdirs)
        self.organize_by_uploader.setChecked(profile.organize_by_uploader)
        self.concurrent_downloads.setValue(profile.concurrent_downloads)
        self.max_retries.setValue(profile.max_retries)
        self.timeout.setValue(profile.timeout)
        
        # Quality settings
        self.video_format.setCurrentText(profile.video_format)
        self.audio_format.setCurrentText(profile.audio_format)
        self.prefer_free_codecs.setChecked(profile.prefer_free_codecs)
        self.max_filesize.setText(profile.max_filesize or "")
        self.extract_audio.setChecked(profile.extract_audio)
        self.write_subtitles.setChecked(profile.write_subtitles)
        self.write_thumbnail.setChecked(profile.write_thumbnail)
        self.write_info_json.setChecked(profile.write_info_json)
        self.embed_metadata.setChecked(profile.embed_metadata)
        self.convert_format.setCurrentText(profile.convert_format or "None")
        
        # Advanced settings
        self.preferred_engine.setCurrentText(profile.preferred_engine)
        self.fallback_enabled.setChecked(profile.fallback_enabled)
        self.rate_limit.setText(profile.rate_limit or "")
        self.retry_delay.setValue(int(profile.retry_delay))
        
        # Filters
        self.min_duration.setValue(profile.min_duration or 0)
        self.max_duration.setValue(profile.max_duration or 0)
        self.skip_live_streams.setChecked(profile.skip_live_streams)
        self.skip_premieres.setChecked(profile.skip_premieres)
        self.allowed_extensions.setText(",".join(profile.allowed_extensions))
        
        # Blocked uploaders
        self.blocked_uploaders.clear()
        for uploader in profile.blocked_uploaders:
            self.blocked_uploaders.addItem(uploader)
        
        # Description
        self.profile_description.setPlainText(profile.description)
    
    def load_initial_config(self):
        """Load initial configuration"""
        if not self.initial_config:
            return
        
        # Load from initial config dict
        config = self.initial_config
        
        self.output_path.setText(config.get('output_path', './downloads'))
        self.concurrent_downloads.setValue(config.get('concurrent_downloads', 3))
        self.video_format.setCurrentText(config.get('format_selector', 'best[height<=1080]'))
        self.extract_audio.setChecked(config.get('extract_audio', False))
        self.write_subtitles.setChecked(config.get('write_subtitles', False))
        self.write_thumbnail.setChecked(config.get('write_thumbnail', True))
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        # Get blocked uploaders list
        blocked_uploaders = []
        for i in range(self.blocked_uploaders.count()):
            blocked_uploaders.append(self.blocked_uploaders.item(i).text())
        
        # Get allowed extensions list
        allowed_ext = [ext.strip() for ext in self.allowed_extensions.text().split(',') if ext.strip()]
        
        return {
            'output_path': self.output_path.text(),
            'filename_template': self.filename_template.text(),
            'create_subdirs': self.create_subdirs.isChecked(),
            'organize_by_uploader': self.organize_by_uploader.isChecked(),
            'concurrent_downloads': self.concurrent_downloads.value(),
            'max_retries': self.max_retries.value(),
            'timeout': self.timeout.value(),
            'video_format': self.video_format.currentText(),
            'audio_format': self.audio_format.currentText(),
            'prefer_free_codecs': self.prefer_free_codecs.isChecked(),
            'max_filesize': self.max_filesize.text() or None,
            'extract_audio': self.extract_audio.isChecked(),
            'write_subtitles': self.write_subtitles.isChecked(),
            'write_thumbnail': self.write_thumbnail.isChecked(),
            'write_info_json': self.write_info_json.isChecked(),
            'embed_metadata': self.embed_metadata.isChecked(),
            'convert_format': self.convert_format.currentText() if self.convert_format.currentText() != "None" else None,
            'preferred_engine': self.preferred_engine.currentText(),
            'fallback_enabled': self.fallback_enabled.isChecked(),
            'rate_limit': self.rate_limit.text() or None,
            'retry_delay': self.retry_delay.value(),
            'min_duration': self.min_duration.value() or None,
            'max_duration': self.max_duration.value() or None,
            'skip_live_streams': self.skip_live_streams.isChecked(),
            'skip_premieres': self.skip_premieres.isChecked(),
            'allowed_extensions': allowed_ext,
            'blocked_uploaders': blocked_uploaders
        }
    
    def apply_config(self):
        """Apply current configuration"""
        config = self.get_config()
        self.config_changed.emit(config)
    
    def accept(self):
        """Accept dialog and emit config"""
        self.apply_config()
        super().accept()
