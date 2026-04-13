"""
Storage — salva JobPosting su PostgreSQL, gestisce deduplicazione.
GNU AGPL-3.0
"""

import logging
import os

import asyncpg

from .parser import JobPosting

log = logging.getLogger(__name__)


async def get_connection() -> asyncpg.Connection:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL non impostata")
    return await asyncpg.connect(url)


async def ensure_company(conn: asyncpg.Connection, job: JobPosting) -> int:
    row = await conn.fetchrow(
        """
        INSERT INTO companies (name, domain, careers_url)
        VALUES ($1, $2, $3)
        ON CONFLICT (domain) DO UPDATE SET name = EXCLUDED.name
        RETURNING id
        """,
        job.company, job.source_domain, job.url,
    )
    return row["id"]


async def job_exists(conn: asyncpg.Connection, url: str, html_hash: str, title: str, company_id: int) -> bool:
    """Controlla duplicati per URL, hash HTML, oppure stesso titolo+azienda."""
    row = await conn.fetchrow(
        """
        SELECT id FROM job_postings
        WHERE url = $1
           OR html_hash = $2
           OR (lower(title) = lower($3) AND company_id = $4)
        """,
        url, html_hash, title, company_id,
    )
    return row is not None


async def save_job(conn: asyncpg.Connection, job: JobPosting) -> int | None:
    company_id = await ensure_company(conn, job)

    if await job_exists(conn, job.url, job.html_hash, job.title, company_id):
        log.debug(f"Duplicato, skip: [{job.title}] {job.url}")
        return None

    row = await conn.fetchrow(
        """
        INSERT INTO job_postings (
            company_id, title, location, remote, job_type,
            description, salary_min, salary_max, currency,
            url, source_domain, html_hash,
            posted_at, expires_at
        ) VALUES (
            $1, $2, $3, $4, $5,
            $6, $7, $8, $9,
            $10, $11, $12,
            $13, $14
        )
        ON CONFLICT (url) DO NOTHING
        RETURNING id
        """,
        company_id, job.title, job.location, job.remote, job.job_type,
        job.description, job.salary_min, job.salary_max, job.currency,
        job.url, job.source_domain, job.html_hash,
        job.posted_at, job.expires_at,
    )

    if not row:
        return None

    job_id = row["id"]

    if job.tags:
        await conn.executemany(
            "INSERT INTO job_tags (job_id, tag) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            [(job_id, tag) for tag in job.tags],
        )

    log.info(f"Salvato [{job_id}]: {job.title} @ {job.company}")
    return job_id


async def mark_company_crawled(conn: asyncpg.Connection, domain: str):
    await conn.execute(
        "UPDATE companies SET last_crawled_at = NOW() WHERE domain = $1", domain,
    )
