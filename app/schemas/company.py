from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, HttpUrl, field_validator


class CompanyCreate(BaseModel):
    dealer_name: str
    company_url: HttpUrl
    logo_url: HttpUrl | None = None

    @field_validator("dealer_name")
    @classmethod
    def validate_dealer_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("dealer_name cannot be empty")
        return value


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dealer_name: str
    company_url: str
    logo_url: str | None
    created_at: datetime
    updated_at: datetime
