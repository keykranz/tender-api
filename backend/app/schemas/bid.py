from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional, List


class BidBase(BaseModel):
    amount: float
    title: str
    description: Optional[str] = None


class BidCreate(BidBase):
    tender_id: UUID


class BidUpdate(BidBase):
    pass


class BidDecisionResponse(BaseModel):
    id: UUID
    decision: str  # "APPROVED" или "REJECTED"
    decision_date: datetime

    class Config:
        orm_mode = True


class BidResponse(BidBase):
    id: UUID
    tender_id: UUID
    bid_root_id: UUID
    organization_id: UUID
    creator_id: UUID
    status: str
    quorum: Optional[int]
    decisions: list[BidDecisionResponse]
    created_at: datetime
    updated_at: datetime
    version: int

    class Config:
        orm_mode = True


class ReviewResponse(BaseModel):
    id: UUID
    bid_id: UUID
    content: str
    rating: int
    created_at: datetime

    class Config:
        orm_mode = True


class ReviewCreate(BaseModel):
    content: str
    rating: int = Field(..., ge=1, le=5)

    @field_validator('rating')
    def rating_must_be_valid(cls, v):
        if v < 1 or v > 5:
            raise ValueError('Rating must be between 1 and 5')
        return v
