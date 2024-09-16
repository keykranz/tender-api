from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import List, Optional


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    type: str

    class Config:
        orm_mode = True


class EmployeeResponse(BaseModel):
    id: UUID
    username: str
    first_name: Optional[str]
    last_name: Optional[str]
    organizations: List[OrganizationResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class TenderByCompanyResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    status: str
    service_type: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
