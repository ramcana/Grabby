"""
Desktop GUI - Polish the user experience
"""
import sys
import asyncio
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import requests
import threading
import time

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTextEdit, QProgressBar, QLabel,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QCheckBox, QSpinBox, QComboBox, QFileDialog,
    QMessageBox, QSystemTrayIcon, QMenu, QSplitter, QFrame
)
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, Qt, QUrl
from PyQt6.QtGui import QIcon, QFont, QPixmap, QAction
from PyQt6.QtWebEngines.QtWebEngineWidgets import QWebEngineView

# Add backend to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from backend.core.downloader import UniversalDownloader, DownloadOptions, DownloadProgress, DownloadStatus

class DownloadWorker(QThread):
    """Worker thread for handling downloads"""
    progress_updated = pyqtSignal(object)  # DownloadProgress object
    download_completed = pyqtSignal(list)  # List of results
    error_occurred = pyqtSignal(str)  # Error message
    
    def __init__(self, urls: List[str], options: DownloadOptions):
        super().__init__()
        self.urls = urls
        self.options = options
        self.downloader = None
        self.is_cancelled = False
    
    def run(self):
        """Run the download process"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            self.downloader = UniversalDownloader(self.options)
            self.downloader.add_progress_callback(self.on_progress)
            
            results = loop.run_until_complete(self.downloader.download_batch(self.urls))
            
            if not self.is_cancelled:
                self.download_completed.emit(results)
                
        except Exception as e:
            if not self.is_cancelled:
                self.error_occurred.emit(str(e))
    
    def on_progress(self, progress: DownloadProgress):
        """Handle progress updates"""
        if not self.is_cancelled:
            self.progress_updated.emit(progress)
    
    def cancel(self):
        """Cancel the download"""
        self.is_cancelled = True
        if self.downloader:
            self.downloader.cancel_all_downloads()

class VideoInfoWorker(QThread):
    """Worker thread for fetching video information"""
    info_received = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, url: str):
        super().__init__()
        self.url = url
    
    def run(self):
        """Fetch video information"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            downloader = UniversalDownloader()
            info = loop.run_until_complete(downloader.get_video_info(self.url))
            self.info_received.emit(info)
            
        except Exception as e:
            self.error_occurred.emit(str(e))

class DownloadTab(QWidget):
    """Main download tab"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.download_worker = None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # URL input section
        url_group = QGroupBox("📥 Download URLs")
        url_layout = QVBoxLayout()
        
        self.url_input = QTextEdit()
        self.url_input.setPlaceholderText("Enter video URLs (one per line)...")
        self.url_input.setMaximumHeight(100)
        url_layout.addWidget(self.url_input)
        
        # Quick add buttons
        quick_layout = QHBoxLayout()
        self.paste_btn = QPushButton("📋 Paste from Clipboard")
        self.clear_btn = QPushButton("🗑️ Clear")
        self.info_btn = QPushButton("ℹ️ Get Info")
        
        self.paste_btn.clicked.connect(self.paste_from_clipboard)
        self.clear_btn.clicked.connect(self.url_input.clear)
        self.info_btn.clicked.connect(self.get_video_info)
        
        quick_layout.addWidget(self.paste_btn)
        quick_layout.addWidget(self.clear_btn)
        quick_layout.addWidget(self.info_btn)
        quick_layout.addStretch()
        
        url_layout.addLayout(quick_layout)
        url_group.setLayout(url_layout)
        layout.addWidget(url_group)
        
        # Options section
        options_group = QGroupBox("⚙️ Download Options")
        options_layout = QVBoxLayout()
        
        # Output directory
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output Directory:"))
        self.output_path = QLineEdit("./downloads")
        self.browse_btn = QPushButton("📁 Browse")
        self.browse_btn.clicked.connect(self.browse_output_dir)
        
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(self.browse_btn)
        options_layout.addLayout(output_layout)
        
        # Quality and format options
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Quality:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Best", "1080p", "720p", "480p", "Audio Only"])
        format_layout.addWidget(self.quality_combo)
        
        format_layout.addWidget(QLabel("Concurrent Downloads:"))
        self.concurrent_spin = QSpinBox()
        self.concurrent_spin.setRange(1, 10)
        self.concurrent_spin.setValue(3)
        format_layout.addWidget(self.concurrent_spin)
        format_layout.addStretch()
        
        options_layout.addLayout(format_layout)
        
        # Checkboxes for additional options
        checkbox_layout = QHBoxLayout()
        self.subtitles_cb = QCheckBox("Download Subtitles")
        self.thumbnail_cb = QCheckBox("Download Thumbnails")
        self.audio_only_cb = QCheckBox("Audio Only")
        
        checkbox_layout.addWidget(self.subtitles_cb)
        checkbox_layout.addWidget(self.thumbnail_cb)
        checkbox_layout.addWidget(self.audio_only_cb)
        checkbox_layout.addStretch()
        
        options_layout.addLayout(checkbox_layout)
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Download button
        self.download_btn = QPushButton("🚀 Start Download")
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.download_btn.clicked.connect(self.start_download)
        layout.addWidget(self.download_btn)
        
        # Progress section
        progress_group = QGroupBox("📊 Download Progress")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_label = QLabel("Ready to download")
        self.speed_label = QLabel("")
        
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.speed_label)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # Log output
        log_group = QGroupBox("📝 Download Log")
        log_layout = QVBoxLayout()
        
        self.log_output = QTextEdit()
        self.log_output.setMaximumHeight(150)
        self.log_output.setReadOnly(True)
        log_layout.addWidget(self.log_output)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        self.setLayout(layout)
    
    def paste_from_clipboard(self):
        """Paste URLs from clipboard"""
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            current_text = self.url_input.toPlainText()
            if current_text:
                self.url_input.setPlainText(current_text + "\n" + text)
            else:
                self.url_input.setPlainText(text)
    
    def browse_output_dir(self):
        """Browse for output directory"""
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.output_path.setText(directory)
    
    def get_video_info(self):
        """Get information about the first URL"""
        urls = self.get_urls()
        if not urls:
            QMessageBox.warning(self, "Warning", "Please enter at least one URL")
            return
        
        self.info_btn.setEnabled(False)
        self.info_btn.setText("⏳ Getting Info...")
        
        self.info_worker = VideoInfoWorker(urls[0])
        self.info_worker.info_received.connect(self.show_video_info)
        self.info_worker.error_occurred.connect(self.show_info_error)
        self.info_worker.start()
    
    def show_video_info(self, info):
        """Display video information"""
        self.info_btn.setEnabled(True)
        self.info_btn.setText("ℹ️ Get Info")
        
        title = info.get('title', 'Unknown')
        uploader = info.get('uploader', 'Unknown')
        duration = info.get('duration', 'Unknown')
        
        msg = f"Title: {title}\nUploader: {uploader}\nDuration: {duration} seconds"
        QMessageBox.information(self, "Video Information", msg)
    
    def show_info_error(self, error):
        """Show error when getting video info"""
        self.info_btn.setEnabled(True)
        self.info_btn.setText("ℹ️ Get Info")
        QMessageBox.critical(self, "Error", f"Failed to get video info:\n{error}")
    
    def get_urls(self) -> List[str]:
        """Get URLs from input"""
        text = self.url_input.toPlainText().strip()
        if not text:
            return []
        
        urls = [url.strip() for url in text.split('\n') if url.strip()]
        return urls
    
    def get_download_options(self) -> DownloadOptions:
        """Create download options from UI"""
        quality_map = {
            "Best": "best",
            "1080p": "best[height<=1080]",
            "720p": "best[height<=720]",
            "480p": "best[height<=480]",
            "Audio Only": "bestaudio"
        }
        
        quality = self.quality_combo.currentText()
        format_selector = quality_map.get(quality, "best")
        
        return DownloadOptions(
            output_path=self.output_path.text(),
            format_selector=format_selector,
            extract_audio=self.audio_only_cb.isChecked() or quality == "Audio Only",
            write_subtitles=self.subtitles_cb.isChecked(),
            write_thumbnail=self.thumbnail_cb.isChecked(),
            concurrent_downloads=self.concurrent_spin.value()
        )
    
    def start_download(self):
        """Start the download process"""
        urls = self.get_urls()
        if not urls:
            QMessageBox.warning(self, "Warning", "Please enter at least one URL")
            return
        
        options = self.get_download_options()
        
        # Update UI
        self.download_btn.setText("⏹️ Cancel Download")
        self.download_btn.clicked.disconnect()
        self.download_btn.clicked.connect(self.cancel_download)
        
        self.progress_bar.setValue(0)
        self.progress_label.setText("Starting download...")
        self.log_output.clear()
        self.log_output.append(f"Starting download of {len(urls)} URL(s)...")
        
        # Start download worker
        self.download_worker = DownloadWorker(urls, options)
        self.download_worker.progress_updated.connect(self.update_progress)
        self.download_worker.download_completed.connect(self.download_finished)
        self.download_worker.error_occurred.connect(self.download_error)
        self.download_worker.start()
    
    def cancel_download(self):
        """Cancel the current download"""
        if self.download_worker:
            self.download_worker.cancel()
            self.download_worker.wait()
        
        self.reset_download_ui()
        self.log_output.append("Download cancelled by user")
    
    def update_progress(self, progress: DownloadProgress):
        """Update progress display"""
        if progress.status == DownloadStatus.DOWNLOADING:
            self.progress_bar.setValue(int(progress.progress_percent))
            self.progress_label.setText(f"Downloading: {progress.filename}")
            self.speed_label.setText(f"Speed: {progress.speed} | ETA: {progress.eta}")
        elif progress.status == DownloadStatus.COMPLETED:
            self.log_output.append(f"✓ Completed: {progress.filename}")
        elif progress.status == DownloadStatus.FAILED:
            self.log_output.append(f"✗ Failed: {progress.url} - {progress.error_message}")
    
    def download_finished(self, results):
        """Handle download completion"""
        successful = [r for r in results if r.status == DownloadStatus.COMPLETED]
        failed = [r for r in results if r.status == DownloadStatus.FAILED]
        
        self.progress_bar.setValue(100)
        self.progress_label.setText("Download completed")
        self.speed_label.setText("")
        
        self.log_output.append(f"\n📊 Download Summary:")
        self.log_output.append(f"✅ Successful: {len(successful)}")
        self.log_output.append(f"❌ Failed: {len(failed)}")
        self.log_output.append(f"🎯 Total: {len(results)}")
        
        self.reset_download_ui()
        
        # Show notification
        if self.parent_window and hasattr(self.parent_window, 'show_notification'):
            self.parent_window.show_notification(
                "Download Completed",
                f"Downloaded {len(successful)} of {len(results)} videos"
            )
    
    def download_error(self, error):
        """Handle download error"""
        self.log_output.append(f"❌ Error: {error}")
        self.reset_download_ui()
        QMessageBox.critical(self, "Download Error", f"Download failed:\n{error}")
    
    def reset_download_ui(self):
        """Reset download UI to initial state"""
        self.download_btn.setText("🚀 Start Download")
        self.download_btn.clicked.disconnect()
        self.download_btn.clicked.connect(self.start_download)
        self.download_worker = None

class HistoryTab(QWidget):
    """Download history tab"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Controls
        controls_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.clear_btn = QPushButton("🗑️ Clear History")
        
        controls_layout.addWidget(self.refresh_btn)
        controls_layout.addWidget(self.clear_btn)
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        # History table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels([
            "Filename", "URL", "Status", "Size", "Date"
        ])
        
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(self.history_table)
        
        self.setLayout(layout)

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.init_system_tray()
    
    def init_ui(self):
        self.setWindowTitle("Grabby - Universal Video Downloader")
        self.setGeometry(100, 100, 800, 600)
        
        # Central widget with tabs
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        
        # Title
        title_label = QLabel("🎬 Grabby - Universal Video Downloader")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                padding: 10px;
            }
        """)
        layout.addWidget(title_label)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        
        # Download tab
        self.download_tab = DownloadTab(self)
        self.tab_widget.addTab(self.download_tab, "📥 Download")
        
        # History tab
        self.history_tab = HistoryTab(self)
        self.tab_widget.addTab(self.history_tab, "📚 History")
        
        layout.addWidget(self.tab_widget)
        central_widget.setLayout(layout)
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
        # Apply modern styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QTabWidget::pane {
                border: 1px solid #c0c0c0;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #e1e1e1;
                padding: 8px 12px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #4CAF50;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin: 5px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
    
    def init_system_tray(self):
        """Initialize system tray icon"""
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(self)
            
            # Create tray menu
            tray_menu = QMenu()
            
            show_action = QAction("Show", self)
            show_action.triggered.connect(self.show)
            tray_menu.addAction(show_action)
            
            quit_action = QAction("Quit", self)
            quit_action.triggered.connect(QApplication.instance().quit)
            tray_menu.addAction(quit_action)
            
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.activated.connect(self.tray_icon_activated)
            
            # Set icon (you would need to add an actual icon file)
            self.tray_icon.setToolTip("Grabby Video Downloader")
            self.tray_icon.show()
    
    def tray_icon_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.raise_()
                self.activateWindow()
    
    def show_notification(self, title: str, message: str):
        """Show system notification"""
        if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
            self.tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)
    
    def closeEvent(self, event):
        """Handle close event"""
        if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            event.accept()

def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running in system tray
    
    # Set application properties
    app.setApplicationName("Grabby")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Grabby Team")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
