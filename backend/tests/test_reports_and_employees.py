from app.db.mongo import EMPLOYEES, get_collection


def _park_and_release(client, login, employee_id, slot_id):
    headers = login(employee_id)
    client.post("/api/parking/occupy", json={"slot_id": slot_id}, headers=headers)
    client.post("/api/parking/release", headers=headers)


def test_employee_cannot_open_reports(client, make_employee, login):
    make_employee("EMP401")
    response = client.get("/api/reports/daily", headers=login("EMP401"))
    assert response.status_code == 403


def test_daily_report_counts_real_entries_and_exits(client, make_employee, make_slot, login):
    make_employee("ADM401", role="admin")
    make_employee("EMP402")
    make_employee("EMP403")
    make_slot("1-C01")
    make_slot("1-C02")
    _park_and_release(client, login, "EMP402", "1-C01")
    client.post("/api/parking/occupy", json={"slot_id": "1-C02"}, headers=login("EMP403"))

    response = client.get("/api/reports/daily", headers=login("ADM401", admin=True))
    report = response.json()["data"]
    assert response.status_code == 200
    assert report["entries"] == 2
    assert report["exits"] == 1
    assert report["completed_sessions"] == 1
    assert report["sessions_still_parked"] == 1
    assert len(report["hourly_entries"]) == 24
    assert sum(report["hourly_entries"]) == 2
    assert report["most_used_slots"][0]["sessions"] == 1


def test_dashboard_stats_reflect_slot_states(client, make_employee, make_slot, login):
    make_employee("EMP404")
    make_slot("1-C01")
    make_slot("1-C02", status="Reserved")
    make_slot("1-C03", status="Inactive")
    client.post("/api/parking/occupy", json={"slot_id": "1-C01"}, headers=login("EMP404"))

    stats = client.get("/api/dashboard/stats", headers=login("EMP404")).json()["data"]
    assert stats["slots"]["total_slots"] == 3
    assert stats["slots"]["occupied"] == 1
    assert stats["slots"]["reserved"] == 1
    assert stats["slots"]["inactive"] == 1
    assert stats["slots"]["usable_slots"] == 2
    assert stats["slots"]["occupancy_percentage"] == 50.0
    assert stats["active_sessions"] == 1
    assert stats["recent_activity"][0]["slot_id"] == "1-C01"
    assert stats["recent_activity"][0]["employee_id"] is None, "employees must not see other people's identities"


def test_trends_return_one_point_per_day(client, make_employee, login):
    make_employee("ADM402", role="admin")
    response = client.get("/api/reports/trends?days=7", headers=login("ADM402", admin=True))
    series = response.json()["data"]["series"]
    assert len(series) == 7
    assert all({"date", "entries", "exits", "completed_sessions"} <= set(point) for point in series)


def test_peak_hours_and_summary_endpoints_respond(client, make_employee, make_slot, login):
    make_employee("ADM403", role="admin")
    make_employee("EMP405")
    make_slot("1-C01")
    _park_and_release(client, login, "EMP405", "1-C01")
    headers = login("ADM403", admin=True)

    peak = client.get("/api/reports/peak-hours?days=30", headers=headers).json()["data"]
    assert len(peak["hourly_entries"]) == 24
    assert peak["peak_entry_hour"]["entries"] == 1

    summary = client.get("/api/reports/summary?days=30", headers=headers).json()["data"]
    assert summary["total_sessions"] == 1
    assert summary["completed_sessions"] == 1

    slots = client.get("/api/reports/most-used-slots?days=30&limit=3", headers=headers).json()["data"]
    assert slots["slots"][0]["slot_id"] == "1-C01"


def test_admin_creates_employee_without_password(client, make_employee, login):
    make_employee("ADM404", role="admin")
    headers = login("ADM404", admin=True)

    created = client.post(
        "/api/employees",
        json={
            "employee_id": "emp601",
            "employee_name": "New Hire",
            "email": "NEW.HIRE@example.com",
            "department": "Sales",
            "vehicle_type": "Bike",
            "vehicle_number": "ka01nh0601",
        },
        headers=headers,
    )
    assert created.status_code == 201
    body = created.json()["data"]
    assert body["employee_id"] == "EMP601"
    assert body["email"] == "new.hire@example.com"
    assert "password" not in body and "password_hash" not in body
    stored = get_collection(EMPLOYEES).find_one({"employee_id": "EMP601"})
    assert "password_hash" not in stored

    duplicate = client.post(
        "/api/employees",
        json={
            "employee_id": "EMP601",
            "employee_name": "Dup",
            "email": "other@example.com",
            "department": "Sales",
            "vehicle_type": "Car",
            "vehicle_number": "KA01DUP1",
        },
        headers=headers,
    )
    assert duplicate.status_code == 409


def test_deactivating_employee_with_active_slot_is_blocked(client, make_employee, make_slot, login):
    make_employee("ADM405", role="admin")
    make_employee("EMP406")
    make_slot("1-C01")
    client.post("/api/parking/occupy", json={"slot_id": "1-C01"}, headers=login("EMP406"))

    blocked = client.post("/api/employees/EMP406/deactivate", headers=login("ADM405", admin=True))
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "ACTIVE_ALLOCATION_EXISTS"
