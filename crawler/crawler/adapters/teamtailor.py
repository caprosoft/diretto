"""
Adattatore Teamtailor — ATS usato da molte aziende privacy-focused.
API pubblica JSON, nessun auth richiesto.
GNU AGPL-3.0
"""

import json
import logging

from ..fetcher import PoliteFetcher

log = logging.getLogger(__name__)

TEAMTAILOR_API = "https://api.teamtailor.com/v1/jobs"


async def fetch_teamtailor(company_slug: str, fetcher: PoliteFetcher) -> list[str]:
    """
    Prova l'API pubblica Teamtailor.
    Lo slug si trova nell'URL: company.teamtailor.com → slug = "company"
    """
    # Endpoint pubblico embed
    url = f"https://{company_slug}.teamtailor.com/jobs.json"
    html = await fetcher.fetch_text(url)
    if not html:
        return []
    try:
        data = json.loads(html)
        jobs = data if isinstance(data, list) else data.get("jobs", [])
        urls = []
        for j in jobs:
            # Teamtailor restituisce slug o id
            job_url = j.get("links", {}).get("careersite-job-url") or \
                      j.get("url") or \
                      f"https://{company_slug}.teamtailor.com/jobs/{j.get('id', '')}"
            if job_url:
                urls.append(job_url)
        log.info(f"Teamtailor [{company_slug}]: {len(urls)} annunci")
        return urls
    except Exception as e:
        log.debug(f"Teamtailor fallback per {company_slug}: {e}")
        return []
