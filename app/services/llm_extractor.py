import logfire
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from app.core.config import settings
from app.core.exceptions import ConfigurationError, LLMExtractionError
from app.schemas.llm import OfferExtractionResponse


SYSTEM_PROMPT = """
You extract vehicle offers from automobile dealer website text.

Return structured data matching the provided schema.

Rules:
1. Extract vehicle offers in the same top-to-bottom order they appear on the website.
2. Return at most the first 5 offers. If there are 5 or fewer, return all of them.
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
6. If the same vehicle offer explicitly includes both lease and APR/finance terms,
   use Combined Lease/APR Offer.
7. Vehicle Type must be one of New, Used, CPO,
   Loaner/Courtesy Vehicle/Nearly New, or null.
8. For "due at lease signing" or equivalent, use Due at Signing and put the amount
   in total_due_at_signing. Do not call it a down payment unless the source explicitly
   says down payment/cash down.
9. finance_rate is the APR percentage number, e.g. 1.9 for 1.9% APR.
10. Do not calculate missing values. For example, do not sum incentives and call the
    result Discount Towards MSRP unless the source explicitly identifies an MSRP discount.
11. If multiple VINs belong to one offer, return them in vin_number as one comma-separated string.
12. Preserve the offer disclaimer text when available. Do not fabricate disclaimer language.
13. offer_emphasis must be null for now.
14. Do not treat navigation text, buttons, headings, financing links, or inventory links
    as separate offers.
""".strip()


class LLMOfferExtractor:
    def __init__(self) -> None:
        api_key = settings.groq_api_key.get_secret_value()
        if not api_key:
            raise ConfigurationError(
                "GROQ_API_KEY is not configured. Add it to the .env file."
            )

        self.model = ChatGroq(
            model=settings.groq_model,
            api_key=api_key,
            temperature=0,
            timeout=settings.groq_timeout_seconds,
            max_retries=settings.groq_max_retries,
        )
        self.structured_model = self.model.with_structured_output(
            OfferExtractionResponse,
            method=settings.groq_structured_output_method,
            include_raw=True,
        )
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                (
                    "human",
                    "Dealer website body:\n\n{body}\n\n"
                    "Extract the first five vehicle offers at most.",
                ),
            ]
        )
        self.chain = self.prompt | self.structured_model

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
            model=settings.groq_model,
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
