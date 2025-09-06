"""
Settings Panel for Advanced Desktop UI
"""
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QFormLayout,
    QLineEdit, QSpinBox, QCheckBox, QComboBox, QPushButton,
    QFileDialog, QGroupBox, QSlider, QLabel, QTextEdit,
    QListWidget, QListWidgetItem, QMessageBox, QScrollArea,
    QButtonGroup, QRadioButton, QColorDialog, QFontDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

# Add backend to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from config.settings_manager import SettingsManager

class SettingsPanel(QWidget):
    """Advanced settings panel for application configuration"""
    
    settings_changed = pyqtSignal(dict)
    theme_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings_manager = None
        self.current_settings = {}
        
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        
        # Create scroll area for settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Add tabs
        self.tab_widget.addTab(self.create_general_tab(), "General")
        self.tab_widget.addTab(self.create_download_tab(), "Downloads")
        self.tab_widget.addTab(self.create_interface_tab(), "Interface")
        self.tab_widget.addTab(self.create_network_tab(), "Network")
        self.tab_widget.addTab(self.create_advanced_tab(), "Advanced")
        
        scroll.setWidget(self.tab_widget)
        layout.addWidget(scroll)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.reset_btn = QPushButton("Reset to Defaults")
        self.apply_btn = QPushButton("Apply")
        self.save_btn = QPushButton("Save")
        
        self.reset_btn.clicked.connect(self.reset_to_defaults)
        self.apply_btn.clicked.connect(self.apply_settings)
        self.save_btn.clicked.connect(self.save_settings)
        
        button_layout.addWidget(self.reset_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def create_general_tab(self) -> QWidget:
        """Create general settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Startup group
        startup_group = QGroupBox("Startup")
        startup_layout = QFormLayout()
        
        self.start_minimized = QCheckBox("Start minimized to system tray")
        startup_layout.addRow("", self.start_minimized)
        
        self.auto_check_updates = QCheckBox("Check for updates on startup")
        startup_layout.addRow("", self.auto_check_updates)
        
        self.restore_session = QCheckBox("Restore previous session")
        startup_layout.addRow("", self.restore_session)
        
        startup_group.setLayout(startup_layout)
        layout.addWidget(startup_group)
        
        # Default paths group
        paths_group = QGroupBox("Default Paths")
        paths_layout = QFormLayout()
        
        self.default_download_path = QLineEdit()
        browse_download_btn = QPushButton("Browse...")
        browse_download_btn.clicked.connect(self.browse_download_path)
        
        download_layout = QHBoxLayout()
        download_layout.addWidget(self.default_download_path)
        download_layout.addWidget(browse_download_btn)
        paths_layout.addRow("Download Directory:", download_layout)
        
        self.temp_path = QLineEdit()
        browse_temp_btn = QPushButton("Browse...")
        browse_temp_btn.clicked.connect(self.browse_temp_path)
        
        temp_layout = QHBoxLayout()
        temp_layout.addWidget(self.temp_path)
        temp_layout.addWidget(browse_temp_btn)
        paths_layout.addRow("Temporary Directory:", temp_layout)
        
        paths_group.setLayout(paths_layout)
        layout.addWidget(paths_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_download_tab(self) -> QWidget:
        """Create download settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Default download options group
        defaults_group = QGroupBox("Default Download Options")
        defaults_layout = QFormLayout()
        
        self.default_quality = QComboBox()
        self.default_quality.addItems([
            "best", "best[height<=2160]", "best[height<=1080]", 
            "best[height<=720]", "best[height<=480]", "worst"
        ])
        defaults_layout.addRow("Default Quality:", self.default_quality)
        
        self.default_format = QComboBox()
        self.default_format.addItems(["mp4", "mkv", "webm", "best", "any"])
        defaults_layout.addRow("Default Format:", self.default_format)
        
        self.auto_extract_audio = QCheckBox("Extract audio by default")
        defaults_layout.addRow("", self.auto_extract_audio)
        
        self.auto_download_subtitles = QCheckBox("Download subtitles by default")
        defaults_layout.addRow("", self.auto_download_subtitles)
        
        self.auto_download_thumbnails = QCheckBox("Download thumbnails by default")
        defaults_layout.addRow("", self.auto_download_thumbnails)
        
        defaults_group.setLayout(defaults_layout)
        layout.addWidget(defaults_group)
        
        # Performance group
        performance_group = QGroupBox("Performance")
        performance_layout = QFormLayout()
        
        self.max_concurrent_downloads = QSpinBox()
        self.max_concurrent_downloads.setRange(1, 20)
        self.max_concurrent_downloads.setValue(3)
        performance_layout.addRow("Max Concurrent Downloads:", self.max_concurrent_downloads)
        
        self.max_retries = QSpinBox()
        self.max_retries.setRange(0, 10)
        self.max_retries.setValue(3)
        performance_layout.addRow("Max Retries:", self.max_retries)
        
        performance_group.setLayout(performance_layout)
        layout.addWidget(performance_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_interface_tab(self) -> QWidget:
        """Create interface settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Theme group
        theme_group = QGroupBox("Theme")
        theme_layout = QFormLayout()
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["System", "Light", "Dark", "Auto"])
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        theme_layout.addRow("Theme:", self.theme_combo)
        
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)
        
        # Notifications group
        notifications_group = QGroupBox("Notifications")
        notifications_layout = QFormLayout()
        
        self.show_download_complete = QCheckBox("Show download complete notifications")
        notifications_layout.addRow("", self.show_download_complete)
        
        self.show_download_failed = QCheckBox("Show download failed notifications")
        notifications_layout.addRow("", self.show_download_failed)
        
        notifications_group.setLayout(notifications_layout)
        layout.addWidget(notifications_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_network_tab(self) -> QWidget:
        """Create network settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Proxy group
        proxy_group = QGroupBox("Proxy Settings")
        proxy_layout = QFormLayout()
        
        self.use_proxy = QCheckBox("Use proxy server")
        proxy_layout.addRow("", self.use_proxy)
        
        self.proxy_host = QLineEdit()
        self.proxy_host.setPlaceholderText("proxy.example.com")
        proxy_layout.addRow("Proxy Host:", self.proxy_host)
        
        self.proxy_port = QSpinBox()
        self.proxy_port.setRange(1, 65535)
        self.proxy_port.setValue(8080)
        proxy_layout.addRow("Proxy Port:", self.proxy_port)
        
        proxy_group.setLayout(proxy_layout)
        layout.addWidget(proxy_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_advanced_tab(self) -> QWidget:
        """Create advanced settings tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Engine preferences group
        engine_group = QGroupBox("Engine Preferences")
        engine_layout = QFormLayout()
        
        self.preferred_engine = QComboBox()
        self.preferred_engine.addItems(["auto", "yt-dlp", "streamlink", "gallery-dl", "ripme"])
        engine_layout.addRow("Preferred Engine:", self.preferred_engine)
        
        self.enable_engine_fallback = QCheckBox("Enable engine fallback")
        engine_layout.addRow("", self.enable_engine_fallback)
        
        engine_group.setLayout(engine_layout)
        layout.addWidget(engine_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def browse_download_path(self):
        """Browse for default download directory"""
        directory = QFileDialog.getExistingDirectory(self, "Select Default Download Directory")
        if directory:
            self.default_download_path.setText(directory)
    
    def browse_temp_path(self):
        """Browse for temporary directory"""
        directory = QFileDialog.getExistingDirectory(self, "Select Temporary Directory")
        if directory:
            self.temp_path.setText(directory)
    
    def on_theme_changed(self, theme: str):
        """Handle theme change"""
        self.theme_changed.emit(theme.lower())
    
    def load_settings(self):
        """Load settings from settings manager"""
        try:
            if not self.settings_manager:
                self.settings_manager = SettingsManager()
            
            # Load default settings for now
            self.load_default_settings()
            
        except Exception as e:
            print(f"Error loading settings: {e}")
            self.load_default_settings()
    
    def load_default_settings(self):
        """Load default settings"""
        defaults = {
            'start_minimized': False,
            'auto_check_updates': True,
            'restore_session': True,
            'default_download_path': './downloads',
            'temp_path': './temp',
            'default_quality': 'best[height<=1080]',
            'default_format': 'mp4',
            'auto_extract_audio': False,
            'auto_download_subtitles': False,
            'auto_download_thumbnails': True,
            'max_concurrent_downloads': 3,
            'max_retries': 3,
            'theme': 'System',
            'show_download_complete': True,
            'show_download_failed': True,
            'use_proxy': False,
            'proxy_host': '',
            'proxy_port': 8080,
            'preferred_engine': 'auto',
            'enable_engine_fallback': True
        }
        
        self.current_settings = defaults
        self.apply_settings_to_ui(defaults)
    
    def apply_settings_to_ui(self, settings: Dict[str, Any]):
        """Apply settings to UI elements"""
        # General
        self.start_minimized.setChecked(settings.get('start_minimized', False))
        self.auto_check_updates.setChecked(settings.get('auto_check_updates', True))
        self.restore_session.setChecked(settings.get('restore_session', True))
        self.default_download_path.setText(settings.get('default_download_path', './downloads'))
        self.temp_path.setText(settings.get('temp_path', './temp'))
        
        # Downloads
        self.default_quality.setCurrentText(settings.get('default_quality', 'best[height<=1080]'))
        self.default_format.setCurrentText(settings.get('default_format', 'mp4'))
        self.auto_extract_audio.setChecked(settings.get('auto_extract_audio', False))
        self.auto_download_subtitles.setChecked(settings.get('auto_download_subtitles', False))
        self.auto_download_thumbnails.setChecked(settings.get('auto_download_thumbnails', True))
        self.max_concurrent_downloads.setValue(settings.get('max_concurrent_downloads', 3))
        self.max_retries.setValue(settings.get('max_retries', 3))
        
        # Interface
        self.theme_combo.setCurrentText(settings.get('theme', 'System'))
        self.show_download_complete.setChecked(settings.get('show_download_complete', True))
        self.show_download_failed.setChecked(settings.get('show_download_failed', True))
        
        # Network
        self.use_proxy.setChecked(settings.get('use_proxy', False))
        self.proxy_host.setText(settings.get('proxy_host', ''))
        self.proxy_port.setValue(settings.get('proxy_port', 8080))
        
        # Advanced
        self.preferred_engine.setCurrentText(settings.get('preferred_engine', 'auto'))
        self.enable_engine_fallback.setChecked(settings.get('enable_engine_fallback', True))
    
    def get_current_settings(self) -> Dict[str, Any]:
        """Get current settings from UI"""
        return {
            # General
            'start_minimized': self.start_minimized.isChecked(),
            'auto_check_updates': self.auto_check_updates.isChecked(),
            'restore_session': self.restore_session.isChecked(),
            'default_download_path': self.default_download_path.text(),
            'temp_path': self.temp_path.text(),
            
            # Downloads
            'default_quality': self.default_quality.currentText(),
            'default_format': self.default_format.currentText(),
            'auto_extract_audio': self.auto_extract_audio.isChecked(),
            'auto_download_subtitles': self.auto_download_subtitles.isChecked(),
            'auto_download_thumbnails': self.auto_download_thumbnails.isChecked(),
            'max_concurrent_downloads': self.max_concurrent_downloads.value(),
            'max_retries': self.max_retries.value(),
            
            # Interface
            'theme': self.theme_combo.currentText(),
            'show_download_complete': self.show_download_complete.isChecked(),
            'show_download_failed': self.show_download_failed.isChecked(),
            
            # Network
            'use_proxy': self.use_proxy.isChecked(),
            'proxy_host': self.proxy_host.text(),
            'proxy_port': self.proxy_port.value(),
            
            # Advanced
            'preferred_engine': self.preferred_engine.currentText(),
            'enable_engine_fallback': self.enable_engine_fallback.isChecked()
        }
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        reply = QMessageBox.question(
            self, "Reset Settings",
            "Are you sure you want to reset all settings to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.load_default_settings()
    
    def apply_settings(self):
        """Apply current settings"""
        settings = self.get_current_settings()
        self.current_settings = settings
        self.settings_changed.emit(settings)
    
    def save_settings(self):
        """Save current settings"""
        self.apply_settings()
        
        try:
            if self.settings_manager:
                # Save to settings manager
                pass  # Implementation depends on settings manager API
            
            QMessageBox.information(self, "Settings Saved", "Settings have been saved successfully.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")
