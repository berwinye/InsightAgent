from pydantic import BaseModel
from typing import Optional


class EmployeeBase(BaseModel):
    employeeNumber: int
    lastName: str
    firstName: str
    extension: str
    email: str
    officeCode: str
    reportsTo: Optional[int] = None
    jobTitle: str

    model_config = {"from_attributes": True}


class EmployeeList(BaseModel):
    total: int
    items: list[EmployeeBase]
