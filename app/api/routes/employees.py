from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import verify_api_key
from app.db.ro_session import get_ro_db
from app.schemas.employees import EmployeeBase, EmployeeList
from app.services.employees_service import get_employee, list_employees

router = APIRouter(prefix="/employees", tags=["Employees"], dependencies=[Depends(verify_api_key)])


@router.get("", response_model=EmployeeList, summary="List all employees")
def list_employees_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_ro_db),
):
    return list_employees(db, skip=skip, limit=limit)


@router.get("/{employee_id}", response_model=EmployeeBase, summary="Get employee by ID")
def get_employee_endpoint(employee_id: int, db: Session = Depends(get_ro_db)):
    return get_employee(db, employee_id)
