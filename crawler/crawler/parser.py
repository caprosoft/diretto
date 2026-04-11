"""
Parser — estrae JobPosting strutturato da HTML grezzo.
Strategia: JSON-LD (Schema.org) → euristiche CSS → None
GNU AGPL-3.0
"""

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from dateutil import parser as dateparser

log = logging.getLogger(__name__)


@dataclass
class JobPosting:
    title: str
    company: str
    source_domain: str
    url: str

    location: str = ""
    remote: bool = False
    job_type: str = ""          # full-time | part-time | contract | internship
    description: str = ""
    salary_min: int | None = None
    salary_max: int | None = None
    currency: str | None = None
    posted_at: datetime | None = None
    expires_at: datetime | None = None
    tags: list[str] = field(default_factory=list)
    html_hash: str = ""

    def is_valid(self) -> bool:
        """Un posting minimo deve avere titolo e azienda."""
        return bool(self.title.strip() and self.company.strip())


# ── Selettori euristici ───────────────────────────────────────────────────────

TITLE_SELECTORS = [
    "[data-qa='posting-name']",
    "[class*='job-title']",
    "[class*='jobtitle']",
    "[class*='position-title']",
    "h1.title",
    "h1",
]

DESCRIPTION_SELECTORS = [
    "[class*='job-description']",
    "[class*='description']",
    "[class*='job-details']",
    ".posting-description",
    "article",
    "main",
]

LOCATION_SELECTORS = [
    "[data-qa='posting-location']",
    "[class*='location']",
    "[class*='job-location']",
]

REMOTE_KEYWORDS = [
    "remote", "remoto", "da remoto", "full remote",
    "telelavoro", "smart working", "distributed",
]

JOB_TYPE_MAP = {
    "FULL_TIME": "full-time",
    "PART_TIME": "part-time",
    "CONTRACT": "contract",
    "INTERN": "internship",
    "TEMPORARY": "temporary",
    "full-time": "full-time",
    "part-time": "part-time",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _html_hash(html: str) -> str:
    return hashlib.sha256(html.encode()).hexdigest()[:16]


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return dateparser.parse(value)
    except Exception:
        return None


def _clean_text(text: str, max_chars: int = 3000) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def _detect_remote(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in REMOTE_KEYWORDS)


def _normalize_job_type(raw: str) -> str:
    return JOB_TYPE_MAP.get(raw.upper(), JOB_TYPE_MAP.get(raw.lower(), raw.lower()))


def _extract_salary(salary_data: dict) -> tuple[int | None, int | None, str | None]:
    """Estrae (min, max, currency) da un blocco baseSalary Schema.org."""
    if not salary_data:
        return None, None, None
    value = salary_data.get("value", {})
    if isinstance(value, dict):
        return (
            _to_int(value.get("minValue")),
            _to_int(value.get("maxValue")),
            salary_data.get("currency"),
        )
    return _to_int(value), None, salary_data.get("currency")


def _to_int(v) -> int | None:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


# ── Livello 1: JSON-LD / Schema.org ──────────────────────────────────────────

def _extract_jsonld(soup: BeautifulSoup) -> dict | None:
    """Cerca il primo blocco JSON-LD di tipo JobPosting."""
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
            # Gestisce sia oggetto singolo che array
            if isinstance(data, list):
                data = next((d for d in data if d.get("@type") == "JobPosting"), None)
            if isinstance(data, dict) and data.get("@type") == "JobPosting":
                return data
        except (json.JSONDecodeError, AttributeError):
            continue
    return None


def _parse_jsonld(data: dict, url: str, html: str) -> JobPosting:
    company_data = data.get("hiringOrganization", {})
    location_data = data.get("jobLocation", {})

    # location: può essere stringa o oggetto
    if isinstance(location_data, dict):
        addr = location_data.get("address", {})
        location = ", ".join(filter(None, [
            addr.get("addressLocality"),
            addr.get("addressRegion"),
            addr.get("addressCountry"),
        ]))
    else:
        location = str(location_data)

    salary_min, salary_max, currency = _extract_salary(
        data.get("baseSalary", {})
    )

    job_type_raw = data.get("employmentType", "")
    description = _clean_text(
        BeautifulSoup(data.get("description", ""), "lxml").get_text()
    )
    is_remote = (
        "TELECOMMUTE" in data.get("jobLocationType", "").upper()
        or _detect_remote(location + " " + description)
    )

    return JobPosting(
        title=_clean_text(data.get("title", ""), 200),
        company=company_data.get("name", "") if isinstance(company_data, dict) else str(company_data),
        source_domain=urlparse(url).netloc,
        url=url,
        location=location,
        remote=is_remote,
        job_type=_normalize_job_type(job_type_raw),
        description=description,
        salary_min=salary_min,
        salary_max=salary_max,
        currency=currency,
        posted_at=_parse_date(data.get("datePosted")),
        expires_at=_parse_date(data.get("validThrough")),
        html_hash=_html_hash(html),
    )


# ── Livello 2: Euristiche CSS ─────────────────────────────────────────────────

def _parse_heuristic(soup: BeautifulSoup, url: str, html: str, company_name: str) -> JobPosting | None:
    """Fallback: cerca titolo, descrizione e sede con selettori CSS comuni."""

    title = None
    for sel in TITLE_SELECTORS:
        el = soup.select_one(sel)
        if el:
            title = _clean_text(el.get_text(), 200)
            break

    if not title:
        log.debug(f"Nessun titolo trovato via euristiche: {url}")
        return None

    description = ""
    for sel in DESCRIPTION_SELECTORS:
        el = soup.select_one(sel)
        if el:
            description = _clean_text(el.get_text())
            break

    location = ""
    for sel in LOCATION_SELECTORS:
        el = soup.select_one(sel)
        if el:
            location = _clean_text(el.get_text(), 100)
            break

    return JobPosting(
        title=title,
        company=company_name,
        source_domain=urlparse(url).netloc,
        url=url,
        location=location,
        remote=_detect_remote(location + " " + description),
        description=description,
        html_hash=_html_hash(html),
    )


# ── Entrypoint pubblico ───────────────────────────────────────────────────────

def parse_job(html: str, url: str, company_name: str = "") -> JobPosting | None:
    """
    Tenta di estrarre un JobPosting dall'HTML.
    Prova JSON-LD prima, poi euristiche CSS.
    Ritorna None se non riesce a estrarre i campi minimi.
    """
    if not html:
        return None

    soup = BeautifulSoup(html, "lxml")

    # Strategia 1: JSON-LD
    jsonld = _extract_jsonld(soup)
    if jsonld:
        log.debug(f"JSON-LD trovato: {url}")
        job = _parse_jsonld(jsonld, url, html)
        if not job.company and company_name:
            job.company = company_name
        if job.is_valid():
            return job

    # Strategia 2: euristiche
    log.debug(f"Fallback euristiche: {url}")
    job = _parse_heuristic(soup, url, html, company_name)
    if job and job.is_valid():
        return job

    log.warning(f"Impossibile estrarre posting da: {url}")
    return None
