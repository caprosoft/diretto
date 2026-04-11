"use client";

import { useState, useEffect, useCallback } from "react";
import { searchJobs, Job, JobsResponse } from "@/lib/api";
import {
  isFavorite, toggleFavorite,
  hasApplied, addApplication,
  getApplications, updateApplicationStatus, deleteApplication,
  getFavorites, Application, ApplicationStatus,
} from "@/lib/storage";

// ── Icone SVG inline ──────────────────────────────────────────────────────────

const SearchIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
  </svg>
);
const HeartIcon = ({ filled }: { filled: boolean }) => (
  <svg width="16" height="16" viewBox="0 0 24 24"
    fill={filled ? "currentColor" : "none"}
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
  </svg>
);
const ShieldIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
  </svg>
);
const ArrowIcon = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
  </svg>
);
const XIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
);
const CheckIcon = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12"/>
  </svg>
);
const TrashIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6"/>
    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>
  </svg>
);
const GlobeIcon = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <line x1="2" y1="12" x2="22" y2="12"/>
    <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
  </svg>
);

// ── Helpers ───────────────────────────────────────────────────────────────────

const CATEGORIES = ["Tutti", "Remote", "Frontend", "Backend", "DevOps", "Privacy", "Open Source"];
const STATUS_OPTS: ApplicationStatus[] = ["inviata", "vista", "colloquio", "rifiutata"];
const STATUS_COLORS: Record<ApplicationStatus, string> = {
  inviata:   "background:#EBF5FB;color:#2471A3;border:1px solid #AED6F1",
  vista:     "background:#FEF9E7;color:#9A7D0A;border:1px solid #F9E79F",
  colloquio: "background:#EAFAF1;color:#1D8348;border:1px solid #A9DFBF",
  rifiutata: "background:#FDEDEC;color:#922B21;border:1px solid #F5B7B1",
};

function formatSalary(min: number | null, max: number | null, currency: string | null) {
  if (!min && !max) return null;
  const c = currency ?? "€";
  const fmt = (n: number) =>
    new Intl.NumberFormat("it-IT", { notation: "compact" }).format(n);
  if (min && max) return `${fmt(min)}–${fmt(max)} ${c}`;
  if (min) return `da ${fmt(min)} ${c}`;
  return `fino a ${fmt(max!)} ${c}`;
}

function timeAgo(iso: string | null) {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  const days = Math.floor(diff / 86400000);
  if (days === 0) return "oggi";
  if (days === 1) return "ieri";
  if (days < 7) return `${days} giorni fa`;
  if (days < 30) return `${Math.floor(days / 7)} settimane fa`;
  return `${Math.floor(days / 30)} mesi fa`;
}

// ── Componenti ────────────────────────────────────────────────────────────────

function JobCard({
  job, onSelect, favs, applied, onToggleFav,
}: {
  job: Job;
  onSelect: (j: Job) => void;
  favs: Set<number>;
  applied: Set<number>;
  onToggleFav: (j: Job, e: React.MouseEvent) => void;
}) {
  const salary = formatSalary(job.salary_min, job.salary_max, job.currency);
  const isFav = favs.has(job.id);
  const isApplied = applied.has(job.id);

  return (
    <div onClick={() => onSelect(job)} style={{
      background: "var(--surface)", border: "1.5px solid var(--border)",
      borderRadius: 12, padding: "18px 20px", marginBottom: 10,
      cursor: "pointer", display: "grid",
      gridTemplateColumns: "1fr auto", gap: 12,
      transition: "border-color .15s, box-shadow .15s, transform .15s",
    }}
      onMouseEnter={e => {
        (e.currentTarget as HTMLDivElement).style.borderColor = "var(--accent-mid)";
        (e.currentTarget as HTMLDivElement).style.transform = "translateY(-1px)";
        (e.currentTarget as HTMLDivElement).style.boxShadow = "0 4px 16px rgba(45,106,79,.08)";
      }}
      onMouseLeave={e => {
        (e.currentTarget as HTMLDivElement).style.borderColor = "var(--border)";
        (e.currentTarget as HTMLDivElement).style.transform = "";
        (e.currentTarget as HTMLDivElement).style.boxShadow = "";
      }}
    >
      <div>
        <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 2 }}>{job.title}</div>
        <div style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--accent)", marginBottom: 8 }}>
          {job.company}
        </div>
        <div style={{ display: "flex", gap: 14, flexWrap: "wrap", fontSize: 12, color: "var(--muted)" }}>
          {job.location && <span>📍 {job.location}</span>}
          {job.remote && <span>🌐 Remote</span>}
          {job.job_type && <span>💼 {job.job_type}</span>}
          <span>🕐 {timeAgo(job.indexed_at)}</span>
        </div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 10 }}>
          {job.tags.slice(0, 4).map(t => (
            <span key={t} style={{
              background: "var(--bg)", border: "1px solid var(--border)",
              borderRadius: 4, padding: "2px 8px",
              fontSize: 11, fontFamily: "var(--mono)", color: "var(--muted)",
            }}>{t}</span>
          ))}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 5, marginTop: 8,
          fontSize: 11, fontFamily: "var(--mono)", color: "var(--accent-mid)" }}>
          <GlobeIcon /> {job.company_domain}
        </div>
        {isApplied && (
          <div style={{
            display: "inline-flex", alignItems: "center", gap: 5,
            background: "#EBF5FB", color: "#2471A3",
            border: "1.5px solid #AED6F1", borderRadius: 20,
            padding: "2px 10px", fontSize: 11,
            fontFamily: "var(--mono)", fontWeight: 700, marginTop: 8,
          }}>
            <CheckIcon /> Candidatura inviata
          </div>
        )}
      </div>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 8 }}>
        {salary && (
          <span style={{ fontFamily: "var(--mono)", fontSize: 12, fontWeight: 700 }}>{salary}</span>
        )}
        <button
          onClick={e => onToggleFav(job, e)}
          style={{
            border: "none", background: "transparent", padding: 4, borderRadius: 6,
            color: isFav ? "#e74c3c" : "var(--border)",
            cursor: "pointer", transition: "transform .1s",
          }}
        >
          <HeartIcon filled={isFav} />
        </button>
      </div>
    </div>
  );
}

function JobModal({
  job, onClose, favs, applied,
  onToggleFav, onApply,
}: {
  job: Job; onClose: () => void;
  favs: Set<number>; applied: Set<number>;
  onToggleFav: (j: Job, e: React.MouseEvent) => void;
  onApply: (j: Job) => void;
}) {
  const salary = formatSalary(job.salary_min, job.salary_max, job.currency);
  const isFav = favs.has(job.id);
  const isApplied = applied.has(job.id);

  return (
    <div onClick={onClose} style={{
      position: "fixed", inset: 0,
      background: "rgba(0,0,0,.3)", zIndex: 200,
      display: "flex", alignItems: "center", justifyContent: "center",
      padding: 24, animation: "fadeIn .15s ease",
    }}>
      <style>{`@keyframes fadeIn{from{opacity:0}} @keyframes slideUp{from{transform:translateY(20px);opacity:0}}`}</style>
      <div onClick={e => e.stopPropagation()} style={{
        background: "var(--surface)", borderRadius: 16,
        maxWidth: 560, width: "100%", maxHeight: "80vh",
        overflowY: "auto", border: "2px solid var(--border)",
        animation: "slideUp .2s ease",
      }}>
        {/* Header */}
        <div style={{
          padding: "24px 24px 18px",
          borderBottom: "1.5px solid var(--border)",
          display: "flex", gap: 14, alignItems: "flex-start",
        }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 20, fontWeight: 600, marginBottom: 3 }}>{job.title}</div>
            <div style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--accent)", marginBottom: 10 }}>
              {job.company}
            </div>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {job.tags.map(t => (
                <span key={t} style={{
                  background: "var(--bg)", border: "1px solid var(--border)",
                  borderRadius: 4, padding: "2px 8px",
                  fontSize: 11, fontFamily: "var(--mono)", color: "var(--muted)",
                }}>{t}</span>
              ))}
            </div>
            {isApplied && (
              <div style={{
                display: "inline-flex", alignItems: "center", gap: 5,
                background: "#EBF5FB", color: "#2471A3",
                border: "1.5px solid #AED6F1", borderRadius: 20,
                padding: "3px 10px", fontSize: 11,
                fontFamily: "var(--mono)", fontWeight: 700, marginTop: 8,
              }}>
                <CheckIcon /> Candidatura registrata
              </div>
            )}
          </div>
          <button onClick={onClose} style={{
            background: "var(--bg)", border: "1.5px solid var(--border)",
            borderRadius: 8, width: 34, height: 34,
            display: "flex", alignItems: "center", justifyContent: "center",
            cursor: "pointer", color: "var(--muted)", flexShrink: 0,
          }}><XIcon /></button>
        </div>

        {/* Body */}
        <div style={{ padding: "22px 24px" }}>
          {/* Meta grid */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 20 }}>
            {[
              ["Sede", job.location ?? (job.remote ? "Remote" : "—")],
              ["Tipo", job.job_type ?? "—"],
              ["Stipendio", salary ?? "—"],
              ["Fonte", job.company_domain],
            ].map(([label, value]) => (
              <div key={label} style={{
                background: "var(--bg)", borderRadius: 8, padding: "10px 12px",
              }}>
                <div style={{ fontSize: 10, fontFamily: "var(--mono)", color: "var(--muted)",
                  textTransform: "uppercase", letterSpacing: "1px", marginBottom: 3 }}>
                  {label}
                </div>
                <div style={{ fontSize: 13, fontWeight: 500, color:
                  label === "Fonte" ? "var(--accent)" : "var(--text)",
                  fontFamily: label === "Fonte" ? "var(--mono)" : "inherit",
                }}>{value}</div>
              </div>
            ))}
          </div>

          {/* Descrizione */}
          {job.description && (
            <p style={{ fontSize: 14, color: "#444", lineHeight: 1.75,
              fontWeight: 300, marginBottom: 22 }}>
              {job.description.slice(0, 600)}{job.description.length > 600 ? "…" : ""}
            </p>
          )}

          {/* Azioni */}
          <div style={{ display: "flex", gap: 10 }}>
            <button
              onClick={() => { if (!isApplied) onApply(job); }}
              style={{
                flex: 1, background: isApplied ? "#2c3e50" : "var(--accent)",
                color: "white", border: "none", borderRadius: 8,
                padding: "12px 20px", fontFamily: "var(--mono)",
                fontSize: 13, fontWeight: 700, cursor: isApplied ? "default" : "pointer",
                display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
              }}
            >
              {isApplied ? <><CheckIcon /> Candidatura registrata</> : "Vai all'annuncio →"}
            </button>
            <button
              onClick={e => onToggleFav(job, e)}
              style={{
                background: "var(--bg)", border: "1.5px solid var(--border)",
                borderRadius: 8, padding: "12px 14px",
                display: "flex", alignItems: "center", gap: 6,
                fontSize: 13, fontFamily: "var(--mono)", cursor: "pointer",
                color: isFav ? "#e74c3c" : "var(--text)",
              }}
            >
              <HeartIcon filled={isFav} /> {isFav ? "Salvato" : "Salva"}
            </button>
          </div>

          <p style={{ fontSize: 11, color: "var(--muted)", marginTop: 12,
            fontFamily: "var(--mono)", lineHeight: 1.6 }}>
            ⚡ Diretto registra la candidatura localmente e ti reindirizza al sito ufficiale.
            Nessun dato personale viene trasmesso a Diretto.
          </p>
        </div>
      </div>
    </div>
  );
}

// ── Pagina principale ─────────────────────────────────────────────────────────

type Tab = "search" | "favorites" | "applications" | "about";

export default function Home() {
  const [tab, setTab] = useState<Tab>("search");
  const [query, setQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState("Tutti");
  const [searched, setSearched] = useState(false);
  const [results, setResults] = useState<JobsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<Job | null>(null);
  const [favs, setFavs] = useState<Set<number>>(new Set());
  const [applied, setApplied] = useState<Set<number>>(new Set());
  const [applications, setApplications] = useState<Application[]>([]);
  const [favJobs, setFavJobs] = useState<Job[]>([]);

  // Carica stato da localStorage al mount
  useEffect(() => {
    setFavs(new Set(getFavorites().map(j => j.id)));
    setApplied(new Set(getApplications().map(a => a.job.id)));
    setApplications(getApplications());
    setFavJobs(getFavorites());
  }, []);

  const doSearch = useCallback(async (q: string, filter: string) => {
    setLoading(true);
    setSearched(true);
    try {
      const params: Record<string, string | boolean> = {};
      if (q) params.q = q;
      if (filter === "Remote") params.remote = true;
      else if (filter !== "Tutti") params.tag = filter.toLowerCase().replace(" ", "-");
      const data = await searchJobs(params);
      setResults(data);
    } catch {
      setResults({ total: 0, page: 1, per_page: 20, jobs: [] });
    } finally {
      setLoading(false);
    }
  }, []);

  const handleSearch = () => doSearch(query, activeFilter);

  const handleFilter = (f: string) => {
    setActiveFilter(f);
    doSearch(query, f);
  };

  const handleToggleFav = (job: Job, e: React.MouseEvent) => {
    e.stopPropagation();
    toggleFavorite(job);
    setFavs(new Set(getFavorites().map(j => j.id)));
    setFavJobs(getFavorites());
  };

  const handleApply = (job: Job) => {
    addApplication(job);
    setApplied(new Set(getApplications().map(a => a.job.id)));
    setApplications(getApplications());
    window.open(job.url, "_blank", "noopener,noreferrer");
  };

  const handleUpdateStatus = (jobId: number, status: ApplicationStatus) => {
    updateApplicationStatus(jobId, status);
    setApplications(getApplications());
  };

  const handleDeleteApp = (jobId: number) => {
    deleteApplication(jobId);
    setApplied(new Set(getApplications().map(a => a.job.id)));
    setApplications(getApplications());
  };

  const appCount = applications.length;
  const favCount = favJobs.length;

  return (
    <>
      {/* NAV */}
      <nav style={{
        background: "var(--surface)", borderBottom: "1.5px solid var(--border)",
        padding: "0 24px", display: "flex", alignItems: "center",
        gap: 24, height: 56, position: "sticky", top: 0, zIndex: 100,
      }}>
        <div
          onClick={() => { setTab("search"); setSearched(false); }}
          style={{ fontFamily: "var(--mono)", fontWeight: 700, fontSize: 17,
            letterSpacing: "-0.5px", cursor: "pointer", display: "flex",
            alignItems: "center", gap: 7 }}
        >
          <span style={{ width: 8, height: 8, background: "var(--accent)",
            borderRadius: "50%", display: "inline-block" }} />
          diretto
        </div>

        <div style={{ display: "flex", gap: 4, flex: 1 }}>
          {([
            { id: "search", label: "Ricerca", badge: null },
            { id: "favorites", label: "Preferiti", badge: favCount || null },
            { id: "applications", label: "Candidature", badge: appCount || null },
            { id: "about", label: "Info", badge: null },
          ] as const).map(t => (
            <button key={t.id} onClick={() => setTab(t.id)} style={{
              padding: "6px 13px", borderRadius: 6, fontSize: 13,
              fontWeight: 500, border: "none", cursor: "pointer",
              display: "flex", alignItems: "center", gap: 6,
              background: tab === t.id ? "var(--accent-light)" : "transparent",
              color: tab === t.id ? "var(--accent)" : "var(--muted)",
            }}>
              {t.label}
              {t.badge ? (
                <span style={{
                  background: "var(--accent)", color: "white",
                  fontSize: 10, fontFamily: "var(--mono)",
                  padding: "1px 5px", borderRadius: 10, fontWeight: 700,
                }}>{t.badge}</span>
              ) : null}
            </button>
          ))}
        </div>

        <div style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--accent)",
          display: "flex", alignItems: "center", gap: 5, opacity: 0.8 }}>
          <ShieldIcon /> zero tracking
        </div>
      </nav>

      {/* ── TAB: SEARCH ── */}
      {tab === "search" && !searched && (
        <div style={{ maxWidth: 700, margin: "0 auto", padding: "72px 24px 48px", textAlign: "center" }}>
          <div style={{ fontFamily: "var(--mono)", fontSize: 11, letterSpacing: 2,
            textTransform: "uppercase", color: "var(--accent)", marginBottom: 20,
            display: "flex", alignItems: "center", justifyContent: "center", gap: 10 }}>
            <span style={{ display: "block", height: 1, width: 40,
              background: "var(--accent)", opacity: 0.4 }} />
            Solo aziende dirette · Zero agenzie
            <span style={{ display: "block", height: 1, width: 40,
              background: "var(--accent)", opacity: 0.4 }} />
          </div>
          <h1 style={{ fontFamily: "var(--mono)", fontSize: "clamp(28px,5vw,42px)",
            fontWeight: 700, letterSpacing: "-1px", lineHeight: 1.15, marginBottom: 14 }}>
            Trova lavoro<br />
            <em style={{ fontStyle: "italic", color: "var(--accent)", fontWeight: 400 }}>
              senza intermediari.
            </em>
          </h1>
          <p style={{ fontSize: 16, color: "var(--muted)", fontWeight: 300,
            marginBottom: 36, maxWidth: 480, marginLeft: "auto", marginRight: "auto" }}>
            Annunci diretti da aziende reali. Nessun account, nessun tracciamento, nessuna agenzia.
          </p>

          {/* Search bar */}
          <div style={{
            display: "flex", gap: 8, maxWidth: 620, margin: "0 auto 20px",
            background: "var(--surface)", border: "2px solid var(--border)",
            borderRadius: 12, padding: "6px 6px 6px 16px", alignItems: "center",
          }}>
            <SearchIcon />
            <input
              placeholder="es. React developer, backend Rust, remote…"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleSearch()}
              autoFocus
              style={{ flex: 1, border: "none", outline: "none",
                background: "transparent", fontSize: 15, color: "var(--text)" }}
            />
            <button onClick={handleSearch} style={{
              background: "var(--accent)", color: "white", border: "none",
              borderRadius: 8, padding: "10px 20px", fontFamily: "var(--mono)",
              fontSize: 13, fontWeight: 700, display: "flex",
              alignItems: "center", gap: 8, cursor: "pointer",
            }}>
              Cerca <ArrowIcon />
            </button>
          </div>

          {/* Filtri */}
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "center" }}>
            {CATEGORIES.map(c => (
              <button key={c} onClick={() => handleFilter(c)} style={{
                padding: "5px 14px", borderRadius: 20, fontSize: 12,
                fontWeight: 500, fontFamily: "var(--mono)", cursor: "pointer",
                border: `1.5px solid ${activeFilter === c ? "var(--accent)" : "var(--border)"}`,
                background: activeFilter === c ? "var(--accent-light)" : "var(--surface)",
                color: activeFilter === c ? "var(--accent)" : "var(--muted)",
              }}>{c}</button>
            ))}
          </div>

          {/* Privacy strip */}
          <div style={{
            background: "var(--accent-light)", border: "1.5px solid var(--accent-mid)",
            borderRadius: 10, padding: "10px 18px", display: "flex",
            alignItems: "center", gap: 10, fontSize: 12,
            color: "var(--accent)", maxWidth: 620, margin: "18px auto 0",
            fontFamily: "var(--mono)",
          }}>
            <ShieldIcon />
            <span style={{ color: "#2D4A3E" }}>
              Nessun cookie · Nessuna profilazione · Dati salvati solo sul tuo dispositivo · AGPL-3.0
            </span>
          </div>
        </div>
      )}

      {/* ── RISULTATI ── */}
      {tab === "search" && searched && (
        <div style={{ maxWidth: 860, margin: "0 auto", padding: "0 24px 48px" }}>
          {/* Search bar compatta */}
          <div style={{ display: "flex", gap: 8, padding: "20px 0 14px", alignItems: "center" }}>
            <div style={{
              display: "flex", flex: 1, gap: 8,
              background: "var(--surface)", border: "2px solid var(--border)",
              borderRadius: 12, padding: "6px 6px 6px 14px", alignItems: "center",
            }}>
              <SearchIcon />
              <input
                placeholder="Cerca annunci…"
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleSearch()}
                style={{ flex: 1, border: "none", outline: "none",
                  background: "transparent", fontSize: 14 }}
              />
            </div>
            <button onClick={handleSearch} style={{
              background: "var(--accent)", color: "white", border: "none",
              borderRadius: 8, padding: "10px 18px", fontFamily: "var(--mono)",
              fontSize: 13, fontWeight: 700, cursor: "pointer",
            }}>Cerca</button>
          </div>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 14 }}>
            {CATEGORIES.map(c => (
              <button key={c} onClick={() => handleFilter(c)} style={{
                padding: "4px 13px", borderRadius: 20, fontSize: 11,
                fontFamily: "var(--mono)", cursor: "pointer",
                border: `1.5px solid ${activeFilter === c ? "var(--accent)" : "var(--border)"}`,
                background: activeFilter === c ? "var(--accent-light)" : "var(--surface)",
                color: activeFilter === c ? "var(--accent)" : "var(--muted)",
              }}>{c}</button>
            ))}
          </div>

          <div style={{
            display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "12px 0", borderBottom: "1.5px solid var(--border)", marginBottom: 14,
          }}>
            <span style={{ fontFamily: "var(--mono)", fontSize: 12, color: "var(--muted)" }}>
              {loading ? "Ricerca in corso…" : (
                <><strong style={{ color: "var(--text)" }}>{results?.total ?? 0}</strong> annunci · solo aziende dirette</>
              )}
            </span>
          </div>

          {loading ? (
            <div style={{ textAlign: "center", padding: 48, fontFamily: "var(--mono)",
              fontSize: 13, color: "var(--muted)" }}>Caricamento…</div>
          ) : results?.jobs.length === 0 ? (
            <div style={{ textAlign: "center", padding: 64 }}>
              <div style={{ fontSize: 36, marginBottom: 14 }}>🔍</div>
              <div style={{ fontFamily: "var(--mono)", fontSize: 15, fontWeight: 700, marginBottom: 8 }}>
                Nessun annuncio trovato
              </div>
              <div style={{ fontSize: 13, color: "var(--muted)", fontWeight: 300 }}>
                Prova con altri termini o cambia filtro.
              </div>
            </div>
          ) : results?.jobs.map(job => (
            <JobCard key={job.id} job={job} onSelect={setSelected}
              favs={favs} applied={applied} onToggleFav={handleToggleFav} />
          ))}
        </div>
      )}

      {/* ── TAB: PREFERITI ── */}
      {tab === "favorites" && (
        <div style={{ maxWidth: 860, margin: "0 auto", padding: "32px 24px 48px" }}>
          <div style={{ fontFamily: "var(--mono)", fontSize: 22, fontWeight: 700,
            letterSpacing: "-0.5px", marginBottom: 6 }}>Preferiti</div>
          <div style={{ fontSize: 14, color: "var(--muted)", fontWeight: 300, marginBottom: 28 }}>
            Annunci salvati — archiviati localmente, nessun dato inviato.
          </div>
          {favJobs.length === 0 ? (
            <div style={{ textAlign: "center", padding: 64 }}>
              <div style={{ fontSize: 36, marginBottom: 14 }}>❤️</div>
              <div style={{ fontFamily: "var(--mono)", fontSize: 15, fontWeight: 700, marginBottom: 8 }}>
                Nessun preferito ancora
              </div>
              <div style={{ fontSize: 13, color: "var(--muted)", fontWeight: 300 }}>
                Cerca annunci e clicca ❤️ per salvarli qui.
              </div>
            </div>
          ) : favJobs.map(job => (
            <JobCard key={job.id} job={job} onSelect={setSelected}
              favs={favs} applied={applied} onToggleFav={handleToggleFav} />
          ))}
        </div>
      )}

      {/* ── TAB: CANDIDATURE ── */}
      {tab === "applications" && (
        <div style={{ maxWidth: 860, margin: "0 auto", padding: "32px 24px 48px" }}>
          <div style={{ fontFamily: "var(--mono)", fontSize: 22, fontWeight: 700,
            letterSpacing: "-0.5px", marginBottom: 6 }}>Candidature</div>
          <div style={{ fontSize: 14, color: "var(--muted)", fontWeight: 300, marginBottom: 28 }}>
            Storico locale — nessun account richiesto.
          </div>
          {applications.length === 0 ? (
            <div style={{ textAlign: "center", padding: 64 }}>
              <div style={{ fontSize: 36, marginBottom: 14 }}>📋</div>
              <div style={{ fontFamily: "var(--mono)", fontSize: 15, fontWeight: 700, marginBottom: 8 }}>
                Nessuna candidatura ancora
              </div>
              <div style={{ fontSize: 13, color: "var(--muted)", fontWeight: 300 }}>
                Quando clicchi "Vai all'annuncio" su un posting, appare qui.
              </div>
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    {["Posizione", "Azienda", "Data", "Stato", ""].map(h => (
                      <th key={h} style={{
                        textAlign: "left", fontFamily: "var(--mono)",
                        fontSize: 10, letterSpacing: "1.5px",
                        textTransform: "uppercase", color: "var(--muted)",
                        padding: "8px 12px", borderBottom: "2px solid var(--border)",
                        fontWeight: 400,
                      }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {applications.map(app => (
                    <tr key={app.job.id}
                      onMouseEnter={e => (e.currentTarget.style.background = "var(--bg)")}
                      onMouseLeave={e => (e.currentTarget.style.background = "")}
                    >
                      <td style={{ padding: "13px 12px", fontSize: 13.5, fontWeight: 500,
                        borderBottom: "1px solid var(--border)" }}>
                        {app.job.title}
                      </td>
                      <td style={{ padding: "13px 12px", borderBottom: "1px solid var(--border)",
                        fontFamily: "var(--mono)", fontSize: 12, color: "var(--accent)" }}>
                        {app.job.company}
                      </td>
                      <td style={{ padding: "13px 12px", borderBottom: "1px solid var(--border)",
                        fontFamily: "var(--mono)", fontSize: 12, color: "var(--muted)" }}>
                        {new Date(app.appliedAt).toLocaleDateString("it-IT")}
                      </td>
                      <td style={{ padding: "13px 12px", borderBottom: "1px solid var(--border)" }}>
                        <select
                          value={app.status}
                          onChange={e => handleUpdateStatus(app.job.id, e.target.value as ApplicationStatus)}
                          style={{
                            border: "none", cursor: "pointer",
                            fontFamily: "var(--mono)", fontSize: 11, fontWeight: 700,
                            borderRadius: 20, padding: "3px 10px",
                            ...(Object.fromEntries(
                              STATUS_COLORS[app.status]
                                .split(";")
                                .filter(Boolean)
                                .map(s => {
                                  const [k, v] = s.split(":");
                                  return [k.trim().replace(/-([a-z])/g, (_, c) => c.toUpperCase()), v.trim()];
                                })
                            )),
                          }}
                        >
                          {STATUS_OPTS.map(s => (
                            <option key={s} value={s}>
                              {s.charAt(0).toUpperCase() + s.slice(1)}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td style={{ padding: "13px 12px", borderBottom: "1px solid var(--border)" }}>
                        <button onClick={() => handleDeleteApp(app.job.id)} style={{
                          background: "transparent", border: "none",
                          cursor: "pointer", color: "var(--border)", padding: 4,
                          borderRadius: 4, display: "flex", transition: "color .15s",
                        }}
                          onMouseEnter={e => (e.currentTarget.style.color = "var(--danger)")}
                          onMouseLeave={e => (e.currentTarget.style.color = "var(--border)")}
                        ><TrashIcon /></button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── TAB: ABOUT ── */}
      {tab === "about" && (
        <div style={{ maxWidth: 860, margin: "0 auto", padding: "32px 24px 48px" }}>
          <div style={{ fontFamily: "var(--mono)", fontSize: 22, fontWeight: 700,
            letterSpacing: "-0.5px", marginBottom: 6 }}>Cos'è Diretto?</div>
          <div style={{ fontSize: 14, color: "var(--muted)", fontWeight: 300, marginBottom: 28 }}>
            Una piattaforma di ricerca lavoro libera, minimalista e rispettosa della privacy.
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 28 }}>
            {[
              { icon: "🏢", title: "Solo aziende dirette", text: "Zero agenzie. Ogni annuncio è scansionato direttamente dal sito dell'azienda." },
              { icon: "🔒", title: "Privacy by design", text: "Nessun cookie, nessun account. Preferiti e candidature vivono solo nel tuo browser." },
              { icon: "🔍", title: "Motore di scansione", text: "Un crawler etico (rispetta robots.txt) analizza le pagine careers aziendali." },
              { icon: "⚖️", title: "AGPL-3.0", text: "Software libero. Puoi usarlo, studiarlo, modificarlo. Il codice è sempre pubblico." },
            ].map(card => (
              <div key={card.title} style={{
                background: "var(--surface)", border: "1.5px solid var(--border)",
                borderRadius: 12, padding: 20,
              }}>
                <div style={{ fontSize: 24, marginBottom: 10 }}>{card.icon}</div>
                <div style={{ fontFamily: "var(--mono)", fontSize: 13, fontWeight: 700, marginBottom: 6 }}>
                  {card.title}
                </div>
                <div style={{ fontSize: 13, color: "var(--muted)", fontWeight: 300, lineHeight: 1.6 }}>
                  {card.text}
                </div>
              </div>
            ))}
          </div>

          <div style={{ background: "var(--surface)", border: "1.5px solid var(--border)",
            borderRadius: 12, padding: "20px 22px" }}>
            <div style={{ fontFamily: "var(--mono)", fontSize: 13, fontWeight: 700, marginBottom: 12 }}>
              Cosa NON fa Diretto
            </div>
            {[
              "Raccogliere dati personali",
              "Richiedere registrazione",
              "Pubblicare annunci di agenzie",
              "Vendere dati a recruiter",
              "Usare gamification o notifiche push",
              "Mostrare pubblicità",
            ].map(x => (
              <div key={x} style={{
                display: "flex", alignItems: "center", gap: 10,
                fontSize: 13, color: "var(--muted)", padding: "6px 0",
                borderBottom: "1px solid var(--border)", fontWeight: 300,
              }}>
                <span style={{ color: "var(--danger)" }}><XIcon /></span> {x}
              </div>
            ))}
          </div>

          <div style={{ marginTop: 24, fontSize: 12, color: "var(--muted)",
            fontFamily: "var(--mono)", lineHeight: 1.8 }}>
            <a href="https://github.com/TUO_USERNAME/diretto"
              target="_blank" rel="noopener noreferrer"
              style={{ color: "var(--accent)" }}>
              Codice sorgente su GitHub
            </a>
            {" · "}
            <a href="https://www.gnu.org/licenses/agpl-3.0.html"
              target="_blank" rel="noopener noreferrer"
              style={{ color: "var(--accent)" }}>
              GNU AGPL-3.0
            </a>
            {" · "}
            diretto.org
          </div>
        </div>
      )}

      {/* ── MODAL DETTAGLIO ── */}
      {selected && (
        <JobModal
          job={selected}
          onClose={() => setSelected(null)}
          favs={favs}
          applied={applied}
          onToggleFav={handleToggleFav}
          onApply={handleApply}
        />
      )}
    </>
  );
}
