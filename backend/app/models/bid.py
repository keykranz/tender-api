from sqlalchemy import Column, TIMESTAMP, func, Enum, ForeignKey, Numeric, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from backend.app.models.base import Base
import uuid


class Bid(Base):
    __tablename__ = 'bid'

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bid_root_id = Column(PG_UUID(as_uuid=True), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(String)
    status = Column(Enum("CREATED", "PUBLISHED", "CANCELED", "APPROVED", "REJECTED", name="bid_status"),
                    default="CREATED")
    tender_id = Column(PG_UUID(as_uuid=True), ForeignKey('tender.id', ondelete='CASCADE'), nullable=False)
    organization_id = Column(PG_UUID(as_uuid=True), ForeignKey('organization.id', ondelete='CASCADE'), nullable=False)
    creator_id = Column(PG_UUID(as_uuid=True), ForeignKey('employee.id', ondelete='CASCADE'), nullable=False)
    version = Column(Integer, default=1)
    quorum = Column(Integer)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    tender = relationship("Tender", back_populates="bids")
    decisions = relationship("BidDecision", back_populates="bid")
    reviews = relationship("Review", back_populates="bid")


class BidDecision(Base):
    __tablename__ = 'bid_decision'

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bid_id = Column(PG_UUID(as_uuid=True), ForeignKey('bid.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey('employee.id', ondelete='CASCADE'), nullable=False)
    decision = Column(Enum("APPROVED", "REJECTED", name="decision_status"), nullable=False)
    decision_date = Column(TIMESTAMP, server_default=func.now())

    bid = relationship("Bid", back_populates="decisions")


class Review(Base):
    __tablename__ = 'review'

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bid_id = Column(PG_UUID(as_uuid=True), ForeignKey('bid.id', ondelete='CASCADE'), nullable=False)
    reviewer_id = Column(PG_UUID(as_uuid=True), ForeignKey('employee.id', ondelete='CASCADE'), nullable=False)
    author_id = Column(PG_UUID(as_uuid=True), ForeignKey('employee.id', ondelete='CASCADE'), nullable=False)
    content = Column(String, nullable=False)
    rating = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    bid = relationship("Bid", back_populates="reviews")
    reviewer = relationship("Employee", foreign_keys=[reviewer_id])
    author = relationship("Employee", foreign_keys=[author_id])
