import threading
from datetime import timedelta

from app.core.exceptions import AppError
from app.core.timezone import utc_now
from app.db.mongo import BOOKINGS, get_collection
from app.services import booking_service


def _window(days_ahead=2, hours=1, offset_hours=0):
    start = utc_now() + timedelta(days=days_ahead, hours=offset_hours)
    return start, start + timedelta(hours=hours)


def _payload(slot_id, start, end):
    return {"slot_id": slot_id, "start_time": start.isoformat(), "end_time": end.isoformat()}


def _insert_booking(employee_id, slot_id, start, end, status="booked", vehicle_type="Car"):
    result = get_collection(BOOKINGS).insert_one({
        "employee_id": employee_id,
        "employee_name": f"Test {employee_id}",
        "slot_id": slot_id,
        "vehicle_type": vehicle_type,
        "vehicle_number": "TN0001",
        "start_time": start,
        "end_time": end,
        "status": status,
        "created_at": utc_now(),
        "updated_at": utc_now(),
    })
    return str(result.inserted_id)


def test_employee_books_future_slot_and_sees_it_as_upcoming(client, make_employee, make_slot, login):
    make_employee("EMP601")
    make_slot("1-C01")
    headers = login("EMP601")
    start, end = _window()

    response = client.post("/api/bookings", json=_payload("1-c01", start, end), headers=headers)
    assert response.status_code == 201, response.text
    booking = response.json()["data"]
    assert booking["slot_id"] == "1-C01"
    assert booking["state"] == "upcoming"
    assert booking["editable"] is True

    upcoming = client.get("/api/bookings?scope=upcoming", headers=headers).json()["data"]
    assert [item["id"] for item in upcoming["items"]] == [booking["id"]]


def test_booking_must_start_in_the_future(client, make_employee, make_slot, login):
    make_employee("EMP602")
    make_slot("1-C01")
    start, end = _window(days_ahead=-1)
    response = client.post("/api/bookings", json=_payload("1-C01", start, end), headers=login("EMP602"))
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BOOKING_IN_PAST"


def test_booking_more_than_14_days_ahead_is_rejected(client, make_employee, make_slot, login):
    make_employee("EMP603")
    make_slot("1-C01")
    start, end = _window(days_ahead=15)
    response = client.post("/api/bookings", json=_payload("1-C01", start, end), headers=login("EMP603"))
    assert response.json()["error"]["code"] == "BOOKING_TOO_FAR"


def test_booking_duration_limits_are_enforced(client, make_employee, make_slot, login):
    make_employee("EMP604")
    make_slot("1-C01")
    headers = login("EMP604")
    short_start, short_end = _window(hours=0.25)
    long_start, long_end = _window(hours=13)
    assert client.post("/api/bookings", json=_payload("1-C01", short_start, short_end), headers=headers).json()["error"]["code"] == "INVALID_DURATION"
    assert client.post("/api/bookings", json=_payload("1-C01", long_start, long_end), headers=headers).json()["error"]["code"] == "INVALID_DURATION"


def test_booking_without_timezone_is_rejected(client, make_employee, make_slot, login):
    make_employee("EMP605")
    make_slot("1-C01")
    start, end = _window()
    naive = {"slot_id": "1-C01", "start_time": start.replace(tzinfo=None).isoformat(), "end_time": end.replace(tzinfo=None).isoformat()}
    response = client.post("/api/bookings", json=naive, headers=login("EMP605"))
    assert response.json()["error"]["code"] == "TIMEZONE_REQUIRED"


def test_booking_rejects_wrong_vehicle_type_and_unbookable_status(client, make_employee, make_slot, login):
    make_employee("EMP606", vehicle_type="Bike")
    make_slot("1-C01", vehicle_type="Car")
    make_slot("1-B01", vehicle_type="Bike", status="Reserved")
    start, end = _window()
    headers = login("EMP606")
    wrong_type = client.post("/api/bookings", json=_payload("1-C01", start, end), headers=headers)
    assert wrong_type.json()["error"]["code"] == "VEHICLE_TYPE_MISMATCH"
    reserved = client.post("/api/bookings", json=_payload("1-B01", start, end), headers=headers)
    assert reserved.json()["error"]["code"] == "SLOT_NOT_BOOKABLE"


def test_same_slot_overlapping_window_is_blocked_for_other_employee(client, make_employee, make_slot, login):
    make_employee("EMP607")
    make_employee("EMP608")
    make_slot("1-C01")
    start, end = _window()
    assert client.post("/api/bookings", json=_payload("1-C01", start, end), headers=login("EMP607")).status_code == 201

    overlapping = client.post(
        "/api/bookings", json=_payload("1-C01", start + timedelta(minutes=30), end + timedelta(hours=1)),
        headers=login("EMP608"),
    )
    assert overlapping.json()["error"]["code"] == "SLOT_BOOKED"

    adjacent = client.post("/api/bookings", json=_payload("1-C01", end, end + timedelta(hours=1)), headers=login("EMP608"))
    assert adjacent.status_code == 201


def test_employee_cannot_hold_overlapping_bookings(client, make_employee, make_slot, login):
    make_employee("EMP609")
    make_slot("1-C01")
    make_slot("1-C02")
    start, end = _window()
    headers = login("EMP609")
    client.post("/api/bookings", json=_payload("1-C01", start, end), headers=headers)
    response = client.post("/api/bookings", json=_payload("1-C02", start, end), headers=headers)
    assert response.json()["error"]["code"] == "EMPLOYEE_OVERLAP"


def test_employee_can_edit_upcoming_booking(client, make_employee, make_slot, login):
    make_employee("EMP610")
    make_slot("1-C01")
    make_slot("1-C02")
    headers = login("EMP610")
    start, end = _window()
    booking_id = client.post("/api/bookings", json=_payload("1-C01", start, end), headers=headers).json()["data"]["id"]

    new_start, new_end = _window(hours=2, offset_hours=3)
    response = client.patch(f"/api/bookings/{booking_id}", json=_payload("1-C02", new_start, new_end), headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["slot_id"] == "1-C02"
    assert response.json()["data"]["duration_minutes"] == 120


def test_employee_cannot_edit_another_employees_booking(client, make_employee, make_slot, login):
    make_employee("EMP611")
    make_employee("EMP612")
    make_slot("1-C01")
    start, end = _window()
    booking_id = client.post("/api/bookings", json=_payload("1-C01", start, end), headers=login("EMP611")).json()["data"]["id"]
    response = client.patch(f"/api/bookings/{booking_id}", json=_payload("1-C01", start, end), headers=login("EMP612"))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "NOT_BOOKING_OWNER"


def test_past_booking_cannot_be_edited_or_cancelled(client, make_employee, make_slot, login):
    make_employee("EMP613")
    make_slot("1-C01")
    headers = login("EMP613")
    past_start = utc_now() - timedelta(days=2)
    booking_id = _insert_booking("EMP613", "1-C01", past_start, past_start + timedelta(hours=1))
    start, end = _window()

    edit = client.patch(f"/api/bookings/{booking_id}", json=_payload("1-C01", start, end), headers=headers)
    assert edit.status_code == 409
    assert edit.json()["error"]["code"] == "BOOKING_NOT_EDITABLE"

    cancel = client.post(f"/api/bookings/{booking_id}/cancel", headers=headers)
    assert cancel.json()["error"]["code"] == "BOOKING_NOT_EDITABLE"


def test_in_progress_booking_cannot_be_edited(client, make_employee, make_slot, login):
    make_employee("EMP614")
    make_slot("1-C01")
    headers = login("EMP614")
    started = utc_now() - timedelta(minutes=10)
    booking_id = _insert_booking("EMP614", "1-C01", started, started + timedelta(hours=1))
    cancel = client.post(f"/api/bookings/{booking_id}/cancel", headers=headers)
    assert cancel.json()["error"]["code"] == "BOOKING_NOT_EDITABLE"
    listing = client.get("/api/bookings?scope=upcoming", headers=headers).json()["data"]["items"]
    assert listing[0]["state"] == "in_progress"
    assert listing[0]["editable"] is False


def test_cancel_upcoming_booking_moves_it_to_past_list(client, make_employee, make_slot, login):
    make_employee("EMP615")
    make_slot("1-C01")
    headers = login("EMP615")
    start, end = _window()
    booking_id = client.post("/api/bookings", json=_payload("1-C01", start, end), headers=headers).json()["data"]["id"]

    cancelled = client.post(f"/api/bookings/{booking_id}/cancel", headers=headers)
    assert cancelled.status_code == 200
    assert cancelled.json()["data"]["state"] == "cancelled"

    again = client.post(f"/api/bookings/{booking_id}/cancel", headers=headers)
    assert again.status_code == 409

    past = client.get("/api/bookings?scope=past", headers=headers).json()["data"]["items"]
    assert [item["id"] for item in past] == [booking_id]
    upcoming = client.get("/api/bookings?scope=upcoming", headers=headers).json()["data"]["items"]
    assert upcoming == []


def test_past_scope_lists_completed_bookings(client, make_employee, make_slot, login):
    make_employee("EMP616")
    make_slot("1-C01")
    old = utc_now() - timedelta(days=3)
    _insert_booking("EMP616", "1-C01", old, old + timedelta(hours=1))
    past = client.get("/api/bookings?scope=past", headers=login("EMP616")).json()["data"]
    assert past["total"] == 1
    assert past["items"][0]["state"] == "past"


def test_available_slots_exclude_booked_window(client, make_employee, make_slot, login):
    make_employee("EMP617")
    make_employee("EMP618")
    make_slot("1-C01")
    make_slot("1-C02")
    start, end = _window()
    client.post("/api/bookings", json=_payload("1-C01", start, end), headers=login("EMP618"))
    response = client.get(
        "/api/bookings/available-slots",
        params={"start_time": start.isoformat(), "end_time": end.isoformat()},
        headers=login("EMP617"),
    )
    assert [slot["slot_id"] for slot in response.json()["data"]["slots"]] == ["1-C02"]


def test_employee_cannot_occupy_slot_while_another_booking_is_in_progress(client, make_employee, make_slot, login):
    make_employee("EMP619")
    make_employee("EMP620")
    make_slot("1-C01")
    started = utc_now() - timedelta(minutes=5)
    _insert_booking("EMP620", "1-C01", started, started + timedelta(hours=1))

    blocked = client.post("/api/parking/occupy", json={"slot_id": "1-C01"}, headers=login("EMP619"))
    assert blocked.json()["error"]["code"] == "SLOT_BOOKED"

    owner = client.post("/api/parking/occupy", json={"slot_id": "1-C01"}, headers=login("EMP620"))
    assert owner.status_code == 201


def test_concurrent_bookings_for_same_window_allow_exactly_one(make_employee, make_slot):
    make_slot("1-C01")
    employees = [make_employee(f"EMP7{index:02d}") for index in range(1, 9)]
    start, end = _window(days_ahead=3)
    barrier = threading.Barrier(len(employees))
    outcomes = []
    lock = threading.Lock()

    def attempt(employee_document):
        barrier.wait()
        try:
            booking_service.create_booking(employee_document, "1-C01", start, end)
            result = "ok"
        except AppError as error:
            result = error.code
        with lock:
            outcomes.append(result)

    threads = [threading.Thread(target=attempt, args=(doc,)) for doc in employees]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert outcomes.count("ok") == 1, outcomes
    assert get_collection(BOOKINGS).count_documents({"slot_id": "1-C01", "status": "booked"}) == 1


def test_admin_can_edit_any_upcoming_booking(client, make_employee, make_slot, login):
    make_employee("EMP621")
    make_slot("1-C01")
    make_slot("1-C02")
    start, end = _window()
    booking_id = client.post("/api/bookings", json=_payload("1-C01", start, end), headers=login("EMP621")).json()["data"]["id"]
    new_start, new_end = _window(hours=2, offset_hours=3)
    response = client.patch(f"/api/bookings/{booking_id}", json=_payload("1-C02", new_start, new_end), headers=login("ADMIN", admin=True))
    assert response.status_code == 200, response.text
    assert response.json()["data"]["slot_id"] == "1-C02"


def test_admin_lists_slots_for_a_named_vehicle_type(client, make_slot, login):
    make_slot("1-B01", vehicle_type="Bike")
    make_slot("1-C01", vehicle_type="Car")
    start, end = _window()
    response = client.get(
        "/api/bookings/available-slots",
        params={"start_time": start.isoformat(), "end_time": end.isoformat(), "vehicle_type": "Bike"},
        headers=login("ADMIN", admin=True),
    )
    assert [slot["slot_id"] for slot in response.json()["data"]["slots"]] == ["1-B01"]

    missing = client.get(
        "/api/bookings/available-slots",
        params={"start_time": start.isoformat(), "end_time": end.isoformat()},
        headers=login("ADMIN", admin=True),
    )
    assert missing.json()["error"]["code"] == "VEHICLE_TYPE_REQUIRED"
