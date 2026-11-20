"""Applies migrations in order and records each applied version in `schema_migrations`.

Run from the backend folder:  python -m migrations.runner
"""

import importlib
import pkgutil
from datetime import datetime, timezone

from app.db.mongo import get_database

MIGRATIONS_COLLECTION = "schema_migrations"


def discover_migrations() -> list:
    package = importlib.import_module("migrations")
    modules = []
    for module_info in pkgutil.iter_modules(package.__path__):
        if module_info.name[:3].isdigit():
            modules.append(importlib.import_module(f"migrations.{module_info.name}"))
    return sorted(modules, key=lambda module: module.VERSION)


def run_migrations() -> list[str]:
    db = get_database()
    applied_versions = {doc["version"] for doc in db[MIGRATIONS_COLLECTION].find({}, {"version": 1})}
    newly_applied = []
    for migration in discover_migrations():
        if migration.VERSION in applied_versions:
            continue
        migration.apply(db)
        db[MIGRATIONS_COLLECTION].insert_one(
            {
                "version": migration.VERSION,
                "description": migration.DESCRIPTION,
                "applied_at": datetime.now(timezone.utc),
            }
        )
        newly_applied.append(migration.VERSION)
    return newly_applied


if __name__ == "__main__":
    applied = run_migrations()
    if applied:
        print(f"Applied migrations: {', '.join(applied)}")
    else:
        print("Database is already up to date.")
