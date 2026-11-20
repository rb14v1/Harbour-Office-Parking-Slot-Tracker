from fastapi import APIRouter, Depends

from app.api.deps import require_admin
from app.schemas.auth import AdminLoginRequest
from app.schemas.common import success_response
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Administrator"])


@router.post("/admin/login")
def admin_login(payload: AdminLoginRequest):
    result = auth_service.admin_login(payload.password)
    return success_response(result, message="Administrator login successful.")


@router.get("/admin/me")
def admin_me(_admin: dict = Depends(require_admin)):
    return success_response({"role": "admin"}, message="Administrator session is active.")
