from pydantic import BaseModel, Field, field_validator


class SlotActionRequest(BaseModel):
    slot_id: str = Field(min_length=3, max_length=20)

    @field_validator("slot_id")
    @classmethod
    def normalise_slot_id(cls, value: str) -> str:
        return value.strip().upper()
