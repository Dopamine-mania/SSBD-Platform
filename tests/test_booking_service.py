"""Tests for booking service."""
import pytest
from datetime import datetime, timedelta

from database.models import BookingStatus
from services.booking_service import BookingService, BookingConflictError

class TestBookingService:
    """Test booking service."""

    def test_create_booking_success(self, booking_service, sample_room, sample_customer, sample_admin):
        """Test successful booking creation."""
        start = datetime(2024, 1, 1, 10, 0)
        end = datetime(2024, 1, 1, 12, 0)

        booking = booking_service.create_booking(
            customer_id=sample_customer.id,
            created_by=sample_admin.id,
            start_time=start,
            end_time=end,
            resource_ids=[sample_room.id]
        )

        assert booking.id is not None
        assert booking.customer_id == sample_customer.id
        assert booking.start_time == start
        assert booking.end_time == end
        assert booking.status == BookingStatus.PENDING

    def test_create_booking_minimum_duration(self, booking_service, sample_room, sample_customer, sample_admin):
        """Test booking with minimum duration requirement."""
        start = datetime(2024, 1, 1, 10, 0)
        end = datetime(2024, 1, 1, 10, 15)  # Only 15 minutes

        with pytest.raises(ValueError, match="预约时长不能少于"):
            booking_service.create_booking(
                customer_id=sample_customer.id,
                created_by=sample_admin.id,
                start_time=start,
                end_time=end,
                resource_ids=[sample_room.id]
            )

    def test_create_booking_invalid_time_range(self, booking_service, sample_room, sample_customer, sample_admin):
        """Test booking with invalid time range."""
        start = datetime(2024, 1, 1, 12, 0)
        end = datetime(2024, 1, 1, 10, 0)  # End before start

        with pytest.raises(ValueError, match="开始时间必须早于结束时间"):
            booking_service.create_booking(
                customer_id=sample_customer.id,
                created_by=sample_admin.id,
                start_time=start,
                end_time=end,
                resource_ids=[sample_room.id]
            )

    def test_conflict_detection_same_resource_overlap(self, booking_service, sample_room, sample_customer, sample_admin):
        """Test conflict detection for same resource with overlapping times."""
        # Create first booking
        start1 = datetime(2024, 1, 1, 10, 0)
        end1 = datetime(2024, 1, 1, 12, 0)

        booking1 = booking_service.create_booking(
            customer_id=sample_customer.id,
            created_by=sample_admin.id,
            start_time=start1,
            end_time=end1,
            resource_ids=[sample_room.id]
        )

        # Try to create overlapping booking
        start2 = datetime(2024, 1, 1, 11, 0)  # Overlaps with first booking
        end2 = datetime(2024, 1, 1, 13, 0)

        with pytest.raises(BookingConflictError, match="预约冲突"):
            booking_service.create_booking(
                customer_id=sample_customer.id,
                created_by=sample_admin.id,
                start_time=start2,
                end_time=end2,
                resource_ids=[sample_room.id]
            )

    def test_no_conflict_different_resources(self, booking_service, sample_room, sample_equipment, sample_customer, sample_admin):
        """Test no conflict for different resources at same time."""
        start = datetime(2024, 1, 1, 10, 0)
        end = datetime(2024, 1, 1, 12, 0)

        # Create first booking with room
        booking1 = booking_service.create_booking(
            customer_id=sample_customer.id,
            created_by=sample_admin.id,
            start_time=start,
            end_time=end,
            resource_ids=[sample_room.id]
        )

        # Create second booking with equipment at same time - should succeed
        booking2 = booking_service.create_booking(
            customer_id=sample_customer.id,
            created_by=sample_admin.id,
            start_time=start,
            end_time=end,
            resource_ids=[sample_equipment.id]
        )

        assert booking1.id != booking2.id

    def test_no_conflict_non_overlapping_times(self, booking_service, sample_room, sample_customer, sample_admin):
        """Test no conflict for same resource with non-overlapping times."""
        # Create first booking
        start1 = datetime(2024, 1, 1, 10, 0)
        end1 = datetime(2024, 1, 1, 12, 0)

        booking1 = booking_service.create_booking(
            customer_id=sample_customer.id,
            created_by=sample_admin.id,
            start_time=start1,
            end_time=end1,
            resource_ids=[sample_room.id]
        )

        # Create second booking after first ends - should succeed
        start2 = datetime(2024, 1, 1, 12, 0)  # Starts when first ends
        end2 = datetime(2024, 1, 1, 14, 0)

        booking2 = booking_service.create_booking(
            customer_id=sample_customer.id,
            created_by=sample_admin.id,
            start_time=start2,
            end_time=end2,
            resource_ids=[sample_room.id]
        )

        assert booking1.id != booking2.id

    def test_conflict_exact_match(self, booking_service, sample_room, sample_customer, sample_admin):
        """Test conflict detection for exact time match."""
        start = datetime(2024, 1, 1, 10, 0)
        end = datetime(2024, 1, 1, 12, 0)

        # Create first booking
        booking1 = booking_service.create_booking(
            customer_id=sample_customer.id,
            created_by=sample_admin.id,
            start_time=start,
            end_time=end,
            resource_ids=[sample_room.id]
        )

        # Try to create booking with exact same time - should conflict
        with pytest.raises(BookingConflictError):
            booking_service.create_booking(
                customer_id=sample_customer.id,
                created_by=sample_admin.id,
                start_time=start,
                end_time=end,
                resource_ids=[sample_room.id]
            )

    def test_start_session(self, booking_service, sample_room, sample_customer, sample_admin):
        """Test starting a booking session."""
        start = datetime(2024, 1, 1, 10, 0)
        end = datetime(2024, 1, 1, 12, 0)

        booking = booking_service.create_booking(
            customer_id=sample_customer.id,
            created_by=sample_admin.id,
            start_time=start,
            end_time=end,
            resource_ids=[sample_room.id]
        )

        time_log = booking_service.start_session(booking.id)

        assert time_log.action == 'start'
        assert booking.status == BookingStatus.IN_PROGRESS
        assert booking.actual_start_time is not None

    def test_pause_and_resume_session(self, booking_service, sample_room, sample_customer, sample_admin, test_session):
        """Test pausing and resuming a session."""
        start = datetime(2024, 1, 1, 10, 0)
        end = datetime(2024, 1, 1, 12, 0)

        booking = booking_service.create_booking(
            customer_id=sample_customer.id,
            created_by=sample_admin.id,
            start_time=start,
            end_time=end,
            resource_ids=[sample_room.id]
        )

        # Start session
        booking_service.start_session(booking.id)

        # Pause session
        pause_log = booking_service.pause_session(booking.id, notes="休息")
        assert pause_log.action == 'pause'

        # Resume session
        resume_log = booking_service.resume_session(booking.id)
        assert resume_log.action == 'resume'

        # Refresh booking to get updated pause duration
        test_session.refresh(booking)
        assert booking.pause_duration_minutes >= 0  # Should have calculated pause duration

    def test_end_session(self, booking_service, sample_room, sample_customer, sample_admin):
        """Test ending a booking session."""
        start = datetime(2024, 1, 1, 10, 0)
        end = datetime(2024, 1, 1, 12, 0)

        booking = booking_service.create_booking(
            customer_id=sample_customer.id,
            created_by=sample_admin.id,
            start_time=start,
            end_time=end,
            resource_ids=[sample_room.id]
        )

        # Start and end session
        booking_service.start_session(booking.id)
        end_log = booking_service.end_session(booking.id)

        assert end_log.action == 'end'
        assert booking.status == BookingStatus.COMPLETED
        assert booking.actual_end_time is not None

    def test_cancel_booking(self, booking_service, sample_room, sample_customer, sample_admin):
        """Test cancelling a booking."""
        start = datetime(2024, 1, 1, 10, 0)
        end = datetime(2024, 1, 1, 12, 0)

        booking = booking_service.create_booking(
            customer_id=sample_customer.id,
            created_by=sample_admin.id,
            start_time=start,
            end_time=end,
            resource_ids=[sample_room.id]
        )

        cancelled_booking = booking_service.cancel_booking(booking.id, notes="客户取消")

        assert cancelled_booking.status == BookingStatus.CANCELLED
        assert "客户取消" in cancelled_booking.notes
