from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OfferRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    file_name: str
    file_url: str | None
    file_created_date: datetime
    excel_headers: list[str]


class GenerateOfferResponse(BaseModel):
    scrape_run_id: UUID
    offer_id: UUID
    company_id: UUID
    file_name: str
    file_url: str | None
    file_created_date: datetime
    excel_headers: list[str]
    incentive_count: int
