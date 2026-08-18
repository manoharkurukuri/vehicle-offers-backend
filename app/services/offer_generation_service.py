from datetime import datetime, timezone
from uuid import UUID

import logfire
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import EXCEL_HEADERS
from app.core.exceptions import AppException, CompanyNotFoundError
from app.models.company import Company
from app.models.scrape_run import ScrapeRun
from app.schemas.offer import GenerateOfferResponse
from app.workflows.offer_generation_graph import OfferGenerationWorkflow


class OfferGenerationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def generate_for_company(self, company_id: UUID) -> GenerateOfferResponse:
        company = self.db.get(Company, company_id)
        if company is None:
            raise CompanyNotFoundError(f"Company id={company_id} was not found.")

        scrape_run = ScrapeRun(
            company_id=company.id,
            status="running",
            source_url=company.company_url,
            llm_model=settings.gemini_model,
        )
        self.db.add(scrape_run)
        self.db.commit()
        self.db.refresh(scrape_run)

        try:
            workflow = OfferGenerationWorkflow(self.db)
            result = workflow.invoke(
                {
                    "company_id": company.id,
                    "dealer_name": company.dealer_name,
                    "company_url": company.company_url,
                }
            )

            scrape_run.offer_id = result["offer_id"]
            scrape_run.status = "completed"
            scrape_run.body_char_count = result.get("body_char_count")
            scrape_run.extracted_offer_count = result.get("incentive_count", 0)
            scrape_run.finished_at = datetime.now(timezone.utc)
            self.db.commit()

            logfire.info(
                "Offer generation completed",
                company_id=company.id,
                offer_id=result["offer_id"],
                scrape_run_id=scrape_run.id,
                incentive_count=result.get("incentive_count", 0),
            )

            return GenerateOfferResponse(
                scrape_run_id=scrape_run.id,
                offer_id=result["offer_id"],
                company_id=company.id,
                file_name=result["file_name"],
                file_url=result.get("file_url"),
                file_created_date=result["file_created_date"],
                excel_headers=list(EXCEL_HEADERS),
                incentive_count=result.get("incentive_count", 0),
            )
        except AppException as exc:
            self._mark_failed(scrape_run, exc.message)
            raise
        except Exception as exc:
            self._mark_failed(scrape_run, str(exc))
            raise

    def _mark_failed(self, scrape_run: ScrapeRun, message: str) -> None:
        # A workflow node can roll back the session, so reload the run before updating it.
        persisted_run = self.db.get(ScrapeRun, scrape_run.id)
        if persisted_run is None:
            return
        persisted_run.status = "failed"
        persisted_run.error_message = message[:5000]
        persisted_run.finished_at = datetime.now(timezone.utc)
        self.db.commit()
