# Vehicle Offer Extraction API

FastAPI backend that:

1. Loads a dealer/company by database ID.
2. Reads its `company_url`.
3. Scrapes the rendered page with Playwright and falls back to ScrapingBee.
4. Sends the cleaned website body to ChatGroq.
5. Uses Pydantic structured output to validate/normalize the LLM response.
6. Uses LangGraph to orchestrate scrape -> LLM -> normalize -> Excel -> DB.
7. Keeps only the first five offers in website order.
8. Generates a local `.xlsx` file with the 27 requested columns and Excel dropdowns.
9. Stores file metadata in `offers` and row data in `monthly_vehicle_incentives`.
10. Leaves `offers.file_url` as `NULL` until object/cloud storage is added.
11. Records each attempt in `scrape_runs`.
12. Uses Logfire for FastAPI, SQLAlchemy, Pydantic, and custom workflow logging.

## Project structure

```text
vehicle-offers-backend/
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── storage/
│   └── offers/
│       └── .gitkeep
├── app/
│   ├── main.py
│   ├── api/
│   │   └── v1/
│   │       ├── router.py
│   │       └── endpoints/
│   │           ├── companies.py
│   │           ├── offers.py
│   │           └── scrape_runs.py
│   ├── core/
│   │   ├── config.py
│   │   ├── constants.py
│   │   ├── exceptions.py
│   │   └── exception_handlers.py
│   ├── db/
│   │   ├── base.py
│   │   └── session.py
│   ├── models/
│   │   ├── company.py
│   │   ├── offer.py
│   │   ├── monthly_vehicle_incentive.py
│   │   └── scrape_run.py
│   ├── schemas/
│   │   ├── company.py
│   │   ├── offer.py
│   │   ├── incentive.py
│   │   ├── scrape_run.py
│   │   └── llm.py
│   ├── services/
│   │   ├── scraper.py
│   │   ├── llm_extractor.py
│   │   ├── excel_service.py
│   │   └── offer_generation_service.py
│   └── workflows/
│       └── offer_generation_graph.py
└── tests/
    ├── test_llm_schema.py
    ├── test_excel_service.py
    └── test_database_schema.py
```

## Database tables

### `companies`

- `id`
- `dealer_name`
- `company_url`
- `logo_url`
- `created_at`
- `updated_at`

### `offers`

One row per generated Excel file.

- `id`
- `company_id` FK -> `companies.id`
- `file_name`
- `file_url` nullable; currently always NULL
- `file_created_date`
- `excel_headers` JSON containing the exact 27 header names

The requested base filename format is:

```text
dealer_name_month_date_day.xlsx
```

Example:

```text
norm_reeves_honda_irvine_august_11_tuesday.xlsx
```

If a file with that name already exists on the same day, `_2`, `_3`, etc. is added to avoid overwriting an earlier export.

### `monthly_vehicle_incentives`

One row per extracted vehicle offer. It has the 27 Excel fields as nullable columns plus `id`, `offer_id`, and `company_id`.

The backend assigns `Vehicle #1` through `Vehicle #5` itself. Missing fields stay `NULL` in the database and blank in Excel.

### `scrape_runs`

Audit table for the fourth table:

- `id`
- `company_id`
- `offer_id` nullable
- `status`: running/completed/failed
- `source_url`
- `llm_model`
- `body_char_count`
- `extracted_offer_count`
- `error_message`
- `started_at`
- `finished_at`

## Setup

Python 3.11+ is recommended.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
```

Set at minimum:

```env
GROQ_API_KEY=your_key_here
```

If Playwright is running on a server without a desktop/display, set:

```env
PLAYWRIGHT_HEADLESS=true
```

If you want the ScrapingBee fallback:

```env
SCRAPINGBEE_API_KEY=your_key_here
```

Logfire sends remotely only when a `LOGFIRE_TOKEN` is present. Without it, the application still uses the Logfire instrumentation locally without requiring a token.

## Run

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

## API flow

### 1. Create a dealer

```bash
curl -X POST http://127.0.0.1:8000/api/v1/companies \
  -H 'Content-Type: application/json' \
  -d '{
    "dealer_name": "Norm Reeves Honda Irvine",
    "company_url": "https://www.normreeveshondairvine.com/vehicle-specials/",
    "logo_url": null
  }'
```

### 2. Generate the offer workbook

```bash
curl -X POST http://127.0.0.1:8000/api/v1/companies/1/generate-offers
```

Example response shape:

```json
{
  "scrape_run_id": 1,
  "offer_id": 1,
  "company_id": 1,
  "file_name": "norm_reeves_honda_irvine_august_11_tuesday.xlsx",
  "file_url": null,
  "file_created_date": "2026-08-11T16:00:00Z",
  "excel_headers": ["Offer Priority", "Offer Type"],
  "incentive_count": 5
}
```

The real `excel_headers` response contains all 27 headers.

### 3. Read generated file metadata

```bash
curl http://127.0.0.1:8000/api/v1/offers/1
```

### 4. Read the extracted database rows

```bash
curl http://127.0.0.1:8000/api/v1/offers/1/incentives
```

### 5. Inspect a scrape run

```bash
curl http://127.0.0.1:8000/api/v1/scrape-runs/1
```

## LLM behavior

The LLM receives the dealer website body and must return a Pydantic `OfferExtractionResponse`. Every offer field is optional.

Important rules enforced by prompt plus backend validation:

- At most five offers.
- Preserve website order.
- Unknown/missing values -> `None`.
- Invalid enum values -> `None`.
- Invalid numeric values -> `None`.
- `offer_emphasis` is currently forced to `None`.
- Website conquest/loyalty wording does not automatically replace a lease offer's primary type.
- No invented calculations such as treating arbitrary incentive cash as an MSRP discount.
- Backend, not LLM, assigns `Vehicle #1` ... `Vehicle #5`.
- Excel creation and database column mapping are deterministic code.

## Excel output

The workbook contains exactly the requested 27 columns. It also adds dropdown validation for:

- Offer Type
- Vehicle Type
- Down Payment or Due at Signing

The source dealer URL is stored as a comment on the first header cell so the workbook retains source provenance without adding another data column.

## Notes for production later

This version intentionally has no authentication/authorization because that was requested. Before production, add Alembic migrations, authentication, cloud/object storage, background jobs if scraping becomes slow, retries/queueing, rate limits, and a PostgreSQL database.

## Relevant library docs

- LangGraph: https://docs.langchain.com/oss/python/langgraph/overview
- ChatGroq: https://docs.langchain.com/oss/python/integrations/chat/groq
- Groq models: https://console.groq.com/docs/models
- Logfire FastAPI: https://logfire.pydantic.dev/docs/integrations/web-frameworks/fastapi/
- Logfire SQLAlchemy: https://logfire.pydantic.dev/docs/integrations/databases/sqlalchemy/
