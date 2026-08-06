from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
import html
import re
import time

import requests

from core.config import Settings
from core.utils import compact_join, normalize_whitespace, read_json, write_json

CROSSREF_API_URL = "https://api.crossref.org/works"

# Crossref tra ve payload rat lon neu lay het field (reference list, funder, ...).
# Chi lay dung field can cho PaperRecord + provenance de raw snapshot con doc duoc.
# Luu y: `language` KHONG nam trong whitelist cua `select` (Crossref tra 400).
SELECT_FIELDS = (
    "DOI,title,subtitle,abstract,author,subject,container-title,short-container-title,"
    "publisher,type,group-title,issued,published,published-online,posted,created,"
    "deposited,indexed,URL,link,score"
)

RETRY_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
MAX_ATTEMPTS = 5
BACKOFF_BASE_SECONDS = 2.0
REQUEST_TIMEOUT_SECONDS = 30

# Abstract cua Crossref la JATS XML, khong phai plain text.
_TAG_PATTERN = re.compile(r"<[^>]+>")
# Section heading ("Abstract", "Summary", "BACKGROUND", "Introduction", ...). Crossref
# dung ca <jats:title> lan <title> tran. Phai xoa CA NOI DUNG chu khong chi xoa tag:
# neu chi strip tag thi heading dinh vao dau summary thanh text rac.
# Day la tang duy nhat con biet do la heading - sau khi ve plain text thi khong con
# phan biet duoc "Summary" (nhan muc) voi "Summary" (mot tu trong cau).
_SECTION_TITLE_PATTERN = re.compile(
    r"<(?P<ns>jats:)?title\b[^>]*>.*?</(?P=ns)?title>", re.IGNORECASE | re.DOTALL
)
_DOI_PREFIX_PATTERN = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:)", re.IGNORECASE)


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


def _strip_markup(value: str) -> str:
    """Bo JATS/HTML tag va giai ma entity thanh plain text.

    Section heading bi xoa han (ca tag lan noi dung); cac tag con lai chi bi thay
    bang khoang trang de giu nguyen noi dung.
    """
    without_headings = _SECTION_TITLE_PATTERN.sub(" ", value)
    return normalize_whitespace(html.unescape(_TAG_PATTERN.sub(" ", without_headings)))


def _stable_paper_id(doi: str) -> str:
    """DOI la identifier on dinh cua Crossref: cung mot paper luon ra cung id.

    Chuan hoa de id khong doi giua cac lan fetch: bo prefix resolver va lowercase
    (DOI la case-insensitive theo spec).
    """
    return _DOI_PREFIX_PATTERN.sub("", doi.strip()).lower()


def _first_text(value: object) -> str:
    """Crossref tra ve title/container-title duoi dang list."""
    if isinstance(value, list):
        for item in value:
            if isinstance(item, str) and item.strip():
                return normalize_whitespace(item)
        return ""
    if isinstance(value, str):
        return normalize_whitespace(value)
    return ""


def _date_from_parts(node: object) -> str:
    """`date-parts` co the thieu thang/ngay: [[2026]] hoac [[2026, 6]]."""
    if not isinstance(node, dict):
        return ""
    parts = node.get("date-parts") or []
    if not parts or not isinstance(parts[0], list) or not parts[0]:
        return ""
    numbers = [int(part) for part in parts[0][:3] if isinstance(part, int)]
    if not numbers:
        return ""
    year = numbers[0]
    month = numbers[1] if len(numbers) > 1 else 1
    day = numbers[2] if len(numbers) > 2 else 1
    try:
        return datetime(year, month, day, tzinfo=UTC).date().isoformat()
    except ValueError:
        return ""


def _datetime_field(node: object) -> str:
    """Uu tien `date-time` (co gio) truoc khi fallback ve `date-parts`."""
    if isinstance(node, dict):
        raw = node.get("date-time")
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return _date_from_parts(node)


def _published_date(item: dict) -> str:
    """`issued` la ngay xuat ban chinh thuc; cac field con lai la fallback."""
    for key in ("issued", "published", "published-online", "posted", "created"):
        value = _date_from_parts(item.get(key))
        if value:
            return value
    return ""


def _updated_date(item: dict, published: str) -> str:
    """`deposited` = lan cuoi metadata duoc cap nhat tai Crossref."""
    for key in ("deposited", "indexed", "created"):
        value = _datetime_field(item.get(key))
        if value:
            return value
    return published


def _extract_authors(item: dict) -> list[str]:
    authors: list[str] = []
    for entry in item.get("author") or []:
        if not isinstance(entry, dict):
            continue
        # Author co the la to chuc (chi co `name`) thay vi ca nhan (`given`/`family`).
        name = entry.get("name") or compact_join(
            [str(entry.get("given") or ""), str(entry.get("family") or "")], sep=" "
        )
        name = normalize_whitespace(str(name))
        if name:
            authors.append(name)
    return authors


def _extract_categories(item: dict) -> list[str]:
    """`subject` gan nhu luon rong tren Crossref, nen phai co fallback chain.

    Neu chi dua vao `subject`, toan bo record se co categories = [] va cac cau hoi
    ve category o buoc evaluation se khong con du lieu that de kiem chung.
    """
    subjects = [normalize_whitespace(s) for s in item.get("subject") or [] if isinstance(s, str)]
    subjects = [s for s in subjects if s]
    if subjects:
        return subjects

    fallbacks = [
        _first_text(item.get("container-title")),
        _first_text(item.get("short-container-title")),
        normalize_whitespace(str(item.get("group-title") or "")),
        normalize_whitespace(str(item.get("type") or "")),
    ]
    seen: set[str] = set()
    categories: list[str] = []
    for value in fallbacks:
        if value and value.lower() not in seen:
            seen.add(value.lower())
            categories.append(value)
    return categories


def _extract_pdf_url(item: dict) -> str:
    links = item.get("link") or []
    if not isinstance(links, list):
        return ""
    candidates = [entry for entry in links if isinstance(entry, dict) and entry.get("URL")]
    for entry in candidates:
        if str(entry.get("content-type") or "").lower() == "application/pdf":
            return str(entry["URL"])
    for entry in candidates:
        if str(entry.get("intended-application") or "").lower() == "text-mining":
            return str(entry["URL"])
    return str(candidates[0]["URL"]) if candidates else ""


def _extract_title(item: dict) -> str:
    title = _first_text(item.get("title"))
    subtitle = _first_text(item.get("subtitle"))
    if title and subtitle and subtitle.lower() not in title.lower():
        return f"{title}: {subtitle}"
    return title


def _build_comment(item: dict) -> str:
    """Provenance ngan gon: giup truy vet record ve dung nguon phat hanh."""
    return compact_join(
        [
            normalize_whitespace(str(item.get("type") or "")),
            _first_text(item.get("container-title")),
            normalize_whitespace(str(item.get("publisher") or "")),
        ],
        sep=" | ",
    )


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload thanh list PaperRecord.

    Chi bo record thieu identifier/title/abstract - day la ba field ma toan bo
    pipeline phia sau phu thuoc vao. Cac quyet dinh khac (dedupe, loc ngon ngu,
    loc do dai) thuoc ve buoc cleaning de raw snapshot con phan anh dung source.
    """
    items = (payload or {}).get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        if not isinstance(item, dict):
            continue

        doi = str(item.get("DOI") or "").strip()
        title = _extract_title(item)
        summary = _strip_markup(str(item.get("abstract") or ""))
        if not doi or not title or not summary:
            continue

        categories = _extract_categories(item)
        published = _published_date(item)

        records.append(
            PaperRecord(
                paper_id=_stable_paper_id(doi),
                title=title,
                summary=summary,
                authors=_extract_authors(item),
                categories=categories,
                primary_category=categories[0] if categories else "",
                published=published,
                updated=_updated_date(item, published),
                abs_url=str(item.get("URL") or (f"https://doi.org/{doi}" if doi else "")),
                pdf_url=_extract_pdf_url(item),
                comment=_build_comment(item),
            )
        )

    return records


def _get_with_retry(params: dict) -> requests.Response:
    """Goi Crossref voi exponential backoff cho 429/5xx.

    Ton trong header `Retry-After` khi Crossref gui ve, vi day la con so server
    thuc su muon client cho.
    """
    headers = {
        "User-Agent": "day10-data-observability-lab/0.1 (https://github.com/; python-requests)",
        "Accept": "application/json",
    }
    last_error: Exception | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(
                CROSSREF_API_URL,
                params=params,
                headers=headers,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            last_error = exc
            response = None
        else:
            if response.status_code not in RETRY_STATUS_CODES:
                response.raise_for_status()
                return response
            last_error = requests.HTTPError(
                f"Crossref returned {response.status_code}", response=response
            )

        if attempt == MAX_ATTEMPTS:
            break

        delay = BACKOFF_BASE_SECONDS ** (attempt - 1)
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                delay = max(delay, float(retry_after))
        print(f"[crossref] attempt {attempt}/{MAX_ATTEMPTS} failed, retrying in {delay:.0f}s")
        time.sleep(delay)

    raise RuntimeError(
        f"Crossref request failed after {MAX_ATTEMPTS} attempts: {last_error}"
    ) from last_error


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Goi Crossref, luu raw response, parse thanh records va luu snapshot.

    Raw response duoc ghi xuong dia TRUOC khi parse: neu parsing sai thi van con
    nguyen payload goc de debug hoac repair ma khong phai goi lai source.
    """
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
        "select": SELECT_FIELDS,
    }

    response = _get_with_retry(params)
    payload = response.json()

    write_json(settings.paths.raw_api_response, payload)

    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [asdict(record) for record in records])

    returned = len(payload.get("message", {}).get("items", []))
    print(
        f"[crossref] fetched {returned} items -> {len(records)} valid records "
        f"({returned - len(records)} dropped: missing DOI/title/abstract)"
    )
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Doc JSON snapshot va map thanh `PaperRecord`."""
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"Expected a list of records in {path}, got {type(payload).__name__}.")

    records: list[PaperRecord] = []
    for entry in payload:
        records.append(
            PaperRecord(
                paper_id=str(entry["paper_id"]),
                title=str(entry["title"]),
                summary=str(entry["summary"]),
                authors=list(entry.get("authors") or []),
                categories=list(entry.get("categories") or []),
                primary_category=str(entry.get("primary_category") or ""),
                published=str(entry.get("published") or ""),
                updated=str(entry.get("updated") or ""),
                abs_url=str(entry.get("abs_url") or ""),
                pdf_url=str(entry.get("pdf_url") or ""),
                comment=str(entry.get("comment") or ""),
            )
        )
    return records
