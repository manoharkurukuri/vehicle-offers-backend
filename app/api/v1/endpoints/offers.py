from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.exceptions import AppException
from app.db.session import get_db
from app.models.monthly_vehicle_incentive import MonthlyVehicleIncentive
from app.models.offer import Offer
from app.schemas.incentive import MonthlyVehicleIncentiveRead
from app.schemas.offer import GenerateOfferResponse, OfferRead
from app.services.offer_generation_service import OfferGenerationService


router = APIRouter(tags=["offers"])


class OfferNotFoundError(AppException):
    status_code = 404
    code = "offer_not_found"


@router.post(
    "/companies/{company_id}/generate-offers",
    response_model=GenerateOfferResponse,
)
def generate_offers(
    company_id: UUID,
    db: Session = Depends(get_db),
) -> GenerateOfferResponse:
    """Scrape the company's URL, extract top five offers, create Excel, persist DB rows."""
    return OfferGenerationService(db).generate_for_company(company_id)


@router.get("/offers/{offer_id}", response_model=OfferRead)
def get_offer(offer_id: UUID, db: Session = Depends(get_db)) -> Offer:
    offer = db.get(Offer, offer_id)
    if offer is None:
        raise OfferNotFoundError(f"Offer id={offer_id} was not found.")
    return offer


@router.get("/companies/{company_id}/offers", response_model=list[OfferRead])
def list_company_offers(
    company_id: UUID,
    db: Session = Depends(get_db),
) -> list[Offer]:
    statement = (
        select(Offer)
        .where(Offer.company_id == company_id)
        .order_by(Offer.file_created_date.desc())
    )
    return list(db.scalars(statement).all())


@router.get(
    "/offers/{offer_id}/incentives",
    response_model=list[MonthlyVehicleIncentiveRead],
)
def list_offer_incentives(
    offer_id: UUID,
    db: Session = Depends(get_db),
) -> list[MonthlyVehicleIncentive]:
    offer = db.get(Offer, offer_id)
    if offer is None:
        raise OfferNotFoundError(f"Offer id={offer_id} was not found.")

    statement = (
        select(MonthlyVehicleIncentive)
        .where(MonthlyVehicleIncentive.offer_id == offer_id)
        .order_by(MonthlyVehicleIncentive.id)
    )
    return list(db.scalars(statement).all())


@router.get("/offers/{offer_id}/row-count")
def get_offer_row_count(offer_id: UUID, db: Session = Depends(get_db)) -> dict:
    offer = db.get(Offer, offer_id)
    if offer is None:
        raise OfferNotFoundError(f"Offer id={offer_id} was not found.")

    count = db.scalar(
        select(func.count(MonthlyVehicleIncentive.id)).where(
            MonthlyVehicleIncentive.offer_id == offer_id
        )
    )
    return {"offer_id": offer_id, "row_count": int(count or 0)}
