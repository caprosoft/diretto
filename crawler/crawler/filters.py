"""
Filtri — scarta agenzie, duplicati, annunci scaduti e pagine non pertinenti.
GNU AGPL-3.0
"""

import logging
import re
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


_blocklist: dict | None = None


def _get_blocklist() -> dict:
    global _blocklist
    if _blocklist is None:
        _blocklist = _load_blocklist()
    return _blocklist


# ── Parole chiave che indicano un vero annuncio ───────────────────────────────

JOB_POSITIVE_KEYWORDS = [
    # italiano
    "candidati", "candidatura", "invia cv", "posizione aperta",
    "stiamo cercando", "cerchiamo", "offerta di lavoro", "requisiti",
    "responsabilità", "competenze", "esperienza richiesta",
    "cosa farai", "cosa offriamo", "contratto", "stipendio",
    "sede di lavoro", "lavorerai", "ti occuperai",
    # inglese
    "apply", "application", "we are looking for", "we're looking for",
    "job description", "requirements", "responsibilities", "qualifications",
    "what you'll do", "what we offer", "you will", "you'll",
    "full-time", "part-time", "salary", "compensation", "benefits",
    "years of experience", "bachelor", "degree", "team",
]

# Parole chiave che indicano che NON è un annuncio
JOB_NEGATIVE_KEYWORDS = [
    "cookie", "privacy policy", "terms of service", "sign up", "log in",
    "free trial", "pricing", "download", "install", "subscribe",
    "newsletter", "press release", "blog", "case study",
    "accetta i cookie", "informativa", "abbonati",
]

# Titoli che chiaramente non sono annunci
FAKE_JOB_TITLE_PATTERNS = [
    r"^(privacy|cookie|terms|pricing|download|install|sign\s*up|log\s*in)",
    r"^(about|contact|home|blog|news|press)",
    r"^(select|choose|accept|decline)",
    r"^(request|start|try|get)\s+(a\s+)?(free\s+)?(trial|demo|quote)",
    r"^(we are hiring)$",   # pagina generica "stiamo assumendo"
    r"^(join our team)$",   # idem
    r"^(work with us)$",    # idem
]


def is_agency(job: JobPosting) -> bool:
    bl = _get_blocklist()
    blocked_domains = bl.get("domains", [])
    blocked_keywords = bl.get("keywords", [])

    for domain in blocked_domains:
        if job.source_domain == domain or job.source_domain.endswith(f".{domain}"):
            log.info(f"Bloccato per dominio [{domain}]: {job.url}")
            return True

    text = (job.title + " " + job.description).lower()
    for kw in blocked_keywords:
        if kw.lower() in text:
            log.info(f"Bloccato per keyword [{kw!r}]: {job.url}")
            return True

    return False


def is_expired(job: JobPosting) -> bool:
    if job.expires_at is None:
        return False
    now = datetime.now(timezone.utc)
    exp = job.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return exp < now


def is_too_short(job: JobPosting, min_chars: int = 80) -> bool:
    return len(job.description.strip()) < min_chars


def looks_like_job(job: JobPosting) -> bool:
    """
    Controlla se il posting assomiglia a un vero annuncio di lavoro.
    Usa un sistema a punteggio: +1 per ogni segnale positivo, -2 per negativi.
    Soglia minima: 2 punti.
    """
    title_lower = job.title.lower().strip()
    text_lower = (job.title + " " + job.description).lower()

    # Titoli chiaramente non-annuncio → scarta subito (inclusi multilingua)
    all_title_patterns = FAKE_JOB_TITLE_PATTERNS + FAKE_JOB_TITLE_MULTILANG
    for pattern in all_title_patterns:
        if re.match(pattern, title_lower, re.IGNORECASE):
            log.debug(f"Titolo non-annuncio [{job.title!r}]: {job.url}")
            return False

    score = 0

    # Segnali positivi
    for kw in JOB_POSITIVE_KEYWORDS:
        if kw in text_lower:
            score += 1

    # Segnali negativi (peso doppio)
    for kw in JOB_NEGATIVE_KEYWORDS:
        if kw in text_lower:
            score -= 2

    # Bonus: URL contiene pattern tipici degli annunci
    url_lower = job.url.lower()
    if any(p in url_lower for p in ["/job", "/career", "/position", "/opening", "/role", "/offerta", "/posizione"]):
        score += 2

    # Bonus: ha dati strutturati (salary, job_type)
    if job.salary_min or job.salary_max:
        score += 2
    if job.job_type:
        score += 1

    result = score >= 2
    if not result:
        log.debug(f"Score insufficiente ({score}): [{job.title!r}] {job.url}")
    return result


# ── Entrypoint pubblico ───────────────────────────────────────────────────────

def should_skip(job: JobPosting) -> tuple[bool, str]:
    if not job.is_valid():
        return True, "campi minimi mancanti"

    if is_expired(job):
        return True, "annuncio scaduto"

    if is_agency(job):
        return True, "agenzia rilevata"

    if is_too_short(job):
        return True, "descrizione troppo breve"

    if not looks_like_job(job):
        return True, "non sembra un annuncio di lavoro"

    return False, ""


# Aggiunte al pattern FAKE_JOB_TITLE_PATTERNS (multilingua)
FAKE_JOB_TITLE_MULTILANG = [
    r"^trabajar\s+(en|con)",       # spagnolo
    r"^arbeiten\s+(bei|mit)",      # tedesco
    r"^at\s+arbejde\s+hos",        # danese
    r"^travailler\s+(chez|avec)",  # francese
    r"^werken\s+(bij|met)",        # olandese
    r"^lavora(re)?\s+(con|in|da)", # italiano generico
    r"^join\s+us",
    r"^work\s+with\s+us",
    r"^work\s+at\s+\w+$",
    r"^careers?\s+at\s+\w+$",
    r"^jobs?\s+at\s+\w+$",
]
