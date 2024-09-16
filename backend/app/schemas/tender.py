from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional


class TenderCreate(BaseModel):
    title: str
    description: Optional[str]
    service_type: str


class TenderBase(BaseModel):
    title: str
    description: Optional[str] = None


class TenderUpdate(TenderBase):
    pass


class TenderResponse(TenderBase):
    id: UUID
    tender_root_id: UUID
    organization_id: UUID
    creator_id: UUID
    status: str
    service_type: str
    created_at: datetime
    updated_at: datetime
    version: int

    class Config:
        orm_mode = True
