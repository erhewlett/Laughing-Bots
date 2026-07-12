"""JSearch (RapidAPI) client for fetching real job postings.

Docs: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch

Only the /search-v2 endpoint is used for ingestion. The API key is read from
settings (env / .env) and never hard-coded.
"""
from __future__ import annotations

import httpx

from app.config import settings

BASE_URL = "https://jsearch.p.rapidapi.com"


class JSearchError(RuntimeError):
    """Raised when the JSearch API cannot be reached or returns an error."""


def _headers() -> dict[str, str]:
    if not settings.rapidapi_key:
        raise JSearchError(
            "RAPIDAPI_KEY is not set. Add it to backend/.env before ingesting."
        )
    return {
        "X-RapidAPI-Key": settings.rapidapi_key,
        "X-RapidAPI-Host": settings.rapidapi_host,
    }


def search_jobs(
    query: str,
    *,
    page: int = 1,
    num_pages: int = 1,
    country: str = "us",
    date_posted: str = "month",  # today | 3days | week | month | all -> "month" ~ 30 days
) -> list[dict]:
    """Call /search and return the list of raw job dicts from `data`.

    date_posted defaults to "month" to honor the requirement that keywords come
    only from postings no more than ~30 days old.
    """
    params = {
        "query": query,
        "page": page,
        "num_pages": num_pages,
        "country": country,
        "date_posted": date_posted,
    }
    try:
        resp = httpx.get(
            f"{BASE_URL}/search-v2", headers=_headers(), params=params, timeout=30
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:  # network error, 4xx/5xx, timeout
        raise JSearchError(f"JSearch request failed: {exc}") from exc

    try:
        payload = resp.json()
    except ValueError as exc:  # malformed / non-JSON body
        raise JSearchError("JSearch returned a non-JSON response") from exc
    if payload.get("status") != "OK":
        raise JSearchError(f"JSearch returned non-OK status: {payload.get('status')}")

    # /search-v2 wraps results as {"data": {"jobs": [...], "cursor": "..."}};
    # older /search returned {"data": [...]}. Handle both.
    data = payload.get("data", [])
    if isinstance(data, dict):
        return data.get("jobs", [])
    return data
