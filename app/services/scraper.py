"""Scraping is delegated to a dedicated AWS Lambda container image.

The heavy Playwright/Chromium work lives in ``lambda_scraper/`` and runs in
Lambda. This module invokes that function and returns the same
``{url, title, header, body, footer}`` dict the workflow expects.

If the Lambda scrape fails or comes back as an anti-bot/maintenance page (some
sites block the Lambda's datacenter IP), we fall back to a direct HTTP GET from
this backend, which often succeeds because it runs from a different IP.
"""

import json

import boto3
import requests
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.exceptions import ScrapingError


# Browser-like headers so the direct HTTP fallback is served the real page.
_HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
_HTTP_FALLBACK_TIMEOUT = 30


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


def _fetch_via_lambda(url: str) -> dict[str, str]:
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


def _extract_sections(html: str, url: str) -> dict[str, str]:
    """Turn raw HTML into the same {url,title,header,body,footer} shape the
    Lambda produces, so downstream code is unchanged."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()

    title = soup.title.get_text(strip=True) if soup.title else ""

    header_tag = soup.find("header")
    header = (
        header_tag.get_text(separator="\n", strip=True) if header_tag else ""
    )

    footer_tag = soup.find("footer")
    footer = (
        footer_tag.get_text(separator="\n", strip=True) if footer_tag else ""
    )

    for tag in soup(["header", "footer", "nav"]):
        tag.decompose()

    container = soup.body or soup
    body = container.get_text(separator="\n", strip=True) if container else ""

    return {
        "url": url,
        "title": title,
        "header": header,
        "body": body,
        "footer": footer,
    }


def _fetch_via_http(url: str) -> dict[str, str]:
    """Direct HTTP GET fallback for sites that block the Lambda's IP."""
    try:
        response = requests.get(
            url,
            headers=_HTTP_HEADERS,
            timeout=_HTTP_FALLBACK_TIMEOUT,
        )
    except requests.RequestException as exc:
        raise ScrapingError(f"Direct HTTP request failed: {exc}") from exc

    content = _extract_sections(response.text, url)
    body = content["body"]

    # Anti-bot pages are often served with a 503, so check the page before status.
    if _looks_blocked(body):
        raise ScrapingError(
            "The dealer site also served an anti-bot/maintenance page to the "
            "direct HTTP request."
        )
    if response.status_code >= 400:
        raise ScrapingError(
            f"Direct HTTP request returned HTTP {response.status_code}."
        )
    if not body.strip():
        raise ScrapingError("Direct HTTP request returned an empty body.")
    return content


def get_website_content_from_url(url: str) -> dict[str, str]:
    """Scrape via Lambda; on failure/block, fall back to a direct HTTP GET."""
    try:
        return _fetch_via_lambda(url)
    except ScrapingError as lambda_error:
        try:
            return _fetch_via_http(url)
        except ScrapingError as http_error:
            raise ScrapingError(
                f"Scraping failed. Lambda: {lambda_error} | "
                f"HTTP fallback: {http_error}"
            ) from http_error
