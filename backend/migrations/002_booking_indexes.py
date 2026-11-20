"""Indexes for future slot bookings."""

from pymongo import ASCENDING

from app.db.mongo import BOOKINGS, get_database

VERSION = "002"
DESCRIPTION = "Create indexes for slot bookings"


def apply(database=None) -> None:
    db = database if database is not None else get_database()
    db[BOOKINGS].create_index(
        [("slot_id", ASCENDING), ("start_time", ASCENDING), ("end_time", ASCENDING)],
        name="idx_slot_window",
    )
    db[BOOKINGS].create_index([("employee_id", ASCENDING), ("start_time", ASCENDING)], name="idx_employee_start")
    db[BOOKINGS].create_index([("status", ASCENDING), ("end_time", ASCENDING)], name="idx_status_end")
