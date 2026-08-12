import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.company import Company
    from app.models.offer import Offer


class MonthlyVehicleIncentive(Base):
    __tablename__ = "monthly_vehicle_incentives"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    offer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("offers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    offer_priority: Mapped[str | None] = mapped_column(String(50), nullable=True)
    offer_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    offer_emphasis: Mapped[str | None] = mapped_column(Text, nullable=True)
    vehicle_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    make: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(150), nullable=True)
    trim: Mapped[str | None] = mapped_column(String(150), nullable=True)
    drive_train: Mapped[str | None] = mapped_column(String(50), nullable=True)
    stock_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    vin_number: Mapped[str | None] = mapped_column(Text, nullable=True)
    msrp: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    lowest_monthly_payment: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2), nullable=True
    )
    lease_term_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    down_payment_or_due_at_signing: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    down_payment: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    total_due_at_signing: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2), nullable=True
    )
    annual_mileage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    finance_rate: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    finance_term_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discount_towards_msrp: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2), nullable=True
    )
    buy_for_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    selling_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    disclaimer: Mapped[str | None] = mapped_column(Text, nullable=True)
    additional_creative_needs: Mapped[str | None] = mapped_column(Text, nullable=True)
    impel_model_movers: Mapped[str | None] = mapped_column(Text, nullable=True)

    offer: Mapped["Offer"] = relationship(back_populates="incentives")
    company: Mapped["Company"] = relationship(back_populates="incentives")
