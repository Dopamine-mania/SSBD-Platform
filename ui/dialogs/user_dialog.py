"""User management dialog."""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QMessageBox
from database.models import User

class UserManagementDialog(QDialog):
    """Dialog for user management."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Setup user interface."""
        self.setWindowTitle("用户管理")
        self.setMinimumSize(600, 400)

        layout = QVBoxLayout(self)

        title = QLabel("用户管理")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        info = QLabel("功能开发中...\n\n将包括:\n• 用户列表\n• 添加用户\n• 编辑用户\n• 禁用/启用用户\n• 重置密码")
        info.setStyleSheet("font-size: 14px; color: #7f8c8d;")
        layout.addWidget(info)

        layout.addStretch()
