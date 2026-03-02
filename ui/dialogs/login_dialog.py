"""Login dialog for user authentication."""
import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QFormLayout
)
from PySide6.QtCore import Qt

from database.connection import db
from repositories.user_repository import UserRepository
from services.auth_service import AuthService, AuthenticationError, AccountLockedError

logger = logging.getLogger(__name__)

class LoginDialog(QDialog):
    """Login dialog for user authentication."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_user = None
        self.setup_ui()

    def setup_ui(self):
        """Setup user interface."""
        self.setWindowTitle("登录 - 声匠录音棚排班与计费系统")
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QVBoxLayout()

        # Title
        title_label = QLabel("声匠录音棚排班与计费系统")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; margin: 20px;")
        layout.addWidget(title_label)

        # Form
        form_layout = QFormLayout()

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("请输入用户名")
        form_layout.addRow("用户名:", self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("请输入密码")
        self.password_input.returnPressed.connect(self.handle_login)
        form_layout.addRow("密码:", self.password_input)

        layout.addLayout(form_layout)

        # Buttons
        button_layout = QHBoxLayout()

        self.login_button = QPushButton("登录")
        self.login_button.clicked.connect(self.handle_login)
        self.login_button.setDefault(True)
        button_layout.addWidget(self.login_button)

        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

        # Info label
        self.info_label = QLabel()
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("color: #666; margin-top: 10px;")
        self.info_label.setText("提示：首次使用请联系管理员创建账号")
        layout.addWidget(self.info_label)

        self.setLayout(layout)

    def handle_login(self):
        """Handle login button click."""
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(self, "登录失败", "请输入用户名和密码")
            return

        try:
            # Authenticate user
            with db.get_session() as session:
                user_repo = UserRepository(session)
                from repositories.audit_repository import AuditLogRepository
                from services.audit_service import AuditService

                audit_repo = AuditLogRepository(session)
                audit_service = AuditService(audit_repo)
                auth_service = AuthService(user_repo, audit_service)

                user = auth_service.login(username, password)
                self.current_user = user

                logger.info(f"Login successful: {username}")
                self.accept()

        except AccountLockedError as e:
            logger.warning(f"Login failed - account locked: {username}")
            QMessageBox.critical(self, "账号已锁定", str(e))
            self.password_input.clear()

        except AuthenticationError as e:
            logger.warning(f"Login failed - authentication error: {username}")
            QMessageBox.warning(self, "登录失败", str(e))
            self.password_input.clear()
            self.password_input.setFocus()

        except Exception as e:
            logger.error(f"Login error: {e}", exc_info=True)
            QMessageBox.critical(self, "系统错误", f"登录时发生错误：{str(e)}")
