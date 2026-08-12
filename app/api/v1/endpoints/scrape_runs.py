from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.exceptions import AppException
from app.db.session import get_db
from app.models.scrape_run import ScrapeRun
from app.schemas.scrape_run import ScrapeRunRead


router = APIRouter(prefix="/scrape-runs", tags=["scrape-runs"])


class ScrapeRunNotFoundError(AppException):
    status_code = 404
    code = "scrape_run_not_found"


@router.get("/{scrape_run_id}", response_model=ScrapeRunRead)
def get_scrape_run(
    scrape_run_id: UUID,
    db: Session = Depends(get_db),
) -> ScrapeRun:
    scrape_run = db.get(ScrapeRun, scrape_run_id)
    if scrape_run is None:
        raise ScrapeRunNotFoundError(
            f"Scrape run id={scrape_run_id} was not found."
        )
    return scrape_run
