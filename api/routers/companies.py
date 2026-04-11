from fastapi import APIRouter, HTTPException

from database import get_pool
from models import CompaniesResponse, JobsResponse

router = APIRouter()


@router.get("/companies", response_model=CompaniesResponse)
async def list_companies():
    pool = await get_pool()
    sql = """
        SELECT id, name, domain, careers_url, last_crawled_at
        FROM companies WHERE active = true ORDER BY name ASC
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql)
    return CompaniesResponse(total=len(rows), companies=[dict(r) for r in rows])


@router.get("/companies/{domain}/jobs", response_model=JobsResponse)
async def company_jobs(domain: str, page: int = 1, per_page: int = 20):
    pool = await get_pool()
    async with pool.acquire() as conn:
        company = await conn.fetchrow(
            "SELECT id FROM companies WHERE domain = $1 AND active = true", domain
        )
        if not company:
            raise HTTPException(status_code=404, detail="Azienda non trovata")
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM job_postings WHERE company_id = $1 AND active = true",
            company["id"],
        )
        offset = (page - 1) * per_page
        rows = await conn.fetch(
            """
            SELECT j.id, j.title,
                c.name AS company, c.domain AS company_domain,
                j.location, j.remote, j.job_type,
                j.salary_min, j.salary_max, j.currency,
                coalesce(array_agg(jt.tag) FILTER (WHERE jt.tag IS NOT NULL), ARRAY[]::text[]) AS tags,
                j.url, j.posted_at, j.indexed_at
            FROM job_postings j
            JOIN companies c ON j.company_id = c.id
            LEFT JOIN job_tags jt ON jt.job_id = j.id
            WHERE j.company_id = $1 AND j.active = true
            GROUP BY j.id, c.id
            ORDER BY j.indexed_at DESC
            LIMIT $2 OFFSET $3
            """,
            company["id"], per_page, offset,
        )
    return JobsResponse(total=total, page=page, per_page=per_page, jobs=[dict(r) for r in rows])
