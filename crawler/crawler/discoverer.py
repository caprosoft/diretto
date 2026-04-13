"""
Discoverer — trova URL annunci usando il tipo ATS dichiarato nel seed.
GNU AGPL-3.0
"""

import json
import logging
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .fetcher import PoliteFetcher

log = logging.getLogger(__name__)

# Pattern URL annunci singoli
JOB_URL_PATTERNS = [
    r"/jobs/[\w-]+",
    r"/careers/[\w-]+",
    r"/positions/[\w-]+",
    r"/opening/[\w-]+",
    r"/role/[\w-]+",
    r"/offerte/[\w-]+",
    r"/posizione/[\w-]+",
    r"/apply/[\w-]+",
]

# Pattern URL da ignorare sempre
IGNORE_URL_PATTERNS = [
    r"\.(pdf|doc|docx|png|jpg|jpeg|gif|svg|zip)(\?|$)",
    r"/blog/", r"/news/", r"/press/", r"/about", r"/contact",
    r"/pricing", r"/download", r"/install", r"/support",
    r"/cookie", r"/privacy", r"/terms", r"/legal",
    r"/login", r"/signup", r"/register",
    r"/product", r"/features", r"/solutions",
    r"#", r"mailto:", r"javascript:",
]


# ── Adattatori ATS ────────────────────────────────────────────────────────────

async def _fetch_greenhouse(slug: str, fetcher: PoliteFetcher) -> list[str]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    html = await fetcher.fetch_text(url)
    if not html:
        return []
    try:
        data = json.loads(html)
        return [j["absolute_url"] for j in data.get("jobs", []) if "absolute_url" in j]
    except Exception:
        return []


async def _fetch_lever(slug: str, fetcher: PoliteFetcher) -> list[str]:
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    html = await fetcher.fetch_text(url)
    if not html:
        return []
    try:
        data = json.loads(html)
        return [j["hostedUrl"] for j in data if "hostedUrl" in j]
    except Exception:
        return []


async def _fetch_workable(slug: str, fetcher: PoliteFetcher) -> list[str]:
    url = f"https://apply.workable.com/api/v1/widget/accounts/{slug}/jobs"
    html = await fetcher.fetch_text(url)
    if not html:
        return []
    try:
        data = json.loads(html)
        base = f"https://apply.workable.com/{slug}/j/"
        return [base + j["shortcode"] for j in data.get("results", []) if "shortcode" in j]
    except Exception:
        return []


async def _fetch_ashby(slug: str, fetcher: PoliteFetcher) -> list[str]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    html = await fetcher.fetch_text(url)
    if not html:
        return []
    try:
        data = json.loads(html)
        return [j["jobUrl"] for j in data.get("jobs", []) if "jobUrl" in j]
    except Exception:
        return []


async def _fetch_teamtailor(slug: str, fetcher: PoliteFetcher) -> list[str]:
    url = f"https://{slug}.teamtailor.com/jobs.json"
    html = await fetcher.fetch_text(url)
    if not html:
        # fallback: scraping pagina careers
        html = await fetcher.fetch_text(f"https://{slug}.teamtailor.com/jobs")
        if not html:
            return []
        return _extract_links_matching(html, f"https://{slug}.teamtailor.com")
    try:
        data = json.loads(html)
        jobs = data if isinstance(data, list) else data.get("jobs", [])
        urls = []
        for j in jobs:
            u = (j.get("links") or {}).get("careersite-job-url") or j.get("url")
            if u:
                urls.append(u)
        return urls
    except Exception:
        return []


ATS_FETCHERS = {
    "greenhouse": _fetch_greenhouse,
    "lever":      _fetch_lever,
    "workable":   _fetch_workable,
    "ashby":      _fetch_ashby,
    "teamtailor": _fetch_teamtailor,
}


# ── Link discovery (fallback per siti statici) ────────────────────────────────

def _is_valid_url(url: str, base_domain: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc and parsed.netloc != base_domain:
        return False
    if any(re.search(p, url, re.IGNORECASE) for p in IGNORE_URL_PATTERNS):
        return False
    return True


def _looks_like_job(url: str) -> bool:
    return any(re.search(p, url, re.IGNORECASE) for p in JOB_URL_PATTERNS)


def _extract_links_matching(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    base_domain = urlparse(base_url).netloc
    seen = set()
    links = []
    for a in soup.find_all("a", href=True):
        absolute = urljoin(base_url, a["href"].strip())
        clean = urlparse(absolute)._replace(fragment="").geturl()
        if clean in seen:
            continue
        seen.add(clean)
        if _is_valid_url(clean, base_domain) and _looks_like_job(clean):
            links.append(clean)
    return links


# ── Entrypoint pubblico ───────────────────────────────────────────────────────

async def discover_job_urls(
    careers_url: str,
    fetcher: PoliteFetcher,
    company_type: str = "static",
    company_slug: str = "",
) -> list[str]:
    """
    Trova URL annunci usando il tipo dichiarato nel seed.
    Se il tipo è un ATS noto, usa la sua API diretta.
    Altrimenti fa link discovery statico.
    """
    log.info(f"Discoverer [{company_type}]: {careers_url}")

    # ATS con API diretta
    if company_type in ATS_FETCHERS and company_slug:
        urls = await ATS_FETCHERS[company_type](company_slug, fetcher)
        if urls:
            log.info(f"API {company_type}: {len(urls)} annunci trovati")
            return urls
        log.warning(f"API {company_type} vuota per {company_slug}, fallback statico")

    # Fallback: link discovery statico
    html = await fetcher.fetch_text(careers_url)
    if not html:
        log.warning(f"Impossibile scaricare: {careers_url}")
        return []

    urls = _extract_links_matching(html, careers_url)
    log.info(f"Link discovery statico: {len(urls)} URL trovati")
    return urls
