"""Scraping is delegated to a dedicated AWS Lambda container image.

The heavy Playwright/Chromium work now lives in ``lambda_scraper/`` and runs in
Lambda. This module simply invokes that function synchronously and returns the
same ``{url, title, header, body, footer}`` dict the workflow already expects,
so nothing downstream had to change.
"""

import json

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings
from app.core.exceptions import ScrapingError


# Interstitials some OEM/dealer sites serve to datacenter/bot IPs instead of the
# real inventory. When we see one, fail loudly instead of extracting 0 offers.
_BLOCK_PAGE_MARKERS = (
    "site is currently offline due to maintenance",
    "site currently not available",
    "site currently\n        not available",
    "nicht erreichbar",
    "access denied",
    "attention required",
    "just a moment",
    "checking your browser",
    "enable javascript and cookies",
)


def _looks_blocked(body: str) -> bool:
    lowered = body.lower()
    return any(marker in lowered for marker in _BLOCK_PAGE_MARKERS)



def _lambda_client():
    config = Config(
        region_name=settings.aws_region,
        connect_timeout=15,
        read_timeout=settings.scraper_lambda_invoke_timeout,
        retries={"max_attempts": 2, "mode": "standard"},
    )
    return boto3.client("lambda", config=config)


def get_website_content_from_url(url: str) -> dict[str, str]:
    """Invoke the scraper Lambda and return the extracted page text."""
    payload = json.dumps({"url": url}).encode("utf-8")

    try:
        response = _lambda_client().invoke(
            FunctionName=settings.scraper_lambda_name,
            InvocationType="RequestResponse",
            Payload=payload,
        )
    except (BotoCoreError, ClientError) as exc:
        raise ScrapingError(f"Failed to invoke scraper Lambda: {exc}") from exc

    raw = response["Payload"].read()
    try:
        result = json.loads(raw or b"{}")
    except json.JSONDecodeError as exc:
        raise ScrapingError(
            f"Scraper Lambda returned non-JSON output: {raw[:500]!r}"
        ) from exc

    # An unhandled exception inside the Lambda surfaces here.
    if response.get("FunctionError"):
        message = (
            result.get("errorMessage", result)
            if isinstance(result, dict)
            else result
        )
        raise ScrapingError(f"Scraper Lambda crashed: {message}")

    if not isinstance(result, dict) or result.get("ok") is not True:
        message = result.get("error") if isinstance(result, dict) else result
        raise ScrapingError(message or "Scraper Lambda reported an error.")

    content = result.get("content") or {}
    body = content.get("body", "")
    if not body.strip():
        raise ScrapingError("Scraper Lambda returned an empty body.")

    if _looks_blocked(body):
        raise ScrapingError(
            "The dealer site served an anti-bot/maintenance page to the scraper "
            "instead of its inventory, so no offers could be extracted. The site "
            "is likely blocking the scraper's IP address."
        )

    return {
        "url": content.get("url", url),
        "title": content.get("title", ""),
        "header": content.get("header", ""),
        "body": body,
        "footer": content.get("footer", ""),
    }
