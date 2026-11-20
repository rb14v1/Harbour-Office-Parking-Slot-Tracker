from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

SlotStatusInput = Literal["Available", "Reserved"]
VehicleType = Literal["Car", "Bike"]


class SlotCreate(BaseModel):
    slot_id: str = Field(min_length=3, max_length=20, pattern=r"^[A-Za-z0-9-]+$")
    floor: str = Field(min_length=1, max_length=10)
    location: str = Field(min_length=2, max_length=100)
    vehicle_type: VehicleType

    @field_validator("slot_id")
    @classmethod
    def normalise_slot_id(cls, value: str) -> str:
        return value.upper()


class SlotUpdate(BaseModel):
    floor: Optional[str] = Field(default=None, min_length=1, max_length=10)
    location: Optional[str] = Field(default=None, min_length=2, max_length=100)
    vehicle_type: Optional[VehicleType] = None
    status: Optional[SlotStatusInput] = None
