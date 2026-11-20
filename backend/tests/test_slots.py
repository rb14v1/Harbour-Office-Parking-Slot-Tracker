from app.db.mongo import PARKING_SLOTS, get_collection


def test_employee_can_list_slots_with_filters(client, make_employee, make_slot, login):
    make_employee("EMP201")
    make_slot("1-C01", vehicle_type="Car", floor="1")
    make_slot("1-B01", vehicle_type="Bike", floor="1")
    make_slot("2-C01", vehicle_type="Car", floor="2")
    headers = login("EMP201")

    by_floor = client.get("/api/slots?floor=1", headers=headers).json()["data"]["slots"]
    assert {slot["slot_id"] for slot in by_floor} == {"1-C01", "1-B01"}

    by_type = client.get("/api/slots?vehicle_type=Bike", headers=headers).json()["data"]["slots"]
    assert [slot["slot_id"] for slot in by_type] == ["1-B01"]

    by_search = client.get("/api/slots?search=2-c", headers=headers).json()["data"]["slots"]
    assert [slot["slot_id"] for slot in by_search] == ["2-C01"]


def test_available_endpoint_excludes_occupied_and_inactive(client, make_employee, make_slot, login):
    make_employee("EMP202")
    make_slot("1-C01")
    make_slot("1-C02", status="Occupied")
    make_slot("1-C03", status="Inactive")
    response = client.get("/api/slots/available?vehicle_type=Car", headers=login("EMP202"))
    assert [slot["slot_id"] for slot in response.json()["data"]["slots"]] == ["1-C01"]


def test_employee_cannot_create_slot(client, make_employee, login):
    make_employee("EMP203")
    response = client.post(
        "/api/slots",
        json={"slot_id": "9-C01", "floor": "9", "location": "Roof", "vehicle_type": "Car"},
        headers=login("EMP203"),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ADMIN_REQUIRED"


def test_admin_creates_slot_and_rejects_duplicate(client, make_employee, login):
    make_employee("ADM201", role="admin")
    headers = login("ADM201", admin=True)
    payload = {"slot_id": "3-c01", "floor": "3", "location": "Roof Wing", "vehicle_type": "Car"}
    created = client.post("/api/slots", json=payload, headers=headers)
    assert created.status_code == 201
    assert created.json()["data"]["slot_id"] == "3-C01"

    duplicate = client.post("/api/slots", json=payload, headers=headers)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "DUPLICATE_SLOT"


def test_slot_validation_rejects_bad_vehicle_type(client, make_employee, login):
    make_employee("ADM202", role="admin")
    response = client.post(
        "/api/slots",
        json={"slot_id": "4-C01", "floor": "4", "location": "Wing", "vehicle_type": "Truck"},
        headers=login("ADM202", admin=True),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_admin_updates_available_slot_location(client, make_employee, make_slot, login):
    make_employee("ADM203", role="admin")
    make_slot("1-C01")
    response = client.patch("/api/slots/1-C01", json={"location": "Relocated Wing"}, headers=login("ADM203", admin=True))
    assert response.status_code == 200
    assert response.json()["data"]["location"] == "Relocated Wing"


def test_occupied_slot_cannot_be_deactivated_or_retyped(client, make_employee, make_slot, login):
    make_employee("ADM204", role="admin")
    make_slot("1-C01", status="Occupied")
    headers = login("ADM204", admin=True)

    deactivate = client.post("/api/slots/1-C01/deactivate", headers=headers)
    assert deactivate.status_code == 409
    assert deactivate.json()["error"]["code"] == "SLOT_OCCUPIED"

    retype = client.patch("/api/slots/1-C01", json={"vehicle_type": "Bike"}, headers=headers)
    assert retype.status_code == 409


def test_deactivate_available_slot_sets_inactive(client, make_employee, make_slot, login):
    make_employee("ADM205", role="admin")
    make_slot("1-C01")
    response = client.post("/api/slots/1-C01/deactivate", headers=login("ADM205", admin=True))
    assert response.status_code == 200
    assert get_collection(PARKING_SLOTS).find_one({"slot_id": "1-C01"})["status"] == "Inactive"


def test_unknown_slot_returns_404(client, make_employee, login):
    make_employee("EMP204")
    response = client.get("/api/slots/NOPE-99", headers=login("EMP204"))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SLOT_NOT_FOUND"
