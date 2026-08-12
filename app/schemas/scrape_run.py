from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ScrapeRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_id: UUID
    offer_id: UUID | None
    status: str
    source_url: str
    llm_model: str
    body_char_count: int | None
    extracted_offer_count: int | None
    error_message: str | None
    started_at: datetime
    finished_at: datetime | None
