"""Tests for billing service."""
import pytest
from datetime import datetime, timedelta

from database.models import Booking, BookingResource, BookingStatus
from services.billing_service import BillingService

class TestBillingService:
    """Test billing service calculations."""

    def test_15_minute_rounding_exact(self, billing_service, test_session, sample_room, sample_customer, sample_admin):
        """Test billing with exact 15-minute duration."""
        # 30 minutes exactly
        start = datetime(2024, 1, 1, 10, 0)
        end = datetime(2024, 1, 1, 10, 30)

        booking = Booking(
            customer_id=sample_customer.id,
            created_by=sample_admin.id,
            start_time=start,
            end_time=end,
            actual_start_time=start,
            actual_end_time=end,
            status=BookingStatus.COMPLETED
        )
        test_session.add(booking)
        test_session.flush()

        booking_resource = BookingResource(
            booking_id=booking.id,
            resource_id=sample_room.id,
            quantity=1
        )
        test_session.add(booking_resource)
        test_session.commit()

        # Refresh to load relationships
        test_session.refresh(booking)

        result = billing_service.calculate_billing(booking)

        assert result['hours'] == 0.5  # 30 minutes = 0.5 hours
        assert result['room_charge'] == 100.0  # 200 * 0.5
        assert result['night_surcharge'] == 0.0  # No night hours
        assert result['total'] == 100.0

    def test_15_minute_rounding_up_13_minutes(self, billing_service, test_session, sample_room, sample_customer, sample_admin):
        """Test billing rounds up 13 minutes to 15 minutes."""
        # 13 minutes should round up to 15
        start = datetime(2024, 1, 1, 10, 0)
        end = datetime(2024, 1, 1, 10, 13)

        booking = Booking(
            customer_id=sample_customer.id,
            created_by=sample_admin.id,
            start_time=start,
            end_time=end,
            actual_start_time=start,
            actual_end_time=end,
            status=BookingStatus.COMPLETED
        )
        test_session.add(booking)
        test_session.flush()

        booking_resource = BookingResource(
            booking_id=booking.id,
            resource_id=sample_room.id,
            quantity=1
        )
        test_session.add(booking_resource)
        test_session.commit()

        test_session.refresh(booking)

        result = billing_service.calculate_billing(booking)

        assert result['hours'] == 0.25  # Rounded to 15 minutes = 0.25 hours
        assert result['room_charge'] == 50.0  # 200 * 0.25

    def test_15_minute_rounding_up_16_minutes(self, billing_service, test_session, sample_room, sample_customer, sample_admin):
        """Test billing rounds up 16 minutes to 30 minutes."""
        # 16 minutes should round up to 30
        start = datetime(2024, 1, 1, 10, 0)
        end = datetime(2024, 1, 1, 10, 16)

        booking = Booking(
            customer_id=sample_customer.id,
            created_by=sample_admin.id,
            start_time=start,
            end_time=end,
            actual_start_time=start,
            actual_end_time=end,
            status=BookingStatus.COMPLETED
        )
        test_session.add(booking)
        test_session.flush()

        booking_resource = BookingResource(
            booking_id=booking.id,
            resource_id=sample_room.id,
            quantity=1
        )
        test_session.add(booking_resource)
        test_session.commit()

        test_session.refresh(booking)

        result = billing_service.calculate_billing(booking)

        assert result['hours'] == 0.5  # Rounded to 30 minutes = 0.5 hours
        assert result['room_charge'] == 100.0  # 200 * 0.5

    def test_night_surcharge_full_night(self, billing_service, test_session, sample_room, sample_customer, sample_admin):
        """Test night surcharge for booking entirely in night hours."""
        # 23:00 - 01:00 (2 hours, all night)
        start = datetime(2024, 1, 1, 23, 0)
        end = datetime(2024, 1, 2, 1, 0)

        booking = Booking(
            customer_id=sample_customer.id,
            created_by=sample_admin.id,
            start_time=start,
            end_time=end,
            actual_start_time=start,
            actual_end_time=end,
            status=BookingStatus.COMPLETED
        )
        test_session.add(booking)
        test_session.flush()

        booking_resource = BookingResource(
            booking_id=booking.id,
            resource_id=sample_room.id,
            quantity=1
        )
        test_session.add(booking_resource)
        test_session.commit()

        test_session.refresh(booking)

        result = billing_service.calculate_billing(booking)

        assert result['hours'] == 2.0
        assert result['night_hours'] == 2.0
        assert result['room_charge'] == 400.0  # 200 * 2
        assert result['night_surcharge'] == 80.0  # 400 * 0.20
        assert result['total'] == 480.0  # 400 + 80

    def test_night_surcharge_partial_night(self, billing_service, test_session, sample_room, sample_customer, sample_admin):
        """Test night surcharge for booking partially in night hours."""
        # 21:00 - 23:00 (2 hours, 1 hour night)
        start = datetime(2024, 1, 1, 21, 0)
        end = datetime(2024, 1, 1, 23, 0)

        booking = Booking(
            customer_id=sample_customer.id,
            created_by=sample_admin.id,
            start_time=start,
            end_time=end,
            actual_start_time=start,
            actual_end_time=end,
            status=BookingStatus.COMPLETED
        )
        test_session.add(booking)
        test_session.flush()

        booking_resource = BookingResource(
            booking_id=booking.id,
            resource_id=sample_room.id,
            quantity=1
        )
        test_session.add(booking_resource)
        test_session.commit()

        test_session.refresh(booking)

        result = billing_service.calculate_billing(booking)

        assert result['hours'] == 2.0
        assert result['night_hours'] == 1.0  # Only 22:00-23:00 is night
        assert result['room_charge'] == 400.0  # 200 * 2
        # Night surcharge: 400 * (1/2) * 0.20 = 40
        assert result['night_surcharge'] == 40.0
        assert result['total'] == 440.0

    def test_night_surcharge_no_night(self, billing_service, test_session, sample_room, sample_customer, sample_admin):
        """Test no night surcharge for daytime booking."""
        # 10:00 - 12:00 (2 hours, no night)
        start = datetime(2024, 1, 1, 10, 0)
        end = datetime(2024, 1, 1, 12, 0)

        booking = Booking(
            customer_id=sample_customer.id,
            created_by=sample_admin.id,
            start_time=start,
            end_time=end,
            actual_start_time=start,
            actual_end_time=end,
            status=BookingStatus.COMPLETED
        )
        test_session.add(booking)
        test_session.flush()

        booking_resource = BookingResource(
            booking_id=booking.id,
            resource_id=sample_room.id,
            quantity=1
        )
        test_session.add(booking_resource)
        test_session.commit()

        test_session.refresh(booking)

        result = billing_service.calculate_billing(booking)

        assert result['hours'] == 2.0
        assert result['night_hours'] == 0.0
        assert result['night_surcharge'] == 0.0
        assert result['total'] == 400.0  # No surcharge

    def test_multi_day_booking(self, billing_service, test_session, sample_room, sample_customer, sample_admin):
        """Test billing for multi-day booking."""
        # 22:00 Day 1 to 10:00 Day 2 (12 hours)
        start = datetime(2024, 1, 1, 22, 0)
        end = datetime(2024, 1, 2, 10, 0)

        booking = Booking(
            customer_id=sample_customer.id,
            created_by=sample_admin.id,
            start_time=start,
            end_time=end,
            actual_start_time=start,
            actual_end_time=end,
            status=BookingStatus.COMPLETED
        )
        test_session.add(booking)
        test_session.flush()

        booking_resource = BookingResource(
            booking_id=booking.id,
            resource_id=sample_room.id,
            quantity=1
        )
        test_session.add(booking_resource)
        test_session.commit()

        test_session.refresh(booking)

        result = billing_service.calculate_billing(booking)

        assert result['hours'] == 12.0
        # Night hours: 22:00-24:00 (2h) + 00:00-08:00 (8h) = 10h
        assert result['night_hours'] == 10.0
        assert result['room_charge'] == 2400.0  # 200 * 12
        # Night surcharge: 2400 * (10/12) * 0.20 = 400
        assert result['night_surcharge'] == 400.0
        assert result['total'] == 2800.0

    def test_pause_duration_subtracted(self, billing_service, test_session, sample_room, sample_customer, sample_admin):
        """Test that pause duration is subtracted from billing."""
        # 2 hours with 30 minutes pause = 1.5 hours billed
        start = datetime(2024, 1, 1, 10, 0)
        end = datetime(2024, 1, 1, 12, 0)

        booking = Booking(
            customer_id=sample_customer.id,
            created_by=sample_admin.id,
            start_time=start,
            end_time=end,
            actual_start_time=start,
            actual_end_time=end,
            pause_duration_minutes=30,
            status=BookingStatus.COMPLETED
        )
        test_session.add(booking)
        test_session.flush()

        booking_resource = BookingResource(
            booking_id=booking.id,
            resource_id=sample_room.id,
            quantity=1
        )
        test_session.add(booking_resource)
        test_session.commit()

        test_session.refresh(booking)

        result = billing_service.calculate_billing(booking)

        assert result['hours'] == 1.5  # 120 - 30 = 90 minutes = 1.5 hours
        assert result['room_charge'] == 300.0  # 200 * 1.5

    def test_equipment_charge(self, billing_service, test_session, sample_room, sample_equipment, sample_customer, sample_admin):
        """Test billing with equipment charges."""
        start = datetime(2024, 1, 1, 10, 0)
        end = datetime(2024, 1, 1, 12, 0)

        booking = Booking(
            customer_id=sample_customer.id,
            created_by=sample_admin.id,
            start_time=start,
            end_time=end,
            actual_start_time=start,
            actual_end_time=end,
            status=BookingStatus.COMPLETED
        )
        test_session.add(booking)
        test_session.flush()

        # Add room
        booking_resource1 = BookingResource(
            booking_id=booking.id,
            resource_id=sample_room.id,
            quantity=1
        )
        test_session.add(booking_resource1)

        # Add equipment (2 microphones)
        booking_resource2 = BookingResource(
            booking_id=booking.id,
            resource_id=sample_equipment.id,
            quantity=2
        )
        test_session.add(booking_resource2)
        test_session.commit()

        test_session.refresh(booking)

        result = billing_service.calculate_billing(booking)

        assert result['hours'] == 2.0
        assert result['room_charge'] == 400.0  # 200 * 2
        assert result['equipment_charge'] == 200.0  # 50 * 2 * 2
        assert result['subtotal'] == 600.0
        assert result['total'] == 600.0

    def test_engineer_charge(self, billing_service, test_session, sample_room, sample_customer, sample_admin, sample_engineer):
        """Test billing with engineer charges."""
        start = datetime(2024, 1, 1, 10, 0)
        end = datetime(2024, 1, 1, 12, 0)

        booking = Booking(
            customer_id=sample_customer.id,
            created_by=sample_admin.id,
            engineer_id=sample_engineer.id,
            start_time=start,
            end_time=end,
            actual_start_time=start,
            actual_end_time=end,
            status=BookingStatus.COMPLETED
        )
        test_session.add(booking)
        test_session.flush()

        booking_resource = BookingResource(
            booking_id=booking.id,
            resource_id=sample_room.id,
            quantity=1
        )
        test_session.add(booking_resource)
        test_session.commit()

        test_session.refresh(booking)

        result = billing_service.calculate_billing(booking)

        assert result['hours'] == 2.0
        assert result['room_charge'] == 400.0  # 200 * 2
        assert result['engineer_charge'] == 200.0  # 100 * 2 (default rate)
        assert result['subtotal'] == 600.0
        assert result['total'] == 600.0
