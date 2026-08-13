"""AWS Lambda entry point for the vehicle-offer scraper.

Event contract (any of these shapes is accepted)::

    {"url": "https://dealer.example.com/specials"}
    {"body": "{\"url\": \"https://...\"}"}   # e.g. API Gateway / SQS style

Response contract::

    {"ok": true,  "content": {"url", "title", "header", "body", "footer"}}
    {"ok": false, "error": "reason"}
"""

import json
from typing import Any

from scraper import ScrapingError, get_website_content_from_url


def _extract_url(event: Any) -> str | None:
    if not isinstance(event, dict):
        return None

    if event.get("url"):
        return event["url"]

    body = event.get("body")
    if isinstance(body, dict):
        return body.get("url")
    if isinstance(body, str):
        try:
            return json.loads(body).get("url")
        except (json.JSONDecodeError, AttributeError):
            return None
    return None


def lambda_handler(event: Any, context: Any) -> dict[str, Any]:
    url = _extract_url(event)
    if not url:
        return {"ok": False, "error": "Missing 'url' in the event payload."}

    try:
        content = get_website_content_from_url(url)
        return {"ok": True, "content": content}
    except ScrapingError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:  # never let the container crash on a bad page
        return {"ok": False, "error": f"Unexpected scraper failure: {exc}"}
