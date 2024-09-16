import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from uuid import UUID

from backend.app.models import Bid
from backend.app.schemas.tender import TenderCreate, TenderResponse, TenderUpdate
from backend.app.database import SessionLocal
from backend.app.models.tender import Tender
from backend.app.models.organization import Organization, OrganizationResponsible
from backend.app.models.employee import Employee

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def validate_title(title: str):
    if not title or len(title) < 3 or len(title) > 100:
        raise HTTPException(status_code=422,
                            detail="Title must be from 3 to 100 characters long")


def validate_description(description: str):
    if description and len(description) > 500:
        raise HTTPException(status_code=422,
                            detail="Description must not exceed 500 characters")


def validate_service_type(service_type: str):
    valid_service_types = ["Construction", "IT Services", "Consulting"]
    if service_type not in valid_service_types:
        raise HTTPException(status_code=422,
                            detail=f"Invalid service type. Allowed types: {', '.join(valid_service_types)}")


def get_user_by_username(username: str, db: Session):
    if not username:
        raise HTTPException(status_code=403, detail="Unauthorized user")
    user = db.query(Employee).filter(Employee.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def check_user_responsibility(user_id: UUID, organization_id: UUID, db: Session):
    responsible = db.query(OrganizationResponsible).filter_by(
        user_id=user_id,
        organization_id=organization_id
    ).first()
    if not responsible:
        raise HTTPException(status_code=403, detail="User is not authorized for this organization")


def get_bid_by_id(bid_id: UUID, db: Session):
    bid = db.query(Bid).filter(Bid.id == bid_id).first()
    if not bid:
        raise HTTPException(status_code=404, detail="Bid not found")
    return bid


def get_tender_by_id(tender_id: UUID, db: Session):
    tender = db.query(Tender).filter(Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Tender not found")
    return tender


def handle_exception(e: Exception):
    print(f"Unexpected error: {e}")
    raise HTTPException(status_code=500, detail="Internal Server Error")


def validate_tender_user_responsibility(username: str, tender_id: UUID, db: Session):
    user = get_user_by_username(username, db)
    tender = get_tender_by_id(tender_id, db)
    check_user_responsibility(user.id, tender.organization_id, db)
    return user, tender


@router.get("/", response_model=list[TenderResponse])
def get_tenders(
        skip: int = 0,
        limit: int = 100,
        username: str = None,
        service_type: str = None,
        db: Session = Depends(get_db)
):
    try:
        subquery = db.query(
            Tender.tender_root_id, func.max(Tender.version).label("max_version")
        ).group_by(Tender.tender_root_id).subquery()

        tenders_query = (
            db.query(Tender)
            .join(subquery,
                  (Tender.tender_root_id == subquery.c.tender_root_id) & (Tender.version == subquery.c.max_version))
        )

        if service_type:
            validate_service_type(service_type)
            tenders_query = tenders_query.filter(Tender.service_type == service_type)

        if username is None:
            tenders_query = tenders_query.filter(Tender.status == "PUBLISHED")
        else:
            user = db.query(Employee).filter(Employee.username == username).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            tenders_query = tenders_query.filter(
                (Tender.status == "PUBLISHED") | (
                    db.query(OrganizationResponsible)
                    .filter(
                        OrganizationResponsible.user_id == user.id,
                        OrganizationResponsible.organization_id == Tender.organization_id
                    )
                    .exists()
                )
            )

        tenders = tenders_query.offset(skip).limit(limit).all()
        return tenders

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/my", response_model=list[TenderResponse])
def get_user_tenders(
        username: str,
        db: Session = Depends(get_db)
):
    try:
        user = get_user_by_username(username, db)

        subquery = db.query(
            Tender.tender_root_id, func.max(Tender.version).label("max_version")
        ).group_by(Tender.tender_root_id).subquery()

        tenders = (
            db.query(Tender)
            .join(OrganizationResponsible, OrganizationResponsible.organization_id == Tender.organization_id)
            .join(subquery,
                  (Tender.tender_root_id == subquery.c.tender_root_id) & (Tender.version == subquery.c.max_version))
            .filter(OrganizationResponsible.user_id == user.id)
            .all()
        )

        if not tenders:
            raise HTTPException(status_code=404, detail="No tenders found for this user")

        return tenders

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post("/new", response_model=TenderResponse)
def create_tender(
        tender: TenderCreate,
        username: str = None,
        db: Session = Depends(get_db)
):
    try:
        creator = get_user_by_username(username, db)

        responsible = db.query(OrganizationResponsible).filter(
            OrganizationResponsible.user_id == creator.id
        ).first()

        if not responsible:
            raise HTTPException(status_code=403, detail="User is not responsible for any organization")

        organization = db.query(Organization).filter(Organization.id == responsible.organization_id).first()
        if not organization:
            raise HTTPException(status_code=404, detail="Organization not found")

        if not tender.title or not tender.description or not tender.service_type:
            raise HTTPException(status_code=400, detail="Title, description and service type are required")

        validate_title(tender.title)
        validate_description(tender.description)
        validate_service_type(tender.service_type)

        new_tender = Tender(
            tender_root_id=uuid.uuid4(),
            organization_id=organization.id,
            title=tender.title,
            description=tender.description,
            status="CREATED",
            service_type=tender.service_type,
            creator_id=creator.id,
            version=1,
            created_at=func.now(),
            updated_at=func.now()
        )

        db.add(new_tender)
        db.commit()
        db.refresh(new_tender)
        return new_tender

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.patch("/{tender_id}/status", response_model=TenderResponse)
def update_tender_status(
        tender_id: UUID,
        new_status: str,
        username: str = None,
        db: Session = Depends(get_db)
):
    try:
        user, tender = validate_tender_user_responsibility(username, tender_id, db)

        if new_status not in ["PUBLISHED", "CLOSED"]:
            raise HTTPException(status_code=400, detail="Invalid status")

        tender.status = new_status
        db.commit()
        db.refresh(tender)
        return tender

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        handle_exception(e)


@router.patch("/{tender_id}/edit", response_model=TenderResponse)
def update_tender(
        tender_id: UUID,
        tender: TenderUpdate,
        username: str = None,
        db: Session = Depends(get_db)
):
    if username is None:
        raise HTTPException(status_code=403, detail="Unauthorized users cannot edit tenders")

    try:
        user, current_tender = validate_tender_user_responsibility(username, tender_id, db)

        if not tender.title or not tender.description:
            raise HTTPException(status_code=400, detail="Title and description are required")

        validate_title(tender.title)
        validate_description(tender.description)

        new_tender_data = current_tender.__dict__.copy()
        new_tender_data.pop("_sa_instance_state")
        for key, value in tender.dict(exclude_unset=True).items():
            new_tender_data[key] = value

        new_tender = Tender(
            tender_root_id=current_tender.tender_root_id,
            organization_id=current_tender.organization_id,
            title=new_tender_data["title"],
            description=new_tender_data["description"],
            status=new_tender_data["status"],
            service_type=new_tender_data.get("service_type", current_tender.service_type),
            version=current_tender.version + 1,
            creator_id=current_tender.creator_id,
            created_at=current_tender.created_at,
            updated_at=func.now()
        )

        db.add(new_tender)
        db.commit()
        db.refresh(new_tender)

        return new_tender

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Unexpected error: {e}")
        handle_exception(e)


@router.put("/{tender_id}/rollback/{version}", response_model=TenderResponse)
def rollback_tender(
        tender_id: UUID,
        version: int,
        username: str = None,
        db: Session = Depends(get_db)
):
    try:
        user, current_tender = validate_tender_user_responsibility(username, tender_id, db)

        rollback_version = db.query(Tender).filter(
            Tender.tender_root_id == current_tender.tender_root_id,
            Tender.version == version
        ).first()

        if not rollback_version:
            raise HTTPException(status_code=404, detail="Version not found for the tender")

        new_tender = Tender(
            tender_root_id=current_tender.tender_root_id,
            organization_id=rollback_version.organization_id,
            title=rollback_version.title,
            description=rollback_version.description,
            status=rollback_version.status,
            service_type=rollback_version.service_type,
            version=current_tender.version + 1,
            creator_id=rollback_version.creator_id,
            created_at=current_tender.created_at,
            updated_at=func.now()
        )

        db.add(new_tender)
        db.commit()
        db.refresh(new_tender)

        return new_tender

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        handle_exception(e)
