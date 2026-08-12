from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.exceptions import CompanyNotFoundError
from app.db.session import get_db
from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyRead


router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=CompanyRead, status_code=201)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db)) -> Company:
    company = Company(
        dealer_name=payload.dealer_name,
        company_url=str(payload.company_url),
        logo_url=str(payload.logo_url) if payload.logo_url else None,
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.get("", response_model=list[CompanyRead])
def list_companies(db: Session = Depends(get_db)) -> list[Company]:
    return list(db.scalars(select(Company).order_by(Company.id)).all())


@router.get("/{company_id}", response_model=CompanyRead)
def get_company(company_id: UUID, db: Session = Depends(get_db)) -> Company:
    company = db.get(Company, company_id)
    if company is None:
        raise CompanyNotFoundError(f"Company id={company_id} was not found.")
    return company
