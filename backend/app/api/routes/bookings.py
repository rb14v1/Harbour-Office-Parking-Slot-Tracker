from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_identity, get_viewer
from app.core.exceptions import AppError
from app.schemas.booking import BookingPayload
from app.schemas.common import success_response
from app.services import booking_service

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.get("")
def list_bookings(
    scope: Literal["upcoming", "past", "all"] = "upcoming",
    employee_id: Optional[str] = Query(default=None, max_length=20),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    employee: dict = Depends(get_viewer),
):
    result = booking_service.list_bookings(employee, scope, employee_id, page, page_size)
    return success_response(result)


@router.get("/available-slots")
def available_slots(
    start_time: datetime,
    end_time: datetime,
    vehicle_type: Optional[Literal["Car", "Bike"]] = Query(default=None),
    viewer: dict = Depends(get_viewer),
):
    # Employees always use their own vehicle type. An administrator must name the vehicle type (for example when editing).
    vehicle = viewer.get("vehicle_type") or vehicle_type
    if not vehicle:
        raise AppError(400, "VEHICLE_TYPE_REQUIRED", "Choose a vehicle type to see available slots.")
    slots = booking_service.available_slots_for_window(vehicle, start_time, end_time)
    return success_response({"slots": slots, "count": len(slots)})


@router.post("", status_code=201)
def create_booking(payload: BookingPayload, employee: dict = Depends(get_identity)):
    booking = booking_service.create_booking(employee, payload.slot_id, payload.start_time, payload.end_time)
    return success_response(booking, message=f"Slot {booking['slot_id']} booked.", status_code=201)


@router.patch("/{booking_id}")
def update_booking(booking_id: str, payload: BookingPayload, employee: dict = Depends(get_viewer)):
    booking = booking_service.update_booking(employee, booking_id, payload.slot_id, payload.start_time, payload.end_time)
    return success_response(booking, message="Booking updated.")


@router.post("/{booking_id}/cancel")
def cancel_booking(booking_id: str, employee: dict = Depends(get_viewer)):
    booking = booking_service.cancel_booking(employee, booking_id)
    return success_response(booking, message="Booking cancelled.")
