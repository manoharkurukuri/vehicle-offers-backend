from app.schemas.llm import OfferExtractionResponse


def test_missing_and_unrecognized_values_become_none():
    parsed = OfferExtractionResponse.model_validate(
        {
            "offers": [
                {
                    "offer_type": "something unsupported",
                    "vehicle_type": "unknown",
                    "year": "not found",
                    "msrp": "N/A",
                    "offer_emphasis": "Current owners only",
                }
            ]
        }
    )

    offer = parsed.offers[0]
    assert offer.offer_type is None
    assert offer.vehicle_type is None
    assert offer.year is None
    assert offer.msrp is None
    assert offer.offer_emphasis is None


def test_values_are_normalized_and_parsed():
    parsed = OfferExtractionResponse.model_validate(
        {
            "offers": [
                {
                    "offer_type": "lease",
                    "vehicle_type": "certified pre-owned",
                    "year": "2026",
                    "lowest_monthly_payment": "$229",
                    "lease_term_months": "36 months",
                    "down_payment_or_due_at_signing": "due at lease signing",
                    "total_due_at_signing": "$3,998",
                    "annual_mileage": "10,000 miles per year",
                    "finance_rate": "1.9%",
                }
            ]
        }
    )

    offer = parsed.offers[0]
    assert offer.offer_type == "Lease Offer"
    assert offer.vehicle_type == "CPO"
    assert offer.year == 2026
    assert offer.lowest_monthly_payment == 229.0
    assert offer.lease_term_months == 36
    assert offer.down_payment_or_due_at_signing == "Due at Signing"
    assert offer.total_due_at_signing == 3998.0
    assert offer.annual_mileage == 10000
    assert offer.finance_rate == 1.9
