from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MonthlyVehicleIncentiveRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    offer_id: UUID
    company_id: UUID
    offer_priority: str | None
    offer_type: str | None
    offer_emphasis: str | None
    vehicle_type: str | None
    year: int | None
    make: str | None
    model: str | None
    trim: str | None
    drive_train: str | None
    stock_number: str | None
    vin_number: str | None
    msrp: Decimal | None
    lowest_monthly_payment: Decimal | None
    lease_term_months: int | None
    down_payment_or_due_at_signing: str | None
    down_payment: Decimal | None
    total_due_at_signing: Decimal | None
    annual_mileage: int | None
    finance_rate: Decimal | None
    finance_term_months: int | None
    discount_towards_msrp: Decimal | None
    buy_for_price: Decimal | None
    selling_price: Decimal | None
    disclaimer: str | None
    additional_creative_needs: str | None
    impel_model_movers: str | None
