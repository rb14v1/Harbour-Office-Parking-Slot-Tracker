import math
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ASCENDING, DESCENDING, ReturnDocument
from pymongo.errors import PyMongoError

from app.core.exceptions import AppError
from app.core.timezone import utc_now
from app.db.mongo import BOOKINGS, PARKING_SLOTS, get_collection
from app.services.serializers import serialize_booking, serialize_slot
from app.services.slot_service import get_slot_or_404

MIN_DURATION = timedelta(minutes=30)
MAX_DURATION = timedelta(hours=12)
MAX_ADVANCE = timedelta(days=14)
NON_BOOKABLE_SLOT_STATUSES = ("Inactive", "Reserved")
BOOKING_SCOPES = ("upcoming", "past", "all")


def _bookings():
    return get_collection(BOOKINGS)


def _to_utc(value: datetime, field: str) -> datetime:
    if value.tzinfo is None:
        raise AppError(400, "TIMEZONE_REQUIRED", f"{field} must include a timezone offset, for example +05:30.")
    return value.astimezone(timezone.utc)


def _validate_window(start_time: datetime, end_time: datetime) -> tuple[datetime, datetime]:
    start = _to_utc(start_time, "start_time")
    end = _to_utc(end_time, "end_time")
    now = utc_now()
    if start <= now:
        raise AppError(400, "BOOKING_IN_PAST", "A booking must start in the future.")
    if start - now > MAX_ADVANCE:
        raise AppError(400, "BOOKING_TOO_FAR", "Bookings can be made up to 14 days ahead.")
    if end <= start:
        raise AppError(400, "INVALID_WINDOW", "The end time must be after the start time.")
    duration = end - start
    if duration < MIN_DURATION or duration > MAX_DURATION:
        raise AppError(400, "INVALID_DURATION", "A booking must last between 30 minutes and 12 hours.")
    return start, end


def _check_slot(slot_id: str, vehicle_type: str) -> dict:
    slot = get_slot_or_404(slot_id)
    if slot["status"] in NON_BOOKABLE_SLOT_STATUSES:
        raise AppError(409, "SLOT_NOT_BOOKABLE", f"Slot {slot['slot_id']} is {slot['status'].lower()} and cannot be booked.")
    if slot["vehicle_type"] != vehicle_type:
        raise AppError(
            409,
            "VEHICLE_TYPE_MISMATCH",
            f"Slot {slot['slot_id']} is for {slot['vehicle_type']} parking. Your vehicle is a {vehicle_type}.",
        )
    return slot


def _overlapping(extra_filter: dict, start: datetime, end: datetime, exclude_id=None) -> dict | None:
    query = {
        **extra_filter,
        "status": "booked",
        "start_time": {"$lt": end},
        "end_time": {"$gt": start},
    }
    if exclude_id is not None:
        query["_id"] = {"$ne": exclude_id}
    return _bookings().find_one(query)


def _find_conflict(employee_id: str, slot_id: str, start: datetime, end: datetime, exclude_id=None) -> str | None:
    if _overlapping({"slot_id": slot_id}, start, end, exclude_id):
        return "SLOT_BOOKED"
    if _overlapping({"employee_id": employee_id}, start, end, exclude_id):
        return "EMPLOYEE_OVERLAP"
    return None


def _raise_conflict(code: str) -> None:
    if code == "SLOT_BOOKED":
        raise AppError(409, "SLOT_BOOKED", "This slot is already booked for that time. Choose another slot or time.")
    raise AppError(409, "EMPLOYEE_OVERLAP", "You already have a booking that overlaps this time.")


def _get_booking_or_404(booking_id: str) -> dict:
    try:
        object_id = ObjectId(booking_id)
    except InvalidId as exc:
        raise AppError(404, "BOOKING_NOT_FOUND", "Booking not found.") from exc
    document = _bookings().find_one({"_id": object_id})
    if document is None:
        raise AppError(404, "BOOKING_NOT_FOUND", "Booking not found.")
    return document


def _starts_in_future(booking: dict) -> bool:
    start = booking["start_time"]
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    return start > utc_now()


def _ensure_editable(booking: dict) -> None:
    if booking["status"] != "booked" or not _starts_in_future(booking):
        raise AppError(409, "BOOKING_NOT_EDITABLE", "Only upcoming bookings can be changed or cancelled.")


def create_booking(employee: dict, slot_id: str, start_time: datetime, end_time: datetime) -> dict:
    start, end = _validate_window(start_time, end_time)
    slot = _check_slot(slot_id, employee["vehicle_type"])

    conflict = _find_conflict(employee["employee_id"], slot["slot_id"], start, end)
    if conflict:
        _raise_conflict(conflict)

    document = {
        "employee_id": employee["employee_id"],
        "employee_name": employee["employee_name"],
        "employee_email": employee["email"],
        "floor": slot["floor"],
        "location": slot["location"],
        "slot_id": slot["slot_id"],
        "vehicle_type": employee["vehicle_type"],
        "vehicle_number": employee["vehicle_number"],
        "start_time": start,
        "end_time": end,
        "status": "booked",
        "created_at": utc_now(),
        "updated_at": utc_now(),
    }
    try:
        result = _bookings().insert_one(document)
    except PyMongoError as exc:
        raise AppError(503, "DATABASE_UNAVAILABLE", "Could not save the booking. Please try again.") from exc
    document["_id"] = result.inserted_id

    # Two requests can pass the check above at the same moment. Re-check after insert and withdraw
    # this booking if another overlapping one now exists. Both sides then fail, so nothing is double-booked.
    conflict = _find_conflict(employee["employee_id"], slot["slot_id"], start, end, exclude_id=document["_id"])
    if conflict:
        _bookings().delete_one({"_id": document["_id"]})
        raise AppError(409, "BOOKING_CONFLICT", "That slot or time was booked at the same moment. Please try again.")

    return serialize_booking(document, utc_now())


def update_booking(actor: dict, booking_id: str, slot_id: str, start_time: datetime, end_time: datetime) -> dict:
    booking = _get_booking_or_404(booking_id)
    if booking["employee_id"] != actor["employee_id"] and actor["role"] != "admin":
        raise AppError(403, "NOT_BOOKING_OWNER", "You can only change your own bookings.")
    _ensure_editable(booking)

    start, end = _validate_window(start_time, end_time)
    slot = _check_slot(slot_id, booking["vehicle_type"])
    conflict = _find_conflict(booking["employee_id"], slot["slot_id"], start, end, exclude_id=booking["_id"])
    if conflict:
        _raise_conflict(conflict)

    previous = {key: booking[key] for key in ("slot_id", "start_time", "end_time")}
    updated = _bookings().find_one_and_update(
        {"_id": booking["_id"], "status": "booked", "start_time": {"$gt": utc_now()}},
        {"$set": {"slot_id": slot["slot_id"], "floor": slot["floor"], "location": slot["location"],
                   "start_time": start, "end_time": end, "updated_at": utc_now()}},
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise AppError(409, "BOOKING_NOT_EDITABLE", "This booking started or changed before your update. Refresh and try again.")

    conflict = _find_conflict(booking["employee_id"], slot["slot_id"], start, end, exclude_id=booking["_id"])
    if conflict:
        _bookings().update_one({"_id": booking["_id"]}, {"$set": previous})
        _raise_conflict(conflict)

    return serialize_booking(updated, utc_now())


def cancel_booking(actor: dict, booking_id: str) -> dict:
    booking = _get_booking_or_404(booking_id)
    if booking["employee_id"] != actor["employee_id"] and actor["role"] != "admin":
        raise AppError(403, "NOT_BOOKING_OWNER", "You can only cancel your own bookings.")
    _ensure_editable(booking)

    updated = _bookings().find_one_and_update(
        {"_id": booking["_id"], "status": "booked", "start_time": {"$gt": utc_now()}},
        {"$set": {"status": "cancelled", "cancelled_at": utc_now(), "updated_at": utc_now()}},
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise AppError(409, "BOOKING_NOT_EDITABLE", "This booking has already started or been cancelled.")
    return serialize_booking(updated, utc_now())


def list_bookings(actor: dict, scope: str = "upcoming", employee_id: str | None = None, page: int = 1, page_size: int = 20) -> dict:
    if scope not in BOOKING_SCOPES:
        raise AppError(400, "INVALID_SCOPE", "scope must be upcoming, past or all.")
    now = utc_now()
    query: dict = {}
    if actor["role"] != "admin":
        query["employee_id"] = actor["employee_id"]
    elif employee_id:
        query["employee_id"] = employee_id.strip().upper()

    if scope == "upcoming":
        query.update({"status": "booked", "end_time": {"$gt": now}})
    elif scope == "past":
        query["$or"] = [{"status": "cancelled"}, {"end_time": {"$lte": now}}]

    direction = ASCENDING if scope == "upcoming" else DESCENDING
    total = _bookings().count_documents(query)
    documents = (
        _bookings()
        .find(query)
        .sort([("start_time", direction), ("_id", direction)])
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    return {
        "items": [serialize_booking(doc, now) for doc in documents],
        "scope": scope,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": max(1, math.ceil(total / page_size)),
    }


def available_slots_for_window(vehicle_type: str, start_time: datetime, end_time: datetime) -> list[dict]:
    start, end = _validate_window(start_time, end_time)
    candidates = list(
        get_collection(PARKING_SLOTS)
        .find({"vehicle_type": vehicle_type, "status": {"$nin": list(NON_BOOKABLE_SLOT_STATUSES)}})
        .sort("slot_id", ASCENDING)
    )
    busy_slot_ids = set(
        _bookings().distinct("slot_id", {"status": "booked", "start_time": {"$lt": end}, "end_time": {"$gt": start}})
    )
    return [serialize_slot(doc) for doc in candidates if doc["slot_id"] not in busy_slot_ids]
