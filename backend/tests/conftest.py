import os

# Must run before any app module reads settings. Tests use a separate database so dev data is never touched.
os.environ["ENVIRONMENT"] = "test"
os.environ["MONGO_DB_NAME"] = "parking_tracker_test"
os.environ["JWT_SECRET_KEY"] = "test-only-secret-key-that-is-long-enough-1234"
os.environ["ADMIN_PASSWORD"] = "test-admin-password-123"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.core.timezone import utc_now  # noqa: E402
from app.db.mongo import BOOKINGS, EMPLOYEES, PARKING_HISTORY, PARKING_SLOTS, get_client, get_collection, close_client  # noqa: E402
from app.main import create_app  # noqa: E402

IDENTITY_HEADER = "X-Employee-Email"


def email_for(employee_id: str) -> str:
    """Test employees use <lowercase id>@example.com as their identity email."""
    return f"{employee_id.lower()}@example.com"


@pytest.fixture(scope="session")
def client():
    get_client().drop_database(get_settings().mongo_db_name)
    with TestClient(create_app()) as test_client:
        yield test_client
    close_client()


@pytest.fixture(autouse=True)
def clean_collections(client):
    for name in (EMPLOYEES, PARKING_SLOTS, PARKING_HISTORY, BOOKINGS):
        get_collection(name).delete_many({})
    yield


@pytest.fixture
def make_employee():
    def _make(employee_id, role="employee", vehicle_type="Car", is_active=True):
        document = {
            "employee_id": employee_id,
            "employee_name": f"Test {employee_id}",
            "email": email_for(employee_id),
            "department": "Testing",
            "role": role,
            "vehicle_type": vehicle_type,
            "vehicle_number": f"TN00{employee_id[-4:]}",
            "is_active": is_active,
            "created_at": utc_now(),
        }
        get_collection(EMPLOYEES).insert_one(document)
        return get_collection(EMPLOYEES).find_one({"employee_id": employee_id})

    return _make


@pytest.fixture
def make_slot():
    def _make(slot_id, vehicle_type="Car", status="Available", floor="1"):
        get_collection(PARKING_SLOTS).insert_one(
            {
                "slot_id": slot_id,
                "floor": floor,
                "location": "Test Wing",
                "vehicle_type": vehicle_type,
                "status": status,
                "occupied_by": None,
                "occupied_at": None,
                "updated_at": utc_now(),
            }
        )

    return _make


@pytest.fixture
def login(client):
    """Returns request headers for an identified employee, or for the administrator when admin=True."""

    def _login(identifier, admin=False):
        if not admin:
            return {IDENTITY_HEADER: email_for(identifier)}
        response = client.post("/api/auth/admin/login", json={"password": get_settings().admin_password})
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['data']['access_token']}"}

    return _login
