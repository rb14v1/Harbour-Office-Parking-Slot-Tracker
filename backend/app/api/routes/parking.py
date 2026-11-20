from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_identity, get_viewer, require_admin
from app.schemas.common import success_response
from app.schemas.parking import SlotActionRequest
from app.services import parking_service

router = APIRouter(prefix="/parking", tags=["Parking Operations"])


@router.post("/occupy", status_code=201)
def occupy_slot(payload: SlotActionRequest, employee: dict = Depends(get_identity)):
    result = parking_service.occupy_slot(employee, payload.slot_id)
    return success_response(result, message=result["message"], status_code=201)


@router.post("/release")
def release_slot(payload: Optional[SlotActionRequest] = None, employee: dict = Depends(get_viewer)):
    slot_id = payload.slot_id if payload else None
    result = parking_service.release_slot(employee, slot_id)
    return success_response(result, message=result["message"])


@router.get("/me")
def my_parking(employee: dict = Depends(get_identity)):
    current = parking_service.get_current_allocation(employee["employee_id"])
    return success_response(
        current,
        message="Current allocation loaded." if current else "You have no active parking slot.",
    )


@router.get("/occupancy")
def occupancy_monitor(_admin: dict = Depends(require_admin)):
    rows = parking_service.get_occupancy_monitor()
    return success_response({"occupied": rows, "count": len(rows)})


@router.get("/history")
def parking_history(
    employee_id: Optional[str] = Query(default=None, max_length=20),
    slot_id: Optional[str] = Query(default=None, max_length=20),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    sort_by: str = "entry_time",
    sort_order: Literal["asc", "desc"] = "desc",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    employee: dict = Depends(get_viewer),
):
    result = parking_service.list_history(
        actor=employee,
        employee_id=employee_id,
        slot_id=slot_id,
        date_from=date_from,
        date_to=date_to,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    return success_response(result)
