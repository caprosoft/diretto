"""
Filtri — scarta agenzie, duplicati, annunci scaduti e posting non validi.
GNU AGPL-3.0
"""

import logging
from datetime import datetime, timezone

import yaml

from .parser import JobPosting

log = logging.getLogger(__name__)


def _load_blocklist(path: str = "data/seeds/blocklist.yaml") -> dict:
    try:
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        log.warning(f"blocklist.yaml non trovato: {path}")
        return {}


# Cache blocklist (caricata una volta sola)
_blocklist: dict | None = None


def _get_blocklist() -> dict:
    global _blocklist
    if _blocklist is None:
        _blocklist = _load_blocklist()
    return _blocklist


# ── Filtri singoli ────────────────────────────────────────────────────────────

def is_agency(job: JobPosting) -> bool:
    """True se il posting sembra provenire da un'agenzia o intermediario."""
    bl = _get_blocklist()
    blocked_domains = bl.get("domains", [])
    blocked_keywords = bl.get("keywords", [])

    # 1. Controlla il dominio sorgente
    for domain in blocked_domains:
        if job.source_domain == domain or job.source_domain.endswith(f".{domain}"):
            log.info(f"Bloccato per dominio [{domain}]: {job.url}")
            return True

    # 2. Controlla parole chiave nel testo
    text = (job.title + " " + job.description).lower()
    for kw in blocked_keywords:
        if kw.lower() in text:
            log.info(f"Bloccato per keyword [{kw!r}]: {job.url}")
            return True

    return False


def is_expired(job: JobPosting) -> bool:
    """True se l'annuncio ha una data di scadenza già passata."""
    if job.expires_at is None:
        return False
    now = datetime.now(timezone.utc)
    # Normalizza: se expires_at è naive, assumiamo UTC
    exp = job.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    expired = exp < now
    if expired:
        log.debug(f"Annuncio scaduto ({exp.date()}): {job.url}")
    return expired


def is_too_short(job: JobPosting, min_chars: int = 50) -> bool:
    """True se la descrizione è troppo corta per essere un annuncio reale."""
    return len(job.description.strip()) < min_chars


# ── Entrypoint pubblico ───────────────────────────────────────────────────────

def should_skip(job: JobPosting) -> tuple[bool, str]:
    """
    Controlla tutti i filtri in cascata.
    Ritorna (True, motivo) se il posting va scartato.
    Ritorna (False, "") se il posting è valido.
    """
    if not job.is_valid():
        return True, "campi minimi mancanti (titolo/azienda)"

    if is_expired(job):
        return True, "annuncio scaduto"

    if is_agency(job):
        return True, "agenzia o intermediario rilevato"

    if is_too_short(job):
        return True, "descrizione troppo breve"

    return False, ""
