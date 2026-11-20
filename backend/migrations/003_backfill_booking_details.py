"""Fill employee email, floor and location on bookings created before those fields were stored."""

from app.db.mongo import BOOKINGS, EMPLOYEES, PARKING_SLOTS, get_database

VERSION = "003"
DESCRIPTION = "Backfill employee_email, floor and location on existing bookings"


def apply(database=None) -> None:
    db = database if database is not None else get_database()
    for booking in db[BOOKINGS].find({"$or": [{"employee_email": {"$exists": False}}, {"floor": {"$exists": False}}, {"location": {"$exists": False}}]}):
        employee = db[EMPLOYEES].find_one({"employee_id": booking["employee_id"]}, {"email": 1})
        slot = db[PARKING_SLOTS].find_one({"slot_id": booking["slot_id"]}, {"floor": 1, "location": 1})
        updates = {
            "employee_email": employee["email"] if employee else None,
            "floor": slot["floor"] if slot else None,
            "location": slot["location"] if slot else None,
        }
        db[BOOKINGS].update_one({"_id": booking["_id"]}, {"$set": updates})
