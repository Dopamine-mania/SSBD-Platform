"""Audit service for logging user actions."""
import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime

from database.models import AuditLog
from repositories.audit_repository import AuditLogRepository

logger = logging.getLogger(__name__)

class AuditService:
    """Service for audit logging."""

    def __init__(self, audit_repo: AuditLogRepository):
        """Initialize audit service.

        Args:
            audit_repo: Audit log repository
        """
        self.audit_repo = audit_repo

    def log_action(
        self,
        action: str,
        user_id: Optional[int] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None
    ) -> AuditLog:
        """Log a user action.

        Args:
            action: Action type (e.g., 'LOGIN', 'CREATE_BOOKING', 'REFUND')
            user_id: User ID who performed the action
            entity_type: Type of entity affected (e.g., 'Booking', 'Order')
            entity_id: ID of entity affected
            details: Additional details as dictionary
            ip_address: IP address of the user

        Returns:
            Created audit log
        """
        details_json = json.dumps(details, ensure_ascii=False) if details else None

        audit_log = self.audit_repo.create(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details_json,
            ip_address=ip_address,
            timestamp=datetime.utcnow()
        )

        logger.info(
            f"Audit log created: action={action}, user_id={user_id}, "
            f"entity_type={entity_type}, entity_id={entity_id}"
        )

        return audit_log

    def log_login(self, user_id: int, username: str, success: bool, ip_address: Optional[str] = None):
        """Log login attempt.

        Args:
            user_id: User ID (None if failed)
            username: Username
            success: Whether login was successful
            ip_address: IP address
        """
        action = "LOGIN_SUCCESS" if success else "LOGIN_FAILED"
        details = {
            "username": username,
            "success": success
        }
        return self.log_action(action, user_id, details=details, ip_address=ip_address)

    def log_logout(self, user_id: int, username: str, ip_address: Optional[str] = None):
        """Log logout.

        Args:
            user_id: User ID
            username: Username
            ip_address: IP address
        """
        details = {"username": username}
        return self.log_action("LOGOUT", user_id, details=details, ip_address=ip_address)

    def log_booking_created(self, user_id: int, booking_id: int, customer_name: str, details: Dict[str, Any]):
        """Log booking creation.

        Args:
            user_id: User ID who created the booking
            booking_id: Booking ID
            customer_name: Customer name
            details: Booking details
        """
        details_with_customer = {**details, "customer_name": customer_name}
        return self.log_action(
            "CREATE_BOOKING",
            user_id,
            entity_type="Booking",
            entity_id=booking_id,
            details=details_with_customer
        )

    def log_booking_updated(self, user_id: int, booking_id: int, changes: Dict[str, Any]):
        """Log booking update.

        Args:
            user_id: User ID who updated the booking
            booking_id: Booking ID
            changes: Changes made
        """
        return self.log_action(
            "UPDATE_BOOKING",
            user_id,
            entity_type="Booking",
            entity_id=booking_id,
            details=changes
        )

    def log_booking_cancelled(self, user_id: int, booking_id: int, reason: str):
        """Log booking cancellation.

        Args:
            user_id: User ID who cancelled the booking
            booking_id: Booking ID
            reason: Cancellation reason
        """
        details = {"reason": reason}
        return self.log_action(
            "CANCEL_BOOKING",
            user_id,
            entity_type="Booking",
            entity_id=booking_id,
            details=details
        )

    def log_payment_processed(self, user_id: int, order_id: int, amount: float, method: str):
        """Log payment processing.

        Args:
            user_id: User ID who processed the payment
            order_id: Order ID
            amount: Payment amount
            method: Payment method
        """
        details = {
            "amount": amount,
            "method": method
        }
        return self.log_action(
            "PROCESS_PAYMENT",
            user_id,
            entity_type="Order",
            entity_id=order_id,
            details=details
        )

    def log_refund_approved(self, user_id: int, order_id: int, amount: float, reason: str):
        """Log refund approval.

        Args:
            user_id: User ID who approved the refund
            order_id: Order ID
            amount: Refund amount
            reason: Refund reason
        """
        details = {
            "amount": amount,
            "reason": reason
        }
        return self.log_action(
            "APPROVE_REFUND",
            user_id,
            entity_type="Order",
            entity_id=order_id,
            details=details
        )

    def log_database_backup(self, user_id: int, backup_path: str):
        """Log database backup.

        Args:
            user_id: User ID who performed the backup
            backup_path: Path to backup file
        """
        details = {"backup_path": backup_path}
        return self.log_action("DATABASE_BACKUP", user_id, details=details)

    def log_database_restore(self, user_id: int, backup_path: str):
        """Log database restore.

        Args:
            user_id: User ID who performed the restore
            backup_path: Path to backup file
        """
        details = {"backup_path": backup_path}
        return self.log_action("DATABASE_RESTORE", user_id, details=details)
