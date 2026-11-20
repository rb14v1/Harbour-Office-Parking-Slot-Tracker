import threading

from app.core.exceptions import AppError
from app.db.mongo import EMPLOYEES, PARKING_HISTORY, PARKING_SLOTS, get_collection
from app.services import parking_service


def _slot(slot_id):
    return get_collection(PARKING_SLOTS).find_one({"slot_id": slot_id})


def _active_count(slot_id=None, employee_id=None):
    query = {"status": "active"}
    if slot_id:
        query["slot_id"] = slot_id
    if employee_id:
        query["employee_id"] = employee_id
    return get_collection(PARKING_HISTORY).count_documents(query)


def test_employee_occupies_available_slot(client, make_employee, make_slot, login):
    make_employee("EMP301")
    make_slot("1-C01")
    response = client.post("/api/parking/occupy", json={"slot_id": "1-c01"}, headers=login("EMP301"))
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["slot"]["status"] == "Occupied"
    assert data["allocation"]["status"] == "active"
    assert data["allocation"]["exit_time"] is None

    slot = _slot("1-C01")
    assert slot["status"] == "Occupied"
    assert slot["occupied_by"] == "EMP301"
    assert _active_count(slot_id="1-C01", employee_id="EMP301") == 1


def test_occupying_an_occupied_slot_is_rejected(client, make_employee, make_slot, login):
    make_employee("EMP302")
    make_employee("EMP303")
    make_slot("1-C01")
    client.post("/api/parking/occupy", json={"slot_id": "1-C01"}, headers=login("EMP302"))
    response = client.post("/api/parking/occupy", json={"slot_id": "1-C01"}, headers=login("EMP303"))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SLOT_NOT_AVAILABLE"
    assert _slot("1-C01")["occupied_by"] == "EMP302"


def test_employee_cannot_hold_two_slots(client, make_employee, make_slot, login):
    make_employee("EMP304")
    make_slot("1-C01")
    make_slot("1-C02")
    headers = login("EMP304")
    assert client.post("/api/parking/occupy", json={"slot_id": "1-C01"}, headers=headers).status_code == 201
    second = client.post("/api/parking/occupy", json={"slot_id": "1-C02"}, headers=headers)
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "ALREADY_PARKED"
    assert _slot("1-C02")["status"] == "Available"
    assert _active_count(employee_id="EMP304") == 1


def test_vehicle_type_mismatch_is_rejected(client, make_employee, make_slot, login):
    make_employee("EMP305", vehicle_type="Bike")
    make_slot("1-C01", vehicle_type="Car")
    response = client.post("/api/parking/occupy", json={"slot_id": "1-C01"}, headers=login("EMP305"))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "VEHICLE_TYPE_MISMATCH"


def test_inactive_slot_cannot_be_occupied(client, make_employee, make_slot, login):
    make_employee("EMP306")
    make_slot("1-C01", status="Inactive")
    response = client.post("/api/parking/occupy", json={"slot_id": "1-C01"}, headers=login("EMP306"))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SLOT_INACTIVE"


def test_reserved_slot_cannot_be_occupied(client, make_employee, make_slot, login):
    make_employee("EMP307")
    make_slot("1-C01", status="Reserved")
    response = client.post("/api/parking/occupy", json={"slot_id": "1-C01"}, headers=login("EMP307"))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SLOT_NOT_AVAILABLE"


def test_release_own_slot_completes_history(client, make_employee, make_slot, login):
    make_employee("EMP308")
    make_slot("1-C01")
    headers = login("EMP308")
    client.post("/api/parking/occupy", json={"slot_id": "1-C01"}, headers=headers)
    response = client.post("/api/parking/release", headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["slot_id"] == "1-C01"
    assert data["duration_minutes"] >= 0

    slot = _slot("1-C01")
    assert slot["status"] == "Available"
    assert slot["occupied_by"] is None
    assert slot["occupied_at"] is None

    history = get_collection(PARKING_HISTORY).find_one({"employee_id": "EMP308"})
    assert history["status"] == "completed"
    assert history["exit_time"] is not None
    assert history["duration_minutes"] is not None


def test_employee_cannot_release_another_employees_slot(client, make_employee, make_slot, login):
    make_employee("EMP309")
    make_employee("EMP310")
    make_slot("1-C01")
    client.post("/api/parking/occupy", json={"slot_id": "1-C01"}, headers=login("EMP309"))
    response = client.post("/api/parking/release", json={"slot_id": "1-C01"}, headers=login("EMP310"))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "NOT_SLOT_OWNER"
    assert _slot("1-C01")["occupied_by"] == "EMP309"


def test_release_without_allocation_is_rejected(client, make_employee, login):
    make_employee("EMP311")
    response = client.post("/api/parking/release", headers=login("EMP311"))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "NO_ACTIVE_ALLOCATION"


def test_my_parking_reports_current_allocation(client, make_employee, make_slot, login):
    make_employee("EMP312")
    make_slot("1-C01")
    headers = login("EMP312")
    assert client.get("/api/parking/me", headers=headers).json()["data"] is None
    client.post("/api/parking/occupy", json={"slot_id": "1-C01"}, headers=headers)
    current = client.get("/api/parking/me", headers=headers).json()["data"]
    assert current["slot"]["slot_id"] == "1-C01"


def test_history_is_limited_to_own_records_for_employees(client, make_employee, make_slot, login):
    make_employee("EMP313")
    make_employee("EMP314")
    make_slot("1-C01")
    make_slot("1-C02")
    client.post("/api/parking/occupy", json={"slot_id": "1-C01"}, headers=login("EMP313"))
    client.post("/api/parking/occupy", json={"slot_id": "1-C02"}, headers=login("EMP314"))

    own = client.get("/api/parking/history", headers=login("EMP313")).json()["data"]
    assert own["total"] == 1
    assert own["items"][0]["employee_id"] == "EMP313"


def test_history_pagination_and_sorting(client, make_employee, make_slot, login):
    make_employee("ADM301", role="admin")
    for index in range(1, 4):
        make_employee(f"EMP32{index}")
        make_slot(f"1-C0{index}")
    for index in range(1, 4):
        headers = login(f"EMP32{index}")
        client.post("/api/parking/occupy", json={"slot_id": f"1-C0{index}"}, headers=headers)
        client.post("/api/parking/release", headers=headers)

    admin_headers = login("ADM301", admin=True)
    page_one = client.get("/api/parking/history?page=1&page_size=2&sort_by=slot_id&sort_order=asc", headers=admin_headers)
    data = page_one.json()["data"]
    assert data["total"] == 3
    assert data["total_pages"] == 2
    assert [item["slot_id"] for item in data["items"]] == ["1-C01", "1-C02"]

    bad_sort = client.get("/api/parking/history?sort_by=password_hash", headers=admin_headers)
    assert bad_sort.status_code == 400


def test_admin_occupancy_monitor_lists_occupied_slots(client, make_employee, make_slot, login):
    make_employee("ADM302", role="admin")
    make_employee("EMP330")
    make_slot("1-C01")
    client.post("/api/parking/occupy", json={"slot_id": "1-C01"}, headers=login("EMP330"))
    response = client.get("/api/parking/occupancy", headers=login("ADM302", admin=True))
    rows = response.json()["data"]["occupied"]
    assert [row["slot_id"] for row in rows] == ["1-C01"]
    assert rows[0]["employee_name"] == "Test EMP330"


def test_employee_cannot_access_occupancy_monitor(client, make_employee, login):
    make_employee("EMP331")
    response = client.get("/api/parking/occupancy", headers=login("EMP331"))
    assert response.status_code == 403


def test_concurrent_requests_for_same_slot_allow_exactly_one_winner(make_employee, make_slot):
    make_slot("1-C01")
    employees = [make_employee(f"EMP4{index:02d}") for index in range(1, 11)]
    barrier = threading.Barrier(len(employees))
    outcomes = []
    outcome_lock = threading.Lock()

    def attempt(employee_document):
        barrier.wait()
        try:
            parking_service.occupy_slot(employee_document, "1-C01")
            result = "ok"
        except AppError as error:
            result = error.code
        with outcome_lock:
            outcomes.append(result)

    threads = [threading.Thread(target=attempt, args=(doc,)) for doc in employees]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert outcomes.count("ok") == 1, outcomes
    assert outcomes.count("SLOT_NOT_AVAILABLE") == len(employees) - 1, outcomes
    assert _active_count(slot_id="1-C01") == 1


def test_same_employee_concurrent_requests_leave_one_allocation(make_employee, make_slot):
    employee = make_employee("EMP501")
    slot_ids = [f"1-C{index:02d}" for index in range(1, 6)]
    for slot_id in slot_ids:
        make_slot(slot_id)
    barrier = threading.Barrier(len(slot_ids))
    outcomes = []
    outcome_lock = threading.Lock()

    def attempt(slot_id):
        barrier.wait()
        try:
            parking_service.occupy_slot(employee, slot_id)
            result = "ok"
        except AppError as error:
            result = error.code
        with outcome_lock:
            outcomes.append(result)

    threads = [threading.Thread(target=attempt, args=(slot_id,)) for slot_id in slot_ids]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert outcomes.count("ok") == 1, outcomes
    assert _active_count(employee_id="EMP501") == 1
    occupied = get_collection(PARKING_SLOTS).count_documents({"status": "Occupied", "occupied_by": "EMP501"})
    assert occupied == 1, "a failed attempt left a slot claimed without a history record"
    assert get_collection(EMPLOYEES).count_documents({"employee_id": "EMP501"}) == 1
