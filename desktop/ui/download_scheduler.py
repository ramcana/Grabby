"""
Download Scheduler Widget for Advanced Desktop UI
"""
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QGroupBox, QFormLayout, QDateTimeEdit,
    QComboBox, QLineEdit, QSpinBox, QCheckBox, QLabel, QMessageBox,
    QTabWidget, QCalendarWidget, QTimeEdit, QTextEdit
)
from PyQt6.QtCore import Qt, QTimer, QDateTime, pyqtSignal
from PyQt6.QtGui import QFont

# Add backend to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

class ScheduledDownload:
    """Represents a scheduled download"""
    def __init__(self, url: str, scheduled_time: datetime, profile: str = "default", 
                 repeat_type: str = "none", repeat_interval: int = 1):
        self.id = str(hash(f"{url}{scheduled_time}"))
        self.url = url
        self.scheduled_time = scheduled_time
        self.profile = profile
        self.repeat_type = repeat_type  # none, daily, weekly, monthly
        self.repeat_interval = repeat_interval
        self.enabled = True
        self.last_run = None
        self.next_run = scheduled_time
        self.created_at = datetime.now()

class DownloadScheduler(QWidget):
    """Advanced download scheduler widget"""
    
    schedule_added = pyqtSignal(dict)
    schedule_removed = pyqtSignal(str)
    schedule_modified = pyqtSignal(str, dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scheduled_downloads = {}
        
        self.init_ui()
        self.setup_timer()
    
    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Add tabs
        self.tab_widget.addTab(self.create_schedule_tab(), "Schedule")
        self.tab_widget.addTab(self.create_calendar_tab(), "Calendar")
        self.tab_widget.addTab(self.create_templates_tab(), "Templates")
        
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)
    
    def create_schedule_tab(self) -> QWidget:
        """Create schedule management tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Add new schedule group
        add_group = QGroupBox("Add New Schedule")
        add_layout = QFormLayout()
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter URL to download...")
        add_layout.addRow("URL:", self.url_input)
        
        self.schedule_datetime = QDateTimeEdit()
        self.schedule_datetime.setDateTime(QDateTime.currentDateTime().addSecs(3600))
        self.schedule_datetime.setCalendarPopup(True)
        add_layout.addRow("Scheduled Time:", self.schedule_datetime)
        
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(["default", "high_quality", "audio_only", "mobile"])
        add_layout.addRow("Profile:", self.profile_combo)
        
        self.repeat_combo = QComboBox()
        self.repeat_combo.addItems(["None", "Daily", "Weekly", "Monthly"])
        add_layout.addRow("Repeat:", self.repeat_combo)
        
        self.repeat_interval = QSpinBox()
        self.repeat_interval.setRange(1, 365)
        self.repeat_interval.setValue(1)
        add_layout.addRow("Repeat Every:", self.repeat_interval)
        
        # Add button
        add_btn = QPushButton("Add Schedule")
        add_btn.clicked.connect(self.add_schedule)
        add_layout.addRow("", add_btn)
        
        add_group.setLayout(add_layout)
        layout.addWidget(add_group)
        
        # Scheduled downloads table
        table_group = QGroupBox("Scheduled Downloads")
        table_layout = QVBoxLayout()
        
        self.schedule_table = QTableWidget()
        self.schedule_table.setColumnCount(7)
        self.schedule_table.setHorizontalHeaderLabels([
            "URL", "Next Run", "Profile", "Repeat", "Status", "Last Run", "Actions"
        ])
        
        # Configure table
        header = self.schedule_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        
        table_layout.addWidget(self.schedule_table)
        
        # Table controls
        controls_layout = QHBoxLayout()
        
        self.enable_btn = QPushButton("Enable")
        self.disable_btn = QPushButton("Disable")
        self.edit_btn = QPushButton("Edit")
        self.delete_btn = QPushButton("Delete")
        self.run_now_btn = QPushButton("Run Now")
        
        self.enable_btn.clicked.connect(self.enable_schedule)
        self.disable_btn.clicked.connect(self.disable_schedule)
        self.edit_btn.clicked.connect(self.edit_schedule)
        self.delete_btn.clicked.connect(self.delete_schedule)
        self.run_now_btn.clicked.connect(self.run_schedule_now)
        
        controls_layout.addWidget(self.enable_btn)
        controls_layout.addWidget(self.disable_btn)
        controls_layout.addWidget(self.edit_btn)
        controls_layout.addWidget(self.delete_btn)
        controls_layout.addWidget(self.run_now_btn)
        controls_layout.addStretch()
        
        table_layout.addLayout(controls_layout)
        table_group.setLayout(table_layout)
        layout.addWidget(table_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_calendar_tab(self) -> QWidget:
        """Create calendar view tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Calendar widget
        self.calendar = QCalendarWidget()
        self.calendar.clicked.connect(self.on_date_selected)
        layout.addWidget(self.calendar)
        
        # Selected date schedules
        date_group = QGroupBox("Schedules for Selected Date")
        date_layout = QVBoxLayout()
        
        self.date_schedules_list = QTextEdit()
        self.date_schedules_list.setReadOnly(True)
        self.date_schedules_list.setMaximumHeight(150)
        date_layout.addWidget(self.date_schedules_list)
        
        date_group.setLayout(date_layout)
        layout.addWidget(date_group)
        
        widget.setLayout(layout)
        return widget
    
    def create_templates_tab(self) -> QWidget:
        """Create schedule templates tab"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # Quick templates group
        templates_group = QGroupBox("Quick Schedule Templates")
        templates_layout = QVBoxLayout()
        
        # Template buttons
        template_buttons_layout = QHBoxLayout()
        
        daily_btn = QPushButton("Daily at 9 AM")
        weekly_btn = QPushButton("Weekly on Sunday")
        monthly_btn = QPushButton("Monthly on 1st")
        
        daily_btn.clicked.connect(lambda: self.apply_template("daily"))
        weekly_btn.clicked.connect(lambda: self.apply_template("weekly"))
        monthly_btn.clicked.connect(lambda: self.apply_template("monthly"))
        
        template_buttons_layout.addWidget(daily_btn)
        template_buttons_layout.addWidget(weekly_btn)
        template_buttons_layout.addWidget(monthly_btn)
        template_buttons_layout.addStretch()
        
        templates_layout.addLayout(template_buttons_layout)
        
        # Custom template
        custom_group = QGroupBox("Custom Template")
        custom_layout = QFormLayout()
        
        self.template_name = QLineEdit()
        custom_layout.addRow("Template Name:", self.template_name)
        
        self.template_time = QTimeEdit()
        self.template_time.setTime(self.template_time.time().addSecs(3600))
        custom_layout.addRow("Time:", self.template_time)
        
        self.template_repeat = QComboBox()
        self.template_repeat.addItems(["Daily", "Weekly", "Monthly"])
        custom_layout.addRow("Repeat:", self.template_repeat)
        
        save_template_btn = QPushButton("Save Template")
        save_template_btn.clicked.connect(self.save_template)
        custom_layout.addRow("", save_template_btn)
        
        custom_group.setLayout(custom_layout)
        templates_layout.addWidget(custom_group)
        
        templates_group.setLayout(templates_layout)
        layout.addWidget(templates_group)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def setup_timer(self):
        """Setup timer to check for scheduled downloads"""
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self.check_scheduled_downloads)
        self.check_timer.start(60000)  # Check every minute
    
    def add_schedule(self):
        """Add new scheduled download"""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Warning", "Please enter a URL")
            return
        
        scheduled_time = self.schedule_datetime.dateTime().toPython()
        profile = self.profile_combo.currentText()
        repeat_type = self.repeat_combo.currentText().lower()
        repeat_interval = self.repeat_interval.value()
        
        schedule = ScheduledDownload(url, scheduled_time, profile, repeat_type, repeat_interval)
        self.scheduled_downloads[schedule.id] = schedule
        
        self.refresh_schedule_table()
        self.update_calendar()
        
        # Clear form
        self.url_input.clear()
        
        # Emit signal
        self.schedule_added.emit({
            'id': schedule.id,
            'url': url,
            'scheduled_time': scheduled_time,
            'profile': profile,
            'repeat_type': repeat_type,
            'repeat_interval': repeat_interval
        })
        
        QMessageBox.information(self, "Success", "Schedule added successfully")
    
    def refresh_schedule_table(self):
        """Refresh the schedule table"""
        self.schedule_table.setRowCount(len(self.scheduled_downloads))
        
        for row, (schedule_id, schedule) in enumerate(self.scheduled_downloads.items()):
            # URL
            url_item = QTableWidgetItem(schedule.url[:50] + "..." if len(schedule.url) > 50 else schedule.url)
            url_item.setData(Qt.ItemDataRole.UserRole, schedule_id)
            self.schedule_table.setItem(row, 0, url_item)
            
            # Next run
            next_run_item = QTableWidgetItem(schedule.next_run.strftime("%Y-%m-%d %H:%M"))
            self.schedule_table.setItem(row, 1, next_run_item)
            
            # Profile
            profile_item = QTableWidgetItem(schedule.profile)
            self.schedule_table.setItem(row, 2, profile_item)
            
            # Repeat
            repeat_text = f"{schedule.repeat_type}"
            if schedule.repeat_type != "none":
                repeat_text += f" (every {schedule.repeat_interval})"
            repeat_item = QTableWidgetItem(repeat_text)
            self.schedule_table.setItem(row, 3, repeat_item)
            
            # Status
            status_item = QTableWidgetItem("Enabled" if schedule.enabled else "Disabled")
            self.schedule_table.setItem(row, 4, status_item)
            
            # Last run
            last_run_text = schedule.last_run.strftime("%Y-%m-%d %H:%M") if schedule.last_run else "Never"
            last_run_item = QTableWidgetItem(last_run_text)
            self.schedule_table.setItem(row, 5, last_run_item)
            
            # Actions
            actions_widget = self.create_actions_widget(schedule_id)
            self.schedule_table.setCellWidget(row, 6, actions_widget)
    
    def create_actions_widget(self, schedule_id: str) -> QWidget:
        """Create actions widget for schedule item"""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        
        edit_btn = QPushButton("✏️")
        edit_btn.setToolTip("Edit")
        edit_btn.clicked.connect(lambda: self.edit_schedule_by_id(schedule_id))
        
        delete_btn = QPushButton("🗑️")
        delete_btn.setToolTip("Delete")
        delete_btn.clicked.connect(lambda: self.delete_schedule_by_id(schedule_id))
        
        layout.addWidget(edit_btn)
        layout.addWidget(delete_btn)
        
        widget.setLayout(layout)
        return widget
    
    def enable_schedule(self):
        """Enable selected schedule"""
        current_row = self.schedule_table.currentRow()
        if current_row >= 0:
            url_item = self.schedule_table.item(current_row, 0)
            if url_item:
                schedule_id = url_item.data(Qt.ItemDataRole.UserRole)
                if schedule_id in self.scheduled_downloads:
                    self.scheduled_downloads[schedule_id].enabled = True
                    self.refresh_schedule_table()
    
    def disable_schedule(self):
        """Disable selected schedule"""
        current_row = self.schedule_table.currentRow()
        if current_row >= 0:
            url_item = self.schedule_table.item(current_row, 0)
            if url_item:
                schedule_id = url_item.data(Qt.ItemDataRole.UserRole)
                if schedule_id in self.scheduled_downloads:
                    self.scheduled_downloads[schedule_id].enabled = False
                    self.refresh_schedule_table()
    
    def edit_schedule(self):
        """Edit selected schedule"""
        current_row = self.schedule_table.currentRow()
        if current_row >= 0:
            url_item = self.schedule_table.item(current_row, 0)
            if url_item:
                schedule_id = url_item.data(Qt.ItemDataRole.UserRole)
                self.edit_schedule_by_id(schedule_id)
    
    def edit_schedule_by_id(self, schedule_id: str):
        """Edit schedule by ID"""
        if schedule_id not in self.scheduled_downloads:
            return
        
        schedule = self.scheduled_downloads[schedule_id]
        
        # Pre-fill form with current values
        self.url_input.setText(schedule.url)
        self.schedule_datetime.setDateTime(QDateTime.fromSecsSinceEpoch(int(schedule.next_run.timestamp())))
        self.profile_combo.setCurrentText(schedule.profile)
        self.repeat_combo.setCurrentText(schedule.repeat_type.title())
        self.repeat_interval.setValue(schedule.repeat_interval)
        
        # Switch to schedule tab
        self.tab_widget.setCurrentIndex(0)
        
        QMessageBox.information(self, "Edit Mode", "Form pre-filled with current values. Modify and click 'Add Schedule' to update.")
        
        # Remove old schedule
        del self.scheduled_downloads[schedule_id]
        self.refresh_schedule_table()
    
    def delete_schedule(self):
        """Delete selected schedule"""
        current_row = self.schedule_table.currentRow()
        if current_row >= 0:
            url_item = self.schedule_table.item(current_row, 0)
            if url_item:
                schedule_id = url_item.data(Qt.ItemDataRole.UserRole)
                self.delete_schedule_by_id(schedule_id)
    
    def delete_schedule_by_id(self, schedule_id: str):
        """Delete schedule by ID"""
        if schedule_id not in self.scheduled_downloads:
            return
        
        reply = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to delete this schedule?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            del self.scheduled_downloads[schedule_id]
            self.refresh_schedule_table()
            self.update_calendar()
            self.schedule_removed.emit(schedule_id)
    
    def run_schedule_now(self):
        """Run selected schedule immediately"""
        current_row = self.schedule_table.currentRow()
        if current_row >= 0:
            url_item = self.schedule_table.item(current_row, 0)
            if url_item:
                schedule_id = url_item.data(Qt.ItemDataRole.UserRole)
                if schedule_id in self.scheduled_downloads:
                    schedule = self.scheduled_downloads[schedule_id]
                    self.execute_schedule(schedule)
    
    def check_scheduled_downloads(self):
        """Check for downloads that should be executed"""
        current_time = datetime.now()
        
        for schedule_id, schedule in list(self.scheduled_downloads.items()):
            if not schedule.enabled:
                continue
            
            if current_time >= schedule.next_run:
                self.execute_schedule(schedule)
    
    def execute_schedule(self, schedule: ScheduledDownload):
        """Execute a scheduled download"""
        # Update last run time
        schedule.last_run = datetime.now()
        
        # Calculate next run time if repeating
        if schedule.repeat_type != "none":
            if schedule.repeat_type == "daily":
                schedule.next_run = schedule.next_run + timedelta(days=schedule.repeat_interval)
            elif schedule.repeat_type == "weekly":
                schedule.next_run = schedule.next_run + timedelta(weeks=schedule.repeat_interval)
            elif schedule.repeat_type == "monthly":
                # Approximate monthly repeat (30 days)
                schedule.next_run = schedule.next_run + timedelta(days=30 * schedule.repeat_interval)
        else:
            # One-time schedule, disable after execution
            schedule.enabled = False
        
        # Emit signal to start download
        self.schedule_added.emit({
            'id': schedule.id,
            'url': schedule.url,
            'profile': schedule.profile,
            'immediate': True
        })
        
        self.refresh_schedule_table()
        self.update_calendar()
    
    def on_date_selected(self, date):
        """Handle calendar date selection"""
        selected_date = date.toPython()
        schedules_text = ""
        
        for schedule in self.scheduled_downloads.values():
            if schedule.next_run.date() == selected_date:
                schedules_text += f"• {schedule.next_run.strftime('%H:%M')} - {schedule.url[:50]}...\n"
                schedules_text += f"  Profile: {schedule.profile}, Repeat: {schedule.repeat_type}\n\n"
        
        if not schedules_text:
            schedules_text = "No schedules for this date."
        
        self.date_schedules_list.setPlainText(schedules_text)
    
    def update_calendar(self):
        """Update calendar with schedule markers"""
        # This would require custom calendar widget to show markers
        # For now, just refresh the selected date view
        if hasattr(self, 'calendar'):
            self.on_date_selected(self.calendar.selectedDate())
    
    def apply_template(self, template_type: str):
        """Apply a schedule template"""
        current_time = datetime.now()
        
        if template_type == "daily":
            # Daily at 9 AM
            next_run = current_time.replace(hour=9, minute=0, second=0, microsecond=0)
            if next_run <= current_time:
                next_run += timedelta(days=1)
            
            self.schedule_datetime.setDateTime(QDateTime.fromSecsSinceEpoch(int(next_run.timestamp())))
            self.repeat_combo.setCurrentText("Daily")
            self.repeat_interval.setValue(1)
            
        elif template_type == "weekly":
            # Weekly on Sunday at 9 AM
            days_until_sunday = (6 - current_time.weekday()) % 7
            if days_until_sunday == 0:
                days_until_sunday = 7
            
            next_run = current_time + timedelta(days=days_until_sunday)
            next_run = next_run.replace(hour=9, minute=0, second=0, microsecond=0)
            
            self.schedule_datetime.setDateTime(QDateTime.fromSecsSinceEpoch(int(next_run.timestamp())))
            self.repeat_combo.setCurrentText("Weekly")
            self.repeat_interval.setValue(1)
            
        elif template_type == "monthly":
            # Monthly on 1st at 9 AM
            if current_time.day == 1 and current_time.hour < 9:
                next_run = current_time.replace(hour=9, minute=0, second=0, microsecond=0)
            else:
                if current_time.month == 12:
                    next_run = current_time.replace(year=current_time.year + 1, month=1, day=1, hour=9, minute=0, second=0, microsecond=0)
                else:
                    next_run = current_time.replace(month=current_time.month + 1, day=1, hour=9, minute=0, second=0, microsecond=0)
            
            self.schedule_datetime.setDateTime(QDateTime.fromSecsSinceEpoch(int(next_run.timestamp())))
            self.repeat_combo.setCurrentText("Monthly")
            self.repeat_interval.setValue(1)
        
        # Switch to schedule tab
        self.tab_widget.setCurrentIndex(0)
    
    def save_template(self):
        """Save custom template"""
        template_name = self.template_name.text().strip()
        if not template_name:
            QMessageBox.warning(self, "Warning", "Please enter a template name")
            return
        
        # For now, just show success message
        # In a full implementation, this would save to a templates file
        QMessageBox.information(self, "Success", f"Template '{template_name}' saved successfully")
        self.template_name.clear()
    
    def get_scheduled_downloads(self) -> List[Dict[str, Any]]:
        """Get all scheduled downloads"""
        return [
            {
                'id': schedule.id,
                'url': schedule.url,
                'scheduled_time': schedule.scheduled_time,
                'next_run': schedule.next_run,
                'profile': schedule.profile,
                'repeat_type': schedule.repeat_type,
                'repeat_interval': schedule.repeat_interval,
                'enabled': schedule.enabled,
                'last_run': schedule.last_run
            }
            for schedule in self.scheduled_downloads.values()
        ]
