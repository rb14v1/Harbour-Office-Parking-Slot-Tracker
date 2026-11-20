from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

VehicleType = Literal["Car", "Bike"]


class EmployeeCreate(BaseModel):
    employee_id: str = Field(min_length=3, max_length=20, pattern=r"^[A-Za-z0-9-]+$")
    employee_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    department: str = Field(min_length=2, max_length=80)
    vehicle_type: VehicleType
    vehicle_number: str = Field(min_length=4, max_length=15)

    @field_validator("employee_id", "vehicle_number")
    @classmethod
    def uppercase_identifiers(cls, value: str) -> str:
        return value.upper()

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()


class EmployeeUpdate(BaseModel):
    employee_name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    department: Optional[str] = Field(default=None, min_length=2, max_length=80)
    vehicle_type: Optional[VehicleType] = None
    vehicle_number: Optional[str] = Field(default=None, min_length=4, max_length=15)

    @field_validator("vehicle_number")
    @classmethod
    def uppercase_vehicle_number(cls, value: Optional[str]) -> Optional[str]:
        return value.upper() if value else value

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: Optional[str]) -> Optional[str]:
        return value.lower() if value else value
