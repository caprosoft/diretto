"""
Router /api/jobs
GNU AGPL-3.0
"""

from fastapi import APIRouter, HTTPException, Query

from ..database import get_pool
from ..models import JobDetail, JobsResponse
from ..search import PER_PAGE_DEFAULT, build_search_query

router = APIRouter()


@router.get("/jobs", response_model=JobsResponse, summary="Cerca annunci")
async def list_jobs(
    q: str | None = Query(None, description="Ricerca full-text"),
    location: str | None = Query(None, description="Filtra per città (es. Milano)"),
    remote: bool | None = Query(None, description="Solo remote"),
    job_type: str | None = Query(None, description="full-time | part-time | contract"),
    tag: str | None = Query(None, description="Filtra per tag tecnologia"),
    page: int = Query(1, ge=1, description="Numero pagina"),
    per_page: int = Query(PER_PAGE_DEFAULT, ge=1, le=50, description="Risultati per pagina"),
):
    pool = await get_pool()

    count_sql, count_args, results_sql, results_args = build_search_query(
        q=q, location=location, remote=remote,
        job_type=job_type, tag=tag, page=page, per_page=per_page,
    )

    async with pool.acquire() as conn:
        total = await conn.fetchval(count_sql, *count_args)
        rows = await conn.fetch(results_sql, *results_args)

    jobs = [dict(row) for row in rows]
    return JobsResponse(total=total, page=page, per_page=per_page, jobs=jobs)


@router.get("/jobs/{job_id}", response_model=JobDetail, summary="Dettaglio annuncio")
async def get_job(job_id: int):
    pool = await get_pool()

    sql = """
        SELECT
            j.id, j.title,
            c.name AS company, c.domain AS company_domain,
            j.location, j.remote, j.job_type,
            j.salary_min, j.salary_max, j.currency,
            j.description, j.url, j.posted_at, j.indexed_at,
            coalesce(array_agg(jt.tag) FILTER (WHERE jt.tag IS NOT NULL), ARRAY[]::text[]) AS tags
        FROM job_postings j
        JOIN companies c ON j.company_id = c.id
        LEFT JOIN job_tags jt ON jt.job_id = j.id
        WHERE j.id = $1 AND j.active = true
        GROUP BY j.id, c.id
    """

    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, job_id)

    if not row:
        raise HTTPException(status_code=404, detail="Annuncio non trovato")

    return JobDetail(**dict(row))
