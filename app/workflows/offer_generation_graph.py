from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

import logfire
from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session
from typing_extensions import TypedDict

from app.core.constants import EXCEL_HEADERS
from app.core.exceptions import DatabaseOperationError
from app.models.monthly_vehicle_incentive import MonthlyVehicleIncentive
from app.models.offer import Offer
from app.schemas.llm import OfferExtractionResponse, VehicleIncentiveLLM
from app.services.excel_service import ExcelService
from app.services.llm_extractor import LLMOfferExtractor
from app.services.scraper import get_website_content_from_url
from app.services.storage_service import CloudinaryStorageService


class OfferWorkflowState(TypedDict, total=False):
    company_id: UUID
    dealer_name: str
    company_url: str
    body: str
    body_char_count: int
    extraction: OfferExtractionResponse
    incentives: list[VehicleIncentiveLLM]
    file_name: str
    file_url: str
    file_public_id: str
    offer_id: UUID
    file_created_date: datetime
    incentive_count: int


class OfferGenerationWorkflow:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.llm_extractor = LLMOfferExtractor()
        self.excel_service = ExcelService()
        self.storage = CloudinaryStorageService()
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(OfferWorkflowState)
        builder.add_node("scrape_website", self._scrape_website)
        builder.add_node("extract_with_llm", self._extract_with_llm)
        builder.add_node("normalize_top_five", self._normalize_top_five)
        builder.add_node("create_excel", self._create_excel)
        builder.add_node("persist_results", self._persist_results)

        builder.add_edge(START, "scrape_website")
        builder.add_edge("scrape_website", "extract_with_llm")
        builder.add_edge("extract_with_llm", "normalize_top_five")
        builder.add_edge("normalize_top_five", "create_excel")
        builder.add_edge("create_excel", "persist_results")
        builder.add_edge("persist_results", END)
        return builder.compile()

    @staticmethod
    def _scrape_website(state: OfferWorkflowState) -> dict[str, Any]:
        content = get_website_content_from_url(state["company_url"])
        body = content["body"]
        return {
            "body": body,
            "body_char_count": len(body),
        }

    def _extract_with_llm(self, state: OfferWorkflowState) -> dict[str, Any]:
        extraction = self.llm_extractor.extract(state["body"])
        return {"extraction": extraction}

    @staticmethod
    def _normalize_top_five(state: OfferWorkflowState) -> dict[str, Any]:
        normalized: list[VehicleIncentiveLLM] = []
        for index, incentive in enumerate(state["extraction"].offers[:5], start=1):
            normalized.append(
                incentive.model_copy(
                    update={
                        "offer_priority": f"Vehicle #{index}",
                        "offer_emphasis": None,
                    }
                )
            )

        logfire.info("Offers normalized", offer_count=len(normalized))
        return {
            "incentives": normalized,
            "incentive_count": len(normalized),
        }

    def _create_excel(self, state: OfferWorkflowState) -> dict[str, Any]:
        file_name, local_file_path = self.excel_service.create_workbook(
            dealer_name=state["dealer_name"],
            incentives=state["incentives"],
            source_url=state["company_url"],
        )
        # Push to Cloudinary and drop the local copy; only the URL is kept.
        try:
            file_url, public_id = self.storage.upload(local_file_path, file_name)
        finally:
            Path(local_file_path).unlink(missing_ok=True)
        return {
            "file_name": file_name,
            "file_url": file_url,
            "file_public_id": public_id,
        }

    @staticmethod
    def _db_value(value):
        if hasattr(value, "value"):
            return value.value
        return value

    def _persist_results(self, state: OfferWorkflowState) -> dict[str, Any]:
        created_at = datetime.now(timezone.utc)

        try:
            offer = Offer(
                company_id=state["company_id"],
                file_name=state["file_name"],
                file_url=state["file_url"],
                file_created_date=created_at,
                excel_headers=list(EXCEL_HEADERS),
            )
            self.db.add(offer)
            self.db.flush()

            for incentive in state["incentives"]:
                row = MonthlyVehicleIncentive(
                    offer_id=offer.id,
                    company_id=state["company_id"],
                    offer_priority=incentive.offer_priority,
                    offer_type=self._db_value(incentive.offer_type),
                    offer_emphasis=None,
                    vehicle_type=self._db_value(incentive.vehicle_type),
                    year=incentive.year,
                    make=incentive.make,
                    model=incentive.model,
                    trim=incentive.trim,
                    drive_train=incentive.drive_train,
                    stock_number=incentive.stock_number,
                    vin_number=incentive.vin_number,
                    msrp=incentive.msrp,
                    lowest_monthly_payment=incentive.lowest_monthly_payment,
                    lease_term_months=incentive.lease_term_months,
                    down_payment_or_due_at_signing=self._db_value(
                        incentive.down_payment_or_due_at_signing
                    ),
                    down_payment=incentive.down_payment,
                    total_due_at_signing=incentive.total_due_at_signing,
                    annual_mileage=incentive.annual_mileage,
                    finance_rate=incentive.finance_rate,
                    finance_term_months=incentive.finance_term_months,
                    discount_towards_msrp=incentive.discount_towards_msrp,
                    buy_for_price=incentive.buy_for_price,
                    selling_price=incentive.selling_price,
                    disclaimer=incentive.disclaimer,
                    additional_creative_needs=incentive.additional_creative_needs,
                    impel_model_movers=incentive.impel_model_movers,
                )
                self.db.add(row)

            self.db.commit()
            return {
                "offer_id": offer.id,
                "file_created_date": created_at,
            }
        except Exception as exc:
            self.db.rollback()
            # The workbook already lives on Cloudinary; remove the orphaned asset.
            self.storage.delete(state["file_public_id"])
            raise DatabaseOperationError(
                f"Failed to persist offer workbook metadata and rows: {exc}"
            ) from exc

    def invoke(self, initial_state: OfferWorkflowState) -> OfferWorkflowState:
        return self.graph.invoke(initial_state)
