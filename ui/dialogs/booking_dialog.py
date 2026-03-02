"""Booking dialog for creating and editing bookings."""
import logging
from datetime import datetime, timedelta
from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QPushButton, QComboBox, QDateTimeEdit, QTextEdit, QMessageBox,
    QGroupBox, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt

from database.models import User, Booking, BookingStatus
from database.connection import db
from repositories.customer_repository import CustomerRepository
from repositories.resource_repository import ResourceRepository
from repositories.user_repository import UserRepository
from repositories.booking_repository import BookingRepository
from services.booking_service import BookingService, BookingConflictError
from services.billing_service import BillingService

logger = logging.getLogger(__name__)

class BookingDialog(QDialog):
    """Dialog for creating and editing bookings."""

    def __init__(
        self,
        current_user: User,
        booking: Optional[Booking] = None,
        default_resource_id: Optional[int] = None,
        default_start_time: Optional[datetime] = None,
        default_end_time: Optional[datetime] = None,
        parent=None
    ):
        super().__init__(parent)
        self.current_user = current_user
        self.booking = booking
        self.default_resource_id = default_resource_id
        self.default_start_time = default_start_time
        self.default_end_time = default_end_time

        self.customers = []
        self.resources = []
        self.engineers = []

        self.setup_ui()
        self.load_data()

        if booking:
            self.load_booking_data()

    def setup_ui(self):
        """Setup user interface."""
        self.setWindowTitle("预约详情" if self.booking else "创建预约")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)

        layout = QVBoxLayout(self)

        # Title
        title = QLabel("预约详情" if self.booking else "创建新预约")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # Form
        form_layout = QFormLayout()

        # Customer
        self.customer_combo = QComboBox()
        self.customer_combo.setEditable(True)
        form_layout.addRow("客户:", self.customer_combo)

        # Start time
        self.start_time_edit = QDateTimeEdit()
        self.start_time_edit.setCalendarPopup(True)
        self.start_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        if self.default_start_time:
            self.start_time_edit.setDateTime(self.default_start_time)
        else:
            self.start_time_edit.setDateTime(datetime.now())
        self.start_time_edit.dateTimeChanged.connect(self.update_billing_preview)
        form_layout.addRow("开始时间:", self.start_time_edit)

        # End time
        self.end_time_edit = QDateTimeEdit()
        self.end_time_edit.setCalendarPopup(True)
        self.end_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        if self.default_end_time:
            self.end_time_edit.setDateTime(self.default_end_time)
        else:
            self.end_time_edit.setDateTime(datetime.now() + timedelta(hours=1))
        self.end_time_edit.dateTimeChanged.connect(self.update_billing_preview)
        form_layout.addRow("结束时间:", self.end_time_edit)

        # Engineer
        self.engineer_combo = QComboBox()
        self.engineer_combo.addItem("未分配", None)
        self.engineer_combo.currentIndexChanged.connect(self.update_billing_preview)
        form_layout.addRow("工程师:", self.engineer_combo)

        # Status (if editing)
        if self.booking:
            self.status_combo = QComboBox()
            status_items = [
                ("待确认", BookingStatus.PENDING),
                ("已确认", BookingStatus.CONFIRMED),
                ("进行中", BookingStatus.IN_PROGRESS),
                ("已完成", BookingStatus.COMPLETED),
                ("已取消", BookingStatus.CANCELLED),
            ]
            for text, status in status_items:
                self.status_combo.addItem(text, status)
            form_layout.addRow("状态:", self.status_combo)

        # Notes
        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(80)
        form_layout.addRow("备注:", self.notes_edit)

        layout.addLayout(form_layout)

        # Resources selection
        resources_group = QGroupBox("选择资源")
        resources_layout = QVBoxLayout(resources_group)

        self.resources_list = QListWidget()
        self.resources_list.setSelectionMode(QListWidget.MultiSelection)
        self.resources_list.itemSelectionChanged.connect(self.update_billing_preview)
        resources_layout.addWidget(self.resources_list)

        layout.addWidget(resources_group)

        # Billing preview
        self.billing_group = QGroupBox("计费预览 (15分钟进位)")
        billing_layout = QVBoxLayout(self.billing_group)

        self.billing_label = QLabel("请选择资源和时间")
        self.billing_label.setWordWrap(True)
        billing_layout.addWidget(self.billing_label)

        layout.addWidget(self.billing_group)

        # Buttons
        button_layout = QHBoxLayout()

        if self.booking:
            # Edit mode buttons
            save_btn = QPushButton("保存")
            save_btn.clicked.connect(self.save_booking)
            button_layout.addWidget(save_btn)

            delete_btn = QPushButton("删除")
            delete_btn.setStyleSheet("background-color: #e74c3c;")
            delete_btn.clicked.connect(self.delete_booking)
            button_layout.addWidget(delete_btn)
        else:
            # Create mode button
            create_btn = QPushButton("创建预约")
            create_btn.clicked.connect(self.create_booking)
            button_layout.addWidget(create_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def load_data(self):
        """Load customers, resources, and engineers."""
        try:
            with db.get_session() as session:
                # Load customers
                customer_repo = CustomerRepository(session)
                self.customers = customer_repo.get_all()

                for customer in self.customers:
                    self.customer_combo.addItem(
                        f"{customer.name} ({customer.phone})",
                        customer.id
                    )

                # Load resources
                resource_repo = ResourceRepository(session)
                self.resources = resource_repo.get_available_resources()

                for resource in self.resources:
                    item = QListWidgetItem(f"{resource.name} (¥{resource.hourly_rate}/小时)")
                    item.setData(Qt.UserRole, resource.id)
                    self.resources_list.addItem(item)

                    # Select default resource if provided
                    if self.default_resource_id and resource.id == self.default_resource_id:
                        item.setSelected(True)

                # Load engineers
                user_repo = UserRepository(session)
                self.engineers = user_repo.get_engineers()

                for engineer in self.engineers:
                    self.engineer_combo.addItem(engineer.full_name, engineer.id)

        except Exception as e:
            logger.error(f"Failed to load dialog data: {e}", exc_info=True)
            QMessageBox.critical(self, "加载失败", f"加载数据失败:\n{str(e)}")

    def load_booking_data(self):
        """Load existing booking data into form."""
        if not self.booking:
            return

        # Set customer
        for i in range(self.customer_combo.count()):
            if self.customer_combo.itemData(i) == self.booking.customer_id:
                self.customer_combo.setCurrentIndex(i)
                break

        # Set times
        self.start_time_edit.setDateTime(self.booking.start_time)
        self.end_time_edit.setDateTime(self.booking.end_time)

        # Set engineer
        if self.booking.engineer_id:
            for i in range(self.engineer_combo.count()):
                if self.engineer_combo.itemData(i) == self.booking.engineer_id:
                    self.engineer_combo.setCurrentIndex(i)
                    break

        # Set status
        if hasattr(self, 'status_combo'):
            for i in range(self.status_combo.count()):
                if self.status_combo.itemData(i) == self.booking.status:
                    self.status_combo.setCurrentIndex(i)
                    break

        # Set notes
        if self.booking.notes:
            self.notes_edit.setPlainText(self.booking.notes)

        # Select resources
        booking_resource_ids = [br.resource_id for br in self.booking.booking_resources]
        for i in range(self.resources_list.count()):
            item = self.resources_list.item(i)
            resource_id = item.data(Qt.UserRole)
            if resource_id in booking_resource_ids:
                item.setSelected(True)

    def update_billing_preview(self):
        """Update billing preview with 15-minute rounding."""
        try:
            start_time = self.start_time_edit.dateTime().toPython()
            end_time = self.end_time_edit.dateTime().toPython()

            # Get selected resources
            selected_items = self.resources_list.selectedItems()
            if not selected_items:
                self.billing_label.setText("请选择至少一个资源")
                return

            # Get resource rates
            room_rate = 0.0
            equipment_rates = []

            for item in selected_items:
                resource_id = item.data(Qt.UserRole)
                resource = next((r for r in self.resources if r.id == resource_id), None)
                if resource:
                    from database.models import ResourceType
                    if resource.resource_type in [ResourceType.RECORDING_ROOM, ResourceType.CONTROL_ROOM]:
                        room_rate += resource.hourly_rate
                    else:
                        equipment_rates.append((resource.hourly_rate, 1))

            # Get engineer rate
            engineer_rate = 0.0
            engineer_id = self.engineer_combo.currentData()
            if engineer_id:
                from config.settings import DEFAULT_ENGINEER_HOURLY_RATE
                engineer_rate = DEFAULT_ENGINEER_HOURLY_RATE

            # Calculate billing estimate
            billing_service = BillingService()
            estimate = billing_service.estimate_billing(
                start_time,
                end_time,
                room_rate,
                engineer_rate,
                equipment_rates
            )

            # Format preview
            preview_text = f"""
<b>时长:</b> {estimate['hours']:.2f} 小时 (15分钟进位后)<br>
<b>房间费用:</b> ¥{estimate['room_charge']:.2f}<br>
<b>工程师费用:</b> ¥{estimate['engineer_charge']:.2f}<br>
<b>设备费用:</b> ¥{estimate['equipment_charge']:.2f}<br>
<b>夜间加价 (22:00-08:00):</b> ¥{estimate['night_surcharge']:.2f}<br>
<hr>
<b>小计:</b> ¥{estimate['subtotal']:.2f}<br>
<b style="color: #e74c3c; font-size: 16px;">总计:</b> <b style="color: #e74c3c; font-size: 16px;">¥{estimate['total']:.2f}</b>
            """.strip()

            self.billing_label.setText(preview_text)

        except Exception as e:
            logger.error(f"Failed to update billing preview: {e}", exc_info=True)
            self.billing_label.setText(f"计费预览失败: {str(e)}")

    def create_booking(self):
        """Create new booking."""
        try:
            # Validate inputs
            customer_id = self.customer_combo.currentData()
            if not customer_id:
                QMessageBox.warning(self, "验证失败", "请选择客户")
                return

            start_time = self.start_time_edit.dateTime().toPython()
            end_time = self.end_time_edit.dateTime().toPython()

            selected_items = self.resources_list.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "验证失败", "请选择至少一个资源")
                return

            resource_ids = [item.data(Qt.UserRole) for item in selected_items]

            engineer_id = self.engineer_combo.currentData()
            notes = self.notes_edit.toPlainText()

            # Create booking
            with db.get_session() as session:
                booking_repo = BookingRepository(session)
                from repositories.audit_repository import AuditLogRepository
                from services.audit_service import AuditService

                audit_repo = AuditLogRepository(session)
                audit_service = AuditService(audit_repo)
                booking_service = BookingService(booking_repo, audit_service)

                booking = booking_service.create_booking(
                    customer_id=customer_id,
                    created_by=self.current_user.id,
                    start_time=start_time,
                    end_time=end_time,
                    resource_ids=resource_ids,
                    engineer_id=engineer_id,
                    notes=notes
                )

                session.commit()

            QMessageBox.information(self, "创建成功", "预约创建成功！")
            logger.info(f"Booking created: {booking.id}")
            self.accept()

        except BookingConflictError as e:
            logger.warning(f"Booking conflict: {e}")
            QMessageBox.warning(self, "预约冲突", str(e))

        except ValueError as e:
            logger.warning(f"Validation error: {e}")
            QMessageBox.warning(self, "验证失败", str(e))

        except Exception as e:
            logger.error(f"Failed to create booking: {e}", exc_info=True)
            QMessageBox.critical(self, "创建失败", f"创建预约失败:\n{str(e)}")

    def save_booking(self):
        """Save booking changes."""
        # TODO: Implement booking update
        QMessageBox.information(self, "提示", "编辑功能开发中...")
        self.accept()

    def delete_booking(self):
        """Delete booking."""
        reply = QMessageBox.question(
            self,
            "确认删除",
            "确定要删除这个预约吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                with db.get_session() as session:
                    booking_repo = BookingRepository(session)
                    from repositories.audit_repository import AuditLogRepository
                    from services.audit_service import AuditService

                    audit_repo = AuditLogRepository(session)
                    audit_service = AuditService(audit_repo)
                    booking_service = BookingService(booking_repo, audit_service)

                    booking_service.cancel_booking(self.booking.id, notes="用户删除")
                    session.commit()

                QMessageBox.information(self, "删除成功", "预约已删除")
                logger.info(f"Booking deleted: {self.booking.id}")
                self.accept()

            except Exception as e:
                logger.error(f"Failed to delete booking: {e}", exc_info=True)
                QMessageBox.critical(self, "删除失败", f"删除预约失败:\n{str(e)}")
