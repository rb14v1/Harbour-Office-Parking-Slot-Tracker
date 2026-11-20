import hmac

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.security import create_access_token


def admin_login(password: str) -> dict:
    """Administrator login with the shared admin password. Compared in constant time."""
    expected = get_settings().admin_password
    if not hmac.compare_digest(password.encode("utf-8"), expected.encode("utf-8")):
        raise AppError(401, "INCORRECT_ADMIN_PASSWORD", "Incorrect administrator password.")
    token = create_access_token("ADMIN", "admin")
    return {"access_token": token, "token_type": "bearer", "user": {"role": "admin", "employee_name": "Administrator"}}
