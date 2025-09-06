"""
Queue Management Widget for Advanced Desktop UI
"""
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QMenu, QMessageBox, QProgressBar,
    QLabel, QComboBox, QLineEdit, QGroupBox, QSplitter,
    QTextEdit, QTabWidget, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QAction, QFont, QColor, QPalette

# Add backend to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.core.queue_manager import QueueStatus, QueuePriority
from backend.core.downloader import DownloadStatus

class QueueUpdateWorker(QThread):
    """Worker thread for updating queue status"""
    queue_updated = pyqtSignal(dict)
    
    def __init__(self, queue_manager):
        super().__init__()
        self.queue_manager = queue_manager
        self.running = True
    
    def run(self):
        while self.running:
            try:
                if self.queue_manager:
                    status = self.queue_manager.get_queue_status()
                    self.queue_updated.emit(status)
            except Exception as e:
                print(f"Queue update error: {e}")
            
            self.msleep(1000)  # Update every second
    
    def stop(self):
        self.running = False

class QueueManagementWidget(QWidget):
    """Advanced queue management widget"""
    
    item_selected = pyqtSignal(str)  # item_id
    priority_changed = pyqtSignal(str, str)  # item_id, new_priority
    item_cancelled = pyqtSignal(str)  # item_id
    item_paused = pyqtSignal(str)  # item_id
    item_resumed = pyqtSignal(str)  # item_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.queue_manager = None
        self.update_worker = None
        self.queue_items = {}
        
        self.init_ui()
        self.setup_update_timer()
    
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        
        # Create splitter for main content
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Top section: Queue controls and stats
        top_widget = self.create_queue_controls()
        splitter.addWidget(top_widget)
        
        # Middle section: Queue table
        middle_widget = self.create_queue_table()
        splitter.addWidget(middle_widget)
        
        # Bottom section: Item details
        bottom_widget = self.create_item_details()
        splitter.addWidget(bottom_widget)
        
        # Set splitter proportions
        splitter.setSizes([100, 400, 200])
        
        layout.addWidget(splitter)
        self.setLayout(layout)
    
    def create_queue_controls(self) -> QWidget:
        """Create queue controls and statistics"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Statistics group
        stats_group = QGroupBox("Queue Statistics")
        stats_layout = QHBoxLayout()
        
        self.total_items_label = QLabel("Total: 0")
        self.pending_items_label = QLabel("Pending: 0")
        self.active_items_label = QLabel("Active: 0")
        self.completed_items_label = QLabel("Completed: 0")
        self.failed_items_label = QLabel("Failed: 0")
        
        stats_layout.addWidget(self.total_items_label)
        stats_layout.addWidget(QFrame())  # Separator
        stats_layout.addWidget(self.pending_items_label)
        stats_layout.addWidget(self.active_items_label)
        stats_layout.addWidget(self.completed_items_label)
        stats_layout.addWidget(self.failed_items_label)
        stats_layout.addStretch()
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # Controls group
        controls_group = QGroupBox("Queue Controls")
        controls_layout = QHBoxLayout()
        
        self.pause_all_btn = QPushButton("⏸️ Pause All")
        self.resume_all_btn = QPushButton("▶️ Resume All")
        self.cancel_all_btn = QPushButton("⏹️ Cancel All")
        self.clear_completed_btn = QPushButton("🗑️ Clear Completed")
        self.refresh_btn = QPushButton("🔄 Refresh")
        
        self.pause_all_btn.clicked.connect(self.pause_all_downloads)
        self.resume_all_btn.clicked.connect(self.resume_all_downloads)
        self.cancel_all_btn.clicked.connect(self.cancel_all_downloads)
        self.clear_completed_btn.clicked.connect(self.clear_completed_items)
        self.refresh_btn.clicked.connect(self.refresh_queue)
        
        controls_layout.addWidget(self.pause_all_btn)
        controls_layout.addWidget(self.resume_all_btn)
        controls_layout.addWidget(self.cancel_all_btn)
        controls_layout.addWidget(self.clear_completed_btn)
        controls_layout.addWidget(self.refresh_btn)
        controls_layout.addStretch()
        
        # Filter controls
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter by status:"))
        
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "Pending", "Downloading", "Completed", "Failed", "Paused"])
        self.status_filter.currentTextChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.status_filter)
        
        filter_layout.addWidget(QLabel("Search:"))
        self.search_filter = QLineEdit()
        self.search_filter.setPlaceholderText("Search by URL or title...")
        self.search_filter.textChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.search_filter)
        
        controls_layout.addLayout(filter_layout)
        controls_group.setLayout(controls_layout)
        layout.addWidget(controls_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_queue_table(self) -> QWidget:
        """Create the main queue table"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Create table
        self.queue_table = QTableWidget()
        self.queue_table.setColumnCount(8)
        self.queue_table.setHorizontalHeaderLabels([
            "Status", "Priority", "Title", "URL", "Progress", "Speed", "ETA", "Actions"
        ])
        
        # Configure table
        header = self.queue_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Status
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Priority
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)           # Title
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)           # URL
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)             # Progress
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Speed
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # ETA
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # Actions
        
        self.queue_table.setColumnWidth(4, 120)  # Progress bar width
        
        # Enable sorting
        self.queue_table.setSortingEnabled(True)
        
        # Context menu
        self.queue_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.queue_table.customContextMenuRequested.connect(self.show_context_menu)
        
        # Selection changed
        self.queue_table.itemSelectionChanged.connect(self.on_selection_changed)
        
        layout.addWidget(self.queue_table)
        widget.setLayout(layout)
        return widget
    
    def create_item_details(self) -> QWidget:
        """Create item details panel"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Create tab widget for details
        self.details_tabs = QTabWidget()
        
        # General info tab
        general_tab = QWidget()
        general_layout = QVBoxLayout()
        
        self.item_info_text = QTextEdit()
        self.item_info_text.setReadOnly(True)
        self.item_info_text.setMaximumHeight(150)
        general_layout.addWidget(self.item_info_text)
        
        general_tab.setLayout(general_layout)
        self.details_tabs.addTab(general_tab, "General")
        
        # Metadata tab
        metadata_tab = QWidget()
        metadata_layout = QVBoxLayout()
        
        self.metadata_text = QTextEdit()
        self.metadata_text.setReadOnly(True)
        self.metadata_text.setMaximumHeight(150)
        metadata_layout.addWidget(self.metadata_text)
        
        metadata_tab.setLayout(metadata_layout)
        self.details_tabs.addTab(metadata_tab, "Metadata")
        
        # Error log tab
        error_tab = QWidget()
        error_layout = QVBoxLayout()
        
        self.error_log_text = QTextEdit()
        self.error_log_text.setReadOnly(True)
        self.error_log_text.setMaximumHeight(150)
        error_layout.addWidget(self.error_log_text)
        
        error_tab.setLayout(error_layout)
        self.details_tabs.addTab(error_tab, "Errors")
        
        layout.addWidget(self.details_tabs)
        widget.setLayout(layout)
        return widget
    
    def setup_update_timer(self):
        """Setup automatic queue updates"""
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.refresh_queue)
        self.update_timer.start(2000)  # Update every 2 seconds
    
    def set_queue_manager(self, queue_manager):
        """Set the queue manager"""
        self.queue_manager = queue_manager
        
        # Start update worker
        if self.update_worker:
            self.update_worker.stop()
            self.update_worker.wait()
        
        self.update_worker = QueueUpdateWorker(queue_manager)
        self.update_worker.queue_updated.connect(self.update_statistics)
        self.update_worker.start()
        
        self.refresh_queue()
    
    def refresh_queue(self):
        """Refresh the queue display"""
        if not self.queue_manager:
            return
        
        try:
            # Get queue status
            status = self.queue_manager.get_queue_status()
            self.update_statistics(status)
            
            # Get all items
            all_items = []
            for status_type in [QueueStatus.PENDING, QueueStatus.DOWNLOADING, 
                              QueueStatus.COMPLETED, QueueStatus.FAILED, QueueStatus.PAUSED]:
                items = self.queue_manager.get_items_by_status(status_type)
                all_items.extend(items)
            
            self.update_table(all_items)
            
        except Exception as e:
            print(f"Error refreshing queue: {e}")
    
    def update_statistics(self, status: Dict[str, Any]):
        """Update queue statistics"""
        breakdown = status.get('status_breakdown', {})
        
        self.total_items_label.setText(f"Total: {status.get('total_items', 0)}")
        self.pending_items_label.setText(f"Pending: {breakdown.get('pending', 0)}")
        self.active_items_label.setText(f"Active: {breakdown.get('downloading', 0)}")
        self.completed_items_label.setText(f"Completed: {breakdown.get('completed', 0)}")
        self.failed_items_label.setText(f"Failed: {breakdown.get('failed', 0)}")
    
    def update_table(self, items: List[Any]):
        """Update the queue table with items"""
        self.queue_table.setRowCount(len(items))
        self.queue_items.clear()
        
        for row, item in enumerate(items):
            self.queue_items[item.id] = item
            
            # Status
            status_item = QTableWidgetItem(self.get_status_icon(item.status))
            status_item.setData(Qt.ItemDataRole.UserRole, item.id)
            self.queue_table.setItem(row, 0, status_item)
            
            # Priority
            priority_item = QTableWidgetItem(item.priority.name)
            self.queue_table.setItem(row, 1, priority_item)
            
            # Title
            title = item.metadata.get('title', 'Unknown')
            title_item = QTableWidgetItem(title[:50] + "..." if len(title) > 50 else title)
            self.queue_table.setItem(row, 2, title_item)
            
            # URL
            url_item = QTableWidgetItem(item.url[:50] + "..." if len(item.url) > 50 else item.url)
            self.queue_table.setItem(row, 3, url_item)
            
            # Progress
            progress_widget = self.create_progress_widget(item)
            self.queue_table.setCellWidget(row, 4, progress_widget)
            
            # Speed
            speed = item.metadata.get('speed', 'N/A')
            speed_item = QTableWidgetItem(speed)
            self.queue_table.setItem(row, 5, speed_item)
            
            # ETA
            eta = item.metadata.get('eta', 'N/A')
            eta_item = QTableWidgetItem(eta)
            self.queue_table.setItem(row, 6, eta_item)
            
            # Actions
            actions_widget = self.create_actions_widget(item)
            self.queue_table.setCellWidget(row, 7, actions_widget)
        
        self.apply_filter()
    
    def create_progress_widget(self, item) -> QWidget:
        """Create progress bar widget for item"""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        
        progress_bar = QProgressBar()
        progress_bar.setMaximum(100)
        
        if item.status == QueueStatus.DOWNLOADING:
            # Calculate progress from metadata
            downloaded = item.metadata.get('downloaded_bytes', 0)
            total = item.metadata.get('total_bytes', 0)
            
            if total > 0:
                progress = int((downloaded / total) * 100)
                progress_bar.setValue(progress)
                progress_bar.setFormat(f"{progress}%")
            else:
                progress_bar.setRange(0, 0)  # Indeterminate
                progress_bar.setFormat("Downloading...")
        elif item.status == QueueStatus.COMPLETED:
            progress_bar.setValue(100)
            progress_bar.setFormat("Complete")
        elif item.status == QueueStatus.FAILED:
            progress_bar.setValue(0)
            progress_bar.setFormat("Failed")
            progress_bar.setStyleSheet("QProgressBar::chunk { background-color: #ff6b6b; }")
        else:
            progress_bar.setValue(0)
            progress_bar.setFormat("Pending")
        
        layout.addWidget(progress_bar)
        widget.setLayout(layout)
        return widget
    
    def create_actions_widget(self, item) -> QWidget:
        """Create actions widget for item"""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        
        if item.status == QueueStatus.DOWNLOADING:
            pause_btn = QPushButton("⏸️")
            pause_btn.setToolTip("Pause")
            pause_btn.clicked.connect(lambda: self.pause_item(item.id))
            layout.addWidget(pause_btn)
            
            cancel_btn = QPushButton("⏹️")
            cancel_btn.setToolTip("Cancel")
            cancel_btn.clicked.connect(lambda: self.cancel_item(item.id))
            layout.addWidget(cancel_btn)
            
        elif item.status == QueueStatus.PAUSED:
            resume_btn = QPushButton("▶️")
            resume_btn.setToolTip("Resume")
            resume_btn.clicked.connect(lambda: self.resume_item(item.id))
            layout.addWidget(resume_btn)
            
            cancel_btn = QPushButton("⏹️")
            cancel_btn.setToolTip("Cancel")
            cancel_btn.clicked.connect(lambda: self.cancel_item(item.id))
            layout.addWidget(cancel_btn)
            
        elif item.status in [QueueStatus.PENDING, QueueStatus.RETRYING]:
            cancel_btn = QPushButton("⏹️")
            cancel_btn.setToolTip("Cancel")
            cancel_btn.clicked.connect(lambda: self.cancel_item(item.id))
            layout.addWidget(cancel_btn)
            
        elif item.status == QueueStatus.FAILED:
            retry_btn = QPushButton("🔄")
            retry_btn.setToolTip("Retry")
            retry_btn.clicked.connect(lambda: self.retry_item(item.id))
            layout.addWidget(retry_btn)
        
        widget.setLayout(layout)
        return widget
    
    def get_status_icon(self, status: QueueStatus) -> str:
        """Get icon for queue status"""
        icons = {
            QueueStatus.PENDING: "⏳",
            QueueStatus.DOWNLOADING: "⬇️",
            QueueStatus.COMPLETED: "✅",
            QueueStatus.FAILED: "❌",
            QueueStatus.CANCELLED: "⏹️",
            QueueStatus.PAUSED: "⏸️",
            QueueStatus.RETRYING: "🔄"
        }
        return icons.get(status, "❓")
    
    def apply_filter(self):
        """Apply status and search filters"""
        status_filter = self.status_filter.currentText()
        search_text = self.search_filter.text().lower()
        
        for row in range(self.queue_table.rowCount()):
            show_row = True
            
            # Status filter
            if status_filter != "All":
                status_item = self.queue_table.item(row, 0)
                if status_item:
                    item_id = status_item.data(Qt.ItemDataRole.UserRole)
                    item = self.queue_items.get(item_id)
                    if item and item.status.value.title() != status_filter.lower():
                        show_row = False
            
            # Search filter
            if search_text and show_row:
                title_item = self.queue_table.item(row, 2)
                url_item = self.queue_table.item(row, 3)
                
                title_text = title_item.text().lower() if title_item else ""
                url_text = url_item.text().lower() if url_item else ""
                
                if search_text not in title_text and search_text not in url_text:
                    show_row = False
            
            self.queue_table.setRowHidden(row, not show_row)
    
    def show_context_menu(self, position):
        """Show context menu for queue items"""
        item = self.queue_table.itemAt(position)
        if not item:
            return
        
        # Get the item ID from the status column
        status_item = self.queue_table.item(item.row(), 0)
        if not status_item:
            return
        
        item_id = status_item.data(Qt.ItemDataRole.UserRole)
        queue_item = self.queue_items.get(item_id)
        if not queue_item:
            return
        
        menu = QMenu(self)
        
        # Priority submenu
        priority_menu = menu.addMenu("Set Priority")
        for priority in QueuePriority:
            action = priority_menu.addAction(priority.name.title())
            action.triggered.connect(lambda checked, p=priority: self.change_priority(item_id, p))
        
        menu.addSeparator()
        
        # Status actions
        if queue_item.status == QueueStatus.DOWNLOADING:
            menu.addAction("Pause", lambda: self.pause_item(item_id))
            menu.addAction("Cancel", lambda: self.cancel_item(item_id))
        elif queue_item.status == QueueStatus.PAUSED:
            menu.addAction("Resume", lambda: self.resume_item(item_id))
            menu.addAction("Cancel", lambda: self.cancel_item(item_id))
        elif queue_item.status in [QueueStatus.PENDING, QueueStatus.RETRYING]:
            menu.addAction("Cancel", lambda: self.cancel_item(item_id))
        elif queue_item.status == QueueStatus.FAILED:
            menu.addAction("Retry", lambda: self.retry_item(item_id))
        
        menu.addSeparator()
        menu.addAction("Remove from Queue", lambda: self.remove_item(item_id))
        
        menu.exec(self.queue_table.mapToGlobal(position))
    
    def on_selection_changed(self):
        """Handle selection change in queue table"""
        current_row = self.queue_table.currentRow()
        if current_row >= 0:
            status_item = self.queue_table.item(current_row, 0)
            if status_item:
                item_id = status_item.data(Qt.ItemDataRole.UserRole)
                self.show_item_details(item_id)
                self.item_selected.emit(item_id)
    
    def show_item_details(self, item_id: str):
        """Show details for selected item"""
        item = self.queue_items.get(item_id)
        if not item:
            return
        
        # General info
        info_text = f"ID: {item.id}\n"
        info_text += f"URL: {item.url}\n"
        info_text += f"Status: {item.status.value}\n"
        info_text += f"Priority: {item.priority.name}\n"
        info_text += f"Created: {item.created_at}\n"
        if item.started_at:
            info_text += f"Started: {item.started_at}\n"
        if item.completed_at:
            info_text += f"Completed: {item.completed_at}\n"
        info_text += f"Retry Count: {item.retry_count}/{item.max_retries}\n"
        
        self.item_info_text.setPlainText(info_text)
        
        # Metadata
        metadata_text = ""
        for key, value in item.metadata.items():
            metadata_text += f"{key}: {value}\n"
        
        self.metadata_text.setPlainText(metadata_text)
        
        # Error log
        error_text = item.error_message if item.error_message else "No errors"
        self.error_log_text.setPlainText(error_text)
    
    # Action methods
    def pause_item(self, item_id: str):
        """Pause a download item"""
        self.item_paused.emit(item_id)
    
    def resume_item(self, item_id: str):
        """Resume a paused item"""
        self.item_resumed.emit(item_id)
    
    def cancel_item(self, item_id: str):
        """Cancel a download item"""
        self.item_cancelled.emit(item_id)
    
    def retry_item(self, item_id: str):
        """Retry a failed item"""
        # Add back to queue with pending status
        if self.queue_manager:
            item = self.queue_items.get(item_id)
            if item:
                # Reset item status and add back to queue
                pass  # Implementation depends on queue manager API
    
    def remove_item(self, item_id: str):
        """Remove item from queue"""
        reply = QMessageBox.question(
            self, "Confirm Remove",
            "Are you sure you want to remove this item from the queue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Remove from queue manager
            if self.queue_manager:
                pass  # Implementation depends on queue manager API
    
    def change_priority(self, item_id: str, priority: QueuePriority):
        """Change item priority"""
        self.priority_changed.emit(item_id, priority.name)
    
    def pause_all_downloads(self):
        """Pause all active downloads"""
        reply = QMessageBox.question(
            self, "Confirm Pause All",
            "Are you sure you want to pause all active downloads?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            for item_id, item in self.queue_items.items():
                if item.status == QueueStatus.DOWNLOADING:
                    self.pause_item(item_id)
    
    def resume_all_downloads(self):
        """Resume all paused downloads"""
        for item_id, item in self.queue_items.items():
            if item.status == QueueStatus.PAUSED:
                self.resume_item(item_id)
    
    def cancel_all_downloads(self):
        """Cancel all active and pending downloads"""
        reply = QMessageBox.question(
            self, "Confirm Cancel All",
            "Are you sure you want to cancel all downloads?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            for item_id, item in self.queue_items.items():
                if item.status in [QueueStatus.DOWNLOADING, QueueStatus.PENDING, QueueStatus.PAUSED]:
                    self.cancel_item(item_id)
    
    def clear_completed_items(self):
        """Clear completed and failed items"""
        reply = QMessageBox.question(
            self, "Confirm Clear",
            "Are you sure you want to clear all completed and failed items?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.queue_manager:
                # Clear completed items from queue manager
                pass  # Implementation depends on queue manager API
    
    def closeEvent(self, event):
        """Handle widget close event"""
        if self.update_worker:
            self.update_worker.stop()
            self.update_worker.wait()
        
        super().closeEvent(event)
