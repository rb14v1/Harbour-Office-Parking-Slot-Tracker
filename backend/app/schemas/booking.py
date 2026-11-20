from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class BookingPayload(BaseModel):
    slot_id: str = Field(min_length=3, max_length=20)
    start_time: datetime
    end_time: datetime

    @field_validator("slot_id")
    @classmethod
    def normalise_slot_id(cls, value: str) -> str:
        return value.strip().upper()
