"""
Schema Pydantic per le risposte API.
GNU AGPL-3.0
"""

from datetime import datetime

from pydantic import BaseModel, HttpUrl


class CompanySummary(BaseModel):
    id: int
    name: str
    domain: str
    careers_url: str
    last_crawled_at: datetime | None


class JobSummary(BaseModel):
    id: int
    title: str
    company: str
    company_domain: str
    location: str | None
    remote: bool
    job_type: str | None
    salary_min: int | None
    salary_max: int | None
    currency: str | None
    tags: list[str]
    url: str
    posted_at: datetime | None
    indexed_at: datetime


class JobDetail(JobSummary):
    description: str | None


class JobsResponse(BaseModel):
    total: int
    page: int
    per_page: int
    jobs: list[JobSummary]


class CompaniesResponse(BaseModel):
    total: int
    companies: list[CompanySummary]
