from sqlalchemy.orm import Session
from app.models.employees import Employee
from app.core.exceptions import NotFoundError


def list_employees(db: Session, skip: int = 0, limit: int = 100) -> dict:
    total = db.query(Employee).count()
    items = db.query(Employee).offset(skip).limit(limit).all()
    return {"total": total, "items": items}


def get_employee(db: Session, employee_id: int) -> Employee:
    emp = db.query(Employee).filter(Employee.employeeNumber == employee_id).first()
    if not emp:
        raise NotFoundError("Employee", employee_id)
    return emp
