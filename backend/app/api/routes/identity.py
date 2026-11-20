from fastapi import APIRouter, Depends

from app.api.deps import get_identity
from app.schemas.common import success_response
from app.schemas.identity import IdentityPayload
from app.services import identity_service
from app.services.serializers import serialize_employee

router = APIRouter(prefix="/identity", tags=["Identity"])


@router.post("")
def save_identity(payload: IdentityPayload):
    employee = identity_service.save_identity(payload.model_dump())
    return success_response(employee, message="Your details are saved.")


@router.get("/me")
def current_identity(employee: dict = Depends(get_identity)):
    return success_response(serialize_employee(employee), message="Identity confirmed.")
