"""Order repository for order data access."""
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_

from database.models import Order, OrderStatus, Booking, BookingStatus
from repositories.base_repository import BaseRepository


class OrderRepository(BaseRepository[Order]):
    """Repository for Order entity."""

    def __init__(self, session: Session):
        super().__init__(Order, session)

    def get_with_booking(self, order_id: int) -> Optional[Order]:
        """Get order with booking eagerly loaded.

        Args:
            order_id: Order ID

        Returns:
            Order with booking or None
        """
        return (
            self.session.query(Order)
            .options(joinedload(Order.booking))
            .filter(Order.id == order_id)
            .first()
        )

    def get_pending_orders(self) -> List[Order]:
        """Get all pending (unpaid) orders.

        Returns:
            List of pending orders
        """
        return (
            self.session.query(Order)
            .filter(Order.status == OrderStatus.PENDING)
            .order_by(Order.created_at.desc())
            .all()
        )

    def get_by_booking(self, booking_id: int) -> List[Order]:
        """Get all orders for a booking.

        Args:
            booking_id: Booking ID

        Returns:
            List of orders
        """
        return (
            self.session.query(Order)
            .filter(Order.booking_id == booking_id)
            .order_by(Order.created_at.desc())
            .all()
        )

    def get_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Order]:
        """Get orders within date range.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            List of orders
        """
        return (
            self.session.query(Order)
            .filter(
                and_(
                    Order.created_at >= start_date,
                    Order.created_at < end_date
                )
            )
            .order_by(Order.created_at.desc())
            .all()
        )

    def get_completed_bookings_without_order(self) -> List[Booking]:
        """Get completed bookings that don't have an order yet.

        Returns:
            List of bookings ready for billing
        """
        # Subquery to get booking IDs that already have orders
        bookings_with_orders = (
            self.session.query(Order.booking_id)
            .distinct()
        )

        return (
            self.session.query(Booking)
            .filter(
                and_(
                    Booking.status == BookingStatus.COMPLETED,
                    ~Booking.id.in_(bookings_with_orders)
                )
            )
            .order_by(Booking.end_time.desc())
            .all()
        )

    def mark_as_paid(self, order: Order, payment_method, paid_at: datetime = None) -> Order:
        """Mark order as paid.

        Args:
            order: Order to mark as paid
            payment_method: Payment method used
            paid_at: Payment timestamp (defaults to now)

        Returns:
            Updated order
        """
        if paid_at is None:
            paid_at = datetime.utcnow()

        order.status = OrderStatus.PAID
        order.payment_method = payment_method
        order.paid_at = paid_at
        self.session.flush()
        return order

    def mark_as_refunded(self, order: Order, approved_by_id: int, refunded_at: datetime = None) -> Order:
        """Mark order as refunded.

        Args:
            order: Order to refund
            approved_by_id: User ID who approved the refund
            refunded_at: Refund timestamp (defaults to now)

        Returns:
            Updated order
        """
        if refunded_at is None:
            refunded_at = datetime.utcnow()

        order.status = OrderStatus.REFUNDED
        order.refund_approved_by = approved_by_id
        order.refunded_at = refunded_at
        self.session.flush()
        return order
