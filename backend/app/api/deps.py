from fastapi import Request

from app.core.exceptions import AppError
from app.core.security import decode_access_token
from app.db.mongo import EMPLOYEES, get_collection

IDENTITY_HEADER = "X-Employee-Email"
ADMIN_ACCOUNT = {"role": "admin", "employee_id": None, "employee_name": "Administrator"}
GUEST = {"role": "guest", "employee_id": None, "employee_name": None}


def _bearer_token(request: Request) -> str | None:
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def _admin_from_request(request: Request) -> dict | None:
    token = _bearer_token(request)
    if token is None:
        return None
    claims = decode_access_token(token)
    if claims.get("role") != "admin":
        return None
    return ADMIN_ACCOUNT


def get_identity(request: Request) -> dict:
    """The employee named by the X-Employee-Email header. Required for personal actions."""
    email = request.headers.get(IDENTITY_HEADER, "").strip().lower()
    if not email:
        raise AppError(401, "IDENTITY_REQUIRED", "Enter your name and email first.")
    employee = get_collection(EMPLOYEES).find_one({"email": email})
    if employee is None:
        raise AppError(401, "IDENTITY_REQUIRED", "We could not find that email. Enter your name and email again.")
    if not employee["is_active"]:
        raise AppError(403, "ACCOUNT_INACTIVE", "This account is deactivated. Contact the administrator.")
    return employee


def get_viewer(request: Request) -> dict:
    """Administrator (admin token) or identified employee. Used where personal data is read."""
    admin = _admin_from_request(request)
    if admin is not None:
        return admin
    return get_identity(request)


def get_optional_viewer(request: Request) -> dict:
    """Like get_viewer, but a visitor with no identity is allowed and sees anonymous data only."""
    admin = _admin_from_request(request)
    if admin is not None:
        return admin
    if not request.headers.get(IDENTITY_HEADER, "").strip():
        return GUEST
    return get_identity(request)


def require_admin(request: Request) -> dict:
    admin = _admin_from_request(request)
    if admin is None:
        raise AppError(403, "ADMIN_REQUIRED", "Administrator login is required for this action.")
    return admin
