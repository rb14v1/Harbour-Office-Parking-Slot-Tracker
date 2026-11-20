from datetime import datetime

from bson import ObjectId

from app.core.timezone import ensure_utc, to_ist_iso


def serialize_value(value):
    """Convert Mongo-specific types into JSON-safe values."""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return to_ist_iso(value)
    if isinstance(value, list):
        return [serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {key: serialize_value(item) for key, item in value.items()}
    return value


def serialize_employee(doc: dict) -> dict:
    """Public employee view. Never includes password_hash."""
    return {
        "id": str(doc["_id"]),
        "employee_id": doc["employee_id"],
        "employee_name": doc["employee_name"],
        "email": doc["email"],
        "department": doc["department"],
        "role": doc["role"],
        "vehicle_type": doc["vehicle_type"],
        "vehicle_number": doc["vehicle_number"],
        "is_active": doc["is_active"],
        "created_at": to_ist_iso(doc.get("created_at")),
    }


def serialize_slot(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "slot_id": doc["slot_id"],
        "floor": doc["floor"],
        "location": doc["location"],
        "vehicle_type": doc["vehicle_type"],
        "status": doc["status"],
        "is_active": doc["status"] != "Inactive",
        "occupied_by": doc.get("occupied_by"),
        "occupied_at": to_ist_iso(doc.get("occupied_at")),
        "updated_at": to_ist_iso(doc.get("updated_at")),
    }


def serialize_history(doc: dict, include_personal_fields: bool = True) -> dict:
    record = {
        "id": str(doc["_id"]),
        "employee_id": doc["employee_id"] if include_personal_fields else None,
        "employee_name": doc["employee_name"] if include_personal_fields else None,
        "slot_id": doc["slot_id"],
        "vehicle_number": doc["vehicle_number"] if include_personal_fields else None,
        "entry_time": to_ist_iso(doc.get("entry_time")),
        "exit_time": to_ist_iso(doc.get("exit_time")),
        "duration_minutes": doc.get("duration_minutes"),
        "status": doc["status"],
    }
    return record


def serialize_booking(doc: dict, now: datetime) -> dict:
    """Booking view with derived flags the UI uses to decide which actions are allowed."""
    start = ensure_utc(doc["start_time"])
    end = ensure_utc(doc["end_time"])
    is_booked = doc["status"] == "booked"
    in_progress = is_booked and start <= now < end
    editable = is_booked and start > now
    if doc["status"] == "cancelled":
        state = "cancelled"
    elif end <= now:
        state = "past"
    elif in_progress:
        state = "in_progress"
    else:
        state = "upcoming"
    return {
        "id": str(doc["_id"]),
        "employee_id": doc["employee_id"],
        "employee_name": doc["employee_name"],
        "employee_email": doc.get("employee_email"),
        "slot_id": doc["slot_id"],
        "floor": doc.get("floor"),
        "location": doc.get("location"),
        "vehicle_type": doc["vehicle_type"],
        "vehicle_number": doc["vehicle_number"],
        "start_time": to_ist_iso(start),
        "end_time": to_ist_iso(end),
        "duration_minutes": round((end - start).total_seconds() / 60, 2),
        "created_at": to_ist_iso(doc.get("created_at")),
        "cancelled_at": to_ist_iso(doc.get("cancelled_at")),
        "status": doc["status"],
        "state": state,
        "editable": editable,
        "cancelable": editable,
    }
