"""Billing and settlement widget."""
import logging
from typing import Optional
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QFormLayout, QLineEdit, QTextEdit, QComboBox,
    QTabWidget, QDialogButtonBox
)
from PySide6.QtCore import Qt
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
from PySide6.QtGui import QPainter, QFont

from database.models import User, Order, Booking, PaymentMethod, OrderStatus, UserRole
from database.connection import db
from repositories.order_repository import OrderRepository
from repositories.booking_repository import BookingRepository

logger = logging.getLogger(__name__)


class BillingWidget(QWidget):
    """Widget for billing and settlement."""

    def __init__(self, current_user: User, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.pending_bookings = []
        self.orders = []
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Title
        title = QLabel("财务结算")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.create_pending_tab(), "待结算预约")
        self.tab_widget.addTab(self.create_orders_tab(), "订单历史")
        layout.addWidget(self.tab_widget)

    def create_pending_tab(self) -> QWidget:
        """Create pending bookings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # Info label
        info = QLabel("以下是已完成但尚未生成订单的预约")
        info.setStyleSheet("font-size: 14px; color: #7f8c8d;")
        layout.addWidget(info)

        # Pending bookings table
        self.pending_table = QTableWidget()
        self.pending_table.setColumnCount(7)
        self.pending_table.setHorizontalHeaderLabels([
            "预约ID", "客户", "开始时间", "结束时间", "工程师", "资源", "操作"
        ])

        # Set column widths
        header = self.pending_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        header.setSectionResizeMode(6, QHeaderView.Fixed)
        self.pending_table.setColumnWidth(6, 120)

        self.pending_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.pending_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.pending_table.setAlternatingRowColors(True)

        layout.addWidget(self.pending_table)

        return widget

    def create_orders_tab(self) -> QWidget:
        """Create orders history tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # Toolbar
        toolbar = QHBoxLayout()

        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setFixedSize(100, 35)
        refresh_btn.clicked.connect(self.load_data)
        toolbar.addWidget(refresh_btn)

        toolbar.addStretch()

        layout.addLayout(toolbar)

        # Orders table
        self.orders_table = QTableWidget()
        self.orders_table.setColumnCount(9)
        self.orders_table.setHorizontalHeaderLabels([
            "订单ID", "预约ID", "客户", "总额", "支付方式", "状态", "创建时间", "备注", "操作"
        ])

        # Set column widths
        header = self.orders_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Stretch)
        header.setSectionResizeMode(7, QHeaderView.Stretch)
        header.setSectionResizeMode(8, QHeaderView.Fixed)
        self.orders_table.setColumnWidth(8, 180)

        self.orders_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.orders_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.orders_table.setAlternatingRowColors(True)

        layout.addWidget(self.orders_table)

        return widget

    def load_data(self):
        """Load pending bookings and orders."""
        self.load_pending_bookings()
        self.load_orders()

    def load_pending_bookings(self):
        """Load completed bookings without orders."""
        try:
            with db.get_session() as session:
                repo = OrderRepository(session)
                self.pending_bookings = repo.get_completed_bookings_without_order()
                self.populate_pending_table()
                logger.info(f"Loaded {len(self.pending_bookings)} pending bookings")
        except Exception as e:
            logger.error(f"Failed to load pending bookings: {e}", exc_info=True)
            QMessageBox.critical(self, "加载失败", f"加载待结算预约失败:\n{str(e)}")

    def populate_pending_table(self):
        """Populate pending bookings table."""
        self.pending_table.setRowCount(0)

        for booking in self.pending_bookings:
            row = self.pending_table.rowCount()
            self.pending_table.insertRow(row)

            # Booking ID
            self.pending_table.setItem(row, 0, QTableWidgetItem(str(booking.id)))

            # Customer
            customer_name = booking.customer.name if booking.customer else "-"
            self.pending_table.setItem(row, 1, QTableWidgetItem(customer_name))

            # Start time
            start_time = booking.start_time.strftime("%Y-%m-%d %H:%M")
            self.pending_table.setItem(row, 2, QTableWidgetItem(start_time))

            # End time
            end_time = booking.end_time.strftime("%Y-%m-%d %H:%M")
            self.pending_table.setItem(row, 3, QTableWidgetItem(end_time))

            # Engineer
            engineer_name = booking.engineer_user.full_name if booking.engineer_user else "-"
            self.pending_table.setItem(row, 4, QTableWidgetItem(engineer_name))

            # Resources
            resources = ", ".join([br.resource.name for br in booking.booking_resources])
            self.pending_table.setItem(row, 5, QTableWidgetItem(resources))

            # Action button
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(5, 2, 5, 2)

            create_btn = QPushButton("生成订单")
            create_btn.setFixedSize(100, 30)
            create_btn.clicked.connect(lambda checked, b=booking: self.create_order(b))
            action_layout.addWidget(create_btn)

            self.pending_table.setCellWidget(row, 6, action_widget)

    def load_orders(self):
        """Load all orders."""
        try:
            with db.get_session() as session:
                repo = OrderRepository(session)
                self.orders = repo.get_all()
                self.populate_orders_table()
                logger.info(f"Loaded {len(self.orders)} orders")
        except Exception as e:
            logger.error(f"Failed to load orders: {e}", exc_info=True)
            QMessageBox.critical(self, "加载失败", f"加载订单历史失败:\n{str(e)}")

    def populate_orders_table(self):
        """Populate orders table."""
        self.orders_table.setRowCount(0)

        for order in self.orders:
            row = self.orders_table.rowCount()
            self.orders_table.insertRow(row)

            # Order ID
            self.orders_table.setItem(row, 0, QTableWidgetItem(str(order.id)))

            # Booking ID
            self.orders_table.setItem(row, 1, QTableWidgetItem(str(order.booking_id)))

            # Customer
            customer_name = order.booking.customer.name if order.booking and order.booking.customer else "-"
            self.orders_table.setItem(row, 2, QTableWidgetItem(customer_name))

            # Total
            total_item = QTableWidgetItem(f"¥{order.total:.2f}")
            total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.orders_table.setItem(row, 3, total_item)

            # Payment method
            payment_text = self.get_payment_method_text(order.payment_method) if order.payment_method else "-"
            self.orders_table.setItem(row, 4, QTableWidgetItem(payment_text))

            # Status
            status_text = self.get_order_status_text(order.status)
            status_item = QTableWidgetItem(status_text)
            if order.status == OrderStatus.PAID:
                status_item.setForeground(Qt.darkGreen)
            elif order.status == OrderStatus.REFUNDED:
                status_item.setForeground(Qt.red)
            self.orders_table.setItem(row, 5, status_item)

            # Created at
            created_at = order.created_at.strftime("%Y-%m-%d %H:%M")
            self.orders_table.setItem(row, 6, QTableWidgetItem(created_at))

            # Invoice notes
            notes_text = order.invoice_notes[:20] + "..." if order.invoice_notes and len(order.invoice_notes) > 20 else (order.invoice_notes or "-")
            self.orders_table.setItem(row, 7, QTableWidgetItem(notes_text))

            # Action buttons
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(5, 2, 5, 2)
            action_layout.setSpacing(5)

            if order.status == OrderStatus.PENDING:
                pay_btn = QPushButton("支付")
                pay_btn.setFixedSize(55, 30)
                pay_btn.clicked.connect(lambda checked, o=order: self.process_payment(o))
                action_layout.addWidget(pay_btn)

            if order.status == OrderStatus.PAID:
                print_btn = QPushButton("打印")
                print_btn.setFixedSize(55, 30)
                print_btn.clicked.connect(lambda checked, o=order: self.print_receipt(o))
                action_layout.addWidget(print_btn)

                refund_btn = QPushButton("退款")
                refund_btn.setFixedSize(55, 30)
                refund_btn.setStyleSheet("background-color: #e74c3c;")
                refund_btn.clicked.connect(lambda checked, o=order: self.process_refund(o))
                action_layout.addWidget(refund_btn)

            self.orders_table.setCellWidget(row, 8, action_widget)

    def create_order(self, booking: Booking):
        """Create order from booking."""
        dialog = CreateOrderDialog(booking, self)
        if dialog.exec() == QDialog.Accepted:
            self.load_data()

    def process_payment(self, order: Order):
        """Process payment for order."""
        dialog = PaymentDialog(order, self)
        if dialog.exec() == QDialog.Accepted:
            self.load_data()

    def process_refund(self, order: Order):
        """Process refund for order."""
        # Check admin permission
        if self.current_user.role != UserRole.ADMIN:
            QMessageBox.warning(self, "权限不足", "只有管理员可以执行退款操作")
            return

        dialog = RefundDialog(order, self.current_user, self)
        if dialog.exec() == QDialog.Accepted:
            self.load_data()

    def print_receipt(self, order: Order):
        """Print receipt for order."""
        try:
            printer = QPrinter(QPrinter.HighResolution)
            dialog = QPrintDialog(printer, self)

            if dialog.exec() == QDialog.Accepted:
                self.render_receipt(printer, order)
                QMessageBox.information(self, "打印成功", "小票已发送到打印机")
        except Exception as e:
            logger.error(f"Failed to print receipt: {e}", exc_info=True)
            QMessageBox.critical(self, "打印失败", f"打印小票失败:\n{str(e)}")

    def render_receipt(self, printer: QPrinter, order: Order):
        """Render receipt content to printer."""
        painter = QPainter(printer)

        try:
            # Get page dimensions
            page_rect = printer.pageRect(QPrinter.DevicePixel)
            width = int(page_rect.width())
            y = 50

            # Title font
            title_font = QFont("SimHei", 16, QFont.Bold)
            painter.setFont(title_font)
            painter.drawText(0, y, width, 50, Qt.AlignCenter, "MindFlow 录音棚")
            y += 60

            # Normal font
            normal_font = QFont("SimHei", 10)
            painter.setFont(normal_font)

            # Order info
            painter.drawText(50, y, width - 100, 30, Qt.AlignLeft, f"订单号: {order.id}")
            y += 35

            if order.booking and order.booking.customer:
                painter.drawText(50, y, width - 100, 30, Qt.AlignLeft, f"客户: {order.booking.customer.name}")
                y += 35

            painter.drawText(50, y, width - 100, 30, Qt.AlignLeft, f"时间: {order.created_at.strftime('%Y-%m-%d %H:%M')}")
            y += 50

            # Separator
            painter.drawLine(50, y, width - 50, y)
            y += 30

            # Order details
            painter.drawText(50, y, width - 100, 30, Qt.AlignLeft, "费用明细:")
            y += 35

            if order.room_charge > 0:
                painter.drawText(70, y, width - 120, 30, Qt.AlignLeft, f"录音棚费用: ¥{order.room_charge:.2f}")
                y += 30

            if order.engineer_charge > 0:
                painter.drawText(70, y, width - 120, 30, Qt.AlignLeft, f"工程师费用: ¥{order.engineer_charge:.2f}")
                y += 30

            if order.equipment_charge > 0:
                painter.drawText(70, y, width - 120, 30, Qt.AlignLeft, f"设备费用: ¥{order.equipment_charge:.2f}")
                y += 30

            if order.night_surcharge > 0:
                painter.drawText(70, y, width - 120, 30, Qt.AlignLeft, f"夜间加收: ¥{order.night_surcharge:.2f}")
                y += 30

            y += 20

            # Separator
            painter.drawLine(50, y, width - 50, y)
            y += 30

            # Total
            bold_font = QFont("SimHei", 12, QFont.Bold)
            painter.setFont(bold_font)
            painter.drawText(50, y, width - 100, 30, Qt.AlignLeft, f"总计: ¥{order.total:.2f}")
            y += 40

            # Payment info
            painter.setFont(normal_font)
            if order.payment_method:
                payment_text = self.get_payment_method_text(order.payment_method)
                painter.drawText(50, y, width - 100, 30, Qt.AlignLeft, f"支付方式: {payment_text}")
                y += 30

            if order.paid_at:
                painter.drawText(50, y, width - 100, 30, Qt.AlignLeft, f"支付时间: {order.paid_at.strftime('%Y-%m-%d %H:%M')}")
                y += 30

            # Invoice notes
            if order.invoice_notes:
                y += 20
                painter.drawText(50, y, width - 100, 30, Qt.AlignLeft, "开票备注:")
                y += 30
                painter.drawText(70, y, width - 120, 100, Qt.AlignLeft | Qt.TextWordWrap, order.invoice_notes)

            y += 80

            # Footer
            painter.drawText(0, y, width, 30, Qt.AlignCenter, "感谢您的光临！")

        finally:
            painter.end()

    @staticmethod
    def get_payment_method_text(method: PaymentMethod) -> str:
        """Get Chinese text for payment method."""
        mapping = {
            PaymentMethod.CASH: "现金",
            PaymentMethod.WECHAT: "微信",
            PaymentMethod.ALIPAY: "支付宝"
        }
        return mapping.get(method, str(method))

    @staticmethod
    def get_order_status_text(status: OrderStatus) -> str:
        """Get Chinese text for order status."""
        mapping = {
            OrderStatus.PENDING: "待支付",
            OrderStatus.PAID: "已支付",
            OrderStatus.REFUNDED: "已退款"
        }
        return mapping.get(status, str(status))


class CreateOrderDialog(QDialog):
    """Dialog for creating order from booking."""

    def __init__(self, booking: Booking, parent=None):
        super().__init__(parent)
        self.booking = booking
        self.setWindowTitle("生成订单")
        self.setMinimumWidth(500)
        self.setup_ui()
        self.calculate_charges()

    def setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)

        # Booking info
        info_label = QLabel(f"预约ID: {self.booking.id}\n客户: {self.booking.customer.name if self.booking.customer else '-'}")
        info_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(info_label)

        # Form
        form = QFormLayout()

        self.room_charge_input = QLineEdit()
        self.room_charge_input.setPlaceholderText("0.00")
        self.room_charge_input.textChanged.connect(self.calculate_total)
        form.addRow("录音棚费用:", self.room_charge_input)

        self.engineer_charge_input = QLineEdit()
        self.engineer_charge_input.setPlaceholderText("0.00")
        self.engineer_charge_input.textChanged.connect(self.calculate_total)
        form.addRow("工程师费用:", self.engineer_charge_input)

        self.equipment_charge_input = QLineEdit()
        self.equipment_charge_input.setPlaceholderText("0.00")
        self.equipment_charge_input.textChanged.connect(self.calculate_total)
        form.addRow("设备费用:", self.equipment_charge_input)

        self.night_surcharge_input = QLineEdit()
        self.night_surcharge_input.setPlaceholderText("0.00")
        self.night_surcharge_input.textChanged.connect(self.calculate_total)
        form.addRow("夜间加收:", self.night_surcharge_input)

        self.total_label = QLabel("¥0.00")
        self.total_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #27ae60;")
        form.addRow("总计:", self.total_label)

        self.invoice_notes_input = QTextEdit()
        self.invoice_notes_input.setPlaceholderText("开票信息备注（可选）")
        self.invoice_notes_input.setMaximumHeight(80)
        form.addRow("开票备注:", self.invoice_notes_input)

        layout.addLayout(form)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept_order)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def calculate_charges(self):
        """Calculate charges based on booking."""
        try:
            # Calculate duration in hours
            duration = (self.booking.end_time - self.booking.start_time).total_seconds() / 3600

            # Calculate room charge
            room_charge = 0.0
            for br in self.booking.booking_resources:
                if br.resource.resource_type.value in ['recording_room', 'control_room']:
                    room_charge += br.resource.hourly_rate * duration * br.quantity

            # Calculate equipment charge
            equipment_charge = 0.0
            for br in self.booking.booking_resources:
                if br.resource.resource_type.value not in ['recording_room', 'control_room']:
                    equipment_charge += br.resource.hourly_rate * duration * br.quantity

            # Engineer charge (if assigned)
            engineer_charge = 0.0
            if self.booking.engineer_id:
                engineer_charge = 100.0 * duration  # Default rate

            # Night surcharge (22:00-08:00 +20%)
            night_surcharge = 0.0
            start_hour = self.booking.start_time.hour
            end_hour = self.booking.end_time.hour
            if start_hour >= 22 or start_hour < 8 or end_hour >= 22 or end_hour < 8:
                night_surcharge = (room_charge + equipment_charge + engineer_charge) * 0.2

            # Set values
            self.room_charge_input.setText(f"{room_charge:.2f}")
            self.engineer_charge_input.setText(f"{engineer_charge:.2f}")
            self.equipment_charge_input.setText(f"{equipment_charge:.2f}")
            self.night_surcharge_input.setText(f"{night_surcharge:.2f}")

        except Exception as e:
            logger.error(f"Failed to calculate charges: {e}", exc_info=True)

    def calculate_total(self):
        """Calculate total from inputs."""
        try:
            room = float(self.room_charge_input.text() or 0)
            engineer = float(self.engineer_charge_input.text() or 0)
            equipment = float(self.equipment_charge_input.text() or 0)
            night = float(self.night_surcharge_input.text() or 0)

            total = room + engineer + equipment + night
            self.total_label.setText(f"¥{total:.2f}")
        except ValueError:
            self.total_label.setText("¥0.00")

    def accept_order(self):
        """Create order and accept dialog."""
        try:
            room_charge = float(self.room_charge_input.text() or 0)
            engineer_charge = float(self.engineer_charge_input.text() or 0)
            equipment_charge = float(self.equipment_charge_input.text() or 0)
            night_surcharge = float(self.night_surcharge_input.text() or 0)

            subtotal = room_charge + engineer_charge + equipment_charge
            total = subtotal + night_surcharge

            if total <= 0:
                QMessageBox.warning(self, "输入错误", "订单总额必须大于0")
                return

            invoice_notes = self.invoice_notes_input.toPlainText().strip()

            with db.get_session() as session:
                repo = OrderRepository(session)
                order = repo.create(
                    booking_id=self.booking.id,
                    room_charge=room_charge,
                    engineer_charge=engineer_charge,
                    equipment_charge=equipment_charge,
                    night_surcharge=night_surcharge,
                    subtotal=subtotal,
                    total=total,
                    invoice_notes=invoice_notes if invoice_notes else None
                )
                session.commit()

            QMessageBox.information(self, "创建成功", f"订单 #{order.id} 已创建")
            logger.info(f"Order created: {order.id} for booking {self.booking.id}")
            self.accept()

        except ValueError:
            QMessageBox.warning(self, "输入错误", "请输入有效的数字")
        except Exception as e:
            logger.error(f"Failed to create order: {e}", exc_info=True)
            QMessageBox.critical(self, "创建失败", f"创建订单失败:\n{str(e)}")


class PaymentDialog(QDialog):
    """Dialog for processing payment."""

    def __init__(self, order: Order, parent=None):
        super().__init__(parent)
        self.order = order
        self.setWindowTitle("处理支付")
        self.setMinimumWidth(400)
        self.setup_ui()

    def setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)

        # Order info
        info_label = QLabel(f"订单ID: {self.order.id}\n总额: ¥{self.order.total:.2f}")
        info_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(info_label)

        # Form
        form = QFormLayout()

        self.payment_method_combo = QComboBox()
        self.payment_method_combo.addItem("现金", PaymentMethod.CASH)
        self.payment_method_combo.addItem("微信", PaymentMethod.WECHAT)
        self.payment_method_combo.addItem("支付宝", PaymentMethod.ALIPAY)
        form.addRow("支付方式:", self.payment_method_combo)

        layout.addLayout(form)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept_payment)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def accept_payment(self):
        """Process payment and accept dialog."""
        try:
            payment_method = self.payment_method_combo.currentData()

            with db.get_session() as session:
                repo = OrderRepository(session)
                order = repo.get_by_id(self.order.id)
                if not order:
                    QMessageBox.warning(self, "错误", "订单不存在")
                    return

                if order.status != OrderStatus.PENDING:
                    QMessageBox.warning(self, "错误", "订单状态不正确")
                    return

                repo.mark_as_paid(order, payment_method)
                session.commit()

            QMessageBox.information(self, "支付成功", f"订单 #{self.order.id} 已支付")
            logger.info(f"Order paid: {self.order.id} via {payment_method}")
            self.accept()

        except Exception as e:
            logger.error(f"Failed to process payment: {e}", exc_info=True)
            QMessageBox.critical(self, "支付失败", f"处理支付失败:\n{str(e)}")


class RefundDialog(QDialog):
    """Dialog for processing refund with admin confirmation."""

    def __init__(self, order: Order, current_user: User, parent=None):
        super().__init__(parent)
        self.order = order
        self.current_user = current_user
        self.setWindowTitle("退款确认")
        self.setMinimumWidth(400)
        self.setup_ui()

    def setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)

        # Warning
        warning_label = QLabel("⚠️ 退款操作需要管理员确认")
        warning_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #e74c3c;")
        layout.addWidget(warning_label)

        # Order info
        info_label = QLabel(f"订单ID: {self.order.id}\n总额: ¥{self.order.total:.2f}")
        info_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(info_label)

        # Confirmation text
        confirm_label = QLabel("确认要退款此订单吗？此操作不可撤销。")
        layout.addWidget(confirm_label)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept_refund)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def accept_refund(self):
        """Process refund and accept dialog."""
        try:
            # Double check admin permission
            if self.current_user.role != UserRole.ADMIN:
                QMessageBox.warning(self, "权限不足", "只有管理员可以执行退款操作")
                return

            with db.get_session() as session:
                repo = OrderRepository(session)
                order = repo.get_by_id(self.order.id)
                if not order:
                    QMessageBox.warning(self, "错误", "订单不存在")
                    return

                if order.status != OrderStatus.PAID:
                    QMessageBox.warning(self, "错误", "只能退款已支付的订单")
                    return

                repo.mark_as_refunded(order, self.current_user.id)
                session.commit()

            QMessageBox.information(self, "退款成功", f"订单 #{self.order.id} 已退款")
            logger.info(f"Order refunded: {self.order.id} by {self.current_user.username}")
            self.accept()

        except Exception as e:
            logger.error(f"Failed to process refund: {e}", exc_info=True)
            QMessageBox.critical(self, "退款失败", f"处理退款失败:\n{str(e)}")

