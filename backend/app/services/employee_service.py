import re

from pymongo.errors import DuplicateKeyError

from app.core.exceptions import AppError
from app.core.timezone import utc_now
from app.db.mongo import EMPLOYEES, PARKING_HISTORY, get_collection
from app.services.serializers import serialize_employee


def _employees():
    return get_collection(EMPLOYEES)


def list_employees(search: str | None = None, department: str | None = None) -> list[dict]:
    query: dict = {}
    if search:
        pattern = {"$regex": re.escape(search.strip()), "$options": "i"}
        query["$or"] = [{"employee_id": pattern}, {"employee_name": pattern}, {"email": pattern}]
    if department:
        query["department"] = department
    documents = _employees().find(query).sort("employee_id", 1)
    return [serialize_employee(doc) for doc in documents]


def get_employee_or_404(employee_id: str) -> dict:
    document = _employees().find_one({"employee_id": employee_id.upper()})
    if document is None:
        raise AppError(404, "EMPLOYEE_NOT_FOUND", "Employee not found.")
    return document


def create_employee(payload: dict) -> dict:
    document = {
        "employee_id": payload["employee_id"],
        "employee_name": payload["employee_name"].strip(),
        "email": payload["email"],
        "department": payload["department"].strip(),
        "role": "employee",
        "vehicle_type": payload["vehicle_type"],
        "vehicle_number": payload["vehicle_number"],
        "is_active": True,
        "created_at": utc_now(),
    }
    try:
        result = _employees().insert_one(document)
    except DuplicateKeyError as exc:
        field = "Employee ID" if "employee_id" in str(exc) else "Email"
        raise AppError(409, "DUPLICATE_EMPLOYEE", f"{field} already exists.") from exc
    document["_id"] = result.inserted_id
    return serialize_employee(document)


def update_employee(employee_id: str, changes: dict) -> dict:
    get_employee_or_404(employee_id)
    update_fields = {key: (value.strip() if isinstance(value, str) else value)
                     for key, value in changes.items() if value is not None}
    if not update_fields:
        raise AppError(400, "NO_CHANGES", "No changes were provided.")

    try:
        _employees().update_one({"employee_id": employee_id.upper()}, {"$set": update_fields})
    except DuplicateKeyError as exc:
        raise AppError(409, "DUPLICATE_EMAIL", "Email already in use by another employee.") from exc
    return serialize_employee(get_employee_or_404(employee_id))


def set_employee_active(employee_id: str, is_active: bool) -> dict:
    employee = get_employee_or_404(employee_id)
    if not is_active:
        has_active_session = get_collection(PARKING_HISTORY).find_one(
            {"employee_id": employee["employee_id"], "status": "active"}
        )
        if has_active_session:
            raise AppError(
                409,
                "ACTIVE_ALLOCATION_EXISTS",
                "Employee has an active parking slot. Release the slot before deactivating.",
            )
    _employees().update_one({"employee_id": employee["employee_id"]}, {"$set": {"is_active": is_active}})
    return serialize_employee(get_employee_or_404(employee_id))
