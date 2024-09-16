from sqlalchemy import Column, String, Text, Enum, TIMESTAMP, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from backend.app.models.base import Base
import uuid


class Organization(Base):
    __tablename__ = 'organization'

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    type = Column(Enum('IE', 'LLC', 'JSC', name='organization_type'))
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    responsible_users = relationship("OrganizationResponsible", back_populates="organization")
    tenders = relationship("Tender", back_populates="organization")


class OrganizationResponsible(Base):
    __tablename__ = 'organization_responsible'

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(PG_UUID(as_uuid=True), ForeignKey('organization.id', ondelete='CASCADE'))
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey('employee.id', ondelete='CASCADE'))

    organization = relationship("Organization", back_populates="responsible_users")
    employee = relationship("Employee", back_populates="organizations")
