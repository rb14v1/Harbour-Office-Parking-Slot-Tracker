import logging
import math
import re
from datetime import datetime

from pymongo import ASCENDING, DESCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError, PyMongoError

from app.core.exceptions import AppError
from app.core.timezone import ensure_utc, ist_day_bounds_utc, to_ist_iso, utc_now
from app.db.mongo import BOOKINGS, PARKING_HISTORY, PARKING_SLOTS, get_collection
from app.services.serializers import serialize_history, serialize_slot
from app.services.slot_service import get_slot_or_404

logger = logging.getLogger(__name__)

EMPLOYEE_ACTIVE_INDEX = "one_active_per_employee"
SORTABLE_HISTORY_FIELDS = {"entry_time", "exit_time", "duration_minutes", "employee_id", "slot_id", "status"}


def _slots():
    return get_collection(PARKING_SLOTS)


def _history():
    return get_collection(PARKING_HISTORY)


def _find_active_session_for_employee(employee_id: str) -> dict | None:
    return _history().find_one({"employee_id": employee_id, "status": "active"})


def _rollback_slot_claim(slot_id: str, employee_id: str, claimed_at: datetime) -> None:
    """Undo a slot claim when the matching history record could not be written."""
    result = _slots().update_one(
        {"slot_id": slot_id, "status": "Occupied", "occupied_by": employee_id, "occupied_at": claimed_at},
        {"$set": {"status": "Available", "occupied_by": None, "occupied_at": None, "updated_at": utc_now()}},
    )
    if result.modified_count == 0:
        logger.error("Slot rollback did not match %s for employee %s; manual check needed", slot_id, employee_id)


def occupy_slot(employee: dict, slot_id: str) -> dict:
    """Claim a slot for an employee. Steps follow the allocation rules in the project spec."""
    employee_id = employee["employee_id"]

    # Step 3: one active allocation per employee
    if _find_active_session_for_employee(employee_id):
        raise AppError(409, "ALREADY_PARKED", "You already have an active parking slot. Release it first.")

    # Steps 4-5: slot exists, is active and suits the vehicle
    slot = get_slot_or_404(slot_id)
    if slot["status"] == "Inactive":
        raise AppError(409, "SLOT_INACTIVE", f"Slot {slot['slot_id']} is inactive and cannot be used.")
    if slot["vehicle_type"] != employee["vehicle_type"]:
        raise AppError(
            409,
            "VEHICLE_TYPE_MISMATCH",
            f"Slot {slot['slot_id']} is for {slot['vehicle_type']} parking. Your vehicle is a {employee['vehicle_type']}.",
        )

    # Another employee's booking that is in progress right now blocks this slot.
    now = utc_now()
    blocking_booking = get_collection(BOOKINGS).find_one({
        "slot_id": slot["slot_id"],
        "status": "booked",
        "employee_id": {"$ne": employee_id},
        "start_time": {"$lte": now},
        "end_time": {"$gt": now},
    })
    if blocking_booking:
        raise AppError(409, "SLOT_BOOKED", f"Slot {slot['slot_id']} is booked by another employee right now.")

    # Steps 6-7: atomic Available -> Occupied claim. Only one request can match this filter.
    claimed_at = utc_now()
    claimed = _slots().find_one_and_update(
        {"slot_id": slot["slot_id"], "status": "Available", "vehicle_type": employee["vehicle_type"]},
        {"$set": {"status": "Occupied", "occupied_by": employee_id, "occupied_at": claimed_at, "updated_at": claimed_at}},
        return_document=ReturnDocument.AFTER,
    )
    if claimed is None:
        raise AppError(409, "SLOT_NOT_AVAILABLE", f"Slot {slot['slot_id']} is no longer available. Choose another slot.")

    # Steps 8-9: history record. Partial unique index blocks a second active session for this employee.
    history_document = {
        "employee_id": employee_id,
        "employee_name": employee["employee_name"],
        "slot_id": slot["slot_id"],
        "vehicle_number": employee["vehicle_number"],
        "entry_time": claimed_at,
        "exit_time": None,
        "duration_minutes": None,
        "status": "active",
    }
    try:
        result = _history().insert_one(history_document)
    except DuplicateKeyError as exc:
        _rollback_slot_claim(slot["slot_id"], employee_id, claimed_at)
        if EMPLOYEE_ACTIVE_INDEX in str(exc):
            raise AppError(409, "ALREADY_PARKED", "You already have an active parking slot. Release it first.") from exc
        raise AppError(409, "SLOT_NOT_AVAILABLE", f"Slot {slot['slot_id']} is no longer available.") from exc
    except PyMongoError as exc:
        _rollback_slot_claim(slot["slot_id"], employee_id, claimed_at)
        logger.exception("Failed to write parking history for %s", slot["slot_id"])
        raise AppError(503, "DATABASE_UNAVAILABLE", "Could not record the parking entry. Please try again.") from exc

    history_document["_id"] = result.inserted_id
    return {
        "allocation": serialize_history(history_document),
        "slot": serialize_slot(claimed),
        "message": f"Slot {slot['slot_id']} is now allocated to you.",
    }


def release_slot(actor: dict, slot_id: str | None) -> dict:
    """Release the actor's own slot, or a specific slot when the actor is an administrator."""
    if slot_id:
        active = _history().find_one({"slot_id": slot_id, "status": "active"})
        if active is None:
            raise AppError(409, "SLOT_NOT_OCCUPIED", f"Slot {slot_id} is not currently occupied.")
        if actor["role"] != "admin" and active["employee_id"] != actor["employee_id"]:
            raise AppError(403, "NOT_SLOT_OWNER", "You can only release your own parking slot.")
    else:
        active = _find_active_session_for_employee(actor["employee_id"])
        if active is None:
            raise AppError(409, "NO_ACTIVE_ALLOCATION", "You do not have an active parking slot.")

    # Steps 2-4: record exit time, duration and mark the history record completed.
    exit_time = utc_now()
    entry_time = ensure_utc(active["entry_time"])
    duration_minutes = round((exit_time - entry_time).total_seconds() / 60, 2)
    history_update = _history().update_one(
        {"_id": active["_id"], "status": "active"},
        {"$set": {"status": "completed", "exit_time": exit_time, "duration_minutes": duration_minutes}},
    )
    if history_update.modified_count == 0:
        raise AppError(409, "ALREADY_RELEASED", "This slot was already released. Refresh and try again.")

    # Steps 5-6: free the slot only if it still belongs to this session.
    slot_update = _slots().update_one(
        {"slot_id": active["slot_id"], "status": "Occupied", "occupied_by": active["employee_id"]},
        {"$set": {"status": "Available", "occupied_by": None, "occupied_at": None, "updated_at": exit_time}},
    )
    if slot_update.modified_count == 0:
        _history().update_one(
            {"_id": active["_id"]},
            {"$set": {"status": "active", "exit_time": None, "duration_minutes": None}},
        )
        raise AppError(500, "SLOT_STATE_MISMATCH", "Slot state did not match its record. Nothing was changed.")

    return {
        "slot_id": active["slot_id"],
        "employee_id": active["employee_id"],
        "entry_time": to_ist_iso(entry_time),
        "exit_time": to_ist_iso(exit_time),
        "duration_minutes": duration_minutes,
        "message": f"Slot {active['slot_id']} has been released.",
    }


def get_current_allocation(employee_id: str) -> dict | None:
    active = _find_active_session_for_employee(employee_id)
    if active is None:
        return None
    slot = _slots().find_one({"slot_id": active["slot_id"]})
    return {
        "allocation": serialize_history(active),
        "slot": serialize_slot(slot) if slot else None,
        "elapsed_minutes": round((utc_now() - ensure_utc(active["entry_time"])).total_seconds() / 60, 2),
    }


def list_available_slots_for_vehicle(vehicle_type: str) -> list[dict]:
    documents = _slots().find({"status": "Available", "vehicle_type": vehicle_type}).sort("slot_id", ASCENDING)
    return [serialize_slot(doc) for doc in documents]


def get_occupancy_monitor() -> list[dict]:
    """Occupied slots with the employee holding each one (administrator view)."""
    occupied_slots = _slots().find({"status": "Occupied"}).sort("slot_id", ASCENDING)
    active_by_slot = {
        doc["slot_id"]: doc for doc in _history().find({"status": "active"})
    }
    rows = []
    now = utc_now()
    for slot_doc in occupied_slots:
        session = active_by_slot.get(slot_doc["slot_id"])
        row = serialize_slot(slot_doc)
        row["employee_name"] = session["employee_name"] if session else None
        row["vehicle_number"] = session["vehicle_number"] if session else None
        row["entry_time"] = to_ist_iso(session["entry_time"]) if session else None
        row["elapsed_minutes"] = (
            round((now - ensure_utc(session["entry_time"])).total_seconds() / 60, 2) if session else None
        )
        rows.append(row)
    return rows


def list_history(
    actor: dict,
    employee_id: str | None = None,
    slot_id: str | None = None,
    date_from=None,
    date_to=None,
    sort_by: str = "entry_time",
    sort_order: str = "desc",
    page: int = 1,
    page_size: int = 10,
) -> dict:
    if sort_by not in SORTABLE_HISTORY_FIELDS:
        raise AppError(400, "INVALID_SORT", f"sort_by must be one of: {', '.join(sorted(SORTABLE_HISTORY_FIELDS))}.")
    if date_from and date_to and date_to < date_from:
        raise AppError(400, "INVALID_DATE_RANGE", "End date must be on or after the start date.")

    query: dict = {}
    if actor["role"] != "admin":
        query["employee_id"] = actor["employee_id"]
    elif employee_id:
        query["employee_id"] = employee_id.strip().upper()
    if slot_id:
        query["slot_id"] = {"$regex": re.escape(slot_id.strip().upper()), "$options": "i"}
    if date_from or date_to:
        start = date_from or date_to
        end = date_to or date_from
        start_utc, end_utc = ist_day_bounds_utc(start, end)
        query["entry_time"] = {"$gte": start_utc, "$lt": end_utc}

    direction = ASCENDING if sort_order == "asc" else DESCENDING
    total = _history().count_documents(query)
    documents = (
        _history()
        .find(query)
        .sort([(sort_by, direction), ("_id", direction)])
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    return {
        "items": [serialize_history(doc) for doc in documents],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": max(1, math.ceil(total / page_size)),
    }
