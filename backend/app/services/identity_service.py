import secrets

from pymongo.errors import DuplicateKeyError

from app.core.exceptions import AppError
from app.core.timezone import utc_now
from app.db.mongo import EMPLOYEES, get_collection
from app.services.serializers import serialize_employee


def _employees():
    return get_collection(EMPLOYEES)


def _new_employee_id() -> str:
    return f"EMP-{secrets.token_hex(3).upper()}"


def save_identity(payload: dict) -> dict:
    """Creates the employee on first use, or updates name and vehicle for an existing email."""
    existing = _employees().find_one({"email": payload["email"]})
    if existing and not existing["is_active"]:
        raise AppError(403, "ACCOUNT_INACTIVE", "This account is deactivated. Contact the administrator.")

    details = {
        "employee_name": payload["employee_name"],
        "vehicle_type": payload["vehicle_type"],
        "vehicle_number": payload["vehicle_number"],
    }
    if existing:
        _employees().update_one({"_id": existing["_id"]}, {"$set": details})
        return serialize_employee(_employees().find_one({"_id": existing["_id"]}))

    document = {
        "employee_id": _new_employee_id(),
        "email": payload["email"],
        "department": "General",
        "role": "employee",
        "is_active": True,
        "created_at": utc_now(),
        **details,
    }
    try:
        result = _employees().insert_one(document)
    except DuplicateKeyError as exc:
        raise AppError(409, "IDENTITY_CONFLICT", "Please try saving your details again.") from exc
    document["_id"] = result.inserted_id
    return serialize_employee(document)
