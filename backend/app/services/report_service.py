import math
import re
from datetime import date, datetime, timedelta

from app.core.exceptions import AppError
from app.core.timezone import IST_NAME, ist_day_bounds_utc, ist_today, utc_now
from app.db.mongo import BOOKINGS, PARKING_HISTORY, get_collection
from app.services.serializers import serialize_booking, serialize_history
from app.services.slot_service import occupancy_summary


def _history():
    return get_collection(PARKING_HISTORY)


def _window_start(days: int) -> date:
    return ist_today() - timedelta(days=days - 1)


def _aggregate_completed_stats(match: dict) -> dict:
    pipeline = [
        {"$match": {**match, "status": "completed"}},
        {
            "$group": {
                "_id": None,
                "completed_sessions": {"$sum": 1},
                "total_minutes": {"$sum": "$duration_minutes"},
                "average_minutes": {"$avg": "$duration_minutes"},
            }
        },
    ]
    rows = list(_history().aggregate(pipeline))
    if not rows:
        return {"completed_sessions": 0, "total_occupied_hours": 0.0, "average_duration_minutes": 0.0}
    row = rows[0]
    return {
        "completed_sessions": row["completed_sessions"],
        "total_occupied_hours": round(row["total_minutes"] / 60, 2),
        "average_duration_minutes": round(row["average_minutes"], 2),
    }


def _most_used_slots(match: dict, limit: int) -> list[dict]:
    pipeline = [
        {"$match": match},
        {"$group": {"_id": "$slot_id", "sessions": {"$sum": 1}, "total_minutes": {"$sum": "$duration_minutes"}}},
        {"$sort": {"sessions": -1, "_id": 1}},
        {"$limit": limit},
    ]
    return [
        {
            "slot_id": row["_id"],
            "sessions": row["sessions"],
            "total_occupied_hours": round((row["total_minutes"] or 0) / 60, 2),
        }
        for row in _history().aggregate(pipeline)
    ]


def _hourly_entries(match: dict) -> list[int]:
    pipeline = [
        {"$match": match},
        {"$group": {"_id": {"$hour": {"date": "$entry_time", "timezone": IST_NAME}}, "count": {"$sum": 1}}},
    ]
    counts = [0] * 24
    for row in _history().aggregate(pipeline):
        counts[row["_id"]] = row["count"]
    return counts


def _peak_hour(hourly_counts: list[int]) -> dict:
    if not any(hourly_counts):
        return {"hour": None, "label": None, "entries": 0}
    peak = max(range(24), key=lambda hour: hourly_counts[hour])
    return {"hour": peak, "label": f"{peak:02d}:00-{peak + 1:02d}:00 IST", "entries": hourly_counts[peak]}


def dashboard_stats(actor: dict) -> dict:
    today_start, today_end = ist_day_bounds_utc(ist_today(), ist_today())
    entries_today = _history().count_documents({"entry_time": {"$gte": today_start, "$lt": today_end}})
    exits_today = _history().count_documents({"exit_time": {"$gte": today_start, "$lt": today_end}})
    active_sessions = _history().count_documents({"status": "active"})

    recent_docs = list(_history().find({}).sort([("entry_time", -1), ("_id", -1)]).limit(8))
    is_admin = actor["role"] == "admin"
    recent_activity = [serialize_history(doc, include_personal_fields=is_admin) for doc in recent_docs]

    return {
        "slots": occupancy_summary(),
        "active_sessions": active_sessions,
        "entries_today": entries_today,
        "exits_today": exits_today,
        "recent_activity": recent_activity,
    }


def daily_report(report_date: date) -> dict:
    start_utc, end_utc = ist_day_bounds_utc(report_date, report_date)
    match = {"entry_time": {"$gte": start_utc, "$lt": end_utc}}
    exits = _history().count_documents({"exit_time": {"$gte": start_utc, "$lt": end_utc}})
    stats = _aggregate_completed_stats(match)
    hourly = _hourly_entries(match)
    return {
        "date": report_date.isoformat(),
        "timezone": IST_NAME,
        "entries": _history().count_documents(match),
        "exits": exits,
        "sessions_still_parked": _history().count_documents(
            {"status": "active", "entry_time": {"$gte": start_utc, "$lt": end_utc}}
        ),
        "completed_sessions": stats["completed_sessions"],
        "total_occupied_hours": stats["total_occupied_hours"],
        "average_duration_minutes": stats["average_duration_minutes"],
        "hourly_entries": hourly,
        "peak_entry_hour": _peak_hour(hourly),
        "most_used_slots": _most_used_slots(match, limit=5),
        "note": "Entries, durations and slot usage are grouped by the IST date of entry.",
    }


def trends(days: int) -> list[dict]:
    start_day = _window_start(days)
    start_utc, _ = ist_day_bounds_utc(start_day, start_day)
    _, end_utc = ist_day_bounds_utc(ist_today(), ist_today())

    entries_pipeline = [
        {"$match": {"entry_time": {"$gte": start_utc, "$lt": end_utc}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$entry_time", "timezone": IST_NAME}},
            "entries": {"$sum": 1},
            "completed": {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}},
        }},
    ]
    exits_pipeline = [
        {"$match": {"exit_time": {"$gte": start_utc, "$lt": end_utc}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$exit_time", "timezone": IST_NAME}},
            "exits": {"$sum": 1},
        }},
    ]
    entries_by_day = {row["_id"]: row for row in _history().aggregate(entries_pipeline)}
    exits_by_day = {row["_id"]: row["exits"] for row in _history().aggregate(exits_pipeline)}

    series = []
    for offset in range(days):
        day = (start_day + timedelta(days=offset)).isoformat()
        entry_row = entries_by_day.get(day, {})
        series.append({
            "date": day,
            "entries": entry_row.get("entries", 0),
            "exits": exits_by_day.get(day, 0),
            "completed_sessions": entry_row.get("completed", 0),
        })
    return series


def peak_hours(days: int) -> dict:
    start_day = _window_start(days)
    start_utc, _ = ist_day_bounds_utc(start_day, start_day)
    _, end_utc = ist_day_bounds_utc(ist_today(), ist_today())
    hourly = _hourly_entries({"entry_time": {"$gte": start_utc, "$lt": end_utc}})
    return {
        "days": days,
        "timezone": IST_NAME,
        "hourly_entries": hourly,
        "peak_entry_hour": _peak_hour(hourly),
    }


def most_used_slots(days: int, limit: int) -> list[dict]:
    start_day = _window_start(days)
    start_utc, _ = ist_day_bounds_utc(start_day, start_day)
    _, end_utc = ist_day_bounds_utc(ist_today(), ist_today())
    return _most_used_slots({"entry_time": {"$gte": start_utc, "$lt": end_utc}}, limit)


def summary(days: int) -> dict:
    start_day = _window_start(days)
    start_utc, _ = ist_day_bounds_utc(start_day, start_day)
    _, end_utc = ist_day_bounds_utc(ist_today(), ist_today())
    match = {"entry_time": {"$gte": start_utc, "$lt": end_utc}}
    stats = _aggregate_completed_stats(match)
    return {
        "days": days,
        "timezone": IST_NAME,
        "total_sessions": _history().count_documents(match),
        **stats,
        "current_occupancy": occupancy_summary(),
    }


BOOKING_STATES = ("upcoming", "in_progress", "past", "cancelled")


def _booking_state_filter(state: str, now: datetime) -> dict:
    """Mongo filter matching the same state rules that serialize_booking applies."""
    if state == "upcoming":
        return {"status": "booked", "start_time": {"$gt": now}}
    if state == "in_progress":
        return {"status": "booked", "start_time": {"$lte": now}, "end_time": {"$gt": now}}
    if state == "past":
        return {"status": "booked", "end_time": {"$lte": now}}
    return {"status": "cancelled"}


def _booking_collection():
    return get_collection(BOOKINGS)


def booking_report(
    date_from: date | None = None,
    date_to: date | None = None,
    employee_id: str | None = None,
    slot_id: str | None = None,
    state: str = "all",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    now = utc_now()
    query: dict = {}
    if date_from or date_to:
        start = date_from or date_to
        end = date_to or date_from
        if end < start:
            raise AppError(400, "INVALID_DATE_RANGE", "End date must be on or after the start date.")
        start_utc, end_utc = ist_day_bounds_utc(start, end)
        query["start_time"] = {"$gte": start_utc, "$lt": end_utc}
    if employee_id:
        query["employee_id"] = employee_id.strip().upper()
    if slot_id:
        query["slot_id"] = {"$regex": re.escape(slot_id.strip().upper()), "$options": "i"}
    if state != "all":
        if state not in BOOKING_STATES:
            raise AppError(400, "INVALID_STATE", f"state must be all, {', '.join(BOOKING_STATES)}.")
        query.update(_booking_state_filter(state, now))

    total = _booking_collection().count_documents(query)
    documents = (
        _booking_collection()
        .find(query)
        .sort([("start_time", -1), ("_id", -1)])
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    return {
        "items": [serialize_booking(doc, now) for doc in documents],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": max(1, math.ceil(total / page_size)),
    }


BOOKING_HORIZON_DAYS = 15  # bookings can start up to 14 days ahead; one extra day for safety


def booking_summary(days: int) -> dict:
    """Counts for the last `days` days plus every booking that starts in the next two weeks."""
    now = utc_now()
    start_day = _window_start(days)
    end_day = ist_today() + timedelta(days=BOOKING_HORIZON_DAYS)
    start_utc, end_utc = ist_day_bounds_utc(start_day, end_day)
    window = {"start_time": {"$gte": start_utc, "$lt": end_utc}}

    counts = {}
    for state in BOOKING_STATES:
        counts[state] = _booking_collection().count_documents({**window, **_booking_state_filter(state, now)})
    total = sum(counts.values())

    per_day_pipeline = [
        {"$match": window},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$start_time", "timezone": IST_NAME}},
            "bookings": {"$sum": 1},
            "cancelled": {"$sum": {"$cond": [{"$eq": ["$status", "cancelled"]}, 1, 0]}},
        }},
    ]
    per_day = {row["_id"]: row for row in _booking_collection().aggregate(per_day_pipeline)}
    series = []
    for offset in range((end_day - start_day).days):
        day = (start_day + timedelta(days=offset)).isoformat()
        row = per_day.get(day, {})
        series.append({"date": day, "bookings": row.get("bookings", 0), "cancelled": row.get("cancelled", 0)})

    top_slots = list(_booking_collection().aggregate([
        {"$match": {**window, "status": "booked"}},
        {"$group": {"_id": "$slot_id", "bookings": {"$sum": 1}}},
        {"$sort": {"bookings": -1, "_id": 1}},
        {"$limit": 5},
    ]))
    by_vehicle = {row["_id"]: row["count"] for row in _booking_collection().aggregate([
        {"$match": window},
        {"$group": {"_id": "$vehicle_type", "count": {"$sum": 1}}},
    ])}

    return {
        "days": days,
        "timezone": IST_NAME,
        "total": total,
        "counts": counts,
        "by_vehicle_type": {"Car": by_vehicle.get("Car", 0), "Bike": by_vehicle.get("Bike", 0)},
        "series": series,
        "top_slots": [{"slot_id": row["_id"], "bookings": row["bookings"]} for row in top_slots],
    }
