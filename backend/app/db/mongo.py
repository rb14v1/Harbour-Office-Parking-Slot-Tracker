from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError

from app.core.config import get_settings

EMPLOYEES = "employees"
PARKING_SLOTS = "parking_slots"
PARKING_HISTORY = "parking_history"
BOOKINGS = "bookings"

_client: MongoClient | None = None


def get_client() -> MongoClient:
    """Return a shared MongoClient. PyMongo clients are thread-safe and pool connections."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = MongoClient(
            settings.mongo_uri,
            tz_aware=True,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
        )
    return _client


def get_database() -> Database:
    return get_client()[get_settings().mongo_db_name]


def get_collection(name: str) -> Collection:
    return get_database()[name]


def ping_database() -> bool:
    try:
        get_client().admin.command("ping")
        return True
    except PyMongoError:
        return False


def close_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None
