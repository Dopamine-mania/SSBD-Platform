"""Billing and settlement widget."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from database.models import User

class BillingWidget(QWidget):
    """Widget for billing and settlement."""

    def __init__(self, current_user: User, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.setup_ui()

    def setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("财务结算")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        info = QLabel("功能开发中...\n\n将包括:\n• 订单生成\n• 支付处理 (现金/微信/支付宝)\n• 退款审批\n• 小票打印\n• 开票信息")
        info.setStyleSheet("font-size: 16px; color: #7f8c8d;")
        layout.addWidget(info)

        layout.addStretch()
