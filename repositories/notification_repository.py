"""Notification repository for data access."""
import logging
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from database.models import Notification
from repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class NotificationRepository(BaseRepository[Notification]):
    """Repository for notification operations."""

    def __init__(self, session: Session):
        super().__init__(Notification, session)

    def get_by_user(self, user_id: int, unread_only: bool = False) -> List[Notification]:
        """获取用户的通知列表"""
        query = self.session.query(Notification).filter(Notification.user_id == user_id)

        if unread_only:
            query = query.filter(Notification.is_read == False)

        return query.order_by(Notification.created_at.desc()).all()

    def get_unread_count(self, user_id: int) -> int:
        """获取用户未读通知数量"""
        return self.session.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).count()

    def mark_as_read(self, notification_id: int) -> bool:
        """标记通知为已读"""
        notification = self.get_by_id(notification_id)
        if notification:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            self.session.commit()
            return True
        return False

    def mark_all_as_read(self, user_id: int) -> int:
        """标记用户所有通知为已读"""
        count = self.session.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).update({
            'is_read': True,
            'read_at': datetime.utcnow()
        })
        self.session.commit()
        return count

    def delete_old_notifications(self, days: int = 30) -> int:
        """删除指定天数之前的已读通知"""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        count = self.session.query(Notification).filter(
            Notification.is_read == True,
            Notification.created_at < cutoff_date
        ).delete()
        self.session.commit()
        return count
