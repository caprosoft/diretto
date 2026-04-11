/**
 * Client API Diretto — wrapper tipizzato per le chiamate al backend.
 * GNU AGPL-3.0
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface Job {
  id: number;
  title: string;
  company: string;
  company_domain: string;
  location: string | null;
  remote: boolean;
  job_type: string | null;
  salary_min: number | null;
  salary_max: number | null;
  currency: string | null;
  tags: string[];
  url: string;
  posted_at: string | null;
  indexed_at: string;
  description?: string;
}

export interface JobsResponse {
  total: number;
  page: number;
  per_page: number;
  jobs: Job[];
}

export interface Company {
  id: number;
  name: string;
  domain: string;
  careers_url: string;
  last_crawled_at: string | null;
}

export interface SearchParams {
  q?: string;
  location?: string;
  remote?: boolean;
  job_type?: string;
  tag?: string;
  page?: number;
  per_page?: number;
}

function buildQuery(params: SearchParams): string {
  const q = new URLSearchParams();
  if (params.q)        q.set("q", params.q);
  if (params.location) q.set("location", params.location);
  if (params.remote !== undefined) q.set("remote", String(params.remote));
  if (params.job_type) q.set("job_type", params.job_type);
  if (params.tag)      q.set("tag", params.tag);
  if (params.page)     q.set("page", String(params.page));
  if (params.per_page) q.set("per_page", String(params.per_page));
  return q.toString();
}

export async function searchJobs(params: SearchParams): Promise<JobsResponse> {
  const qs = buildQuery(params);
  const res = await fetch(`${API_URL}/api/jobs?${qs}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function getJob(id: number): Promise<Job> {
  const res = await fetch(`${API_URL}/api/jobs/${id}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function getCompanies(): Promise<Company[]> {
  const res = await fetch(`${API_URL}/api/companies`, {
    next: { revalidate: 3600 }, // cache 1h lato server
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  const data = await res.json();
  return data.companies;
}
