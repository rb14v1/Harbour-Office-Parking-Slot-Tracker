from app.db.mongo import EMPLOYEES, get_collection
from tests.conftest import IDENTITY_HEADER


def _details(**overrides):
    details = {
        "employee_name": "  Priya   Sharma ",
        "email": "Priya.Sharma@Example.com",
        "vehicle_type": "Bike",
        "vehicle_number": "ka01 xy 9999",
    }
    details.update(overrides)
    return details


def test_first_identity_creates_employee_without_password(client):
    response = client.post("/api/identity", json=_details())
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["email"] == "priya.sharma@example.com"
    assert data["employee_name"] == "Priya Sharma"
    assert data["vehicle_number"] == "KA01 XY 9999"
    assert data["employee_id"].startswith("EMP-")
    stored = get_collection(EMPLOYEES).find_one({"email": "priya.sharma@example.com"})
    assert "password_hash" not in stored


def test_saved_identity_is_used_for_personal_requests(client):
    client.post("/api/identity", json=_details())
    response = client.get("/api/identity/me", headers={IDENTITY_HEADER: "PRIYA.SHARMA@example.com"})
    assert response.status_code == 200
    assert response.json()["data"]["vehicle_type"] == "Bike"


def test_repeat_identity_updates_vehicle_for_same_email(client):
    first = client.post("/api/identity", json=_details()).json()["data"]
    second = client.post("/api/identity", json=_details(vehicle_type="Car")).json()["data"]
    assert second["id"] == first["id"]
    assert second["vehicle_type"] == "Car"


def test_name_with_digits_is_rejected(client):
    response = client.post("/api/identity", json=_details(employee_name="Priya 2"))
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_invalid_email_is_rejected(client):
    response = client.post("/api/identity", json=_details(email="not-an-email"))
    assert response.status_code == 422


def test_personal_request_without_identity_is_rejected(client):
    response = client.get("/api/parking/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "IDENTITY_REQUIRED"


def test_unknown_identity_email_is_rejected(client):
    response = client.get("/api/parking/me", headers={IDENTITY_HEADER: "nobody@example.com"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "IDENTITY_REQUIRED"


def test_deactivated_identity_is_blocked(client):
    client.post("/api/identity", json=_details())
    get_collection(EMPLOYEES).update_one({"email": "priya.sharma@example.com"}, {"$set": {"is_active": False}})
    response = client.get("/api/parking/me", headers={IDENTITY_HEADER: "priya.sharma@example.com"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ACCOUNT_INACTIVE"


def test_admin_login_with_correct_password_returns_token(client):
    from app.core.config import get_settings

    response = client.post("/api/auth/admin/login", json={"password": get_settings().admin_password})
    assert response.status_code == 200
    assert response.json()["data"]["user"]["role"] == "admin"
    assert response.json()["data"]["access_token"]


def test_admin_login_with_wrong_password_is_rejected(client):
    response = client.post("/api/auth/admin/login", json={"password": "not-the-password"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INCORRECT_ADMIN_PASSWORD"


def test_admin_endpoint_without_admin_token_is_forbidden(client, login):
    assert client.get("/api/auth/admin/me").status_code == 403
    response = client.get("/api/auth/admin/me", headers=login("EMP999"))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ADMIN_REQUIRED"


def test_tampered_admin_token_is_rejected(client, login):
    headers = login("ADMIN", admin=True)
    bad = {"Authorization": headers["Authorization"][:-4] + "abcd"}
    response = client.get("/api/auth/admin/me", headers=bad)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


def test_admin_token_is_accepted_for_admin_endpoints(client, login):
    response = client.get("/api/auth/admin/me", headers=login("ADMIN", admin=True))
    assert response.status_code == 200
