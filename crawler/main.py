"""
Main — loop principale del crawler Diretto.
Carica il seed, scansiona ogni azienda, salva i risultati.
GNU AGPL-3.0
"""

import asyncio
import logging
import os
from urllib.parse import urlparse

import yaml

from .discoverer import discover_job_urls
from .fetcher import PoliteFetcher
from .filters import should_skip
from .parser import parse_job
from .storage import get_connection, mark_company_crawled, save_job

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("diretto.crawler")

SEEDS_PATH = os.environ.get("SEEDS_PATH", "data/seeds/companies.yaml")


def load_seeds(path: str) -> list[dict]:
    with open(path) as f:
        return yaml.safe_load(f) or []


async def crawl_company(company: dict, fetcher: PoliteFetcher):
    """Scansiona una singola azienda e salva gli annunci trovati."""
    name = company["name"]
    url = company["careers_url"]
    slug = company.get("slug", "")
    domain = urlparse(url).netloc

    log.info(f"── Inizio crawl: {name} ({url})")

    # 1. Trova URL annunci
    job_urls = await discover_job_urls(url, fetcher, slug)
    if not job_urls:
        log.warning(f"Nessun annuncio trovato per {name}")
        return

    # 2. Scarica e analizza ogni annuncio
    saved = 0
    skipped = 0

    conn = await get_connection()
    try:
        for job_url in job_urls:
            html = await fetcher.fetch_text(job_url)
            if not html:
                continue

            job = parse_job(html, job_url, company_name=name)
            if not job:
                continue

            skip, reason = should_skip(job)
            if skip:
                log.debug(f"Skip [{reason}]: {job_url}")
                skipped += 1
                continue

            result = await save_job(conn, job)
            if result:
                saved += 1

        await mark_company_crawled(conn, domain)
    finally:
        await conn.close()

    log.info(f"── Fine crawl {name}: {saved} salvati, {skipped} scartati")


async def crawl_all():
    """Scansiona tutte le aziende nel seed."""
    companies = load_seeds(SEEDS_PATH)
    log.info(f"Seed caricato: {len(companies)} aziende")

    async with PoliteFetcher() as fetcher:
        for company in companies:
            try:
                await crawl_company(company, fetcher)
            except Exception as e:
                log.error(f"Errore su {company.get('name', '?')}: {e}", exc_info=True)
                # Mai fermare il loop per un singolo errore


async def run_loop():
    """Loop pianificato: crawl ogni N ore (da env CRAWL_INTERVAL_HOURS)."""
    interval_hours = int(os.environ.get("CRAWL_INTERVAL_HOURS", "24"))
    interval_seconds = interval_hours * 3600

    log.info(f"Crawler avviato — intervallo: {interval_hours}h")

    while True:
        await crawl_all()
        log.info(f"Prossimo crawl tra {interval_hours}h")
        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    asyncio.run(run_loop())
