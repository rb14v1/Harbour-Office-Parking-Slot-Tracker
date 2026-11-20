"""Checks that MongoDB is reachable, has the expected collections and indexes, and that the data is consistent.

Usage (from the backend folder, with the virtual environment active):
    python -m scripts.check_mongo

Exit code 0 = everything passed, 1 = at least one check failed.
"""

import sys
from uuid import uuid4

from app.db.mongo import BOOKINGS, EMPLOYEES, PARKING_HISTORY, PARKING_SLOTS, get_client, get_database

EXPECTED_INDEXES = {
    EMPLOYEES: ["uniq_employee_id", "uniq_email"],
    PARKING_SLOTS: ["uniq_slot_id"],
    PARKING_HISTORY: ["one_active_per_employee", "one_active_per_slot"],
    BOOKINGS: ["idx_slot_window", "idx_employee_start", "idx_status_end"],
}
EXPECTED_MIGRATIONS = {"001", "002", "003"}

results: list[tuple[bool, str]] = []


def check(passed: bool, message: str) -> None:
    results.append((passed, message))
    print(f"[{'PASS' if passed else 'FAIL'}] {message}")


def main() -> int:
    client = get_client()
    db = get_database()

    try:
        client.admin.command("ping")
        check(True, f"Server reachable (database: {db.name})")
        version = client.server_info()["version"]
        check(True, f"MongoDB server version {version}")
    except Exception as error:  # noqa: BLE001 - report any connection problem and stop
        check(False, f"Cannot reach MongoDB: {error}")
        return 1

    existing = set(db.list_collection_names())
    for name in (EMPLOYEES, PARKING_SLOTS, PARKING_HISTORY, BOOKINGS):
        if name in existing:
            count = db[name].count_documents({})
            check(True, f"Collection '{name}' exists with {count} document(s)")
        else:
            check(False, f"Collection '{name}' is missing (start the API once or run migrations)")

    for name, index_names in EXPECTED_INDEXES.items():
        if name not in existing:
            continue
        present = db[name].index_information()
        for index_name in index_names:
            check(index_name in present, f"Index '{index_name}' on '{name}'")

    history_indexes = db[PARKING_HISTORY].index_information() if PARKING_HISTORY in existing else {}
    for index_name in ("one_active_per_employee", "one_active_per_slot"):
        info = history_indexes.get(index_name, {})
        check(
            info.get("unique") is True and info.get("partialFilterExpression") == {"status": "active"},
            f"'{index_name}' is a unique index limited to active sessions",
        )

    if "schema_migrations" in existing:
        applied = {doc["version"] for doc in db["schema_migrations"].find({}, {"version": 1})}
        check(EXPECTED_MIGRATIONS <= applied, f"Migrations applied: {', '.join(sorted(applied))}")
    else:
        check(False, "schema_migrations collection missing (run: python -m migrations.runner)")

    scratch = "_healthcheck_scratch"
    marker = uuid4().hex
    try:
        db[scratch].insert_one({"marker": marker})
        found = db[scratch].find_one({"marker": marker}) is not None
        db[scratch].delete_many({"marker": marker})
        check(found, "Write, read and delete round-trip")
    except Exception as error:  # noqa: BLE001
        check(False, f"Write/read round-trip failed: {error}")

    if PARKING_SLOTS in existing and PARKING_HISTORY in existing:
        occupied = list(db[PARKING_SLOTS].find({"status": "Occupied"}, {"slot_id": 1, "occupied_by": 1}))
        active = list(db[PARKING_HISTORY].find({"status": "active"}, {"slot_id": 1, "employee_id": 1}))
        active_by_slot = {doc["slot_id"]: doc["employee_id"] for doc in active}
        mismatched = [slot["slot_id"] for slot in occupied if active_by_slot.get(slot["slot_id"]) != slot.get("occupied_by")]
        check(not mismatched, f"Occupied slots match active sessions ({len(occupied)} occupied)")
        if mismatched:
            print(f"       Mismatched slots: {', '.join(mismatched)}")
        orphan = [doc["slot_id"] for doc in active if doc["slot_id"] not in {s["slot_id"] for s in occupied}]
        check(not orphan, f"Every active session has an occupied slot ({len(active)} active)")
        if orphan:
            print(f"       Active sessions without occupied slot: {', '.join(orphan)}")

    failed = sum(1 for passed, _ in results if not passed)
    print(f"\n{len(results) - failed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
