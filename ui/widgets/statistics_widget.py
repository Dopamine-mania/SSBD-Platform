"""Statistics and reports widget."""
import logging
import csv
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QTabWidget, QFileDialog, QComboBox
)
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from database.models import User, Booking, Order, BookingStatus, OrderStatus
from database.connection import db
from repositories.booking_repository import BookingRepository
from repositories.order_repository import OrderRepository
from repositories.resource_repository import ResourceRepository

logger = logging.getLogger(__name__)


class StatisticsWidget(QWidget):
    """Widget for statistics and reports."""

    def __init__(self, current_user: User, parent=None):
        super().__init__(parent)
        self.current_user = current_user
        self.current_period = "day"  # day, week, month
        self.setup_ui()
        self.load_statistics()

    def setup_ui(self):
        """Setup user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Title and controls
        header_layout = QHBoxLayout()

        title = QLabel("统计报表")
        title.setObjectName("pageTitle")
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Export button
        export_btn = QPushButton("导出 CSV")
        export_btn.setObjectName("primaryButton")
        export_btn.clicked.connect(self.export_to_csv)
        header_layout.addWidget(export_btn)

        layout.addLayout(header_layout)

        # Period tabs
        self.tab_widget = QTabWidget()
        self.tab_widget.currentChanged.connect(self.on_period_changed)

        # Create tabs for day, week, month
        self.day_tab = self.create_statistics_tab()
        self.week_tab = self.create_statistics_tab()
        self.month_tab = self.create_statistics_tab()

        self.tab_widget.addTab(self.day_tab, "日统计")
        self.tab_widget.addTab(self.week_tab, "周统计")
        self.tab_widget.addTab(self.month_tab, "月统计")

        layout.addWidget(self.tab_widget)

    def create_statistics_tab(self) -> QWidget:
        """Create a statistics tab with all sections."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(20)

        # Resource utilization section
        util_label = QLabel("资源利用率统计")
        util_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(util_label)

        util_table = QTableWidget()
        util_table.setColumnCount(4)
        util_table.setHorizontalHeaderLabels(["资源名称", "类型", "使用时长(小时)", "利用率(%)"])
        util_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        util_table.setEditTriggers(QTableWidget.NoEditTriggers)
        util_table.setSelectionBehavior(QTableWidget.SelectRows)
        util_table.setAlternatingRowColors(True)
        util_table.setMaximumHeight(200)
        layout.addWidget(util_table)

        # Device revenue ranking section
        revenue_label = QLabel("设备收入排行")
        revenue_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(revenue_label)

        revenue_table = QTableWidget()
        revenue_table.setColumnCount(4)
        revenue_table.setHorizontalHeaderLabels(["排名", "设备名称", "预约次数", "总收入(元)"])
        revenue_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        revenue_table.setEditTriggers(QTableWidget.NoEditTriggers)
        revenue_table.setSelectionBehavior(QTableWidget.SelectRows)
        revenue_table.setAlternatingRowColors(True)
        revenue_table.setMaximumHeight(200)
        layout.addWidget(revenue_table)

        # Engineer work hours ranking section
        engineer_label = QLabel("工程师工时排行")
        engineer_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(engineer_label)

        engineer_table = QTableWidget()
        engineer_table.setColumnCount(4)
        engineer_table.setHorizontalHeaderLabels(["排名", "工程师", "预约次数", "工作时长(小时)"])
        engineer_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        engineer_table.setEditTriggers(QTableWidget.NoEditTriggers)
        engineer_table.setSelectionBehavior(QTableWidget.SelectRows)
        engineer_table.setAlternatingRowColors(True)
        engineer_table.setMaximumHeight(200)
        layout.addWidget(engineer_table)

        # Revenue trend chart section
        chart_label = QLabel("收入趋势图")
        chart_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(chart_label)

        # Matplotlib canvas
        figure = Figure(figsize=(10, 4))
        canvas = FigureCanvas(figure)
        canvas.setMinimumHeight(300)
        layout.addWidget(canvas)

        layout.addStretch()

        # Store references
        tab.util_table = util_table
        tab.revenue_table = revenue_table
        tab.engineer_table = engineer_table
        tab.figure = figure
        tab.canvas = canvas

        return tab

    def on_period_changed(self, index: int):
        """Handle period tab change."""
        periods = ["day", "week", "month"]
        self.current_period = periods[index]
        self.load_statistics()

    def get_date_range(self) -> Tuple[datetime, datetime]:
        """Get date range based on current period."""
        now = datetime.now()

        if self.current_period == "day":
            # Today
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
        elif self.current_period == "week":
            # This week (Monday to Sunday)
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=7)
        else:  # month
            # This month
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if now.month == 12:
                end = start.replace(year=now.year + 1, month=1)
            else:
                end = start.replace(month=now.month + 1)

        return start, end

    def load_statistics(self):
        """Load all statistics data."""
        try:
            with db.get_session() as session:
                booking_repo = BookingRepository(session)
                order_repo = OrderRepository(session)
                resource_repo = ResourceRepository(session)

                start_date, end_date = self.get_date_range()

                # Get bookings and orders in date range
                bookings = booking_repo.get_by_date_range(start_date, end_date)
                orders = order_repo.get_by_date_range(start_date, end_date)
                all_resources = resource_repo.get_all()

                # Calculate statistics
                resource_stats = self.calculate_resource_utilization(bookings, all_resources, start_date, end_date)
                revenue_stats = self.calculate_device_revenue(bookings, orders)
                engineer_stats = self.calculate_engineer_hours(bookings)
                revenue_trend = self.calculate_revenue_trend(orders, start_date, end_date)

                # Get current tab
                current_tab = self.get_current_tab()

                # Update tables
                self.update_utilization_table(current_tab.util_table, resource_stats)
                self.update_revenue_table(current_tab.revenue_table, revenue_stats)
                self.update_engineer_table(current_tab.engineer_table, engineer_stats)
                self.update_revenue_chart(current_tab.figure, current_tab.canvas, revenue_trend)

        except Exception as e:
            logger.error(f"Failed to load statistics: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"加载统计数据失败: {str(e)}")

    def get_current_tab(self) -> QWidget:
        """Get current statistics tab."""
        index = self.tab_widget.currentIndex()
        return [self.day_tab, self.week_tab, self.month_tab][index]

    def calculate_resource_utilization(
        self,
        bookings: List[Booking],
        all_resources: List,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """Calculate resource utilization statistics."""
        # Calculate total available hours
        total_days = (end_date - start_date).total_seconds() / 86400
        total_hours = total_days * 24

        # Track usage per resource
        resource_usage = defaultdict(float)
        resource_info = {}

        for resource in all_resources:
            resource_info[resource.id] = {
                'name': resource.name,
                'type': resource.resource_type.value
            }

        # Calculate actual usage from bookings
        for booking in bookings:
            if booking.status in [BookingStatus.COMPLETED, BookingStatus.IN_PROGRESS]:
                # Calculate booking duration
                booking_start = max(booking.start_time, start_date)
                booking_end = min(booking.end_time, end_date)

                if booking_end > booking_start:
                    duration_hours = (booking_end - booking_start).total_seconds() / 3600

                    # Add to each resource in booking
                    for br in booking.booking_resources:
                        resource_usage[br.resource_id] += duration_hours * br.quantity

        # Build statistics list
        stats = []
        for resource_id, info in resource_info.items():
            usage_hours = resource_usage.get(resource_id, 0)
            utilization = (usage_hours / total_hours * 100) if total_hours > 0 else 0

            stats.append({
                'name': info['name'],
                'type': info['type'],
                'usage_hours': round(usage_hours, 2),
                'utilization': round(utilization, 2)
            })

        # Sort by utilization descending
        stats.sort(key=lambda x: x['utilization'], reverse=True)
        return stats

    def calculate_device_revenue(self, bookings: List[Booking], orders: List[Order]) -> List[Dict]:
        """Calculate device revenue ranking."""
        # Map booking to order revenue
        booking_revenue = {}
        for order in orders:
            if order.status == OrderStatus.PAID:
                booking_revenue[order.booking_id] = order.total

        # Track revenue per resource
        resource_stats = defaultdict(lambda: {'count': 0, 'revenue': 0.0, 'name': ''})

        for booking in bookings:
            if booking.id in booking_revenue:
                revenue = booking_revenue[booking.id]
                num_resources = len(booking.booking_resources)

                if num_resources > 0:
                    # Distribute revenue evenly among resources
                    revenue_per_resource = revenue / num_resources

                    for br in booking.booking_resources:
                        resource_stats[br.resource_id]['name'] = br.resource.name
                        resource_stats[br.resource_id]['count'] += 1
                        resource_stats[br.resource_id]['revenue'] += revenue_per_resource

        # Build ranking list
        ranking = []
        for resource_id, stats in resource_stats.items():
            ranking.append({
                'name': stats['name'],
                'count': stats['count'],
                'revenue': round(stats['revenue'], 2)
            })

        # Sort by revenue descending
        ranking.sort(key=lambda x: x['revenue'], reverse=True)
        return ranking

    def calculate_engineer_hours(self, bookings: List[Booking]) -> List[Dict]:
        """Calculate engineer work hours ranking."""
        engineer_stats = defaultdict(lambda: {'count': 0, 'hours': 0.0, 'name': ''})

        for booking in bookings:
            if booking.engineer_id and booking.status in [BookingStatus.COMPLETED, BookingStatus.IN_PROGRESS]:
                # Calculate work hours
                duration_hours = (booking.end_time - booking.start_time).total_seconds() / 3600

                engineer_stats[booking.engineer_id]['name'] = booking.engineer_user.full_name
                engineer_stats[booking.engineer_id]['count'] += 1
                engineer_stats[booking.engineer_id]['hours'] += duration_hours

        # Build ranking list
        ranking = []
        for engineer_id, stats in engineer_stats.items():
            ranking.append({
                'name': stats['name'],
                'count': stats['count'],
                'hours': round(stats['hours'], 2)
            })

        # Sort by hours descending
        ranking.sort(key=lambda x: x['hours'], reverse=True)
        return ranking

    def calculate_revenue_trend(
        self,
        orders: List[Order],
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, float]:
        """Calculate revenue trend over time."""
        trend = defaultdict(float)

        for order in orders:
            if order.status == OrderStatus.PAID and order.paid_at:
                # Group by date
                date_key = order.paid_at.strftime('%Y-%m-%d')
                trend[date_key] += order.total

        return dict(trend)

    def update_utilization_table(self, table: QTableWidget, stats: List[Dict]):
        """Update resource utilization table."""
        table.setRowCount(len(stats))

        for row, stat in enumerate(stats):
            table.setItem(row, 0, QTableWidgetItem(stat['name']))
            table.setItem(row, 1, QTableWidgetItem(stat['type']))

            hours_item = QTableWidgetItem(str(stat['usage_hours']))
            hours_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(row, 2, hours_item)

            util_item = QTableWidgetItem(f"{stat['utilization']:.2f}%")
            util_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(row, 3, util_item)

    def update_revenue_table(self, table: QTableWidget, ranking: List[Dict]):
        """Update device revenue ranking table."""
        table.setRowCount(len(ranking))

        for row, item in enumerate(ranking):
            rank_item = QTableWidgetItem(str(row + 1))
            rank_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 0, rank_item)

            table.setItem(row, 1, QTableWidgetItem(item['name']))

            count_item = QTableWidgetItem(str(item['count']))
            count_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(row, 2, count_item)

            revenue_item = QTableWidgetItem(f"¥{item['revenue']:.2f}")
            revenue_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(row, 3, revenue_item)

    def update_engineer_table(self, table: QTableWidget, ranking: List[Dict]):
        """Update engineer work hours ranking table."""
        table.setRowCount(len(ranking))

        for row, item in enumerate(ranking):
            rank_item = QTableWidgetItem(str(row + 1))
            rank_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 0, rank_item)

            table.setItem(row, 1, QTableWidgetItem(item['name']))

            count_item = QTableWidgetItem(str(item['count']))
            count_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(row, 2, count_item)

            hours_item = QTableWidgetItem(f"{item['hours']:.2f}")
            hours_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(row, 3, hours_item)

    def update_revenue_chart(self, figure: Figure, canvas: FigureCanvas, trend: Dict[str, float]):
        """Update revenue trend chart."""
        figure.clear()
        ax = figure.add_subplot(111)

        if not trend:
            ax.text(0.5, 0.5, '暂无数据', ha='center', va='center', fontsize=14)
        else:
            # Sort by date
            dates = sorted(trend.keys())
            revenues = [trend[date] for date in dates]

            # Plot
            ax.plot(dates, revenues, marker='o', linewidth=2, markersize=6, color='#3498db')
            ax.fill_between(range(len(dates)), revenues, alpha=0.3, color='#3498db')

            # Formatting
            ax.set_xlabel('日期', fontsize=10)
            ax.set_ylabel('收入 (元)', fontsize=10)
            ax.set_title('收入趋势', fontsize=12, fontweight='bold')
            ax.grid(True, alpha=0.3)

            # Rotate x-axis labels
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

            # Format y-axis as currency
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'¥{x:,.0f}'))

        figure.tight_layout()
        canvas.draw()

    def export_to_csv(self):
        """Export current statistics to CSV file."""
        try:
            # Get file path from user
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出统计数据",
                f"statistics_{self.current_period}_{datetime.now().strftime('%Y%m%d')}.csv",
                "CSV Files (*.csv)"
            )

            if not file_path:
                return

            current_tab = self.get_current_tab()

            with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)

                # Export resource utilization
                writer.writerow(['资源利用率统计'])
                writer.writerow(['资源名称', '类型', '使用时长(小时)', '利用率(%)'])

                for row in range(current_tab.util_table.rowCount()):
                    row_data = []
                    for col in range(current_tab.util_table.columnCount()):
                        item = current_tab.util_table.item(row, col)
                        row_data.append(item.text() if item else '')
                    writer.writerow(row_data)

                writer.writerow([])  # Empty row

                # Export device revenue
                writer.writerow(['设备收入排行'])
                writer.writerow(['排名', '设备名称', '预约次数', '总收入(元)'])

                for row in range(current_tab.revenue_table.rowCount()):
                    row_data = []
                    for col in range(current_tab.revenue_table.columnCount()):
                        item = current_tab.revenue_table.item(row, col)
                        row_data.append(item.text() if item else '')
                    writer.writerow(row_data)

                writer.writerow([])  # Empty row

                # Export engineer hours
                writer.writerow(['工程师工时排行'])
                writer.writerow(['排名', '工程师', '预约次数', '工作时长(小时)'])

                for row in range(current_tab.engineer_table.rowCount()):
                    row_data = []
                    for col in range(current_tab.engineer_table.columnCount()):
                        item = current_tab.engineer_table.item(row, col)
                        row_data.append(item.text() if item else '')
                    writer.writerow(row_data)

            QMessageBox.information(self, "成功", f"统计数据已导出到:\n{file_path}")

        except Exception as e:
            logger.error(f"Failed to export CSV: {e}", exc_info=True)
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

