from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_optional_viewer, require_admin
from app.core.timezone import ist_today
from app.schemas.common import success_response
from app.services import report_service

dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
reports_router = APIRouter(prefix="/reports", tags=["Reports"])


@dashboard_router.get("/stats")
def dashboard_stats(viewer: dict = Depends(get_optional_viewer)):
    return success_response(report_service.dashboard_stats(viewer))


@reports_router.get("/daily")
def daily_report(
    report_date: Optional[date] = Query(default=None, alias="date"),
    _admin: dict = Depends(require_admin),
):
    return success_response(report_service.daily_report(report_date or ist_today()))


@reports_router.get("/trends")
def trends(days: int = Query(default=7, ge=1, le=90), _admin: dict = Depends(require_admin)):
    return success_response({"days": days, "series": report_service.trends(days)})


@reports_router.get("/peak-hours")
def peak_hours(days: int = Query(default=30, ge=1, le=365), _admin: dict = Depends(require_admin)):
    return success_response(report_service.peak_hours(days))


@reports_router.get("/most-used-slots")
def most_used_slots(
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=5, ge=1, le=50),
    _admin: dict = Depends(require_admin),
):
    return success_response({"days": days, "slots": report_service.most_used_slots(days, limit)})


@reports_router.get("/summary")
def summary(days: int = Query(default=30, ge=1, le=365), _admin: dict = Depends(require_admin)):
    return success_response(report_service.summary(days))


@reports_router.get("/bookings")
def booking_report(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    employee_id: Optional[str] = Query(default=None, max_length=20),
    slot_id: Optional[str] = Query(default=None, max_length=20),
    state: str = Query(default="all", max_length=20),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _admin: dict = Depends(require_admin),
):
    result = report_service.booking_report(date_from, date_to, employee_id, slot_id, state, page, page_size)
    return success_response(result)


@reports_router.get("/bookings/summary")
def booking_summary(days: int = Query(default=30, ge=1, le=365), _admin: dict = Depends(require_admin)):
    return success_response(report_service.booking_summary(days))
