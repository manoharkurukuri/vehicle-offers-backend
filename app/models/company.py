import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.monthly_vehicle_incentive import MonthlyVehicleIncentive
    from app.models.offer import Offer
    from app.models.scrape_run import ScrapeRun


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    dealer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_url: Mapped[str] = mapped_column(Text, nullable=False)
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    offers: Mapped[list["Offer"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    incentives: Mapped[list["MonthlyVehicleIncentive"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    scrape_runs: Mapped[list["ScrapeRun"]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
