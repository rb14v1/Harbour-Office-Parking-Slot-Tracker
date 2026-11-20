"""Create collection indexes, including the concurrency guards for parking allocation.

Guards:
- one_active_per_employee: an employee can hold at most one active parking session.
- one_active_per_slot: a slot can have at most one active parking session.
"""

from pymongo import ASCENDING, DESCENDING

from app.db.mongo import EMPLOYEES, PARKING_HISTORY, PARKING_SLOTS, get_database

VERSION = "001"
DESCRIPTION = "Create collection indexes and active-allocation unique guards"


def apply(database=None) -> None:
    db = database if database is not None else get_database()

    db[EMPLOYEES].create_index([("employee_id", ASCENDING)], unique=True, name="uniq_employee_id")
    db[EMPLOYEES].create_index([("email", ASCENDING)], unique=True, name="uniq_email")
    db[EMPLOYEES].create_index([("department", ASCENDING)], name="idx_department")

    db[PARKING_SLOTS].create_index([("slot_id", ASCENDING)], unique=True, name="uniq_slot_id")
    db[PARKING_SLOTS].create_index(
        [("floor", ASCENDING), ("vehicle_type", ASCENDING), ("status", ASCENDING)],
        name="idx_floor_type_status",
    )
    db[PARKING_SLOTS].create_index([("status", ASCENDING)], name="idx_status")

    db[PARKING_HISTORY].create_index(
        [("employee_id", ASCENDING), ("entry_time", DESCENDING)],
        name="idx_employee_entry",
    )
    db[PARKING_HISTORY].create_index(
        [("slot_id", ASCENDING), ("entry_time", DESCENDING)],
        name="idx_slot_entry",
    )
    db[PARKING_HISTORY].create_index([("entry_time", DESCENDING)], name="idx_entry_time")
    db[PARKING_HISTORY].create_index(
        [("employee_id", ASCENDING)],
        unique=True,
        partialFilterExpression={"status": "active"},
        name="one_active_per_employee",
    )
    db[PARKING_HISTORY].create_index(
        [("slot_id", ASCENDING)],
        unique=True,
        partialFilterExpression={"status": "active"},
        name="one_active_per_slot",
    )
