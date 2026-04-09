-- Diretto - Schema iniziale
-- GNU AGPL-3.0

CREATE TABLE IF NOT EXISTS companies (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    domain          TEXT NOT NULL UNIQUE,
    careers_url     TEXT NOT NULL,
    crawl_type      TEXT DEFAULT 'static',
    locale          TEXT DEFAULT 'en',
    country         CHAR(2),
    last_crawled_at TIMESTAMPTZ,
    active          BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS job_postings (
    id            SERIAL PRIMARY KEY,
    company_id    INTEGER REFERENCES companies(id) ON DELETE CASCADE,
    title         TEXT NOT NULL,
    location      TEXT,
    remote        BOOLEAN DEFAULT false,
    job_type      TEXT,
    description   TEXT,
    salary_min    INTEGER,
    salary_max    INTEGER,
    currency      CHAR(3),
    url           TEXT NOT NULL UNIQUE,
    source_domain TEXT NOT NULL,
    html_hash     TEXT,
    posted_at     TIMESTAMPTZ,
    expires_at    TIMESTAMPTZ,
    indexed_at    TIMESTAMPTZ DEFAULT NOW(),
    active        BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS job_tags (
    job_id INTEGER REFERENCES job_postings(id) ON DELETE CASCADE,
    tag    TEXT NOT NULL,
    PRIMARY KEY (job_id, tag)
);

-- Full-text search italiano + inglese
CREATE INDEX IF NOT EXISTS idx_jobs_fts_it ON job_postings
    USING gin(to_tsvector('italian', coalesce(title,'') || ' ' || coalesce(description,'')));

CREATE INDEX IF NOT EXISTS idx_jobs_fts_en ON job_postings
    USING gin(to_tsvector('english', coalesce(title,'') || ' ' || coalesce(description,'')));

CREATE INDEX IF NOT EXISTS idx_jobs_remote  ON job_postings (remote) WHERE remote = true;
CREATE INDEX IF NOT EXISTS idx_jobs_active  ON job_postings (active, indexed_at DESC);
CREATE INDEX IF NOT EXISTS idx_jobs_company ON job_postings (company_id);
