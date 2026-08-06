from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import time

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, safe_slug, write_json

CROSSREF_API_URL = "https://api.crossref.org/works"
_USER_AGENT = "Day10DataPipelineLab/0.1 (mailto:student@example.com)"
_RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 5
_BACKOFF_BASE_SECONDS = 1.0


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _date_parts_to_iso(date_field: dict | None) -> str:
    if not date_field:
        return ""
    parts = date_field.get("date-parts")
    if not parts or not parts[0]:
        return ""
    values = list(parts[0]) + [1, 1]
    year, month, day = values[0], values[1], values[2]
    try:
        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
    except (TypeError, ValueError):
        return ""


def _extract_authors(item: dict) -> list[str]:
    authors = []
    for author in item.get("author") or []:
        given = normalize_whitespace(author.get("given", ""))
        family = normalize_whitespace(author.get("family", ""))
        name = normalize_whitespace(f"{given} {family}")
        if name:
            authors.append(name)
    return authors

def _extract_categories(item: dict) -> list[str]:
    subjects = [normalize_whitespace(s) for s in (item.get("subject") or []) if normalize_whitespace(s)]
    if subjects:
        return subjects
    container_titles = [normalize_whitespace(c) for c in (item.get("container-title") or []) if normalize_whitespace(c)]
    if container_titles:
        return container_titles
    item_type = normalize_whitespace(item.get("type", ""))
    return [item_type] if item_type else []


def _extract_pdf_url(item: dict) -> str:
    links = item.get("link") or []
    for link in links:
        if "pdf" in str(link.get("content-type", "")).lower():
            return link.get("URL", "")
    if links:
        return links[0].get("URL", "")
    return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    items = payload.get("message", {}).get("items", [])
    seen_ids: set[str] = set()
    records: list[PaperRecord] = []

    for item in items:
        doi = item.get("DOI", "")
        titles = item.get("title") or []
        title = normalize_whitespace(titles[0]) if titles else ""
        summary = item.get("abstract", "") or ""

        if not doi or not title or not summary.strip():
            continue

        paper_id = safe_slug(doi)
        if paper_id in seen_ids:
            continue
        seen_ids.add(paper_id)

        categories = _extract_categories(item)
        published = _date_parts_to_iso(item.get("published") or item.get("issued"))
        updated = item.get("created", {}).get("date-time", "") or published

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=_extract_authors(item),
                categories=categories,
                primary_category=categories[0] if categories else "",
                published=published,
                updated=updated,
                abs_url=item.get("URL", ""),
                pdf_url=_extract_pdf_url(item),
                comment=normalize_whitespace(item.get("type", "")),
            )
        )

    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    headers = {"User-Agent": _USER_AGENT}

    response = None
    last_error: Exception | None = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            response = requests.get(CROSSREF_API_URL, params=params, headers=headers, timeout=30)
        except requests.RequestException as exc:
            last_error = exc
            time.sleep(_BACKOFF_BASE_SECONDS * (2**attempt))
            continue

        if response.status_code in _RETRY_STATUS_CODES and attempt < _MAX_ATTEMPTS - 1:
            retry_after = response.headers.get("Retry-After")
            delay = float(retry_after) if retry_after else _BACKOFF_BASE_SECONDS * (2**attempt)
            time.sleep(delay)
            continue

        break

    if response is None:
        raise RuntimeError(f"Crossref request failed after {_MAX_ATTEMPTS} attempts: {last_error}")
    response.raise_for_status()

    payload = response.json()
    write_json(settings.paths.raw_api_response, payload)

    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    payload = read_json(path)
    return [PaperRecord(**item) for item in payload]
