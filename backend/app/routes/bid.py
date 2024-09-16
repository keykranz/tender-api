import uuid
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, and_
from sqlalchemy.orm import Session
from backend.app.models import Bid, Tender, Employee, Organization, OrganizationResponsible
from backend.app.models.bid import BidDecision, Review
from backend.app.schemas.bid import BidCreate, BidResponse, BidUpdate, ReviewResponse, ReviewCreate
from backend.app.database import SessionLocal

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def validate_title(title: str):
    if not title or len(title) < 3 or len(title) > 100:
        raise HTTPException(status_code=422, detail="Title must be from 3 to 100 characters long")


def validate_description(description: str):
    if description and len(description) > 500:
        raise HTTPException(status_code=422, detail="Description must not exceed 500 characters")


def validate_amount(amount: float):
    if amount <= 0:
        raise HTTPException(status_code=422, detail="Amount must be greater than 0")


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


@router.get("/", response_model=list[BidResponse])
def get_bids(
        skip: int = 0,
        limit: int = 100,
        username: str = None,
        db: Session = Depends(get_db)
):
    try:
        user = get_user_by_username(username, db)

        subquery = db.query(
            Bid.bid_root_id, func.max(Bid.version).label("max_version")
        ).group_by(Bid.bid_root_id).subquery()

        bids_query = (
            db.query(Bid)
            .join(subquery, (Bid.bid_root_id == subquery.c.bid_root_id) & (Bid.version == subquery.c.max_version))
        )

        responsible_orgs = db.query(OrganizationResponsible.organization_id).filter(
            OrganizationResponsible.user_id == user.id
        ).subquery()

        bids_query = bids_query.filter(
            (Bid.organization_id.in_(responsible_orgs)) | and_(
                Bid.status == "PUBLISHED",
                db.query(Tender.organization_id)
                .filter(Tender.id == Bid.tender_id, Tender.organization_id.in_(responsible_orgs))
                .exists()
            )
        )

        bids = bids_query.offset(skip).limit(limit).all()
        return bids

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.get("/my", response_model=list[BidResponse])
def get_user_bids(
        username: str,
        db: Session = Depends(get_db)
):
    try:
        user = get_user_by_username(username, db)

        subquery = db.query(
            Bid.bid_root_id, func.max(Bid.version).label("max_version")
        ).group_by(Bid.bid_root_id).subquery()

        # Основной запрос для получения последних версий предложений пользователя
        bids = (
            db.query(Bid)
            .join(subquery, (Bid.bid_root_id == subquery.c.bid_root_id) & (Bid.version == subquery.c.max_version))
            .filter(Bid.creator_id == user.id)
            .all()
        )

        if not bids:
            raise HTTPException(status_code=404, detail="No bids found for this user")
        return bids

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        handle_exception(e)


@router.post("/new", response_model=BidResponse)
def create_bid(
        bid: BidCreate,
        username: str = None,
        db: Session = Depends(get_db)
):
    try:
        creator = get_user_by_username(username, db)

        responsible = db.query(OrganizationResponsible).filter(
            OrganizationResponsible.user_id == creator.id
        ).first()

        if not responsible:
            raise HTTPException(status_code=403,
                                detail="User is not responsible for any organization")

        organization = db.query(Organization).filter(
            Organization.id == responsible.organization_id).first()
        if not organization:
            raise HTTPException(status_code=404, detail="Organization not found")

        tender = db.query(Tender).filter(Tender.id == bid.tender_id).first()
        if not tender:
            raise HTTPException(status_code=404, detail="Tender not found")

        if not bid.title or not bid.description or not bid.amount:
            raise HTTPException(status_code=400, detail="Title, description, and amount are required")

        validate_title(bid.title)
        validate_description(bid.description)

        new_bid = Bid(
            bid_root_id=uuid.uuid4(),
            tender_id=bid.tender_id,
            organization_id=organization.id,
            creator_id=creator.id,
            title=bid.title,
            description=bid.description,
            amount=bid.amount,
            status="CREATED",
            quorum=None,
            version=1,
            created_at=func.now(),
            updated_at=func.now()
        )

        db.add(new_bid)
        db.commit()
        db.refresh(new_bid)

        return new_bid

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        handle_exception(e)


@router.get("/{tender_id}/list", response_model=list[BidResponse])
def get_bids_for_tender(
        tender_id: UUID,
        username: str = None,
        db: Session = Depends(get_db)
):
    try:
        user = get_user_by_username(username, db)
        tender = get_tender_by_id(tender_id, db)
        check_user_responsibility(user.id, tender.organization_id, db)

        subquery = db.query(
            Bid.bid_root_id, func.max(Bid.version).label("max_version")
        ).group_by(Bid.bid_root_id).subquery()

        bids_query = db.query(Bid).join(
            subquery,
            (Bid.bid_root_id == subquery.c.bid_root_id) & (Bid.version == subquery.c.max_version)
        ).filter(
            Bid.tender_id == tender_id,
            Bid.status == "PUBLISHED"
        )

        bids = bids_query.all()

        if not bids:
            raise HTTPException(status_code=404, detail="No bids found for this tender")

        return bids

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        handle_exception(e)


@router.patch("/{bid_id}/status", response_model=BidResponse)
def update_bid_status(
        bid_id: UUID,
        new_status: str,
        username: str = None,
        db: Session = Depends(get_db)
):
    try:
        user = get_user_by_username(username, db)
        bid = get_bid_by_id(bid_id, db)
        check_user_responsibility(user.id, bid.organization_id, db)

        if new_status not in ["CREATED", "PUBLISHED", "CANCELED", "APPROVED", "REJECTED"]:
            raise HTTPException(status_code=400, detail="Invalid status")

        bid.status = new_status
        db.commit()
        db.refresh(bid)

        return bid

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        handle_exception(e)


@router.patch("/{bid_id}/edit", response_model=BidResponse)
def update_bid(
        bid_id: UUID,
        bid: BidUpdate,
        username: str = None,
        db: Session = Depends(get_db)
):
    try:
        user = get_user_by_username(username, db)
        current_bid = get_bid_by_id(bid_id, db)
        check_user_responsibility(user.id, current_bid.organization_id, db)

        if not bid.title or not bid.description or bid.amount is None:
            raise HTTPException(status_code=400,
                                detail="Title, description, and amount are required")

        validate_title(bid.title)
        validate_description(bid.description)
        validate_amount(bid.amount)

        new_bid_data = current_bid.__dict__.copy()
        new_bid_data.pop("_sa_instance_state")
        for key, value in bid.dict(exclude_unset=True).items():
            new_bid_data[key] = value

        new_bid = Bid(
            bid_root_id=current_bid.bid_root_id,
            organization_id=current_bid.organization_id,
            tender_id=current_bid.tender_id,
            title=new_bid_data["title"],
            description=new_bid_data["description"],
            amount=new_bid_data["amount"],
            status=new_bid_data["status"],
            version=current_bid.version + 1,
            creator_id=current_bid.creator_id,
            created_at=current_bid.created_at,
            updated_at=func.now()
        )

        db.add(new_bid)
        db.commit()
        db.refresh(new_bid)

        return new_bid

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        handle_exception(e)


@router.put("/{bid_id}/rollback/{version}", response_model=BidResponse)
def rollback_bid(
        bid_id: UUID,
        version: int,
        username: str = None,
        db: Session = Depends(get_db)
):
    try:
        user = get_user_by_username(username, db)
        current_bid = get_bid_by_id(bid_id, db)
        check_user_responsibility(user.id, current_bid.organization_id, db)

        rollback_version = db.query(Bid).filter(
            Bid.bid_root_id == current_bid.bid_root_id,
            Bid.version == version
        ).first()

        if not rollback_version:
            raise HTTPException(status_code=404, detail="Version not found for the bid")

        new_bid = Bid(
            bid_root_id=current_bid.bid_root_id,
            organization_id=rollback_version.organization_id,
            tender_id=rollback_version.tender_id,
            title=rollback_version.title,
            description=rollback_version.description,
            amount=rollback_version.amount,
            status=rollback_version.status,
            version=current_bid.version + 1,
            creator_id=rollback_version.creator_id,
            created_at=current_bid.created_at,
            updated_at=func.now()
        )

        db.add(new_bid)
        db.commit()
        db.refresh(new_bid)

        return new_bid

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        handle_exception(e)


@router.post("/submit_decision")
def submit_bid_decision(
        bid_id: UUID,
        decision: str,
        username: str = None,
        db: Session = Depends(get_db)
):
    try:
        user = get_user_by_username(username, db)

        bid = db.query(Bid).filter(Bid.id == bid_id).first()
        if not bid:
            raise HTTPException(status_code=404, detail="Bid not found")

        if bid.status in ["REJECTED", "APPROVED"]:
            raise HTTPException(status_code=400,
                                detail=f"Bid is already {bid.status}. No further decisions allowed.")

        tender = db.query(Tender).filter(Tender.id == bid.tender_id).first()
        if not tender:
            raise HTTPException(status_code=404, detail="Tender not found")

        check_user_responsibility(user.id, tender.organization_id, db)

        if decision not in ["REJECTED", "APPROVED"]:
            raise HTTPException(status_code=400, detail="Invalid decision")

        # Проверка, не существует ли уже решение от этого пользователя для данного предложения
        existing_decision = db.query(BidDecision).filter(
            BidDecision.bid_id == bid.id,
            BidDecision.user_id == user.id
        ).first()

        if existing_decision:
            raise HTTPException(status_code=400,
                                detail="User has already submitted a decision for this bid")

        new_decision = BidDecision(
            bid_id=bid.id,
            user_id=user.id,
            decision=decision
        )
        db.add(new_decision)
        db.commit()

        # Проверка на отклонение предложения при наличии хотя бы одного "REJECTED"
        if decision == "REJECTED":
            bid.status = "REJECTED"
            db.commit()
            return {"status": "Bid has been rejected"}

        responsible_users = db.query(OrganizationResponsible).filter(
            OrganizationResponsible.organization_id == tender.organization_id
        ).count()

        quorum = min(3, responsible_users)

        # Подсчет количества одобрений
        approvals = db.query(BidDecision).filter(
            BidDecision.bid_id == bid.id,
            BidDecision.decision == "APPROVED"
        ).count()

        if approvals >= quorum:
            bid.status = "APPROVED"
            db.commit()
            return {"status": "Bid has been approved"}

        return {"status": "Decision recorded, awaiting further responses"}

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        handle_exception(e)


@router.get("/{bid_id}/reviews", response_model=list[ReviewResponse])
def get_reviews(
        bid_id: UUID,
        authorUsername: str,
        db: Session = Depends(get_db),
        username: str = None
):
    try:
        user = get_user_by_username(username, db)
        bid = get_bid_by_id(bid_id, db)
        tender = get_tender_by_id(bid.tender_id, db)
        check_user_responsibility(user.id, tender.organization_id, db)

        author = db.query(Employee).filter(Employee.username == authorUsername).first()
        if not author:
            raise HTTPException(status_code=404, detail="Author not found")

        bids = db.query(Bid).filter(Bid.creator_id == author.id, Bid.tender_id == tender.id).all()

        if not bids:
            raise HTTPException(status_code=404,
                                detail="No bids found for this author in the specified tender")

        author_bids = db.query(Bid).filter(Bid.creator_id == author.id).all()
        bid_ids = [bid.id for bid in author_bids]
        reviews = db.query(Review).filter(Review.bid_id.in_(bid_ids)).all()

        return reviews

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        handle_exception(e)


@router.post("/feedback", response_model=ReviewResponse)
def create_review(
        bid_id: UUID,
        authorUsername: str,
        review_data: ReviewCreate,
        db: Session = Depends(get_db),
        username: str = None
):
    try:
        user = get_user_by_username(username, db)
        bid = get_bid_by_id(bid_id, db)
        tender = get_tender_by_id(bid.tender_id, db)
        check_user_responsibility(user.id, tender.organization_id, db)

        author = db.query(Employee).filter(Employee.username == authorUsername).first()
        if not author:
            raise HTTPException(status_code=404, detail="Author not found")

        if bid.creator_id != author.id:
            raise HTTPException(status_code=400,
                                detail="The specified author did not create this bid")

        new_review = Review(
            bid_id=bid.id,
            reviewer_id=user.id,
            author_id=author.id,
            content=review_data.content,
            rating=review_data.rating
        )

        db.add(new_review)
        db.commit()
        db.refresh(new_review)

        return new_review

    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        handle_exception(e)
