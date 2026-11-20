from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_viewer, require_admin
from app.schemas.common import success_response
from app.schemas.slot import SlotCreate, SlotUpdate
from app.services import slot_service
from app.services.parking_service import list_available_slots_for_vehicle
from app.services.serializers import serialize_slot
from app.services.slot_service import SLOT_STATUSES

router = APIRouter(prefix="/slots", tags=["Parking Slots"])

FloorQuery = Optional[str]
VehicleQuery = Optional[Literal["Car", "Bike"]]
StatusQuery = Optional[Literal["Available", "Occupied", "Reserved", "Inactive"]]


@router.get("")
def list_slots(
    floor: FloorQuery = Query(default=None, max_length=10),
    vehicle_type: VehicleQuery = None,
    status: StatusQuery = None,
    search: Optional[str] = Query(default=None, max_length=20),
    _employee: dict = Depends(get_viewer),
):
    slots = slot_service.list_slots(floor=floor, vehicle_type=vehicle_type, status=status, search=search)
    return success_response({"slots": slots, "count": len(slots), "statuses": list(SLOT_STATUSES)})


@router.get("/available")
def available_slots(
    vehicle_type: VehicleQuery = None,
    _employee: dict = Depends(get_viewer),
):
    if vehicle_type:
        slots = list_available_slots_for_vehicle(vehicle_type)
    else:
        slots = slot_service.list_slots(status="Available")
    return success_response({"slots": slots, "count": len(slots)})


@router.get("/occupied")
def occupied_slots(_employee: dict = Depends(get_viewer)):
    slots = slot_service.list_slots(status="Occupied")
    return success_response({"slots": slots, "count": len(slots)})


@router.get("/floors")
def floors(_employee: dict = Depends(get_viewer)):
    return success_response({"floors": slot_service.list_floors()})


@router.get("/{slot_id}")
def slot_detail(slot_id: str, _employee: dict = Depends(get_viewer)):
    return success_response(serialize_slot(slot_service.get_slot_or_404(slot_id)))


@router.post("", status_code=201)
def create_slot(payload: SlotCreate, _admin: dict = Depends(require_admin)):
    slot = slot_service.create_slot(payload.model_dump())
    return success_response(slot, message=f"Slot {slot['slot_id']} created.", status_code=201)


@router.patch("/{slot_id}")
def update_slot(slot_id: str, payload: SlotUpdate, _admin: dict = Depends(require_admin)):
    slot = slot_service.update_slot(slot_id, payload.model_dump(exclude_none=True))
    return success_response(slot, message=f"Slot {slot['slot_id']} updated.")


@router.post("/{slot_id}/deactivate")
def deactivate_slot(slot_id: str, _admin: dict = Depends(require_admin)):
    slot = slot_service.deactivate_slot(slot_id)
    return success_response(slot, message=f"Slot {slot['slot_id']} deactivated.")
