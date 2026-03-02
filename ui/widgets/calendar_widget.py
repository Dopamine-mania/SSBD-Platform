"""Calendar widget with drag-and-drop booking functionality."""
import logging
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QMessageBox, QToolTip, QDateEdit
)
from PySide6.QtCore import Qt, QPoint, QRect
from PySide6.QtGui import QColor, QBrush, QPainter, QPen

from database.models import User, Booking, BookingStatus
from database.connection import db
from repositories.booking_repository import BookingRepository
from repositories.resource_repository import ResourceRepository
from services.booking_service import BookingService, BookingConflictError
from ui.dialogs.booking_dialog import BookingDialog

logger = logging.getLogger(__name__)

class CalendarWidget(QWidget):
    """Calendar widget with drag-and-drop booking functionality."""

    # Time slots (30-minute intervals)
    TIME_SLOTS = [f"{h:02d}:{m:02d}" for h in range(24) for m in (0, 30)]

    # Colors for booking status
    COLOR_CONFIRMED = QColor(52, 152, 219)      # Blue
    COLOR_IN_PROGRESS = QColor(46, 204, 113)    # Green
    COLOR_PENDING = QColor(241, 196, 15)        # Yellow
    COLOR_CONFLICT = QColor(231, 76, 60)        # Red
    COLOR_HOVER = QColor(149, 165, 166, 100)    # Gray transparent

    def __init__(self, current_user: User, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.current_date = date.today()
        self.resources = []
        self.bookings = []

        # Drag state
        self.drag_start_cell = None
        self.drag_current_cell = None
        self.is_dragging = False

        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header_layout = QHBoxLayout()

        title = QLabel("预约日历")
        title.setObjectName("pageTitle")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Date selector
        self.date_edit = QDateEdit()
        self.date_edit.setDate(self.current_date)
        self.date_edit.setCalendarPopup(True)
        self.date_edit.dateChanged.connect(self.on_date_changed)
        header_layout.addWidget(QLabel("日期:"))
        header_layout.addWidget(self.date_edit)

        # Navigation buttons
        prev_btn = QPushButton("◀ 前一天")
        prev_btn.clicked.connect(self.previous_day)
        header_layout.addWidget(prev_btn)

        today_btn = QPushButton("今天")
        today_btn.clicked.connect(self.go_to_today)
        header_layout.addWidget(today_btn)

        next_btn = QPushButton("后一天 ▶")
        next_btn.clicked.connect(self.next_day)
        header_layout.addWidget(next_btn)

        # Refresh button
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.load_data)
        header_layout.addWidget(refresh_btn)

        layout.addLayout(header_layout)

        # Legend
        legend_layout = QHBoxLayout()
        legend_layout.addWidget(QLabel("图例:"))

        legend_items = [
            ("待确认", self.COLOR_PENDING),
            ("已确认", self.COLOR_CONFIRMED),
            ("进行中", self.COLOR_IN_PROGRESS),
            ("冲突", self.COLOR_CONFLICT),
        ]

        for text, color in legend_items:
            label = QLabel(f"■ {text}")
            label.setStyleSheet(f"color: {color.name()}; font-weight: bold;")
            legend_layout.addWidget(label)

        legend_layout.addStretch()
        layout.addLayout(legend_layout)

        # Calendar table
        self.calendar_table = QTableWidget()
        self.calendar_table.setMouseTracking(True)
        self.calendar_table.setSelectionMode(QTableWidget.NoSelection)
        self.calendar_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.calendar_table.cellEntered.connect(self.on_cell_hover)
        self.calendar_table.cellClicked.connect(self.on_cell_clicked)
        self.calendar_table.viewport().installEventFilter(self)

        layout.addWidget(self.calendar_table)

        # Info label
        self.info_label = QLabel("提示: 点击空白单元格创建预约，点击已有预约查看详情")
        self.info_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        layout.addWidget(self.info_label)

    def load_data(self):
        """Load resources and bookings for current date."""
        try:
            with db.get_session() as session:
                # Load resources
                resource_repo = ResourceRepository(session)
                self.resources = resource_repo.get_available_resources()

                # Load bookings for current date
                booking_repo = BookingRepository(session)
                start_of_day = datetime.combine(self.current_date, datetime.min.time())
                end_of_day = datetime.combine(self.current_date, datetime.max.time())
                self.bookings = booking_repo.get_by_date_range(start_of_day, end_of_day)

            self.render_calendar()
            logger.info(f"Loaded {len(self.resources)} resources and {len(self.bookings)} bookings")

        except Exception as e:
            logger.error(f"Failed to load calendar data: {e}", exc_info=True)
            QMessageBox.critical(self, "加载失败", f"加载日历数据失败:\n{str(e)}")

    def render_calendar(self):
        """Render calendar table."""
        # Setup table dimensions
        self.calendar_table.clear()
        self.calendar_table.setRowCount(len(self.TIME_SLOTS))
        self.calendar_table.setColumnCount(len(self.resources) + 1)

        # Set headers
        time_headers = self.TIME_SLOTS
        self.calendar_table.setVerticalHeaderLabels(time_headers)

        resource_headers = ["时间"] + [r.name for r in self.resources]
        self.calendar_table.setHorizontalHeaderLabels(resource_headers)

        # Set column widths
        self.calendar_table.setColumnWidth(0, 80)
        for i in range(1, len(resource_headers)):
            self.calendar_table.setColumnWidth(i, 150)

        # Set row heights
        for i in range(len(time_headers)):
            self.calendar_table.setRowHeight(i, 40)

        # Fill time column
        for row, time_slot in enumerate(time_headers):
            item = QTableWidgetItem(time_slot)
            item.setTextAlignment(Qt.AlignCenter)
            item.setFlags(Qt.ItemIsEnabled)
            self.calendar_table.setItem(row, 0, item)

        # Fill booking cells
        for col_idx, resource in enumerate(self.resources, start=1):
            for row_idx in range(len(time_headers)):
                item = QTableWidgetItem("")
                item.setData(Qt.UserRole, {
                    'resource_id': resource.id,
                    'time_slot': time_headers[row_idx],
                    'bookings': []
                })
                self.calendar_table.setItem(row_idx, col_idx, item)

        # Render bookings
        for booking in self.bookings:
            self.render_booking(booking)

        # Resize to contents
        self.calendar_table.horizontalHeader().setStretchLastSection(True)

    def render_booking(self, booking: Booking):
        """Render a booking on the calendar."""
        for booking_resource in booking.booking_resources:
            resource_id = booking_resource.resource_id

            # Find resource column
            col_idx = None
            for idx, resource in enumerate(self.resources, start=1):
                if resource.id == resource_id:
                    col_idx = idx
                    break

            if col_idx is None:
                continue

            # Calculate time slots
            start_time = booking.start_time
            end_time = booking.end_time

            # Only render if booking is on current date
            if start_time.date() != self.current_date and end_time.date() != self.current_date:
                continue

            # Adjust times to current date boundaries
            day_start = datetime.combine(self.current_date, datetime.min.time())
            day_end = datetime.combine(self.current_date, datetime.max.time())

            display_start = max(start_time, day_start)
            display_end = min(end_time, day_end)

            # Find start and end rows
            start_row = self.time_to_row(display_start.time())
            end_row = self.time_to_row(display_end.time())

            # Color based on status
            if booking.status == BookingStatus.CONFIRMED:
                color = self.COLOR_CONFIRMED
            elif booking.status == BookingStatus.IN_PROGRESS:
                color = self.COLOR_IN_PROGRESS
            elif booking.status == BookingStatus.PENDING:
                color = self.COLOR_PENDING
            else:
                continue  # Don't show cancelled/completed

            # Fill cells
            for row in range(start_row, end_row):
                if row >= len(self.TIME_SLOTS):
                    break

                item = self.calendar_table.item(row, col_idx)
                if item:
                    # Store booking reference
                    data = item.data(Qt.UserRole)
                    data['bookings'].append(booking)
                    item.setData(Qt.UserRole, data)

                    # Set background color
                    item.setBackground(QBrush(color))

                    # Set text (customer name)
                    if row == start_row:
                        item.setText(booking.customer.name if booking.customer else "未知客户")
                        item.setForeground(QBrush(Qt.white))
                        item.setTextAlignment(Qt.AlignCenter)

    def time_to_row(self, time) -> int:
        """Convert time to row index."""
        hour = time.hour
        minute = time.minute
        # Each hour has 2 slots (0 and 30 minutes)
        row = hour * 2
        if minute >= 30:
            row += 1
        return row

    def row_to_time(self, row: int) -> datetime:
        """Convert row index to datetime."""
        hour = row // 2
        minute = 30 if row % 2 == 1 else 0
        return datetime.combine(self.current_date, datetime.min.time().replace(hour=hour, minute=minute))

    def on_cell_hover(self, row: int, col: int):
        """Handle cell hover to show tooltip."""
        if col == 0:  # Time column
            return

        item = self.calendar_table.item(row, col)
        if not item:
            return

        data = item.data(Qt.UserRole)
        bookings = data.get('bookings', [])

        if bookings:
            # Show booking details
            booking = bookings[0]  # Show first booking if multiple
            tooltip = f"""
<b>客户:</b> {booking.customer.name if booking.customer else '未知'}<br>
<b>时间:</b> {booking.start_time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}<br>
<b>状态:</b> {self.get_status_text(booking.status)}<br>
<b>工程师:</b> {booking.engineer_user.full_name if booking.engineer_user else '未分配'}
            """.strip()
            QToolTip.showText(self.calendar_table.viewport().mapToGlobal(
                self.calendar_table.visualItemRect(item).center()
            ), tooltip)

    def get_status_text(self, status: BookingStatus) -> str:
        """Get status text in Chinese."""
        status_map = {
            BookingStatus.PENDING: "待确认",
            BookingStatus.CONFIRMED: "已确认",
            BookingStatus.IN_PROGRESS: "进行中",
            BookingStatus.COMPLETED: "已完成",
            BookingStatus.CANCELLED: "已取消",
        }
        return status_map.get(status, "未知")

    def on_cell_clicked(self, row: int, col: int):
        """Handle cell click."""
        if col == 0:  # Time column
            return

        item = self.calendar_table.item(row, col)
        if not item:
            return

        data = item.data(Qt.UserRole)
        bookings = data.get('bookings', [])

        if bookings:
            # Show booking details
            self.show_booking_details(bookings[0])
        else:
            # Create new booking
            self.create_booking(row, col)

    def create_booking(self, row: int, col: int):
        """Create new booking."""
        resource_id = self.resources[col - 1].id
        start_time = self.row_to_time(row)
        end_time = start_time + timedelta(hours=1)  # Default 1 hour

        dialog = BookingDialog(
            current_user=self.current_user,
            default_resource_id=resource_id,
            default_start_time=start_time,
            default_end_time=end_time,
            parent=self
        )

        if dialog.exec():
            self.load_data()  # Refresh calendar

    def show_booking_details(self, booking: Booking):
        """Show booking details dialog."""
        dialog = BookingDialog(
            current_user=self.current_user,
            booking=booking,
            parent=self
        )

        if dialog.exec():
            self.load_data()  # Refresh calendar

    def on_date_changed(self, new_date):
        """Handle date change."""
        self.current_date = new_date.toPython()
        self.load_data()

    def previous_day(self):
        """Go to previous day."""
        self.current_date -= timedelta(days=1)
        self.date_edit.setDate(self.current_date)

    def next_day(self):
        """Go to next day."""
        self.current_date += timedelta(days=1)
        self.date_edit.setDate(self.current_date)

    def go_to_today(self):
        """Go to today."""
        self.current_date = date.today()
        self.date_edit.setDate(self.current_date)

    def eventFilter(self, obj, event):
        """Event filter for drag-and-drop."""
        # TODO: Implement drag-and-drop in future enhancement
        return super().eventFilter(obj, event)
