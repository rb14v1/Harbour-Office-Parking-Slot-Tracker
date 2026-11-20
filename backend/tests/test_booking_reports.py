from datetime import timedelta

from app.core.timezone import utc_now
from app.db.mongo import BOOKINGS, get_collection
from tests.test_bookings import _insert_booking


def test_booking_list_carries_full_details(client, make_employee, make_slot, login):
    make_employee("EMP801")
    make_slot("1-C01", floor="1")
    headers = login("EMP801")
    start = utc_now() + timedelta(days=2)
    response = client.post(
        "/api/bookings",
        json={"slot_id": "1-C01", "start_time": start.isoformat(), "end_time": (start + timedelta(hours=1)).isoformat()},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    booking = response.json()["data"]
    for field in ("employee_email", "floor", "location", "created_at", "cancelled_at", "duration_minutes", "state", "editable"):
        assert field in booking
    assert booking["employee_email"] == "emp801@example.com"
    assert booking["floor"] == "1"
    assert booking["cancelled_at"] is None


def test_booking_report_is_admin_only(client, make_employee, login):
    make_employee("EMP802")
    assert client.get("/api/reports/bookings", headers=login("EMP802")).status_code == 403
    assert client.get("/api/reports/bookings/summary", headers=login("EMP802")).status_code == 403
    assert client.get("/api/reports/bookings", headers=login("ADMIN", admin=True)).status_code == 200


def test_booking_report_lists_all_states_and_filters(client, make_employee, make_slot, login):
    make_employee("EMP803")
    make_employee("EMP804")
    make_slot("1-C01")
    make_slot("1-C02")
    now = utc_now()
    _insert_booking("EMP803", "1-C01", now + timedelta(days=1), now + timedelta(days=1, hours=1))
    _insert_booking("EMP804", "1-C02", now - timedelta(days=2), now - timedelta(days=2, hours=-1))
    _insert_booking("EMP803", "1-C02", now + timedelta(days=3), now + timedelta(days=3, hours=1), status="cancelled")
    admin = login("ADMIN", admin=True)

    everything = client.get("/api/reports/bookings", headers=admin).json()["data"]
    assert everything["total"] == 3

    upcoming = client.get("/api/reports/bookings?state=upcoming", headers=admin).json()["data"]
    assert [item["state"] for item in upcoming["items"]] == ["upcoming"]

    past = client.get("/api/reports/bookings?state=past", headers=admin).json()["data"]
    assert past["total"] == 1

    by_employee = client.get("/api/reports/bookings?employee_id=EMP803", headers=admin).json()["data"]
    assert by_employee["total"] == 2

    bad = client.get("/api/reports/bookings?state=bogus", headers=admin)
    assert bad.json()["error"]["code"] == "INVALID_STATE"


def test_booking_summary_counts_states_and_top_slots(client, make_employee, make_slot, login):
    make_employee("EMP805")
    make_slot("1-C01")
    now = utc_now()
    _insert_booking("EMP805", "1-C01", now + timedelta(days=1), now + timedelta(days=1, hours=1))
    _insert_booking("EMP805", "1-C01", now + timedelta(days=2), now + timedelta(days=2, hours=1), status="cancelled")
    summary = client.get("/api/reports/bookings/summary?days=7", headers=login("ADMIN", admin=True)).json()["data"]
    assert summary["total"] == 2
    assert summary["counts"]["upcoming"] == 1
    assert summary["counts"]["cancelled"] == 1
    assert summary["top_slots"][0] == {"slot_id": "1-C01", "bookings": 1}
    assert len(summary["series"]) == 21  # 7 days back plus the next 14 days
