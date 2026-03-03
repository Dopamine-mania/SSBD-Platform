"""Customer management widget."""
import logging
import re
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QFormLayout, QLineEdit, QTextEdit
)
from PySide6.QtCore import Qt

from database.models import User, Customer
from database.connection import db
from repositories.customer_repository import CustomerRepository

logger = logging.getLogger(__name__)


class CustomerWidget(QWidget):
    """Widget for managing customers."""

    def __init__(self, current_user: User, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.customers = []
        self.setup_ui()
        self.load_customers()

    def setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Title and toolbar
        header_layout = QHBoxLayout()

        title = QLabel("客户档案")
        title.setObjectName("pageTitle")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Add customer button
        add_btn = QPushButton("➕ 添加客户")
        add_btn.setFixedSize(120, 40)
        add_btn.clicked.connect(self.add_customer)
        header_layout.addWidget(add_btn)

        layout.addLayout(header_layout)

        # Search bar
        search_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索客户姓名或电话...")
        self.search_input.setFixedWidth(300)
        self.search_input.textChanged.connect(self.filter_customers)
        search_layout.addWidget(QLabel("搜索:"))
        search_layout.addWidget(self.search_input)

        search_layout.addStretch()

        layout.addLayout(search_layout)

        # Customer table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "ID", "姓名", "电话", "邮箱", "偏好", "操作"
        ])

        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        self.table.setColumnWidth(5, 150)

        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)

    def load_customers(self):
        """Load all customers from database."""
        try:
            with db.get_session() as session:
                repo = CustomerRepository(session)
                self.customers = repo.get_all()
                self.populate_table(self.customers)
                logger.info(f"Loaded {len(self.customers)} customers")
        except Exception as e:
            logger.error(f"Failed to load customers: {e}", exc_info=True)
            QMessageBox.critical(self, "加载失败", f"加载客户列表失败:\n{str(e)}")

    def populate_table(self, customers):
        """Populate table with customers."""
        self.table.setRowCount(0)

        for customer in customers:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # ID
            self.table.setItem(row, 0, QTableWidgetItem(str(customer.id)))

            # Name
            self.table.setItem(row, 1, QTableWidgetItem(customer.name))

            # Phone
            self.table.setItem(row, 2, QTableWidgetItem(customer.phone))

            # Email
            email_text = customer.email or "-"
            self.table.setItem(row, 3, QTableWidgetItem(email_text))

            # Preferences
            preferences_text = customer.preferences[:30] + "..." if customer.preferences and len(customer.preferences) > 30 else (customer.preferences or "-")
            self.table.setItem(row, 4, QTableWidgetItem(preferences_text))

            # Action buttons
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(5, 2, 5, 2)
            action_layout.setSpacing(5)

            edit_btn = QPushButton("编辑")
            edit_btn.setFixedSize(60, 30)
            edit_btn.clicked.connect(lambda checked, c=customer: self.edit_customer(c))
            action_layout.addWidget(edit_btn)

            delete_btn = QPushButton("删除")
            delete_btn.setFixedSize(60, 30)
            delete_btn.setStyleSheet("background-color: #e74c3c;")
            delete_btn.clicked.connect(lambda checked, c=customer: self.delete_customer(c))
            action_layout.addWidget(delete_btn)

            self.table.setCellWidget(row, 5, action_widget)

    def filter_customers(self):
        """Filter customers based on search text."""
        search_text = self.search_input.text().strip().lower()

        if not search_text:
            self.populate_table(self.customers)
            return

        filtered = []
        for customer in self.customers:
            # Search in name or phone
            if search_text in customer.name.lower() or search_text in customer.phone:
                filtered.append(customer)

        self.populate_table(filtered)

    def add_customer(self):
        """Show dialog to add new customer."""
        dialog = CustomerDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.load_customers()

    def edit_customer(self, customer: Customer):
        """Show dialog to edit customer."""
        dialog = CustomerDialog(self, customer)
        if dialog.exec() == QDialog.Accepted:
            self.load_customers()

    def delete_customer(self, customer: Customer):
        """Delete customer with confirmation."""
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除客户 '{customer.name}' 吗？\n此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                with db.get_session() as session:
                    repo = CustomerRepository(session)
                    repo.delete(customer.id)
                    session.commit()

                QMessageBox.information(self, "删除成功", f"客户 '{customer.name}' 已删除")
                logger.info(f"Customer deleted: {customer.name} (ID: {customer.id})")
                self.load_customers()
            except Exception as e:
                logger.error(f"Failed to delete customer: {e}", exc_info=True)
                QMessageBox.critical(self, "删除失败", f"删除客户失败:\n{str(e)}")


class CustomerDialog(QDialog):
    """Dialog for adding/editing customers."""

    # Email validation regex
    EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    # Phone validation regex (11 digits)
    PHONE_REGEX = re.compile(r'^\d{11}$')

    def __init__(self, parent=None, customer: Optional[Customer] = None):
        super().__init__(parent)
        self.customer = customer
        self.setup_ui()

        if customer:
            self.load_customer_data()

    def setup_ui(self):
        """Setup user interface."""
        self.setWindowTitle("编辑客户" if self.customer else "添加客户")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        # Title
        title = QLabel("编辑客户信息" if self.customer else "添加新客户")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        # Form
        form_layout = QFormLayout()

        # Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("请输入客户姓名")
        form_layout.addRow("姓名*:", self.name_input)

        # Phone
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("请输入11位手机号码")
        self.phone_input.setMaxLength(11)
        form_layout.addRow("电话*:", self.phone_input)

        # Email
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("例如: example@email.com")
        form_layout.addRow("邮箱:", self.email_input)

        # Preferences
        self.preferences_input = QTextEdit()
        self.preferences_input.setPlaceholderText("记录客户的偏好设置、特殊需求等...")
        self.preferences_input.setMaximumHeight(100)
        form_layout.addRow("偏好:", self.preferences_input)

        layout.addLayout(form_layout)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        save_btn = QPushButton("保存")
        save_btn.setFixedSize(100, 40)
        save_btn.clicked.connect(self.save_customer)
        button_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(100, 40)
        cancel_btn.setStyleSheet("background-color: #95a5a6;")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def load_customer_data(self):
        """Load customer data into form."""
        self.name_input.setText(self.customer.name)
        self.phone_input.setText(self.customer.phone)

        if self.customer.email:
            self.email_input.setText(self.customer.email)

        if self.customer.preferences:
            self.preferences_input.setText(self.customer.preferences)

    def validate_phone(self, phone: str) -> bool:
        """Validate phone number format.

        Args:
            phone: Phone number to validate

        Returns:
            True if valid, False otherwise
        """
        return bool(self.PHONE_REGEX.match(phone))

    def validate_email(self, email: str) -> bool:
        """Validate email format.

        Args:
            email: Email to validate

        Returns:
            True if valid, False otherwise
        """
        return bool(self.EMAIL_REGEX.match(email))

    def save_customer(self):
        """Save customer to database."""
        # Get form data
        name = self.name_input.text().strip()
        phone = self.phone_input.text().strip()
        email = self.email_input.text().strip()
        preferences = self.preferences_input.toPlainText().strip()

        # Validate required fields
        if not name:
            QMessageBox.warning(self, "验证失败", "请输入客户姓名")
            self.name_input.setFocus()
            return

        if not phone:
            QMessageBox.warning(self, "验证失败", "请输入客户电话")
            self.phone_input.setFocus()
            return

        # Validate phone format
        if not self.validate_phone(phone):
            QMessageBox.warning(self, "验证失败", "电话号码格式不正确\n请输入11位数字")
            self.phone_input.setFocus()
            return

        # Validate email format if provided
        if email and not self.validate_email(email):
            QMessageBox.warning(self, "验证失败", "邮箱格式不正确\n请输入有效的邮箱地址")
            self.email_input.setFocus()
            return

        try:
            with db.get_session() as session:
                repo = CustomerRepository(session)

                # Check if phone already exists (for new customer or different customer)
                existing = repo.get_by_phone(phone)
                if existing and (not self.customer or existing.id != self.customer.id):
                    QMessageBox.warning(
                        self,
                        "验证失败",
                        f"电话号码 {phone} 已被客户 '{existing.name}' 使用"
                    )
                    self.phone_input.setFocus()
                    return

                if self.customer:
                    # Update existing customer
                    self.customer.name = name
                    self.customer.phone = phone
                    self.customer.email = email or None
                    self.customer.preferences = preferences or None

                    repo.update(self.customer)
                    logger.info(f"Customer updated: {name} (ID: {self.customer.id})")
                else:
                    # Create new customer
                    new_customer = Customer(
                        name=name,
                        phone=phone,
                        email=email or None,
                        preferences=preferences or None
                    )
                    repo.create(new_customer)
                    logger.info(f"Customer created: {name}")

                session.commit()

            QMessageBox.information(
                self,
                "保存成功",
                f"客户 '{name}' 已{'更新' if self.customer else '创建'}"
            )
            self.accept()

        except Exception as e:
            logger.error(f"Failed to save customer: {e}", exc_info=True)
            QMessageBox.critical(self, "保存失败", f"保存客户失败:\n{str(e)}")

