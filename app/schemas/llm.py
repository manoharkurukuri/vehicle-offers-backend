import re
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OfferType(str, Enum):
    LEASE = "Lease Offer"
    COMBINED_LEASE_APR = "Combined Lease/APR Offer"
    BONUS_CASH = "Bonus Cash Offer"
    BUY_FOR = "Buy For Offer"
    FINANCE = "Finance Offer"
    BONUS = "Bonus Offer"
    CONQUEST = "Conquest Offer"


class VehicleType(str, Enum):
    NEW = "New"
    USED = "Used"
    CPO = "CPO"
    LOANER = "Loaner/Courtesy Vehicle/Nearly New"


class PaymentType(str, Enum):
    DOWN_PAYMENT = "Down Payment"
    DUE_AT_SIGNING = "Due at Signing"


_NULL_STRINGS = {
    "",
    "null",
    "none",
    "n/a",
    "na",
    "unknown",
    "not found",
    "not available",
    "-",
}


def _clean_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text.lower() in _NULL_STRINGS:
        return None
    return text


def _parse_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))

    text = str(value).strip()
    if text.lower() in _NULL_STRINGS:
        return None
    text = text.replace("$", "").replace(",", "").replace("%", "").strip()
    text = re.sub(r"[^0-9.\-]", "", text)
    if not text or text in {"-", ".", "-."}:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _parse_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)

    text = str(value).strip()
    if text.lower() in _NULL_STRINGS:
        return None
    match = re.search(r"-?\d[\d,]*", text)
    if not match:
        return None
    try:
        return int(match.group(0).replace(",", ""))
    except ValueError:
        return None


def _normalize_enum(value: Any, allowed: list[str], aliases: dict[str, str]) -> str | None:
    text = _clean_optional_text(value)
    if text is None:
        return None
    lowered = text.casefold()
    for option in allowed:
        if lowered == option.casefold():
            return option
    return aliases.get(lowered)


class VehicleIncentiveLLM(BaseModel):
    """One vehicle offer extracted from dealer website text.

    Every field is optional. If the source does not explicitly provide a value,
    the model must return null and the validator keeps it as None.
    """

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    offer_priority: str | None = Field(
        default=None,
        description="Website order label. Backend overwrites this as Vehicle #1..#5.",
    )
    offer_type: OfferType | None = Field(default=None)
    offer_emphasis: str | None = Field(
        default=None,
        description="Currently intentionally kept null by backend.",
    )
    vehicle_type: VehicleType | None = None
    year: int | None = None
    make: str | None = None
    model: str | None = None
    trim: str | None = None
    drive_train: str | None = None
    stock_number: str | None = None
    vin_number: str | None = Field(
        default=None,
        description="If multiple VINs belong to the offer, return comma-separated VINs.",
    )
    msrp: float | None = None
    lowest_monthly_payment: float | None = None
    lease_term_months: int | None = None
    down_payment_or_due_at_signing: PaymentType | None = None
    down_payment: float | None = None
    total_due_at_signing: float | None = None
    annual_mileage: int | None = None
    finance_rate: float | None = Field(
        default=None,
        description="APR percentage points, e.g. 1.9 for 1.9% APR.",
    )
    finance_term_months: int | None = None
    discount_towards_msrp: float | None = None
    buy_for_price: float | None = None
    selling_price: float | None = None
    disclaimer: str | None = None
    additional_creative_needs: str | None = None
    impel_model_movers: str | None = None

    @field_validator(
        "offer_priority",
        "make",
        "model",
        "trim",
        "drive_train",
        "stock_number",
        "vin_number",
        "disclaimer",
        "additional_creative_needs",
        "impel_model_movers",
        mode="before",
    )
    @classmethod
    def clean_text_fields(cls, value: Any) -> str | None:
        return _clean_optional_text(value)

    @field_validator("offer_emphasis", mode="before")
    @classmethod
    def force_offer_emphasis_null(cls, value: Any) -> None:
        return None

    @field_validator("offer_type", mode="before")
    @classmethod
    def normalize_offer_type(cls, value: Any) -> str | None:
        allowed = [item.value for item in OfferType]
        aliases = {
            "lease": OfferType.LEASE.value,
            "lease offer": OfferType.LEASE.value,
            "lease/apr": OfferType.COMBINED_LEASE_APR.value,
            "combined lease and apr offer": OfferType.COMBINED_LEASE_APR.value,
            "apr offer": OfferType.FINANCE.value,
            "finance": OfferType.FINANCE.value,
            "financing offer": OfferType.FINANCE.value,
            "bonus cash": OfferType.BONUS_CASH.value,
            "buy for": OfferType.BUY_FOR.value,
            "bonus": OfferType.BONUS.value,
            "conquest": OfferType.CONQUEST.value,
        }
        return _normalize_enum(value, allowed, aliases)

    @field_validator("vehicle_type", mode="before")
    @classmethod
    def normalize_vehicle_type(cls, value: Any) -> str | None:
        allowed = [item.value for item in VehicleType]
        aliases = {
            "certified pre-owned": VehicleType.CPO.value,
            "certified preowned": VehicleType.CPO.value,
            "certified": VehicleType.CPO.value,
            "loaner": VehicleType.LOANER.value,
            "courtesy vehicle": VehicleType.LOANER.value,
            "nearly new": VehicleType.LOANER.value,
        }
        return _normalize_enum(value, allowed, aliases)

    @field_validator("down_payment_or_due_at_signing", mode="before")
    @classmethod
    def normalize_payment_type(cls, value: Any) -> str | None:
        allowed = [item.value for item in PaymentType]
        aliases = {
            "due at lease signing": PaymentType.DUE_AT_SIGNING.value,
            "due at signing": PaymentType.DUE_AT_SIGNING.value,
            "lease signing": PaymentType.DUE_AT_SIGNING.value,
            "cash down": PaymentType.DOWN_PAYMENT.value,
            "down": PaymentType.DOWN_PAYMENT.value,
        }
        return _normalize_enum(value, allowed, aliases)

    @field_validator(
        "msrp",
        "lowest_monthly_payment",
        "down_payment",
        "total_due_at_signing",
        "finance_rate",
        "discount_towards_msrp",
        "buy_for_price",
        "selling_price",
        mode="before",
    )
    @classmethod
    def parse_decimal_fields(cls, value: Any) -> float | None:
        parsed = _parse_decimal(value)
        return float(parsed) if parsed is not None else None

    @field_validator(
        "year",
        "lease_term_months",
        "annual_mileage",
        "finance_term_months",
        mode="before",
    )
    @classmethod
    def parse_integer_fields(cls, value: Any) -> int | None:
        return _parse_int(value)

    @field_validator("year")
    @classmethod
    def validate_year(cls, value: int | None) -> int | None:
        if value is None:
            return None
        return value if 1980 <= value <= 2100 else None

    @field_validator("lease_term_months", "finance_term_months")
    @classmethod
    def validate_term(cls, value: int | None) -> int | None:
        if value is None:
            return None
        return value if 1 <= value <= 120 else None

    @field_validator("annual_mileage")
    @classmethod
    def validate_mileage(cls, value: int | None) -> int | None:
        if value is None:
            return None
        return value if 0 < value <= 100_000 else None

    @field_validator("finance_rate")
    @classmethod
    def validate_finance_rate(cls, value: float | None) -> float | None:
        if value is None:
            return None
        return value if 0 <= value <= 100 else None


class OfferExtractionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    offers: list[VehicleIncentiveLLM] = Field(
        default_factory=list,
        description=(
            "Vehicle offers in the same top-to-bottom order as the website. "
            "Return no more than the first five offers."
        ),
    )
