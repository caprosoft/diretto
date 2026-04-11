"""
Logica full-text search su PostgreSQL.
Usa tsvector con dizionario italiano + inglese in cascata.
GNU AGPL-3.0
"""

PER_PAGE_MAX = 50
PER_PAGE_DEFAULT = 20


def build_search_query(
    q: str | None = None,
    location: str | None = None,
    remote: bool | None = None,
    job_type: str | None = None,
    tag: str | None = None,
    page: int = 1,
    per_page: int = PER_PAGE_DEFAULT,
) -> tuple[str, list, str, list]:
    """
    Costruisce due query SQL: una per il totale, una per i risultati paginati.
    Ritorna (count_sql, count_args, results_sql, results_args).
    """
    per_page = min(per_page, PER_PAGE_MAX)
    offset = (page - 1) * per_page

    # Base JOIN per recuperare nome azienda e tag
    base = """
        FROM job_postings j
        JOIN companies c ON j.company_id = c.id
        LEFT JOIN (
            SELECT job_id, array_agg(tag ORDER BY tag) AS tags
            FROM job_tags
            GROUP BY job_id
        ) t ON j.id = t.job_id
        WHERE j.active = true
    """

    conditions = []
    args: list = []
    idx = 1  # indice parametro PostgreSQL ($1, $2, ...)

    # Full-text search: prova italiano, poi inglese
    if q and q.strip():
        conditions.append(f"""
            (
                to_tsvector('italian', j.title || ' ' || coalesce(j.description, ''))
                @@ plainto_tsquery('italian', ${idx})
                OR
                to_tsvector('english', j.title || ' ' || coalesce(j.description, ''))
                @@ plainto_tsquery('english', ${idx})
            )
        """)
        args.append(q.strip())
        idx += 1

    if location:
        conditions.append(f"j.location ILIKE ${idx}")
        args.append(f"%{location}%")
        idx += 1

    if remote is not None:
        conditions.append(f"j.remote = ${idx}")
        args.append(remote)
        idx += 1

    if job_type:
        conditions.append(f"j.job_type = ${idx}")
        args.append(job_type.lower())
        idx += 1

    if tag:
        conditions.append(f"""
            EXISTS (
                SELECT 1 FROM job_tags jt
                WHERE jt.job_id = j.id AND jt.tag ILIKE ${idx}
            )
        """)
        args.append(tag)
        idx += 1

    where_clause = ""
    if conditions:
        where_clause = " AND " + " AND ".join(conditions)

    count_sql = f"SELECT COUNT(*) {base} {where_clause}"

    results_sql = f"""
        SELECT
            j.id,
            j.title,
            c.name      AS company,
            c.domain    AS company_domain,
            j.location,
            j.remote,
            j.job_type,
            j.salary_min,
            j.salary_max,
            j.currency,
            coalesce(t.tags, ARRAY[]::text[]) AS tags,
            j.url,
            j.posted_at,
            j.indexed_at
        {base} {where_clause}
        ORDER BY j.indexed_at DESC
        LIMIT ${idx} OFFSET ${idx + 1}
    """
    results_args = args + [per_page, offset]

    return count_sql, args, results_sql, results_args
