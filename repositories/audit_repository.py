"""Audit log repository for audit log data access."""
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from database.models import AuditLog
from repositories.base_repository import BaseRepository

class AuditLogRepository(BaseRepository[AuditLog]):
    """Repository for AuditLog entity."""

    def __init__(self, session: Session):
        super().__init__(AuditLog, session)

    def get_by_user(self, user_id: int) -> List[AuditLog]:
        """Get audit logs for a specific user.

        Args:
            user_id: User ID

        Returns:
            List of audit logs
        """
        return (
            self.session.query(AuditLog)
            .filter(AuditLog.user_id == user_id)
            .order_by(AuditLog.timestamp.desc())
            .all()
        )

    def get_by_action(self, action: str) -> List[AuditLog]:
        """Get audit logs by action type.

        Args:
            action: Action type

        Returns:
            List of audit logs
        """
        return (
            self.session.query(AuditLog)
            .filter(AuditLog.action == action)
            .order_by(AuditLog.timestamp.desc())
            .all()
        )

    def get_by_date_range(self, start_date: datetime, end_date: datetime) -> List[AuditLog]:
        """Get audit logs within date range.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            List of audit logs
        """
        return (
            self.session.query(AuditLog)
            .filter(
                AuditLog.timestamp >= start_date,
                AuditLog.timestamp <= end_date
            )
            .order_by(AuditLog.timestamp.desc())
            .all()
        )

    def get_recent(self, limit: int = 100) -> List[AuditLog]:
        """Get recent audit logs.

        Args:
            limit: Maximum number of logs to return

        Returns:
            List of recent audit logs
        """
        return (
            self.session.query(AuditLog)
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
            .all()
        )
