"""Calendar widget with drag-and-drop booking functionality."""
import logging
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QMessageBox, QToolTip, QDateEdit
)
from PySide6.QtCore import Qt, QPoint, QRect, QEvent
from PySide6.QtGui import QColor, QBrush, QPainter, QPen, QMouseEvent

from database.models import User, Booking, BookingStatus
from database.connection import db
from repositories.booking_repository import BookingRepository
from repositories.resource_repository import ResourceRepository
from services.booking_service import BookingService, BookingConflictError
from ui.dialogs.booking_dialog import BookingDialog

logger = logging.getLogger(__name__)


class CalendarViewport(QWidget):
    """自定义 viewport 用于绘制拖拽预览"""

    def __init__(self, calendar_widget, parent=None):
        super().__init__(parent)
        self.calendar_widget = calendar_widget

    def paintEvent(self, event):
        """绘制拖拽预览"""
        super().paintEvent(event)

        if not self.calendar_widget.is_dragging:
            return

        if not self.calendar_widget.drag_start_cell or not self.calendar_widget.drag_current_cell:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 获取拖拽范围
        start_row, start_col = self.calendar_widget.drag_start_cell
        end_row, end_col = self.calendar_widget.drag_current_cell

        # 确保起始行小于结束行
        if start_row > end_row:
            start_row, end_row = end_row, start_row

        # 计算矩形区域
        table = self.calendar_widget.calendar_table
        start_item = table.item(start_row, start_col)
        end_item = table.item(end_row, end_col)

        if not start_item or not end_item:
            return

        start_rect = table.visualItemRect(start_item)
        end_rect = table.visualItemRect(end_item)

        # 合并矩形
        preview_rect = QRect(
            start_rect.left(),
            start_rect.top(),
            start_rect.width(),
            end_rect.bottom() - start_rect.top()
        )

        # 检查冲突
        start_time = self.calendar_widget.row_to_time(start_row)
        end_time = self.calendar_widget.row_to_time(end_row + 1)
        resource_id = self.calendar_widget.resources[start_col - 1].id
        has_conflict = self.calendar_widget.check_time_conflict(start_time, end_time, resource_id)

        # 选择颜色
        if has_conflict:
            color = self.calendar_widget.COLOR_DRAG_CONFLICT
            pen_color = QColor(231, 76, 60)  # Red
        else:
            color = self.calendar_widget.COLOR_DRAG_PREVIEW
            pen_color = QColor(52, 152, 219)  # Blue

        # 绘制预览矩形
        painter.fillRect(preview_rect, QBrush(color))
        painter.setPen(QPen(pen_color, 2, Qt.DashLine))
        painter.drawRect(preview_rect)

        # 绘制时间文本
        painter.setPen(QPen(Qt.white))
        time_text = f"{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"
        painter.drawText(preview_rect, Qt.AlignCenter, time_text)

        painter.end()


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
    COLOR_DRAG_PREVIEW = QColor(52, 152, 219, 100)  # Semi-transparent blue
    COLOR_DRAG_CONFLICT = QColor(231, 76, 60, 150)  # Semi-transparent red

    def __init__(self, current_user: User, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.current_date = date.today()
        self.resources = []
        self.bookings = []

        # Drag state
        self.drag_start_cell = None  # (row, col)
        self.drag_current_cell = None  # (row, col)
        self.is_dragging = False
        self.drag_start_pos = None  # QPoint
        self.dragging_booking = None  # Booking being dragged
        self.drag_mode = None  # 'create' or 'move'

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

        # Copy last week button
        copy_week_btn = QPushButton("📋 复制上周排班")
        copy_week_btn.clicked.connect(self.copy_last_week_schedule)
        header_layout.addWidget(copy_week_btn)

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

        # 设置自定义 viewport 用于绘制拖拽预览
        custom_viewport = CalendarViewport(self)
        self.calendar_table.setViewport(custom_viewport)
        custom_viewport.installEventFilter(self)

        layout.addWidget(self.calendar_table)

        # Info label
        self.info_label = QLabel("提示: 拖拽创建预约，点击已有预约查看详情，拖动预约块调整时间")
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
        if obj == self.calendar_table.viewport():
            if event.type() == QEvent.MouseButtonPress:
                return self.handle_mouse_press(event)
            elif event.type() == QEvent.MouseMove:
                return self.handle_mouse_move(event)
            elif event.type() == QEvent.MouseButtonRelease:
                return self.handle_mouse_release(event)
            elif event.type() == QEvent.Paint and self.is_dragging:
                # Trigger custom paint for drag preview
                return False
        return super().eventFilter(obj, event)

    def handle_mouse_press(self, event: QMouseEvent) -> bool:
        """处理鼠标按下事件 - 开始拖拽"""
        if event.button() != Qt.LeftButton:
            return False

        # 获取点击的单元格
        pos = event.pos()
        row = self.calendar_table.rowAt(pos.y())
        col = self.calendar_table.columnAt(pos.x())

        # 忽略时间列
        if col <= 0 or row < 0:
            return False

        # 记录拖拽起始位置
        self.drag_start_cell = (row, col)
        self.drag_current_cell = (row, col)
        self.drag_start_pos = pos
        self.is_dragging = True

        # 检查是否点击了已有预约
        item = self.calendar_table.item(row, col)
        if item:
            data = item.data(Qt.UserRole)
            bookings = data.get('bookings', [])
            if bookings:
                # 拖动已有预约
                self.dragging_booking = bookings[0]
                self.drag_mode = 'move'
                logger.info(f"开始拖动预约: {self.dragging_booking.id}")
            else:
                # 创建新预约
                self.dragging_booking = None
                self.drag_mode = 'create'
                logger.info(f"开始创建预约拖拽: row={row}, col={col}")

        return True

    def handle_mouse_move(self, event: QMouseEvent) -> bool:
        """处理鼠标移动事件 - 显示拖拽预览"""
        if not self.is_dragging:
            return False

        # 获取当前单元格
        pos = event.pos()
        row = self.calendar_table.rowAt(pos.y())
        col = self.calendar_table.columnAt(pos.x())

        # 限制在有效范围内
        if col <= 0:
            col = 1
        if row < 0:
            row = 0
        if col >= self.calendar_table.columnCount():
            col = self.calendar_table.columnCount() - 1
        if row >= self.calendar_table.rowCount():
            row = self.calendar_table.rowCount() - 1

        # 更新当前单元格
        if (row, col) != self.drag_current_cell:
            self.drag_current_cell = (row, col)
            self.calendar_table.viewport().update()  # 触发重绘

        return True

    def handle_mouse_release(self, event: QMouseEvent) -> bool:
        """处理鼠标释放事件 - 完成拖拽"""
        if not self.is_dragging:
            return False

        self.is_dragging = False

        # 检查是否是简单点击（没有拖拽）
        if self.drag_start_cell == self.drag_current_cell:
            # 简单点击，使用原有逻辑
            row, col = self.drag_start_cell
            self.on_cell_clicked(row, col)
            self.reset_drag_state()
            return True

        # 获取拖拽范围
        start_row, start_col = self.drag_start_cell
        end_row, end_col = self.drag_current_cell

        # 确保在同一列（同一资源）
        if start_col != end_col and self.drag_mode == 'create':
            QMessageBox.warning(self, "拖拽错误", "只能在同一资源列内拖拽创建预约")
            self.reset_drag_state()
            self.calendar_table.viewport().update()
            return True

        # 确保起始行小于结束行
        if start_row > end_row:
            start_row, end_row = end_row, start_row

        # 计算时间范围
        start_time = self.row_to_time(start_row)
        end_time = self.row_to_time(end_row + 1)  # +1 因为要包含结束行

        # 获取资源ID
        resource_id = self.resources[start_col - 1].id

        # 检查冲突
        has_conflict = self.check_time_conflict(start_time, end_time, resource_id)

        if has_conflict:
            QMessageBox.warning(
                self,
                "时间冲突",
                f"所选时间段 {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')} 已有预约，请选择其他时间"
            )
            self.reset_drag_state()
            self.calendar_table.viewport().update()
            return True

        # 根据拖拽模式执行操作
        if self.drag_mode == 'create':
            # 创建新预约
            self.create_booking_from_drag(start_time, end_time, resource_id)
        elif self.drag_mode == 'move':
            # 移动已有预约
            self.move_booking(self.dragging_booking, start_time, end_time)

        self.reset_drag_state()
        self.calendar_table.viewport().update()
        return True

    def reset_drag_state(self):
        """重置拖拽状态"""
        self.drag_start_cell = None
        self.drag_current_cell = None
        self.is_dragging = False
        self.drag_start_pos = None
        self.dragging_booking = None
        self.drag_mode = None

    def check_time_conflict(self, start_time: datetime, end_time: datetime, resource_id: int) -> bool:
        """检查时间冲突"""
        for booking in self.bookings:
            # 跳过正在拖动的预约
            if self.dragging_booking and booking.id == self.dragging_booking.id:
                continue

            # 检查是否使用相同资源
            booking_resource_ids = [br.resource_id for br in booking.booking_resources]
            if resource_id not in booking_resource_ids:
                continue

            # 检查时间重叠
            if (start_time < booking.end_time and end_time > booking.start_time):
                return True

        return False

    def create_booking_from_drag(self, start_time: datetime, end_time: datetime, resource_id: int):
        """从拖拽创建预约"""
        dialog = BookingDialog(
            current_user=self.current_user,
            default_resource_id=resource_id,
            default_start_time=start_time,
            default_end_time=end_time,
            parent=self
        )

        if dialog.exec():
            self.load_data()  # 刷新日历

    def move_booking(self, booking: Booking, new_start_time: datetime, new_end_time: datetime):
        """移动已有预约"""
        try:
            with db.get_session() as session:
                booking_service = BookingService(session)

                # 更新预约时间
                booking.start_time = new_start_time
                booking.end_time = new_end_time

                session.commit()

                QMessageBox.information(
                    self,
                    "移动成功",
                    f"预约已移动到 {new_start_time.strftime('%H:%M')} - {new_end_time.strftime('%H:%M')}"
                )

                self.load_data()  # 刷新日历

        except Exception as e:
            logger.error(f"移动预约失败: {e}", exc_info=True)
            QMessageBox.critical(self, "移动失败", f"移动预约失败:\n{str(e)}")

    def copy_last_week_schedule(self):
        """复制上周排班到本周"""
        try:
            # 确认操作
            reply = QMessageBox.question(
                self,
                "确认复制",
                "确定要复制上周的排班到本周吗？\n\n注意：\n• 只会复制上周同一天的预约\n• 如果本周已有预约，可能会产生冲突\n• 冲突的预约将被跳过",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            with db.get_session() as session:
                booking_repo = BookingRepository(session)
                booking_service = BookingService(booking_repo)

                # 计算上周同一天的日期
                last_week_date = self.current_date.addDays(-7)

                # 获取上周同一天的所有预约
                last_week_start = datetime.combine(last_week_date.toPython(), datetime.min.time())
                last_week_end = datetime.combine(last_week_date.toPython(), datetime.max.time())

                last_week_bookings = booking_repo.get_by_date_range(last_week_start, last_week_end)

                if not last_week_bookings:
                    QMessageBox.information(
                        self,
                        "无可复制预约",
                        f"上周 {last_week_date.toString('yyyy-MM-dd')} 没有预约记录"
                    )
                    return

                # 复制预约
                copied_count = 0
                skipped_count = 0
                error_messages = []

                for old_booking in last_week_bookings:
                    # 跳过已取消的预约
                    if old_booking.status == BookingStatus.CANCELLED:
                        continue

                    # 计算新的时间（加7天）
                    time_diff = old_booking.end_time - old_booking.start_time
                    new_start = old_booking.start_time + timedelta(days=7)
                    new_end = old_booking.end_time + timedelta(days=7)

                    # 获取资源ID列表
                    resource_ids = [br.resource_id for br in old_booking.booking_resources]

                    try:
                        # 检查冲突
                        conflicts = booking_service.check_conflicts(resource_ids, new_start, new_end)

                        if conflicts:
                            skipped_count += 1
                            error_messages.append(
                                f"• {old_booking.customer.name} "
                                f"{new_start.strftime('%H:%M')}-{new_end.strftime('%H:%M')} "
                                f"(冲突)"
                            )
                            continue

                        # 创建新预约
                        new_booking = booking_service.create_booking(
                            customer_id=old_booking.customer_id,
                            resource_ids=resource_ids,
                            start_time=new_start,
                            end_time=new_end,
                            engineer_id=old_booking.engineer_id,
                            notes=f"[复制自上周] {old_booking.notes or ''}",
                            created_by=self.current_user.id
                        )

                        copied_count += 1

                    except Exception as e:
                        skipped_count += 1
                        error_messages.append(
                            f"• {old_booking.customer.name} "
                            f"{new_start.strftime('%H:%M')}-{new_end.strftime('%H:%M')} "
                            f"(错误: {str(e)})"
                        )
                        logger.error(f"复制预约失败: {e}", exc_info=True)

                # 显示结果
                result_message = f"复制完成！\n\n成功复制: {copied_count} 个预约\n跳过: {skipped_count} 个预约"

                if error_messages:
                    result_message += "\n\n跳过的预约:\n" + "\n".join(error_messages[:10])
                    if len(error_messages) > 10:
                        result_message += f"\n... 还有 {len(error_messages) - 10} 个"

                if copied_count > 0:
                    QMessageBox.information(self, "复制成功", result_message)
                    self.load_data()  # 刷新日历
                else:
                    QMessageBox.warning(self, "复制失败", result_message)

        except Exception as e:
            logger.error(f"复制上周排班失败: {e}", exc_info=True)
            QMessageBox.critical(self, "复制失败", f"复制上周排班失败:\n{str(e)}")
