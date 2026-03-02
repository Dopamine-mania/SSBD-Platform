"""Billing service for calculating charges."""
import math
import logging
from typing import Dict
from datetime import datetime

from database.models import Booking, ResourceType, User
from utils.datetime_utils import calculate_duration_minutes, calculate_night_hours, round_up_to_interval
from config.settings import (
    BILLING_ROUND_UP_MINUTES,
    NIGHT_HOUR_START,
    NIGHT_HOUR_END,
    NIGHT_SURCHARGE_RATE,
    DEFAULT_ENGINEER_HOURLY_RATE
)

logger = logging.getLogger(__name__)

class BillingService:
    """Service for billing calculations."""

    def calculate_billing(self, booking: Booking) -> Dict[str, float]:
        """Calculate billing with 15-min rounding and night surcharge.

        Rules:
        1. Round up to nearest 15 minutes if not on 15-min boundary
        2. Night hours (22:00-08:00) get 20% surcharge
        3. Calculate: room_charge + engineer_charge + equipment_charge + night_surcharge

        Args:
            booking: Booking to calculate billing for

        Returns:
            Dictionary with billing breakdown
        """
        # Step 1: Calculate actual duration
        start = booking.actual_start_time or booking.start_time
        end = booking.actual_end_time or booking.end_time
        duration_minutes = calculate_duration_minutes(start, end, booking.pause_duration_minutes)

        # Step 2: Round up to nearest 15 minutes
        rounded_minutes = round_up_to_interval(duration_minutes, BILLING_ROUND_UP_MINUTES)
        hours = rounded_minutes / 60

        # Step 3: Calculate night hours (22:00-08:00)
        night_hours = calculate_night_hours(start, end, NIGHT_HOUR_START, NIGHT_HOUR_END)
        day_hours = hours - night_hours

        logger.info(
            f"Billing calculation for booking {booking.id}: "
            f"{duration_minutes:.1f} min -> {rounded_minutes} min ({hours:.2f} hrs), "
            f"night hours: {night_hours:.2f}"
        )

        # Step 4: Calculate charges
        room_charge = 0.0
        equipment_charge = 0.0

        for booking_resource in booking.booking_resources:
            resource = booking_resource.resource
            rate = resource.hourly_rate

            if resource.resource_type in [ResourceType.RECORDING_ROOM, ResourceType.CONTROL_ROOM]:
                room_charge += rate * hours
            else:
                equipment_charge += rate * hours * booking_resource.quantity

        # Engineer charge
        engineer_charge = 0.0
        if booking.engineer_user:
            engineer_rate = self._get_engineer_hourly_rate(booking.engineer_user)
            engineer_charge = engineer_rate * hours

        # Step 5: Calculate night surcharge (20% on night hours)
        if night_hours > 0:
            base_charges = room_charge + engineer_charge + equipment_charge
            night_surcharge = base_charges * (night_hours / hours) * NIGHT_SURCHARGE_RATE
        else:
            night_surcharge = 0.0

        # Step 6: Total
        subtotal = room_charge + engineer_charge + equipment_charge
        total = subtotal + night_surcharge

        result = {
            'room_charge': round(room_charge, 2),
            'engineer_charge': round(engineer_charge, 2),
            'equipment_charge': round(equipment_charge, 2),
            'night_surcharge': round(night_surcharge, 2),
            'subtotal': round(subtotal, 2),
            'total': round(total, 2),
            'hours': round(hours, 2),
            'night_hours': round(night_hours, 2),
            'day_hours': round(day_hours, 2)
        }

        logger.info(f"Billing result for booking {booking.id}: {result}")
        return result

    def _get_engineer_hourly_rate(self, engineer: User) -> float:
        """Get engineer hourly rate.

        Args:
            engineer: Engineer user

        Returns:
            Hourly rate
        """
        # In a real system, this could be stored in a separate table or user profile
        # For now, use default rate
        return DEFAULT_ENGINEER_HOURLY_RATE

    def estimate_billing(
        self,
        start_time: datetime,
        end_time: datetime,
        room_rate: float = 0.0,
        engineer_rate: float = 0.0,
        equipment_rates: list[tuple[float, int]] = None
    ) -> Dict[str, float]:
        """Estimate billing for a potential booking.

        Args:
            start_time: Start time
            end_time: End time
            room_rate: Room hourly rate
            engineer_rate: Engineer hourly rate
            equipment_rates: List of (rate, quantity) tuples for equipment

        Returns:
            Dictionary with billing estimate
        """
        duration_minutes = calculate_duration_minutes(start_time, end_time)
        rounded_minutes = round_up_to_interval(duration_minutes, BILLING_ROUND_UP_MINUTES)
        hours = rounded_minutes / 60

        night_hours = calculate_night_hours(start_time, end_time, NIGHT_HOUR_START, NIGHT_HOUR_END)

        room_charge = room_rate * hours
        engineer_charge = engineer_rate * hours

        equipment_charge = 0.0
        if equipment_rates:
            for rate, quantity in equipment_rates:
                equipment_charge += rate * hours * quantity

        if night_hours > 0:
            base_charges = room_charge + engineer_charge + equipment_charge
            night_surcharge = base_charges * (night_hours / hours) * NIGHT_SURCHARGE_RATE
        else:
            night_surcharge = 0.0

        subtotal = room_charge + engineer_charge + equipment_charge
        total = subtotal + night_surcharge

        return {
            'room_charge': round(room_charge, 2),
            'engineer_charge': round(engineer_charge, 2),
            'equipment_charge': round(equipment_charge, 2),
            'night_surcharge': round(night_surcharge, 2),
            'subtotal': round(subtotal, 2),
            'total': round(total, 2),
            'hours': round(hours, 2),
            'night_hours': round(night_hours, 2)
        }
