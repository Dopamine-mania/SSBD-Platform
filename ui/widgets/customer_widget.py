"""Customer management widget."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from database.models import User

class CustomerWidget(QWidget):
    """Widget for managing customers."""

    def __init__(self, current_user: User, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.setup_ui()

    def setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("客户档案")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        info = QLabel("功能开发中...\n\n将包括:\n• 客户信息管理\n• 联系方式\n• 偏好设置\n• 预约历史\n• 搜索功能")
        info.setStyleSheet("font-size: 16px; color: #7f8c8d;")
        layout.addWidget(info)

        layout.addStretch()
