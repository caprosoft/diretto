"""
Fetcher — scarica pagine rispettando robots.txt e rate limit per dominio.
GNU AGPL-3.0
"""

import asyncio
import logging
import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

log = logging.getLogger(__name__)

USER_AGENT = (
    "DirrettoCrawler/0.1 (+https://diretto.org/crawler; "
    "rispetta robots.txt; open source AGPL-3)"
)

# Secondi minimi tra due richieste allo stesso dominio
RATE_LIMIT_SECONDS = 2.0

# Timeout per singola richiesta
REQUEST_TIMEOUT = 20.0


class PoliteFetcher:
    def __init__(self):
        self._rate_limits: dict[str, float] = {}    # dominio → timestamp ultima richiesta
        self._robots_cache: dict[str, RobotFileParser] = {}
        self._client = httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            timeout=REQUEST_TIMEOUT,
            http2=True,
        )

    async def close(self):
        await self._client.aclose()

    # ── robots.txt ────────────────────────────────────────────────

    async def _load_robots(self, base_url: str) -> RobotFileParser:
        """Scarica e mette in cache robots.txt per un dominio."""
        if base_url in self._robots_cache:
            return self._robots_cache[base_url]

        rp = RobotFileParser()
        robots_url = f"{base_url}/robots.txt"
        try:
            resp = await self._client.get(robots_url, timeout=10)
            rp.parse(resp.text.splitlines())
            log.debug(f"robots.txt caricato: {robots_url}")
        except Exception:
            # Se non esiste o non è raggiungibile, assumiamo permesso totale
            log.debug(f"robots.txt non trovato per {base_url}, procedo liberamente")
            rp.allow_all = True

        self._robots_cache[base_url] = rp
        return rp

    async def can_fetch(self, url: str) -> bool:
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        rp = await self._load_robots(base)
        allowed = rp.can_fetch(USER_AGENT, url)
        if not allowed:
            log.info(f"robots.txt blocca: {url}")
        return allowed

    # ── rate limiting ─────────────────────────────────────────────

    async def _wait_rate_limit(self, domain: str):
        """Aspetta se necessario per rispettare il rate limit del dominio."""
        last = self._rate_limits.get(domain, 0.0)
        elapsed = time.monotonic() - last
        wait = RATE_LIMIT_SECONDS - elapsed
        if wait > 0:
            log.debug(f"Rate limit: aspetto {wait:.1f}s per {domain}")
            await asyncio.sleep(wait)
        self._rate_limits[domain] = time.monotonic()

    # ── fetch principale ──────────────────────────────────────────

    async def fetch(self, url: str) -> httpx.Response | None:
        """
        Scarica un URL rispettando robots.txt e rate limit.
        Ritorna None se bloccato da robots.txt o in caso di errore grave.
        """
        if not await self.can_fetch(url):
            return None

        domain = urlparse(url).netloc
        await self._wait_rate_limit(domain)

        retries = 3
        for attempt in range(retries):
            try:
                resp = await self._client.get(url)
                log.info(f"[{resp.status_code}] {url}")

                if resp.status_code == 429:
                    # Too Many Requests — backoff esponenziale
                    wait = 5 * (2 ** attempt)
                    log.warning(f"429 su {domain}, aspetto {wait}s")
                    await asyncio.sleep(wait)
                    continue

                if resp.status_code >= 500:
                    log.warning(f"Errore server {resp.status_code} su {url}")
                    await asyncio.sleep(3)
                    continue

                return resp

            except httpx.TimeoutException:
                log.warning(f"Timeout ({attempt+1}/{retries}): {url}")
                await asyncio.sleep(2)
            except httpx.RequestError as e:
                log.error(f"Errore rete su {url}: {e}")
                return None

        log.error(f"Tutti i tentativi falliti per {url}")
        return None

    async def fetch_text(self, url: str) -> str | None:
        """Shortcut: ritorna direttamente il testo HTML o None."""
        resp = await self.fetch(url)
        if resp and resp.status_code == 200:
            return resp.text
        return None

    # ── context manager ───────────────────────────────────────────

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
