"""Statistics and reports widget."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from database.models import User

class StatisticsWidget(QWidget):
    """Widget for statistics and reports."""

    def __init__(self, current_user: User, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.setup_ui()

    def setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("统计报表")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        info = QLabel("功能开发中...\n\n将包括:\n• 房间利用率\n• 设备租赁收入\n• 工程师工时排行\n• 日/周/月报表\n• 数据导出")
        info.setStyleSheet("font-size: 16px; color: #7f8c8d;")
        layout.addWidget(info)

        layout.addStretch()
