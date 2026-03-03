"""Modern main window with side navigation."""
import logging
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QStackedWidget, QPushButton, QMessageBox, QFrame
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QIcon
from datetime import datetime

from database.models import User, UserRole
from ui.widgets.calendar_widget import CalendarWidget
from ui.widgets.resource_widget import ResourceWidget
from ui.widgets.customer_widget import CustomerWidget
from ui.widgets.billing_widget import BillingWidget
from ui.widgets.statistics_widget import StatisticsWidget
from ui.dialogs.user_dialog import UserManagementDialog

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """Modern main application window with side navigation."""

    def __init__(self, current_user: User, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.setup_ui()
        logger.info(f"Main window opened for user: {current_user.username}")

    def setup_ui(self):
        """Setup modern user interface."""
        self.setWindowTitle("声匠录音棚排班与计费系统")
        self.setMinimumSize(1400, 900)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Top bar
        top_bar = self.create_top_bar()
        main_layout.addWidget(top_bar)

        # Content area with sidebar
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Sidebar
        sidebar = self.create_sidebar()
        content_layout.addWidget(sidebar)

        # Main content
        self.content_stack = QStackedWidget()
        self.setup_content_pages()
        content_layout.addWidget(self.content_stack, stretch=1)

        main_layout.addLayout(content_layout)

        # Status bar
        self.setup_status_bar()

        # Update time every second
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)

        # Apply modern stylesheet
        self.apply_stylesheet()

    def create_top_bar(self) -> QWidget:
        """Create modern top bar with gradient."""
        top_bar = QFrame()
        top_bar.setObjectName("topBar")
        top_bar.setFixedHeight(70)

        layout = QHBoxLayout(top_bar)
        layout.setContentsMargins(20, 10, 20, 10)

        # Logo and title
        title_layout = QVBoxLayout()
        title = QLabel("声匠录音棚")
        title.setObjectName("appTitle")
        title_layout.addWidget(title)

        subtitle = QLabel("排班与计费管理系统")
        subtitle.setObjectName("appSubtitle")
        title_layout.addWidget(subtitle)

        layout.addLayout(title_layout)
        layout.addStretch()

        # User info
        user_info_layout = QVBoxLayout()
        user_info_layout.setAlignment(Qt.AlignRight)

        role_map = {
            UserRole.ADMIN: "管理员",
            UserRole.FRONT_DESK: "前台",
            UserRole.ENGINEER: "工程师"
        }

        user_name = QLabel(self.current_user.full_name)
        user_name.setObjectName("userName")
        user_info_layout.addWidget(user_name)

        user_role = QLabel(f"角色: {role_map.get(self.current_user.role, '未知')}")
        user_role.setObjectName("userRole")
        user_info_layout.addWidget(user_role)

        layout.addLayout(user_info_layout)

        # Logout button
        logout_btn = QPushButton("退出登录")
        logout_btn.setObjectName("logoutButton")
        logout_btn.setFixedSize(100, 40)
        logout_btn.clicked.connect(self.handle_logout)
        layout.addWidget(logout_btn)

        return top_bar

    def create_sidebar(self) -> QWidget:
        """Create modern sidebar navigation."""
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 20, 0, 20)
        layout.setSpacing(5)

        # Navigation buttons
        nav_items = [
            ("📅 预约日历", 0, "calendar"),
            ("🏢 资源管理", 1, "resources"),
            ("👥 客户档案", 2, "customers"),
            ("💰 财务结算", 3, "billing"),
            ("📊 统计报表", 4, "statistics"),
            ("⚙️ 系统设置", 5, "settings"),
        ]

        self.nav_buttons = []
        for text, index, icon_name in nav_items:
            btn = QPushButton(text)
            btn.setObjectName("navButton")
            btn.setFixedHeight(50)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, i=index: self.switch_page(i))
            layout.addWidget(btn)
            self.nav_buttons.append(btn)

        # Set first button as active
        if self.nav_buttons:
            self.nav_buttons[0].setChecked(True)

        layout.addStretch()

        # Version info
        version_label = QLabel("v1.0.0")
        version_label.setObjectName("versionLabel")
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)

        return sidebar

    def setup_content_pages(self):
        """Setup content pages with actual widgets."""
        # Calendar page
        self.calendar_widget = CalendarWidget(self.current_user)
        self.content_stack.addWidget(self.calendar_widget)

        # Resource management page
        self.resource_widget = ResourceWidget(self.current_user)
        self.content_stack.addWidget(self.resource_widget)

        # Customer management page
        self.customer_widget = CustomerWidget(self.current_user)
        self.content_stack.addWidget(self.customer_widget)

        # Billing page
        self.billing_widget = BillingWidget(self.current_user)
        self.content_stack.addWidget(self.billing_widget)

        # Statistics page
        self.statistics_widget = StatisticsWidget(self.current_user)
        self.content_stack.addWidget(self.statistics_widget)

        # Settings page
        settings_page = self.create_settings_page()
        self.content_stack.addWidget(settings_page)

    def create_settings_page(self) -> QWidget:
        """Create settings page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)

        title = QLabel("系统设置")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # User management button (admin only)
        if self.current_user.role == UserRole.ADMIN:
            user_mgmt_btn = QPushButton("用户管理")
            user_mgmt_btn.setFixedSize(200, 50)
            user_mgmt_btn.clicked.connect(self.show_user_management)
            layout.addWidget(user_mgmt_btn)

        # Database backup button (admin only)
        if self.current_user.role == UserRole.ADMIN:
            backup_btn = QPushButton("数据库备份")
            backup_btn.setFixedSize(200, 50)
            backup_btn.clicked.connect(self.handle_backup)
            layout.addWidget(backup_btn)

            # Database restore button (admin only)
            restore_btn = QPushButton("数据库恢复")
            restore_btn.setFixedSize(200, 50)
            restore_btn.clicked.connect(self.handle_restore)
            layout.addWidget(restore_btn)

        layout.addStretch()

        return page

    def switch_page(self, index: int):
        """Switch to page and update button states."""
        self.content_stack.setCurrentIndex(index)

        # Update button states
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)

        logger.info(f"Switched to page: {index}")

    def setup_status_bar(self):
        """Setup modern status bar."""
        self.time_label = QLabel()
        self.time_label.setObjectName("statusLabel")
        self.statusBar().addPermanentWidget(self.time_label)

        self.db_status_label = QLabel("● 数据库已连接")
        self.db_status_label.setObjectName("statusLabelSuccess")
        self.statusBar().addPermanentWidget(self.db_status_label)

        self.update_time()

    def update_time(self):
        """Update current time display."""
        current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
        self.time_label.setText(f"当前时间: {current_time}")

    def show_user_management(self):
        """Show user management dialog."""
        dialog = UserManagementDialog(self)
        dialog.exec()

    def handle_backup(self):
        """Handle database backup."""
        try:
            from utils.file_utils import backup_file
            from config.settings import DATABASE_PATH

            backup_path = backup_file(DATABASE_PATH)

            # Log backup action
            try:
                with db.get_session() as session:
                    from repositories.audit_repository import AuditLogRepository
                    from services.audit_service import AuditService

                    audit_repo = AuditLogRepository(session)
                    audit_service = AuditService(audit_repo)
                    audit_service.log_database_backup(self.current_user.id, backup_path)
                    session.commit()
            except Exception as e:
                logger.warning(f"Failed to log backup action: {e}")

            QMessageBox.information(
                self,
                "备份成功",
                f"数据库已备份至:\n{backup_path}"
            )
            logger.info(f"Database backed up to: {backup_path}")
        except Exception as e:
            logger.error(f"Backup failed: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "备份失败",
                f"数据库备份失败:\n{str(e)}"
            )

    def handle_restore(self):
        """Handle database restore."""
        try:
            from utils.file_utils import restore_file
            from PySide6.QtWidgets import QFileDialog
            from config.settings import DATABASE_PATH
            import os

            # 选择备份文件
            backup_dir = os.path.join(os.path.dirname(DATABASE_PATH), "backups")
            if not os.path.exists(backup_dir):
                QMessageBox.warning(
                    self,
                    "无备份文件",
                    "备份目录不存在，请先进行数据库备份"
                )
                return

            backup_file_path, _ = QFileDialog.getOpenFileName(
                self,
                "选择备份文件",
                backup_dir,
                "数据库备份文件 (*.db)"
            )

            if not backup_file_path:
                return  # 用户取消

            # 二次确认
            reply = QMessageBox.warning(
                self,
                "确认恢复",
                f"确定要从以下备份恢复数据库吗？\n\n{os.path.basename(backup_file_path)}\n\n"
                "警告：当前数据库将被覆盖，此操作不可撤销！\n建议先备份当前数据库。",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply != QMessageBox.Yes:
                return

            # 执行恢复
            restore_file(backup_file_path, DATABASE_PATH)

            # Log restore action
            try:
                with db.get_session() as session:
                    from services.audit_service import AuditService
                    from repositories.audit_repository import AuditLogRepository

                    audit_service = AuditService(AuditLogRepository(session))
                    audit_service.log_database_restore(self.current_user.id, backup_file_path)
            except Exception as e:
                logger.warning(f"Failed to log restore action: {e}")

            QMessageBox.information(
                self,
                "恢复成功",
                f"数据库已从备份恢复:\n{os.path.basename(backup_file_path)}\n\n"
                "请重新启动应用程序以加载恢复的数据。"
            )
            logger.info(f"Database restored from: {backup_file_path}")

            # 提示重启
            reply = QMessageBox.question(
                self,
                "重启应用",
                "是否立即重启应用程序？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )

            if reply == QMessageBox.Yes:
                import sys
                from PySide6.QtWidgets import QApplication
                QApplication.quit()
                os.execl(sys.executable, sys.executable, *sys.argv)

        except Exception as e:
            logger.error(f"Restore failed: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "恢复失败",
                f"数据库恢复失败:\n{str(e)}"
            )

    def handle_logout(self):
        """Handle logout."""
        reply = QMessageBox.question(
            self,
            "确认退出",
            "确定要退出登录吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            logger.info(f"User logged out: {self.current_user.username}")
            self.close()

    def closeEvent(self, event):
        """Handle window close event."""
        reply = QMessageBox.question(
            self,
            "确认退出",
            "确定要退出系统吗？\n未保存的更改将会丢失。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

    def apply_stylesheet(self):
        """Apply modern stylesheet."""
        self.setStyleSheet("""
            /* Main Window */
            QMainWindow {
                background-color: #f5f6fa;
            }

            /* Top Bar */
            #topBar {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                border-bottom: 2px solid #5568d3;
            }

            #appTitle {
                color: white;
                font-size: 24px;
                font-weight: bold;
            }

            #appSubtitle {
                color: rgba(255, 255, 255, 0.9);
                font-size: 14px;
            }

            #userName {
                color: white;
                font-size: 16px;
                font-weight: bold;
            }

            #userRole {
                color: rgba(255, 255, 255, 0.8);
                font-size: 12px;
            }

            #logoutButton {
                background-color: rgba(255, 255, 255, 0.2);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }

            #logoutButton:hover {
                background-color: rgba(255, 255, 255, 0.3);
            }

            #logoutButton:pressed {
                background-color: rgba(255, 255, 255, 0.1);
            }

            /* Sidebar */
            #sidebar {
                background-color: #2c3e50;
                border-right: 1px solid #34495e;
            }

            #navButton {
                background-color: transparent;
                color: #ecf0f1;
                text-align: left;
                padding-left: 20px;
                border: none;
                border-left: 3px solid transparent;
                font-size: 15px;
            }

            #navButton:hover {
                background-color: rgba(52, 73, 94, 0.5);
                border-left: 3px solid #3498db;
            }

            #navButton:checked {
                background-color: #34495e;
                border-left: 3px solid #3498db;
                color: #3498db;
                font-weight: bold;
            }

            #versionLabel {
                color: #7f8c8d;
                font-size: 11px;
                padding: 10px;
            }

            /* Page Title */
            #pageTitle {
                font-size: 28px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 20px;
            }

            /* Status Bar */
            QStatusBar {
                background-color: #ecf0f1;
                border-top: 1px solid #bdc3c7;
            }

            #statusLabel {
                color: #2c3e50;
                font-size: 12px;
                padding: 5px 10px;
            }

            #statusLabelSuccess {
                color: #27ae60;
                font-size: 12px;
                padding: 5px 10px;
                font-weight: bold;
            }

            /* Buttons */
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-size: 14px;
            }

            QPushButton:hover {
                background-color: #2980b9;
            }

            QPushButton:pressed {
                background-color: #21618c;
            }

            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }

            /* Tables */
            QTableWidget {
                background-color: white;
                border: 1px solid #dfe6e9;
                border-radius: 5px;
                gridline-color: #ecf0f1;
            }

            QTableWidget::item {
                padding: 8px;
            }

            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }

            QHeaderView::section {
                background-color: #34495e;
                color: white;
                padding: 10px;
                border: none;
                font-weight: bold;
            }

            /* Input Fields */
            QLineEdit, QTextEdit, QComboBox, QSpinBox, QDoubleSpinBox {
                background-color: white;
                border: 1px solid #dfe6e9;
                border-radius: 5px;
                padding: 8px;
                font-size: 14px;
            }

            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border: 2px solid #3498db;
            }

            /* Labels */
            QLabel {
                color: #2c3e50;
            }
        """)
