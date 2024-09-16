from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from backend.app.models.employee import Employee
from backend.app.models.organization import OrganizationResponsible
from backend.app.models.tender import Tender
from backend.app.database import SessionLocal
from backend.app.schemas.debug import EmployeeResponse, TenderByCompanyResponse, OrganizationResponse
from uuid import UUID


router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/users", response_model=list[EmployeeResponse])
def get_users(db: Session = Depends(get_db)):
    users = db.query(Employee).options(
        joinedload(Employee.organizations).joinedload(OrganizationResponsible.organization)).all()

    if not users:
        raise HTTPException(status_code=404, detail="No users found")

    result = []
    for user in users:
        organizations = [OrganizationResponse(
            id=org.organization.id,
            name=org.organization.name,
            description=org.organization.description,
            type=org.organization.type
        ) for org in user.organizations]

        user_response = EmployeeResponse(
            id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            organizations=organizations,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
        result.append(user_response)

    return result


@router.get("/tenders/company/{organization_id}", response_model=list[TenderByCompanyResponse])
def get_tenders_by_company(organization_id: UUID, db: Session = Depends(get_db)):
    tenders = db.query(Tender).filter(Tender.organization_id == organization_id).all()
    if not tenders:
        raise HTTPException(status_code=404, detail="No tenders found for this company")

    return tenders
