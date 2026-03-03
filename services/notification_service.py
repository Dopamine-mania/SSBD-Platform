"""Notification service for managing notifications."""
import logging
from typing import List, Optional
from datetime import datetime

from database.models import Notification, User
from repositories.notification_repository import NotificationRepository

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for notification operations."""

    def __init__(self, notification_repo: NotificationRepository):
        self.notification_repo = notification_repo

    def create_notification(
        self,
        user_id: int,
        title: str,
        message: str,
        notification_type: str,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[int] = None
    ) -> Notification:
        """创建通知"""
        notification = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id
        )

        created = self.notification_repo.create(notification)
        logger.info(f"Created notification for user {user_id}: {title}")
        return created

    def notify_late_arrival(
        self,
        engineer_id: int,
        booking_id: int,
        customer_name: str,
        scheduled_time: datetime,
        late_minutes: int
    ):
        """通知工程师客户迟到"""
        title = "客户迟到提醒"
        message = (
            f"客户 {customer_name} 预约时间为 {scheduled_time.strftime('%H:%M')}，"
            f"已迟到 {late_minutes} 分钟，请注意调整工作安排。"
        )

        return self.create_notification(
            user_id=engineer_id,
            title=title,
            message=message,
            notification_type="LATE_ARRIVAL",
            related_entity_type="Booking",
            related_entity_id=booking_id
        )

    def notify_booking_reminder(
        self,
        user_id: int,
        booking_id: int,
        customer_name: str,
        start_time: datetime
    ):
        """预约提醒通知"""
        title = "预约提醒"
        message = (
            f"客户 {customer_name} 的预约将在 {start_time.strftime('%Y-%m-%d %H:%M')} 开始，"
            f"请提前做好准备。"
        )

        return self.create_notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type="BOOKING_REMINDER",
            related_entity_type="Booking",
            related_entity_id=booking_id
        )

    def notify_system_message(self, user_id: int, title: str, message: str):
        """系统消息通知"""
        return self.create_notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type="SYSTEM"
        )

    def get_user_notifications(
        self,
        user_id: int,
        unread_only: bool = False
    ) -> List[Notification]:
        """获取用户通知列表"""
        return self.notification_repo.get_by_user(user_id, unread_only)

    def get_unread_count(self, user_id: int) -> int:
        """获取未读通知数量"""
        return self.notification_repo.get_unread_count(user_id)

    def mark_as_read(self, notification_id: int) -> bool:
        """标记通知为已读"""
        return self.notification_repo.mark_as_read(notification_id)

    def mark_all_as_read(self, user_id: int) -> int:
        """标记所有通知为已读"""
        return self.notification_repo.mark_all_as_read(user_id)
