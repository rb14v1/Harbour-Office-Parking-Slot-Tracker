"""Seed development data: 20 parking slots, 10 employees, 1 administrator and sample parking history.

Development use only. Sample employees are identified by name and email; there are no passwords.

Usage (from the backend folder, with the virtual environment active):
    python -m scripts.seed           # adds sample data only if the database is empty
    python -m scripts.seed --reset   # drops parking data and reseeds
"""

import argparse
import random
from datetime import timedelta

from app.core.timezone import utc_now
from app.db.mongo import EMPLOYEES, PARKING_HISTORY, PARKING_SLOTS, get_collection
from migrations.runner import run_migrations


# (floor, location, car_slots, bike_slots). Totals 20 slots across three floors.
FLOOR_PLAN = [
    ("G", "North Wing", 6, 2),
    ("1", "East Wing", 6, 2),
    ("2", "West Wing", 3, 1),
]

SAMPLE_EMPLOYEES = [
    ("EMP001", "Aarav Sharma", "aarav.sharma@example.com", "Engineering", "Car", "KA01AB1001"),
    ("EMP002", "Diya Patel", "diya.patel@example.com", "Finance", "Car", "KA01AB1002"),
    ("EMP003", "Rohan Mehta", "rohan.mehta@example.com", "Human Resources", "Bike", "KA01AB1003"),
    ("EMP004", "Ananya Iyer", "ananya.iyer@example.com", "Engineering", "Bike", "KA01AB1004"),
    ("EMP005", "Vikram Rao", "vikram.rao@example.com", "Sales", "Car", "KA01AB1005"),
    ("EMP006", "Meera Nair", "meera.nair@example.com", "Marketing", "Car", "KA01AB1006"),
    ("EMP007", "Karan Singh", "karan.singh@example.com", "Operations", "Bike", "KA01AB1007"),
    ("EMP008", "Sneha Reddy", "sneha.reddy@example.com", "Finance", "Car", "KA01AB1008"),
    ("EMP009", "Arjun Kumar", "arjun.kumar@example.com", "Sales", "Bike", "KA01AB1009"),
    ("EMP010", "Priya Menon", "priya.menon@example.com", "Human Resources", "Car", "KA01AB1010"),
]

# Employees who hold a slot right now: employee_id -> slot_id
CURRENTLY_PARKED = {
    "EMP001": "G-C01",
    "EMP002": "G-C02",
    "EMP004": "G-B01",
    "EMP005": "1-C01",
    "EMP007": "1-B01",
}


def build_slots() -> list[dict]:
    now = utc_now()
    slots = []
    for floor, location, car_count, bike_count in FLOOR_PLAN:
        for index in range(1, car_count + 1):
            slots.append(_slot_doc(floor, location, "Car", index, now))
        for index in range(1, bike_count + 1):
            slots.append(_slot_doc(floor, location, "Bike", index, now))
    # One reserved and one inactive slot so every status appears in the demo.
    _set_status(slots, "2-C03", "Reserved")
    _set_status(slots, "2-B01", "Inactive")
    return slots


def _slot_doc(floor: str, location: str, vehicle_type: str, index: int, now) -> dict:
    prefix = "C" if vehicle_type == "Car" else "B"
    return {
        "slot_id": f"{floor}-{prefix}{index:02d}",
        "floor": floor,
        "location": location,
        "vehicle_type": vehicle_type,
        "status": "Available",
        "occupied_by": None,
        "occupied_at": None,
        "updated_at": now,
    }


def _set_status(slots: list[dict], slot_id: str, status: str) -> None:
    for slot in slots:
        if slot["slot_id"] == slot_id:
            slot["status"] = status
            return
    raise ValueError(f"Seed slot {slot_id} is not in the floor plan.")


def build_employees() -> list[dict]:
    now = utc_now()
    return [
        {
            "employee_id": employee_id,
            "employee_name": name,
            "email": email,
            "department": department,
            "role": "employee",
            "vehicle_type": vehicle_type,
            "vehicle_number": vehicle_number,
            "is_active": True,
            "created_at": now,
        }
        for employee_id, name, email, department, vehicle_type, vehicle_number in SAMPLE_EMPLOYEES
    ]


def build_history(employees: list[dict], rng: random.Random) -> tuple[list[dict], dict[str, dict]]:
    """Creates completed sessions for the last 14 days plus the active sessions in CURRENTLY_PARKED."""
    now = utc_now()
    employee_by_id = {employee["employee_id"]: employee for employee in employees}
    slot_pool = {"Car": _slot_ids_for("Car"), "Bike": _slot_ids_for("Bike")}
    history = []

    for day_offset in range(14, 0, -1):
        for employee in employees:
            if rng.random() < 0.45:
                continue
            day_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=day_offset)
            entry = day_start + timedelta(hours=rng.randint(3, 6), minutes=rng.randint(0, 59))
            duration = rng.randint(90, 540)
            slot_id = rng.choice(slot_pool[employee["vehicle_type"]])
            history.append(_history_doc(employee, slot_id, entry, entry + timedelta(minutes=duration), duration))

    active_docs = {}
    for employee_id, slot_id in CURRENTLY_PARKED.items():
        employee = employee_by_id[employee_id]
        entry = now - timedelta(minutes=rng.randint(30, 240))
        doc = _history_doc(employee, slot_id, entry, None, None)
        active_docs[slot_id] = doc
        history.append(doc)
    return history, active_docs


def _slot_ids_for(vehicle_type: str) -> list[str]:
    prefix = "C" if vehicle_type == "Car" else "B"
    ids = []
    for floor, _location, car_count, bike_count in FLOOR_PLAN:
        count = car_count if vehicle_type == "Car" else bike_count
        ids.extend(f"{floor}-{prefix}{index:02d}" for index in range(1, count + 1))
    return [slot_id for slot_id in ids if slot_id not in ("2-B01", "2-C03")]


def _history_doc(employee: dict, slot_id: str, entry, exit_time, duration) -> dict:
    return {
        "employee_id": employee["employee_id"],
        "employee_name": employee["employee_name"],
        "slot_id": slot_id,
        "vehicle_number": employee["vehicle_number"],
        "entry_time": entry,
        "exit_time": exit_time,
        "duration_minutes": round(duration, 2) if duration is not None else None,
        "status": "completed" if exit_time else "active",
    }


def seed(reset: bool) -> None:
    run_migrations()
    employees_collection = get_collection(EMPLOYEES)
    slots_collection = get_collection(PARKING_SLOTS)
    history_collection = get_collection(PARKING_HISTORY)

    if employees_collection.count_documents({}) and not reset:
        print("Database already contains data. Run with --reset to drop and reseed.")
        return

    if reset:
        for collection in (employees_collection, slots_collection, history_collection):
            collection.delete_many({})

    employees = build_employees()
    employees_collection.insert_many(employees)

    slots = build_slots()
    rng = random.Random(42)
    history, active_by_slot = build_history(employees, rng)
    for slot in slots:
        active = active_by_slot.get(slot["slot_id"])
        if active:
            slot["status"] = "Occupied"
            slot["occupied_by"] = active["employee_id"]
            slot["occupied_at"] = active["entry_time"]
    slots_collection.insert_many(slots)

    if history:
        history_collection.insert_many(history)

    print(f"Seeded {len(slots)} slots, {len(employees)} employees, {len(history)} parking history records.")
    print("Sample employees (enter name and email on the booking or parking page):")
    for employee_id, name, email, *_ in SAMPLE_EMPLOYEES:
        print(f"  {name} <{email}>  ({employee_id})")
    print("Administrator password: value of ADMIN_PASSWORD in .env (default Admin@12345 in development).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed development data for the parking tracker.")
    parser.add_argument("--reset", action="store_true", help="Drop parking data before seeding.")
    arguments = parser.parse_args()
    seed(reset=arguments.reset)
