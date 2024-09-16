from sqlalchemy import Column, String, Enum, ForeignKey, TIMESTAMP, Integer, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from backend.app.models.base import Base
import uuid


class Tender(Base):
    __tablename__ = 'tender'

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tender_root_id = Column(PG_UUID(as_uuid=True), nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(String)
    status = Column(Enum("CREATED", "PUBLISHED", "CLOSED", name="tender_status"), default="CREATED")
    service_type = Column(String(100), nullable=False)
    organization_id = Column(PG_UUID(as_uuid=True), ForeignKey('organization.id', ondelete='CASCADE'), nullable=False)
    creator_id = Column(PG_UUID(as_uuid=True), ForeignKey('employee.id', ondelete='CASCADE'), nullable=False)
    version = Column(Integer, default=1)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    organization = relationship("Organization", back_populates="tenders")
    bids = relationship("Bid", back_populates="tender")
