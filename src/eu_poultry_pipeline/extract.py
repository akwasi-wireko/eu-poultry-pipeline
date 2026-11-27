"""Extract: ask the source for data and keep an untouched Bronze copy."""

import json
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

import httpx

BASE_URL = "https://api.tech.ec.europa.eu/agrifood/api/poultry/prices"

# ==============================================================================
# Valid Query Parameter Reference (from OpenAPI Spec)
# ==============================================================================
# memberStateCodes : list[str]   -> EU ISO2 country codes (e.g., ["PT", "ES", "FR", "DE"])
# products         : list[str]   -> Must be one or more of: "Broiler", "Breast", "Legs"
# priceTypes       : list[str]   -> "Selling price" (default if omitted),
#                                   "Retail buying prices", "Non-retail buying prices", "All"
# years            : list[int]   -> 4-digit years (e.g., [2024, 2025])
# months           : list[int]   -> Month numbers 1-12 (e.g., [1, 6, 12])
# weeks            : list[int]   -> Week numbers 1-53 (week 1 = first week of January)
# beginDate        : date | str  -> Start date as a date object or "dd/mm/yyyy" string
# endDate          : date | str  -> End date as a date object or "dd/mm/yyyy" string
# ==============================================================================


class TemporarySourceError(RuntimeError):
    """The source failed in a way that might work if we try again."""


def get_poultry_prices(
    member_state_codes: list[str] | None = None,
    products: list[str] | None = None,
    price_types: list[str] | None = None,
    years: list[int] | None = None,
    months: list[int] | None = None,
    weeks: list[int] | None = None,
    begin_date: date | str | None = None,
    end_date: date | str | None = None,
    base_url: str = BASE_URL,
    timeout: float = 30.0,
) -> list[dict]:
    """Download weekly poultry prices from the EU Agri-food Data Portal API.

    Raises:
        TemporarySourceError: Network trouble, rate limiting (429), or server error (5xx).
        httpx.HTTPStatusError: Any other bad HTTP response (e.g., 400 Bad Request).
    """
    params: dict[str, str] = {}

    if member_state_codes:
        params["memberStateCodes"] = ",".join(member_state_codes)
    if products:
        params["products"] = ",".join(products)
    if price_types:
        params["priceTypes"] = ",".join(price_types)
    if years:
        params["years"] = ",".join(map(str, years))
    if months:
        params["months"] = ",".join(map(str, months))
    if weeks:
        params["weeks"] = ",".join(map(str, weeks))
    if begin_date:
        params["beginDate"] = (
            begin_date.strftime("%d/%m/%Y") if isinstance(begin_date, date) else begin_date
        )
    if end_date:
        params["endDate"] = (
            end_date.strftime("%d/%m/%Y") if isinstance(end_date, date) else end_date
        )

    with httpx.Client(headers={"Accept": "application/json"}, timeout=timeout) as client:
        try:
            response = client.get(base_url, params=params)
        except httpx.TransportError as error:
            raise TemporarySourceError(f"Could not reach EU Agri-food API: {error}") from error

        if response.status_code == 429 or response.status_code >= 500:
            raise TemporarySourceError(
                f"EU Agri-food API answered {response.status_code}. Try later."
            )

        # API returns 404 when valid query filters yield zero matching records
        if response.status_code == 404:
            return []

        response.raise_for_status()
        return response.json()


def save_bronze(
    payload: list[dict],
    bronze_dir: str | Path,
    *,
    member_state_codes: list[str] | None = None,
    source_url: str = BASE_URL,
) -> Path:
    """Save the raw API response list exactly as received, plus ingestion metadata."""
    now = datetime.now(UTC)
    member_state_partition = (
        "-".join(sorted(code.upper() for code in member_state_codes))
        if member_state_codes
        else "ALL"
    )

    folder = (
        Path(bronze_dir)
        / "poultry_prices"
        / f"ingest_date={now.date()}"
        / f"member_state={member_state_partition}"
    )
    folder.mkdir(parents=True, exist_ok=True)

    path = folder / f"{uuid4().hex}.json"
    record = {
        "_source": source_url,
        "_member_state": member_state_partition,
        "_record_count": len(payload),
        "_ingested_at": now.isoformat(),
        "payload": payload,
    }
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
