import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.monthly_vehicle_incentive import MonthlyVehicleIncentive
    from app.models.scrape_run import ScrapeRun


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Offer(Base):
    __tablename__ = "offers"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    file_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_created_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    excel_headers: Mapped[list[str]] = mapped_column(JSON, nullable=False)

    company: Mapped["Company"] = relationship(back_populates="offers")
    incentives: Mapped[list["MonthlyVehicleIncentive"]] = relationship(
        back_populates="offer", cascade="all, delete-orphan"
    )
    scrape_runs: Mapped[list["ScrapeRun"]] = relationship(back_populates="offer")
