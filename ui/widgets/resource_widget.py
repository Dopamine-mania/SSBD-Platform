"""Resource management widget."""
import logging
import os
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QFormLayout, QLineEdit, QComboBox, QTextEdit,
    QFileDialog, QDoubleSpinBox, QGroupBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from database.models import User, Resource, ResourceType, ResourceStatus
from database.connection import db
from repositories.resource_repository import ResourceRepository

logger = logging.getLogger(__name__)

class ResourceWidget(QWidget):
    """Widget for managing resources."""

    def __init__(self, current_user: User, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.resources = []
        self.setup_ui()
        self.load_resources()

    def setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Title and toolbar
        header_layout = QHBoxLayout()

        title = QLabel("资源管理")
        title.setObjectName("pageTitle")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Add resource button
        add_btn = QPushButton("➕ 添加资源")
        add_btn.setFixedSize(120, 40)
        add_btn.clicked.connect(self.add_resource)
        header_layout.addWidget(add_btn)

        layout.addLayout(header_layout)

        # Search and filter bar
        filter_layout = QHBoxLayout()

        # Search box
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索资源名称或序列号...")
        self.search_input.setFixedWidth(300)
        self.search_input.textChanged.connect(self.filter_resources)
        filter_layout.addWidget(QLabel("搜索:"))
        filter_layout.addWidget(self.search_input)

        filter_layout.addSpacing(20)

        # Type filter
        self.type_filter = QComboBox()
        self.type_filter.addItem("全部类型", None)
        self.type_filter.addItem("录音间", ResourceType.RECORDING_ROOM)
        self.type_filter.addItem("控制室", ResourceType.CONTROL_ROOM)
        self.type_filter.addItem("话筒", ResourceType.MICROPHONE)
        self.type_filter.addItem("声卡", ResourceType.SOUND_CARD)
        self.type_filter.addItem("其他设备", ResourceType.OTHER_EQUIPMENT)
        self.type_filter.currentIndexChanged.connect(self.filter_resources)
        filter_layout.addWidget(QLabel("类型:"))
        filter_layout.addWidget(self.type_filter)

        filter_layout.addSpacing(20)

        # Status filter
        self.status_filter = QComboBox()
        self.status_filter.addItem("全部状态", None)
        self.status_filter.addItem("可租", ResourceStatus.AVAILABLE_RENTAL)
        self.status_filter.addItem("仅内用", ResourceStatus.INTERNAL_ONLY)
        self.status_filter.addItem("维修中", ResourceStatus.MAINTENANCE)
        self.status_filter.currentIndexChanged.connect(self.filter_resources)
        filter_layout.addWidget(QLabel("状态:"))
        filter_layout.addWidget(self.status_filter)

        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        # Resource table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "名称", "类型", "状态", "序列号", "时价(元/小时)", "照片", "操作"
        ])

        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.Fixed)
        self.table.setColumnWidth(7, 180)

        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)

    def load_resources(self):
        """Load all resources from database."""
        try:
            with db.get_session() as session:
                repo = ResourceRepository(session)
                self.resources = repo.get_all()
                self.populate_table(self.resources)
                logger.info(f"Loaded {len(self.resources)} resources")
        except Exception as e:
            logger.error(f"Failed to load resources: {e}", exc_info=True)
            QMessageBox.critical(self, "加载失败", f"加载资源列表失败:\n{str(e)}")

    def populate_table(self, resources):
        """Populate table with resources."""
        self.table.setRowCount(0)

        type_map = {
            ResourceType.RECORDING_ROOM: "录音间",
            ResourceType.CONTROL_ROOM: "控制室",
            ResourceType.MICROPHONE: "话筒",
            ResourceType.SOUND_CARD: "声卡",
            ResourceType.OTHER_EQUIPMENT: "其他设备"
        }

        status_map = {
            ResourceStatus.AVAILABLE_RENTAL: "可租",
            ResourceStatus.INTERNAL_ONLY: "仅内用",
            ResourceStatus.MAINTENANCE: "维修中"
        }

        for resource in resources:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # ID
            self.table.setItem(row, 0, QTableWidgetItem(str(resource.id)))

            # Name
            self.table.setItem(row, 1, QTableWidgetItem(resource.name))

            # Type
            type_text = type_map.get(resource.resource_type, "未知")
            self.table.setItem(row, 2, QTableWidgetItem(type_text))

            # Status
            status_text = status_map.get(resource.status, "未知")
            status_item = QTableWidgetItem(status_text)
            if resource.status == ResourceStatus.MAINTENANCE:
                status_item.setForeground(Qt.red)
            elif resource.status == ResourceStatus.AVAILABLE_RENTAL:
                status_item.setForeground(Qt.darkGreen)
            self.table.setItem(row, 3, status_item)

            # Serial number
            self.table.setItem(row, 4, QTableWidgetItem(resource.serial_number or "-"))

            # Hourly rate
            self.table.setItem(row, 5, QTableWidgetItem(f"{resource.hourly_rate:.2f}"))

            # Photo
            photo_text = "有照片" if resource.photo_path else "无照片"
            self.table.setItem(row, 6, QTableWidgetItem(photo_text))

            # Action buttons
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(5, 2, 5, 2)
            action_layout.setSpacing(5)

            edit_btn = QPushButton("编辑")
            edit_btn.setFixedSize(50, 30)
            edit_btn.clicked.connect(lambda checked, r=resource: self.edit_resource(r))
            action_layout.addWidget(edit_btn)

            delete_btn = QPushButton("删除")
            delete_btn.setFixedSize(50, 30)
            delete_btn.setStyleSheet("background-color: #e74c3c;")
            delete_btn.clicked.connect(lambda checked, r=resource: self.delete_resource(r))
            action_layout.addWidget(delete_btn)

            view_photo_btn = QPushButton("查看照片")
            view_photo_btn.setFixedSize(70, 30)
            view_photo_btn.setEnabled(bool(resource.photo_path))
            view_photo_btn.clicked.connect(lambda checked, r=resource: self.view_photo(r))
            action_layout.addWidget(view_photo_btn)

            self.table.setCellWidget(row, 7, action_widget)

    def filter_resources(self):
        """Filter resources based on search and filters."""
        search_text = self.search_input.text().lower()
        selected_type = self.type_filter.currentData()
        selected_status = self.status_filter.currentData()

        filtered = []
        for resource in self.resources:
            # Search filter
            if search_text:
                if search_text not in resource.name.lower():
                    if not resource.serial_number or search_text not in resource.serial_number.lower():
                        continue

            # Type filter
            if selected_type and resource.resource_type != selected_type:
                continue

            # Status filter
            if selected_status and resource.status != selected_status:
                continue

            filtered.append(resource)

        self.populate_table(filtered)

    def add_resource(self):
        """Show dialog to add new resource."""
        dialog = ResourceDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self.load_resources()

    def edit_resource(self, resource: Resource):
        """Show dialog to edit resource."""
        dialog = ResourceDialog(self, resource)
        if dialog.exec() == QDialog.Accepted:
            self.load_resources()

    def delete_resource(self, resource: Resource):
        """Delete resource with confirmation."""
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除资源 '{resource.name}' 吗？\n此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                with db.get_session() as session:
                    repo = ResourceRepository(session)
                    repo.delete(resource.id)
                    session.commit()

                QMessageBox.information(self, "删除成功", f"资源 '{resource.name}' 已删除")
                logger.info(f"Resource deleted: {resource.name} (ID: {resource.id})")
                self.load_resources()
            except Exception as e:
                logger.error(f"Failed to delete resource: {e}", exc_info=True)
                QMessageBox.critical(self, "删除失败", f"删除资源失败:\n{str(e)}")

    def view_photo(self, resource: Resource):
        """View resource photo."""
        if not resource.photo_path or not os.path.exists(resource.photo_path):
            QMessageBox.warning(self, "照片不存在", "该资源的照片文件不存在")
            return

        dialog = PhotoViewDialog(resource.photo_path, resource.name, self)
        dialog.exec()


class ResourceDialog(QDialog):
    """Dialog for adding/editing resources."""

    def __init__(self, parent=None, resource: Optional[Resource] = None):
        super().__init__(parent)
        self.resource = resource
        self.photo_path = resource.photo_path if resource else None
        self.setup_ui()

        if resource:
            self.load_resource_data()

    def setup_ui(self):
        """Setup user interface."""
        self.setWindowTitle("编辑资源" if self.resource else "添加资源")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        # Title
        title = QLabel("编辑资源" if self.resource else "添加新资源")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title)

        # Form
        form_layout = QFormLayout()

        # Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("例如: A录音间, Neumann U87")
        form_layout.addRow("名称*:", self.name_input)

        # Type
        self.type_combo = QComboBox()
        self.type_combo.addItem("录音间", ResourceType.RECORDING_ROOM)
        self.type_combo.addItem("控制室", ResourceType.CONTROL_ROOM)
        self.type_combo.addItem("话筒", ResourceType.MICROPHONE)
        self.type_combo.addItem("声卡", ResourceType.SOUND_CARD)
        self.type_combo.addItem("其他设备", ResourceType.OTHER_EQUIPMENT)
        form_layout.addRow("类型*:", self.type_combo)

        # Status
        self.status_combo = QComboBox()
        self.status_combo.addItem("可租", ResourceStatus.AVAILABLE_RENTAL)
        self.status_combo.addItem("仅内用", ResourceStatus.INTERNAL_ONLY)
        self.status_combo.addItem("维修中", ResourceStatus.MAINTENANCE)
        form_layout.addRow("状态*:", self.status_combo)

        # Serial number
        self.serial_input = QLineEdit()
        self.serial_input.setPlaceholderText("设备序列号（可选）")
        form_layout.addRow("序列号:", self.serial_input)

        # Hourly rate
        self.rate_input = QDoubleSpinBox()
        self.rate_input.setRange(0, 99999)
        self.rate_input.setDecimals(2)
        self.rate_input.setSuffix(" 元/小时")
        self.rate_input.setValue(0)
        form_layout.addRow("时价*:", self.rate_input)

        # Description
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("资源描述（可选）")
        self.description_input.setMaximumHeight(80)
        form_layout.addRow("描述:", self.description_input)

        layout.addLayout(form_layout)

        # Photo section
        photo_group = QGroupBox("照片")
        photo_layout = QVBoxLayout(photo_group)

        photo_btn_layout = QHBoxLayout()

        self.photo_label = QLabel("未选择照片")
        self.photo_label.setStyleSheet("color: #7f8c8d;")
        photo_btn_layout.addWidget(self.photo_label)

        photo_btn_layout.addStretch()

        upload_btn = QPushButton("选择照片")
        upload_btn.setFixedSize(100, 35)
        upload_btn.clicked.connect(self.select_photo)
        photo_btn_layout.addWidget(upload_btn)

        clear_btn = QPushButton("清除照片")
        clear_btn.setFixedSize(100, 35)
        clear_btn.clicked.connect(self.clear_photo)
        photo_btn_layout.addWidget(clear_btn)

        photo_layout.addLayout(photo_btn_layout)

        # Photo preview
        self.photo_preview = QLabel()
        self.photo_preview.setFixedSize(200, 150)
        self.photo_preview.setStyleSheet("border: 1px solid #dfe6e9; background-color: #ecf0f1;")
        self.photo_preview.setAlignment(Qt.AlignCenter)
        self.photo_preview.setText("无预览")
        photo_layout.addWidget(self.photo_preview)

        layout.addWidget(photo_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        save_btn = QPushButton("保存")
        save_btn.setFixedSize(100, 40)
        save_btn.clicked.connect(self.save_resource)
        button_layout.addWidget(save_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(100, 40)
        cancel_btn.setStyleSheet("background-color: #95a5a6;")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def load_resource_data(self):
        """Load resource data into form."""
        self.name_input.setText(self.resource.name)

        # Set type
        for i in range(self.type_combo.count()):
            if self.type_combo.itemData(i) == self.resource.resource_type:
                self.type_combo.setCurrentIndex(i)
                break

        # Set status
        for i in range(self.status_combo.count()):
            if self.status_combo.itemData(i) == self.resource.status:
                self.status_combo.setCurrentIndex(i)
                break

        if self.resource.serial_number:
            self.serial_input.setText(self.resource.serial_number)

        self.rate_input.setValue(self.resource.hourly_rate)

        if self.resource.description:
            self.description_input.setText(self.resource.description)

        if self.resource.photo_path:
            self.photo_label.setText(os.path.basename(self.resource.photo_path))
            self.update_photo_preview(self.resource.photo_path)

    def select_photo(self):
        """Select photo file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择照片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)"
        )

        if file_path:
            self.photo_path = file_path
            self.photo_label.setText(os.path.basename(file_path))
            self.update_photo_preview(file_path)

    def clear_photo(self):
        """Clear selected photo."""
        self.photo_path = None
        self.photo_label.setText("未选择照片")
        self.photo_preview.clear()
        self.photo_preview.setText("无预览")

    def update_photo_preview(self, file_path: str):
        """Update photo preview."""
        if os.path.exists(file_path):
            pixmap = QPixmap(file_path)
            scaled_pixmap = pixmap.scaled(
                self.photo_preview.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.photo_preview.setPixmap(scaled_pixmap)

    def save_resource(self):
        """Save resource to database."""
        # Validate
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "验证失败", "请输入资源名称")
            return

        resource_type = self.type_combo.currentData()
        status = self.status_combo.currentData()
        serial_number = self.serial_input.text().strip() or None
        hourly_rate = self.rate_input.value()
        description = self.description_input.toPlainText().strip() or None

        try:
            # Handle photo upload
            final_photo_path = None
            if self.photo_path:
                # Create uploads directory if not exists
                uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
                os.makedirs(uploads_dir, exist_ok=True)

                # Copy photo to uploads directory
                import shutil
                from datetime import datetime

                file_ext = os.path.splitext(self.photo_path)[1]
                new_filename = f"resource_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_ext}"
                final_photo_path = os.path.join(uploads_dir, new_filename)

                # Only copy if it's a new file
                if self.photo_path != final_photo_path:
                    shutil.copy2(self.photo_path, final_photo_path)

            with db.get_session() as session:
                repo = ResourceRepository(session)

                if self.resource:
                    # Update existing resource
                    self.resource.name = name
                    self.resource.resource_type = resource_type
                    self.resource.status = status
                    self.resource.serial_number = serial_number
                    self.resource.hourly_rate = hourly_rate
                    self.resource.description = description
                    if final_photo_path:
                        self.resource.photo_path = final_photo_path

                    repo.update(self.resource)
                    logger.info(f"Resource updated: {name} (ID: {self.resource.id})")
                else:
                    # Create new resource
                    new_resource = Resource(
                        name=name,
                        resource_type=resource_type,
                        status=status,
                        serial_number=serial_number,
                        hourly_rate=hourly_rate,
                        description=description,
                        photo_path=final_photo_path
                    )
                    repo.create(new_resource)
                    logger.info(f"Resource created: {name}")

                session.commit()

            QMessageBox.information(
                self,
                "保存成功",
                f"资源 '{name}' 已{'更新' if self.resource else '创建'}"
            )
            self.accept()

        except Exception as e:
            logger.error(f"Failed to save resource: {e}", exc_info=True)
            QMessageBox.critical(self, "保存失败", f"保存资源失败:\n{str(e)}")


class PhotoViewDialog(QDialog):
    """Dialog for viewing resource photo."""

    def __init__(self, photo_path: str, resource_name: str, parent=None):
        super().__init__(parent)
        self.photo_path = photo_path
        self.resource_name = resource_name
        self.setup_ui()

    def setup_ui(self):
        """Setup user interface."""
        self.setWindowTitle(f"照片 - {self.resource_name}")
        self.setMinimumSize(600, 500)

        layout = QVBoxLayout(self)

        # Photo
        photo_label = QLabel()
        photo_label.setAlignment(Qt.AlignCenter)

        if os.path.exists(self.photo_path):
            pixmap = QPixmap(self.photo_path)
            scaled_pixmap = pixmap.scaled(
                580, 450,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            photo_label.setPixmap(scaled_pixmap)
        else:
            photo_label.setText("照片文件不存在")

        layout.addWidget(photo_label)

        # Close button
        close_btn = QPushButton("关闭")
        close_btn.setFixedSize(100, 40)
        close_btn.clicked.connect(self.accept)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
