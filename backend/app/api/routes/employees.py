from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import require_admin
from app.schemas.common import success_response
from app.schemas.employee import EmployeeCreate, EmployeeUpdate
from app.services import employee_service
from app.services.serializers import serialize_employee

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.get("")
def list_employees(
    search: Optional[str] = Query(default=None, max_length=100),
    department: Optional[str] = Query(default=None, max_length=80),
    role: Optional[str] = Query(default=None, pattern="^(employee|admin)$"),
    _admin: dict = Depends(require_admin),
):
    employees = employee_service.list_employees(search=search, department=department, role=role)
    return success_response({"employees": employees, "count": len(employees)})


@router.post("", status_code=201)
def create_employee(payload: EmployeeCreate, _admin: dict = Depends(require_admin)):
    employee = employee_service.create_employee(payload.model_dump())
    return success_response(employee, message=f"Employee {employee['employee_id']} created.", status_code=201)


@router.get("/{employee_id}")
def employee_detail(employee_id: str, _admin: dict = Depends(require_admin)):
    return success_response(serialize_employee(employee_service.get_employee_or_404(employee_id)))


@router.patch("/{employee_id}")
def update_employee(employee_id: str, payload: EmployeeUpdate, _admin: dict = Depends(require_admin)):
    employee = employee_service.update_employee(employee_id, payload.model_dump(exclude_none=True))
    return success_response(employee, message=f"Employee {employee['employee_id']} updated.")


@router.post("/{employee_id}/deactivate")
def deactivate_employee(employee_id: str, _admin: dict = Depends(require_admin)):
    employee = employee_service.set_employee_active(employee_id, is_active=False)
    return success_response(employee, message=f"Employee {employee['employee_id']} deactivated.")


@router.post("/{employee_id}/activate")
def activate_employee(employee_id: str, _admin: dict = Depends(require_admin)):
    employee = employee_service.set_employee_active(employee_id, is_active=True)
    return success_response(employee, message=f"Employee {employee['employee_id']} activated.")
