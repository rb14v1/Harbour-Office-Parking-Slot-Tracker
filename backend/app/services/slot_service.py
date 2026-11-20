import re

from pymongo.errors import DuplicateKeyError

from app.core.exceptions import AppError
from app.core.timezone import utc_now
from app.db.mongo import PARKING_SLOTS, get_collection
from app.services.serializers import serialize_slot

SLOT_STATUSES = ("Available", "Occupied", "Reserved", "Inactive")


def _slots():
    return get_collection(PARKING_SLOTS)


def list_slots(
    floor: str | None = None,
    vehicle_type: str | None = None,
    status: str | None = None,
    search: str | None = None,
) -> list[dict]:
    query: dict = {}
    if floor:
        query["floor"] = floor
    if vehicle_type:
        query["vehicle_type"] = vehicle_type
    if status:
        query["status"] = status
    if search:
        query["slot_id"] = {"$regex": re.escape(search.strip()), "$options": "i"}
    documents = _slots().find(query).sort("slot_id", 1)
    return [serialize_slot(doc) for doc in documents]


def get_slot_or_404(slot_id: str) -> dict:
    document = _slots().find_one({"slot_id": slot_id.upper()})
    if document is None:
        raise AppError(404, "SLOT_NOT_FOUND", "Parking slot not found.")
    return document


def list_floors() -> list[str]:
    return sorted(_slots().distinct("floor"))


def create_slot(payload: dict) -> dict:
    document = {
        "slot_id": payload["slot_id"],
        "floor": payload["floor"].strip(),
        "location": payload["location"].strip(),
        "vehicle_type": payload["vehicle_type"],
        "status": "Available",
        "occupied_by": None,
        "occupied_at": None,
        "updated_at": utc_now(),
    }
    try:
        result = _slots().insert_one(document)
    except DuplicateKeyError as exc:
        raise AppError(409, "DUPLICATE_SLOT", f"Slot {payload['slot_id']} already exists.") from exc
    document["_id"] = result.inserted_id
    return serialize_slot(document)


def update_slot(slot_id: str, changes: dict) -> dict:
    slot = get_slot_or_404(slot_id)
    update_fields = {key: (value.strip() if isinstance(value, str) else value)
                     for key, value in changes.items() if value is not None}
    if not update_fields:
        raise AppError(400, "NO_CHANGES", "No changes were provided.")

    changes_vehicle_type = "vehicle_type" in update_fields and update_fields["vehicle_type"] != slot["vehicle_type"]
    changes_status = "status" in update_fields and update_fields["status"] != slot["status"]

    if slot["status"] == "Occupied" and (changes_vehicle_type or changes_status):
        raise AppError(
            409,
            "SLOT_OCCUPIED",
            "An occupied slot cannot change vehicle type or status. Wait for it to be released.",
        )
    if slot["status"] == "Inactive" and changes_status:
        raise AppError(409, "SLOT_INACTIVE", "Inactive slots must be reactivated before changing status.")

    update_fields["updated_at"] = utc_now()
    _slots().update_one({"slot_id": slot["slot_id"]}, {"$set": update_fields})
    return serialize_slot(get_slot_or_404(slot_id))


def deactivate_slot(slot_id: str) -> dict:
    slot = get_slot_or_404(slot_id)
    if slot["status"] == "Occupied":
        raise AppError(409, "SLOT_OCCUPIED", "Occupied slots cannot be deactivated. Release the slot first.")
    _slots().update_one(
        {"slot_id": slot["slot_id"], "status": {"$ne": "Occupied"}},
        {"$set": {"status": "Inactive", "updated_at": utc_now()}},
    )
    return serialize_slot(get_slot_or_404(slot_id))


def occupancy_summary() -> dict:
    counts = {status: 0 for status in SLOT_STATUSES}
    for row in _slots().aggregate([{"$group": {"_id": "$status", "count": {"$sum": 1}}}]):
        counts[row["_id"]] = row["count"]

    total = sum(counts.values())
    usable = total - counts["Inactive"]
    occupancy_percentage = round(counts["Occupied"] / usable * 100, 1) if usable else 0.0
    return {
        "total_slots": total,
        "available": counts["Available"],
        "occupied": counts["Occupied"],
        "reserved": counts["Reserved"],
        "inactive": counts["Inactive"],
        "usable_slots": usable,
        "occupancy_percentage": occupancy_percentage,
    }
