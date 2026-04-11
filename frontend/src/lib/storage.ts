/**
 * Storage locale per preferiti e candidature.
 * Tutto rimane nel browser — nessun dato inviato al server.
 * GNU AGPL-3.0
 */

import { Job } from "./api";

const FAVORITES_KEY = "diretto:favorites";
const APPLICATIONS_KEY = "diretto:applications";

export type ApplicationStatus =
  | "inviata"
  | "vista"
  | "colloquio"
  | "rifiutata";

export interface Application {
  job: Job;
  appliedAt: string;   // ISO date string
  status: ApplicationStatus;
  notes: string;
}

// ── Preferiti ─────────────────────────────────────────────────────────────────

export function getFavorites(): Job[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(FAVORITES_KEY) ?? "[]");
  } catch {
    return [];
  }
}

export function isFavorite(jobId: number): boolean {
  return getFavorites().some((j) => j.id === jobId);
}

export function toggleFavorite(job: Job): boolean {
  const favs = getFavorites();
  const idx = favs.findIndex((j) => j.id === job.id);
  if (idx >= 0) {
    favs.splice(idx, 1);
    localStorage.setItem(FAVORITES_KEY, JSON.stringify(favs));
    return false; // rimosso
  } else {
    favs.unshift(job);
    localStorage.setItem(FAVORITES_KEY, JSON.stringify(favs));
    return true; // aggiunto
  }
}

// ── Candidature ───────────────────────────────────────────────────────────────

export function getApplications(): Application[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(localStorage.getItem(APPLICATIONS_KEY) ?? "[]");
  } catch {
    return [];
  }
}

export function hasApplied(jobId: number): boolean {
  return getApplications().some((a) => a.job.id === jobId);
}

export function addApplication(job: Job): void {
  if (hasApplied(job.id)) return;
  const apps = getApplications();
  apps.unshift({
    job,
    appliedAt: new Date().toISOString(),
    status: "inviata",
    notes: "",
  });
  localStorage.setItem(APPLICATIONS_KEY, JSON.stringify(apps));
}

export function updateApplicationStatus(
  jobId: number,
  status: ApplicationStatus
): void {
  const apps = getApplications();
  const app = apps.find((a) => a.job.id === jobId);
  if (app) {
    app.status = status;
    localStorage.setItem(APPLICATIONS_KEY, JSON.stringify(apps));
  }
}

export function updateApplicationNotes(jobId: number, notes: string): void {
  const apps = getApplications();
  const app = apps.find((a) => a.job.id === jobId);
  if (app) {
    app.notes = notes;
    localStorage.setItem(APPLICATIONS_KEY, JSON.stringify(apps));
  }
}

export function deleteApplication(jobId: number): void {
  const apps = getApplications().filter((a) => a.job.id !== jobId);
  localStorage.setItem(APPLICATIONS_KEY, JSON.stringify(apps));
}
