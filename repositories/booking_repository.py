"""Booking repository for booking data access."""
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_

from database.models import Booking, BookingResource, BookingStatus
from repositories.base_repository import BaseRepository

class BookingRepository(BaseRepository[Booking]):
    """Repository for Booking entity."""

    def __init__(self, session: Session):
        super().__init__(Booking, session)

    def get_with_resources(self, booking_id: int) -> Optional[Booking]:
        """Get booking with resources eagerly loaded.

        Args:
            booking_id: Booking ID

        Returns:
            Booking with resources or None
        """
        return (
            self.session.query(Booking)
            .options(joinedload(Booking.booking_resources).joinedload(BookingResource.resource))
            .filter(Booking.id == booking_id)
            .first()
        )

    def get_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Booking]:
        """Get bookings within date range.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            List of bookings
        """
        return (
            self.session.query(Booking)
            .filter(
                and_(
                    Booking.start_time < end_date,
                    Booking.end_time > start_date
                )
            )
            .all()
        )

    def check_resource_conflicts(
        self,
        resource_ids: List[int],
        start_time: datetime,
        end_time: datetime,
        exclude_booking_id: Optional[int] = None
    ) -> List[Booking]:
        """Check for booking conflicts with specified resources.

        Args:
            resource_ids: List of resource IDs to check
            start_time: Booking start time
            end_time: Booking end time
            exclude_booking_id: Booking ID to exclude from check (for updates)

        Returns:
            List of conflicting bookings
        """
        query = (
            self.session.query(Booking)
            .join(BookingResource)
            .filter(
                and_(
                    BookingResource.resource_id.in_(resource_ids),
                    Booking.start_time < end_time,
                    Booking.end_time > start_time,
                    Booking.status.in_([
                        BookingStatus.PENDING,
                        BookingStatus.CONFIRMED,
                        BookingStatus.IN_PROGRESS
                    ])
                )
            )
        )

        if exclude_booking_id:
            query = query.filter(Booking.id != exclude_booking_id)

        return query.all()

    def get_by_customer(self, customer_id: int) -> List[Booking]:
        """Get all bookings for a customer.

        Args:
            customer_id: Customer ID

        Returns:
            List of bookings
        """
        return (
            self.session.query(Booking)
            .filter(Booking.customer_id == customer_id)
            .order_by(Booking.start_time.desc())
            .all()
        )

    def get_by_engineer(self, engineer_id: int) -> List[Booking]:
        """Get all bookings assigned to an engineer.

        Args:
            engineer_id: Engineer user ID

        Returns:
            List of bookings
        """
        return (
            self.session.query(Booking)
            .filter(Booking.engineer_id == engineer_id)
            .order_by(Booking.start_time.desc())
            .all()
        )

    def get_active_bookings(self) -> List[Booking]:
        """Get all active (in-progress) bookings.

        Returns:
            List of active bookings
        """
        return (
            self.session.query(Booking)
            .filter(Booking.status == BookingStatus.IN_PROGRESS)
            .all()
        )
