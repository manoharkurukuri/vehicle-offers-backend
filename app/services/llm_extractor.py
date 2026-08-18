import logfire
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.core.exceptions import ConfigurationError, LLMExtractionError
from app.schemas.llm import OfferExtractionResponse


SYSTEM_PROMPT = """
You extract vehicle offers from automobile dealer website text.

Return structured data matching the provided schema.

Rules:
1. Extract every DISTINCT vehicle offer you can find on the website.
   A single offer is often repeated on the page: the hero banner, an offer card,
   a "See details" modal, and the fine-print disclaimer can all describe the SAME
   offer. Treat all of those as ONE offer, not several. Two offers are the same
   when they describe the same vehicle (same year/make/model/trim, or same VIN or
   stock number) with the same headline terms (same monthly payment, term, and
   due-at-signing, or the same APR). Never output the same offer more than once.
2. Return at most the 5 best offers ranked by how attractive they are to a customer.
   Rank by customer value in this priority order:
   - Largest discount / savings off MSRP or largest bonus/rebate cash.
   - Lowest monthly lease/finance payment relative to the vehicle.
   - Lowest finance APR (e.g. 0.9% APR beats 3.9% APR).
   - Lowest total due at signing / lowest money down.
   If there are 5 or fewer offers total, return all of them.
   When comparing, treat a clearly larger explicit savings amount as the stronger
   offer. Do not invent or calculate numbers just to rank; only use values the
   source explicitly provides. If value cannot be compared, fall back to the
   top-to-bottom order the offers appear on the website.
3. Never invent a value. If the source does not explicitly provide it, return null.
4. Offer Type must be one of:
   - Lease Offer
   - Combined Lease/APR Offer
   - Bonus Cash Offer
   - Buy For Offer
   - Finance Offer
   - Bonus Offer
   - Conquest Offer
5. If an offer is fundamentally a lease but contains conquest/loyalty eligibility,
   keep Offer Type as Lease Offer. Use Conquest Offer only when the offer itself is
   a standalone conquest incentive.
6. If the SAME vehicle is advertised with more than one financing structure
   (e.g. a lease payment AND an APR AND a bonus cash amount), return it as ONE
   offer, not one offer per structure. When it explicitly includes both lease and
   APR/finance terms, use Combined Lease/APR Offer. Only create separate offers
   for genuinely different vehicles.
7. Vehicle Type must be one of New, Used, CPO,
   Loaner/Courtesy Vehicle/Nearly New, or null.
8. For "due at lease signing" or equivalent, use Due at Signing and put the amount
   in total_due_at_signing. Do not call it a down payment unless the source explicitly
   says down payment/cash down.
9. finance_rate is the APR percentage number, e.g. 1.9 for 1.9% APR.
10. Do not calculate missing values. For example, do not sum incentives and call the
    result Discount Towards MSRP unless the source explicitly identifies an MSRP discount.
11. If multiple VINs belong to one offer, return them in vin_number as one comma-separated string.
12. Every offer has its own disclaimer. Each vehicle typically has a separate
    fine-print block, often starting with "Vehicle shown for illustration purposes
    only" or "Closed-end lease available on a <vehicle>". Copy that block verbatim
    into the disclaimer field for THAT offer. Match each disclaimer to its offer by
    the vehicle name/VIN mentioned inside the disclaimer. Never leave disclaimer null
    when a matching disclaimer exists on the page, and never reuse one offer's
    disclaimer for a different offer. Do not fabricate disclaimer language.
13. offer_emphasis must be null for now.
14. Do not treat navigation text, buttons, headings, financing links, or inventory links
    as separate offers.

OUTPUT FORMAT:
Return ONLY a single JSON object (no markdown, no prose) with this exact shape:
{{
  "offers": [
    {{
      "offer_priority": string | null,
      "offer_type": "Lease Offer" | "Combined Lease/APR Offer" | "Bonus Cash Offer" | "Buy For Offer" | "Finance Offer" | "Bonus Offer" | "Conquest Offer" | null,
      "offer_emphasis": null,
      "vehicle_type": "New" | "Used" | "CPO" | "Loaner/Courtesy Vehicle/Nearly New" | null,
      "year": integer | null,
      "make": string | null,
      "model": string | null,
      "trim": string | null,
      "drive_train": string | null,
      "stock_number": string | null,
      "vin_number": string | null,
      "msrp": number | null,
      "lowest_monthly_payment": number | null,
      "lease_term_months": integer | null,
      "down_payment_or_due_at_signing": "Down Payment" | "Due at Signing" | null,
      "down_payment": number | null,
      "total_due_at_signing": number | null,
      "annual_mileage": integer | null,
      "finance_rate": number | null,
      "finance_term_months": integer | null,
      "discount_towards_msrp": number | null,
      "buy_for_price": number | null,
      "selling_price": number | null,
      "disclaimer": string | null,
      "additional_creative_needs": string | null,
      "impel_model_movers": string | null
    }}
  ]
}}
Every field must be present on each offer; use null when the source does not
explicitly provide a value. Numbers must be plain JSON numbers with no "$", ","
or "%". Return at most five offers.
""".strip()


class LLMOfferExtractor:
    def __init__(self) -> None:
        self.model_name = (
            settings.gemini_model
            if settings.llm_provider == "gemini"
            else settings.groq_model
        )
        self.model = self._build_model()
        method = (
            "json_mode"
            if settings.llm_provider == "gemini"
            else settings.groq_structured_output_method
        )
        self.structured_model = self.model.with_structured_output(
            OfferExtractionResponse,
            method=method,
            include_raw=True,
        )
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                (
                    "human",
                    "Dealer website body:\n\n{body}\n\n"
                    "Extract at most the five best offers for a customer, "
                    "ranked by highest discount/savings and overall value.",
                ),
            ]
        )
        self.chain = self.prompt | self.structured_model

    @staticmethod
    def _build_model():
        if settings.llm_provider == "gemini":
            api_key = settings.gemini_api_key.get_secret_value()
            if not api_key:
                raise ConfigurationError(
                    "GEMINI_API_KEY is not configured. Add it to the .env file."
                )
            # Gemini exposes an OpenAI-compatible endpoint.
            return ChatOpenAI(
                model=settings.gemini_model,
                api_key=api_key,
                base_url=settings.gemini_base_url,
                temperature=0,
                timeout=settings.gemini_timeout_seconds,
                max_retries=settings.gemini_max_retries,
                max_tokens=settings.gemini_max_tokens,
            )

        api_key = settings.groq_api_key.get_secret_value()
        if not api_key:
            raise ConfigurationError(
                "GROQ_API_KEY is not configured. Add it to the .env file."
            )
        return ChatGroq(
            model=settings.groq_model,
            api_key=api_key,
            temperature=0,
            timeout=settings.groq_timeout_seconds,
            max_retries=settings.groq_max_retries,
        )

    @staticmethod
    def _compact(body: str) -> str:
        # Dealer pages repeat the same disclaimer/nav lines per offer card.
        # Drop blank and duplicate lines so we keep more unique signal per token.
        seen: set[str] = set()
        lines: list[str] = []
        for raw in body.splitlines():
            line = raw.strip()
            if not line or line in seen:
                continue
            seen.add(line)
            lines.append(line)
        return "\n".join(lines)

    @staticmethod
    def _prepare_body(body: str) -> str:
        body = LLMOfferExtractor._compact(body.strip())
        if len(body) <= settings.max_body_chars:
            return body

        # Keep the beginning and end instead of silently exceeding the model context.
        # The limit is configurable because different models have different contexts.
        head_size = int(settings.max_body_chars * 0.85)
        tail_size = settings.max_body_chars - head_size
        return (
            body[:head_size]
            + "\n\n[CONTENT TRUNCATED BY BACKEND]\n\n"
            + body[-tail_size:]
        )

    def extract(self, body: str) -> OfferExtractionResponse:
        prepared_body = self._prepare_body(body)

        with logfire.span(
            "groq structured offer extraction",
            model=self.model_name,
            body_chars=len(prepared_body),
        ):
            try:
                result = self.chain.invoke({"body": prepared_body})
            except Exception as exc:
                raise LLMExtractionError(
                    f"Groq extraction request failed: {exc}"
                ) from exc

        parsing_error = result.get("parsing_error")
        if parsing_error is not None:
            raise LLMExtractionError(
                f"LLM structured output validation failed: {parsing_error}"
            )

        parsed = result.get("parsed")
        if parsed is None:
            raise LLMExtractionError(
                "LLM returned no parsed structured output."
            )

        try:
            if not isinstance(parsed, OfferExtractionResponse):
                parsed = OfferExtractionResponse.model_validate(parsed)
        except Exception as exc:
            raise LLMExtractionError(
                f"Pydantic validation failed for LLM output: {exc}"
            ) from exc

        return parsed
