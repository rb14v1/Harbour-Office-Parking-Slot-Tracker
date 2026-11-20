import re
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

VehicleType = Literal["Car", "Bike"]
NAME_PATTERN = re.compile(r"^[A-Za-z]+(?: [A-Za-z]+)*$")


class IdentityPayload(BaseModel):
    employee_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    vehicle_type: VehicleType
    vehicle_number: str = Field(min_length=4, max_length=15, pattern=r"^[A-Za-z0-9 -]+$")

    @field_validator("employee_name")
    @classmethod
    def normalise_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not NAME_PATTERN.match(cleaned):
            raise ValueError("Use English letters and single spaces only.")
        return cleaned

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("vehicle_number")
    @classmethod
    def normalise_vehicle_number(cls, value: str) -> str:
        return value.strip().upper()
