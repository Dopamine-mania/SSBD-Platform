"""Booking service for managing bookings and time tracking."""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict

from database.models import Booking, BookingResource, TimeLog, BookingStatus
from repositories.booking_repository import BookingRepository
from config.settings import MINIMUM_BOOKING_MINUTES, LATE_ARRIVAL_THRESHOLD_MINUTES

logger = logging.getLogger(__name__)

class BookingConflictError(Exception):
    """Booking conflict error exception."""
    pass

class BookingService:
    """Service for booking management."""

    def __init__(self, booking_repo: BookingRepository, audit_service=None):
        """Initialize booking service.

        Args:
            booking_repo: Booking repository
            audit_service: Optional audit service for logging
        """
        self.booking_repo = booking_repo
        self.audit_service = audit_service

    def create_booking(
        self,
        customer_id: int,
        created_by: int,
        start_time: datetime,
        end_time: datetime,
        resource_ids: List[int],
        engineer_id: Optional[int] = None,
        notes: Optional[str] = None
    ) -> Booking:
        """Create a new booking with conflict detection.

        Args:
            customer_id: Customer ID
            created_by: User ID who created the booking
            start_time: Booking start time
            end_time: Booking end time
            resource_ids: List of resource IDs to book
            engineer_id: Optional engineer ID
            notes: Optional notes

        Returns:
            Created booking

        Raises:
            BookingConflictError: If booking conflicts with existing bookings
            ValueError: If booking parameters are invalid
        """
        # Validate booking time range
        if start_time >= end_time:
            raise ValueError("开始时间必须早于结束时间")

        # Validate booking duration
        duration_minutes = (end_time - start_time).total_seconds() / 60
        if duration_minutes < MINIMUM_BOOKING_MINUTES:
            raise ValueError(f"预约时长不能少于 {MINIMUM_BOOKING_MINUTES} 分钟")

        # Check for conflicts
        conflicts = self.check_conflicts(resource_ids, start_time, end_time)
        if conflicts:
            conflict_details = self._format_conflicts(conflicts)
            raise BookingConflictError(f"预约冲突：\n{conflict_details}")

        # Create booking
        booking = self.booking_repo.create(
            customer_id=customer_id,
            created_by=created_by,
            engineer_id=engineer_id,
            start_time=start_time,
            end_time=end_time,
            status=BookingStatus.PENDING,
            notes=notes
        )

        # Add resources
        for resource_id in resource_ids:
            booking_resource = BookingResource(
                booking_id=booking.id,
                resource_id=resource_id,
                quantity=1
            )
            self.booking_repo.session.add(booking_resource)

        self.booking_repo.session.flush()
        logger.info(f"Booking created: {booking.id} for customer {customer_id}")

        # Log booking creation
        if self.audit_service:
            details = {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "resource_ids": resource_ids,
                "engineer_id": engineer_id
            }
            # Get customer name for audit log
            customer_name = booking.customer.name if booking.customer else "Unknown"
            self.audit_service.log_booking_created(created_by, booking.id, customer_name, details)

        return booking

    def check_conflicts(
        self,
        resource_ids: List[int],
        start_time: datetime,
        end_time: datetime,
        exclude_booking_id: Optional[int] = None
    ) -> List[Dict]:
        """Check for booking conflicts.

        Args:
            resource_ids: List of resource IDs to check
            start_time: Booking start time
            end_time: Booking end time
            exclude_booking_id: Optional booking ID to exclude from check

        Returns:
            List of conflict dictionaries with booking and resource info
        """
        conflicting_bookings = self.booking_repo.check_resource_conflicts(
            resource_ids, start_time, end_time, exclude_booking_id
        )

        conflicts = []
        for booking in conflicting_bookings:
            for booking_resource in booking.booking_resources:
                if booking_resource.resource_id in resource_ids:
                    conflicts.append({
                        'booking_id': booking.id,
                        'resource_id': booking_resource.resource_id,
                        'resource_name': booking_resource.resource.name,
                        'start_time': booking.start_time,
                        'end_time': booking.end_time,
                        'customer_name': booking.customer.name if booking.customer else 'Unknown'
                    })

        return conflicts

    def _format_conflicts(self, conflicts: List[Dict]) -> str:
        """Format conflicts for display.

        Args:
            conflicts: List of conflict dictionaries

        Returns:
            Formatted conflict string
        """
        lines = []
        for conflict in conflicts:
            lines.append(
                f"- {conflict['resource_name']}: "
                f"{conflict['start_time'].strftime('%Y-%m-%d %H:%M')} - "
                f"{conflict['end_time'].strftime('%H:%M')} "
                f"(客户: {conflict['customer_name']})"
            )
        return "\n".join(lines)

    def start_session(self, booking_id: int) -> TimeLog:
        """Start a booking session.

        Args:
            booking_id: Booking ID

        Returns:
            Created time log

        Raises:
            ValueError: If booking cannot be started
        """
        booking = self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise ValueError("预约不存在")

        if booking.status == BookingStatus.IN_PROGRESS:
            raise ValueError("预约已经开始")

        if booking.status == BookingStatus.COMPLETED:
            raise ValueError("预约已完成")

        if booking.status == BookingStatus.CANCELLED:
            raise ValueError("预约已取消")

        # Update booking
        now = datetime.utcnow()
        self.booking_repo.update(
            booking,
            status=BookingStatus.IN_PROGRESS,
            actual_start_time=now
        )

        # Check for late arrival
        if now > booking.start_time + timedelta(minutes=LATE_ARRIVAL_THRESHOLD_MINUTES):
            late_minutes = int((now - booking.start_time).total_seconds() / 60)
            self.booking_repo.update(
                booking,
                is_late=True,
                late_minutes=late_minutes
            )
            logger.warning(f"Late arrival for booking {booking_id}: {late_minutes} minutes")

        # Create time log
        time_log = TimeLog(
            booking_id=booking_id,
            action='start',
            timestamp=now
        )
        self.booking_repo.session.add(time_log)
        self.booking_repo.session.flush()

        logger.info(f"Session started for booking {booking_id}")
        return time_log

    def pause_session(self, booking_id: int, notes: Optional[str] = None) -> TimeLog:
        """Pause a booking session.

        Args:
            booking_id: Booking ID
            notes: Optional notes

        Returns:
            Created time log

        Raises:
            ValueError: If booking cannot be paused
        """
        booking = self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise ValueError("预约不存在")

        if booking.status != BookingStatus.IN_PROGRESS:
            raise ValueError("预约未在进行中")

        # Create time log
        time_log = TimeLog(
            booking_id=booking_id,
            action='pause',
            timestamp=datetime.utcnow(),
            notes=notes
        )
        self.booking_repo.session.add(time_log)
        self.booking_repo.session.flush()

        logger.info(f"Session paused for booking {booking_id}")
        return time_log

    def resume_session(self, booking_id: int) -> TimeLog:
        """Resume a paused booking session.

        Args:
            booking_id: Booking ID

        Returns:
            Created time log

        Raises:
            ValueError: If booking cannot be resumed
        """
        booking = self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise ValueError("预约不存在")

        if booking.status != BookingStatus.IN_PROGRESS:
            raise ValueError("预约未在进行中")

        # Calculate pause duration
        time_logs = sorted(booking.time_logs, key=lambda x: x.timestamp)
        last_pause = None
        for log in reversed(time_logs):
            if log.action == 'pause':
                last_pause = log
                break

        if last_pause:
            pause_duration = (datetime.utcnow() - last_pause.timestamp).total_seconds() / 60
            self.booking_repo.update(
                booking,
                pause_duration_minutes=booking.pause_duration_minutes + int(pause_duration)
            )

        # Create time log
        time_log = TimeLog(
            booking_id=booking_id,
            action='resume',
            timestamp=datetime.utcnow()
        )
        self.booking_repo.session.add(time_log)
        self.booking_repo.session.flush()

        logger.info(f"Session resumed for booking {booking_id}")
        return time_log

    def end_session(self, booking_id: int) -> TimeLog:
        """End a booking session.

        Args:
            booking_id: Booking ID

        Returns:
            Created time log

        Raises:
            ValueError: If booking cannot be ended
        """
        booking = self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise ValueError("预约不存在")

        if booking.status != BookingStatus.IN_PROGRESS:
            raise ValueError("预约未在进行中")

        # Check if there's an unresolved pause
        time_logs = sorted(booking.time_logs, key=lambda x: x.timestamp)
        if time_logs and time_logs[-1].action == 'pause':
            # Auto-resume before ending
            self.resume_session(booking_id)

        # Update booking
        now = datetime.utcnow()
        self.booking_repo.update(
            booking,
            status=BookingStatus.COMPLETED,
            actual_end_time=now
        )

        # Create time log
        time_log = TimeLog(
            booking_id=booking_id,
            action='end',
            timestamp=now
        )
        self.booking_repo.session.add(time_log)
        self.booking_repo.session.flush()

        logger.info(f"Session ended for booking {booking_id}")
        return time_log

    def cancel_booking(self, booking_id: int, notes: Optional[str] = None) -> Booking:
        """Cancel a booking.

        Args:
            booking_id: Booking ID
            notes: Optional cancellation notes

        Returns:
            Updated booking

        Raises:
            ValueError: If booking cannot be cancelled
        """
        booking = self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise ValueError("预约不存在")

        if booking.status == BookingStatus.COMPLETED:
            raise ValueError("已完成的预约不能取消")

        if booking.status == BookingStatus.CANCELLED:
            raise ValueError("预约已取消")

        self.booking_repo.update(
            booking,
            status=BookingStatus.CANCELLED,
            notes=f"{booking.notes or ''}\n取消原因: {notes or '无'}"
        )

        logger.info(f"Booking cancelled: {booking_id}")

        # Log booking cancellation
        if self.audit_service:
            # Get user ID from booking creator or use system
            user_id = booking.created_by
            self.audit_service.log_booking_cancelled(user_id, booking_id, notes or "无")

        return booking
