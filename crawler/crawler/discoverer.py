"""
Discoverer — trova i link ai singoli annunci partendo dalla careers page.
Tre strategie: API JSON note (Greenhouse/Lever/Workable) → link discovery → fallback lista URL.
GNU AGPL-3.0
"""

import logging
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .fetcher import PoliteFetcher

log = logging.getLogger(__name__)

# Pattern URL che suggeriscono un annuncio singolo (non una lista)
JOB_URL_PATTERNS = [
    r"/jobs/\d+",
    r"/careers/\w+-\w+",
    r"/positions/",
    r"/offerte/",
    r"/lavora-con-noi/\w+",
    r"/open-positions/\w+",
    r"/job-openings/",
    r"/posting/",
    r"/apply/",
]

# Pattern URL da ignorare (pagine generiche, non annunci)
IGNORE_PATTERNS = [
    r"\.(pdf|doc|docx|png|jpg|jpeg|gif|svg|zip)$",
    r"/tag/",
    r"/category/",
    r"/page/\d+",
    r"#",
    r"mailto:",
    r"javascript:",
]

# ── Adattatori ATS noti ───────────────────────────────────────────────────────

async def _try_greenhouse(company_slug: str, fetcher: PoliteFetcher) -> list[str]:
    """Greenhouse: API pubblica, nessun auth richiesto."""
    url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs"
    import json
    html = await fetcher.fetch_text(url)
    if not html:
        return []
    try:
        data = json.loads(html)
        return [j["absolute_url"] for j in data.get("jobs", []) if "absolute_url" in j]
    except Exception:
        return []


async def _try_lever(company_slug: str, fetcher: PoliteFetcher) -> list[str]:
    """Lever: API pubblica."""
    url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"
    import json
    html = await fetcher.fetch_text(url)
    if not html:
        return []
    try:
        data = json.loads(html)
        return [j["hostedUrl"] for j in data if "hostedUrl" in j]
    except Exception:
        return []


async def _try_workable(company_slug: str, fetcher: PoliteFetcher) -> list[str]:
    """Workable: endpoint pubblico dei posting."""
    url = f"https://apply.workable.com/api/v1/widget/accounts/{company_slug}/jobs"
    import json
    html = await fetcher.fetch_text(url)
    if not html:
        return []
    try:
        data = json.loads(html)
        jobs = data.get("results", [])
        base = f"https://apply.workable.com/{company_slug}/j/"
        return [base + j["shortcode"] for j in jobs if "shortcode" in j]
    except Exception:
        return []


# ── Rilevamento automatico ATS ────────────────────────────────────────────────

ATS_SIGNALS = {
    "greenhouse.io": "greenhouse",
    "boards.greenhouse.io": "greenhouse",
    "lever.co": "lever",
    "workable.com": "workable",
    "apply.workable.com": "workable",
}


def _detect_ats(html: str, careers_url: str) -> tuple[str | None, str | None]:
    """
    Rileva se il sito usa un ATS noto guardando link e iframe.
    Ritorna (ats_name, company_slug) o (None, None).
    """
    soup = BeautifulSoup(html, "lxml")
    all_links = [a.get("href", "") for a in soup.find_all("a", href=True)]
    all_links += [i.get("src", "") for i in soup.find_all("iframe", src=True)]

    for link in all_links:
        for signal, ats in ATS_SIGNALS.items():
            if signal in link:
                # Estrae lo slug dall'URL
                # es: https://boards.greenhouse.io/basecamp → "basecamp"
                parts = [p for p in urlparse(link).path.split("/") if p]
                slug = parts[0] if parts else None
                if slug:
                    log.debug(f"ATS rilevato: {ats} (slug: {slug})")
                    return ats, slug

    return None, None


# ── Link discovery (siti statici) ─────────────────────────────────────────────

def _looks_like_job_url(url: str) -> bool:
    """Euristica: l'URL sembra un annuncio singolo?"""
    if any(re.search(p, url, re.IGNORECASE) for p in IGNORE_PATTERNS):
        return False
    return any(re.search(p, url, re.IGNORECASE) for p in JOB_URL_PATTERNS)


def _extract_links(html: str, base_url: str) -> list[str]:
    """Estrae tutti i link della pagina, assoluti, de-duplicati."""
    soup = BeautifulSoup(html, "lxml")
    seen = set()
    links = []
    base_domain = urlparse(base_url).netloc

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)

        # Solo link dello stesso dominio
        if parsed.netloc != base_domain:
            continue
        # Normalizza rimuovendo fragment
        clean = parsed._replace(fragment="").geturl()
        if clean not in seen:
            seen.add(clean)
            links.append(clean)

    return links


# ── Entrypoint pubblico ───────────────────────────────────────────────────────

async def discover_job_urls(
    careers_url: str,
    fetcher: PoliteFetcher,
    company_slug: str = "",
) -> list[str]:
    """
    Trova tutti gli URL di annunci singoli partendo dalla careers page.
    Prova in ordine:
      1. API ATS note (Greenhouse, Lever, Workable)
      2. Link discovery sulla pagina statica
    Ritorna lista di URL de-duplicati.
    """
    log.info(f"Discoverer avviato: {careers_url}")

    # Step 1: scarica la careers page
    html = await fetcher.fetch_text(careers_url)
    if not html:
        log.warning(f"Impossibile scaricare: {careers_url}")
        return []

    # Step 2: rileva ATS
    ats, slug = _detect_ats(html, careers_url)
    slug = slug or company_slug  # usa quello passato se non rilevato

    if ats and slug:
        log.info(f"Provo API {ats} con slug '{slug}'")
        urls = []
        if ats == "greenhouse":
            urls = await _try_greenhouse(slug, fetcher)
        elif ats == "lever":
            urls = await _try_lever(slug, fetcher)
        elif ats == "workable":
            urls = await _try_workable(slug, fetcher)

        if urls:
            log.info(f"API {ats}: trovati {len(urls)} annunci")
            return urls
        else:
            log.debug(f"API {ats} non ha restituito risultati, fallback link discovery")

    # Step 3: link discovery statico
    all_links = _extract_links(html, careers_url)
    job_links = [l for l in all_links if _looks_like_job_url(l)]

    # Se link discovery non trova nulla, restituisce tutti i link interni
    # (lasciamo al parser capire quali sono annunci veri)
    if not job_links:
        log.debug(f"Nessun link-annuncio rilevato, uso tutti i link interni ({len(all_links)})")
        job_links = all_links[:50]  # limite di sicurezza

    log.info(f"Link discovery: trovati {len(job_links)} URL candidati")
    return job_links
