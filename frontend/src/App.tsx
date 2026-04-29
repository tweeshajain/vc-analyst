import type { CSSProperties, ReactNode } from "react";
import { useCallback, useEffect, useLayoutEffect, useState } from "react";
import { apiJson, apiJsonOrNull } from "./api";

/** Sidebar order: Radar → Deals → Memos → Trends */
type Tab = "radar" | "deals" | "memo" | "trends";

type Startup = {
  id: number;
  name: string;
  sector: string;
  stage: string;
  description: string;
  created_at: string;
  url?: string;
  source?: string;
  upvotes?: number;
  comments_count?: number;
  radar_score?: number;
};

type TopStartup = {
  id: number;
  name: string;
  description: string;
  url: string;
  source: string;
  upvotes: number;
  comments_count: number;
  radar_score: number;
  score: number;
  ranking_reason: string;
  created_at: string;
  sector: string;
  stage: string;
  insight: string;
  why_it_matters: string;
  /** Formatted output: Company Name / Sector / Stage / Why it qualifies / VC relevance 1–10 */
  vc_digest: string;
};

type Memo = {
  id: number;
  startup_id: number | null;
  title: string;
  summary: string;
  status: string;
  created_at: string;
  company_overview?: string;
  market_opportunity?: string;
  business_model?: string;
  competitive_landscape?: string;
  differentiation_analysis?: string;
  competitive_strengths?: string;
  competition?: string;
  risks?: string;
  investment_thesis?: string;
};

type TopDeal = {
  startup_id: number;
  name: string;
  score: number;
  stage: string;
  rationale: string;
  why_it_matters: string;
};

type TrendTheme = {
  label: string;
  description: string;
  count: number;
  share: number;
  examples: string[];
};

type TrendsPayload = {
  startup_pool_size: number;
  headline: string;
  themes: TrendTheme[];
};

/** McKinsey-style memo: fixed section order and field mapping. */
type MemoConsultPart = { key: keyof Memo; subtitle?: string };

const MEMO_CONSULTING_SECTIONS: {
  id: string;
  title: string;
  parts: MemoConsultPart[];
}[] = [
  {
    id: "executive",
    title: "Executive Summary",
    parts: [
      { key: "summary" },
      { key: "company_overview", subtitle: "Company overview" },
    ],
  },
  {
    id: "market",
    title: "Market Opportunity",
    parts: [{ key: "market_opportunity" }],
  },
  {
    id: "business",
    title: "Business Model",
    parts: [{ key: "business_model" }],
  },
  {
    id: "competition",
    title: "Competition",
    parts: [
      { key: "competitive_landscape", subtitle: "Landscape" },
      { key: "differentiation_analysis", subtitle: "Differentiation" },
      { key: "competitive_strengths", subtitle: "Competitive strengths" },
      { key: "competition", subtitle: "Market structure" },
    ],
  },
  {
    id: "risks",
    title: "Risks",
    parts: [{ key: "risks" }],
  },
  {
    id: "thesis",
    title: "Investment Thesis",
    parts: [{ key: "investment_thesis" }],
  },
];

/** Turn accidental JSON blobs into readable prose; otherwise return clean text. */
function formatMemoBodyText(raw: string): string {
  const t = raw?.trim() ?? "";
  if (!t) return "";
  if (t.startsWith("{") && t.endsWith("}")) {
    try {
      const o = JSON.parse(t) as Record<string, unknown>;
      return Object.entries(o)
        .filter(([, v]) => v != null && String(v).trim() !== "")
        .map(([k, v]) => {
          const label = k
            .replace(/_/g, " ")
            .replace(/\b\w/g, (c) => c.toUpperCase());
          return `${label}. ${String(v).trim()}`;
        })
        .join("\n\n");
    } catch {
      return raw.trim();
    }
  }
  return t;
}

function MemoProse({ text }: { text: string }) {
  const cleaned = formatMemoBodyText(text);
  if (!cleaned) return null;
  const blocks = cleaned.split(/\n\n+/).filter((p) => p.trim());
  return (
    <>
      {blocks.map((para, i) => (
        <p key={i} className="memo-consulting__p">
          {para.trim()}
        </p>
      ))}
    </>
  );
}

function buildConsultingMemoSections(memo: Memo): { id: string; title: string; blocks: ReactNode[] }[] {
  const sections: { id: string; title: string; blocks: ReactNode[] }[] = [];
  for (const sec of MEMO_CONSULTING_SECTIONS) {
    const blocks: ReactNode[] = [];
    for (const part of sec.parts) {
      const raw = memo[part.key];
      const text = typeof raw === "string" ? raw : "";
      if (!formatMemoBodyText(text).trim()) continue;
      blocks.push(
        <div key={String(part.key)} className="memo-consulting__subblock">
          {part.subtitle ? <h3 className="memo-consulting__h3">{part.subtitle}</h3> : null}
          <div className="memo-consulting__prose">
            <MemoProse text={text} />
          </div>
        </div>,
      );
    }
    if (blocks.length > 0) {
      sections.push({ id: sec.id, title: sec.title, blocks });
    }
  }
  return sections;
}

const NAV: { id: Tab; label: string }[] = [
  { id: "radar", label: "Radar" },
  { id: "deals", label: "Deals" },
  { id: "memo", label: "Memos" },
  { id: "trends", label: "Trends" },
];

function NavIcon({ tab }: { tab: Tab }) {
  const cls = "nav-icon-svg";
  switch (tab) {
    case "radar":
      return (
        <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
          <circle cx="12" cy="12" r="2" />
          <path d="M12 2v2M12 20v2M2 12h2M20 12h2" strokeLinecap="round" />
          <path d="M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" strokeLinecap="round" />
          <path d="M12 6a6 6 0 0 1 6 6" strokeLinecap="round" opacity="0.5" />
        </svg>
      );
    case "deals":
      return (
        <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
          <path d="M3 3v18h18" strokeLinecap="round" />
          <path d="M7 14l4-4 4 4 5-6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    case "memo":
      return (
        <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" strokeLinejoin="round" />
          <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" strokeLinecap="round" />
        </svg>
      );
    case "trends":
      return (
        <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden>
          <path d="M12 3v3M12 18v3M3 12h3M18 12h3" strokeLinecap="round" />
          <circle cx="12" cy="12" r="7" />
          <path d="M12 8v8M8 12h8" strokeLinecap="round" opacity="0.45" />
        </svg>
      );
    default:
      return null;
  }
}

async function downloadMemoPdf(startupId: number, startupName: string) {
  const res = await fetch(`/api/memo/${startupId}/pdf`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const base = startupName.replace(/[^\w\s\-]+/g, "").trim().replace(/\s+/g, "_").slice(0, 40) || "memo";
  a.download = `${base}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle: string;
  actions?: ReactNode;
}) {
  return (
    <header className="page-header">
      <div>
        <h1 className="page-title">{title}</h1>
        <p className="page-subtitle">{subtitle}</p>
      </div>
      {actions ? <div className="page-actions">{actions}</div> : null}
    </header>
  );
}

function tagOrFallback(raw: string, fallback: string) {
  const s = raw?.trim();
  return s ? s : fallback;
}

/** Green / amber / red quality band for 0–100 deal score. */
function dealScoreBand(score: number): "high" | "mid" | "low" {
  if (score >= 68) return "high";
  if (score >= 42) return "mid";
  return "low";
}

function dealRankTier(rank: number): "leader" | "runner" | "third" | null {
  if (rank === 1) return "leader";
  if (rank === 2) return "runner";
  if (rank === 3) return "third";
  return null;
}

function clipRationale(text: string, max = 200) {
  const t = text.trim();
  if (t.length <= max) return t;
  return t.slice(0, max).trimEnd() + "…";
}

/** Stagger index for `.list-stagger` children (CSS `--stagger-i`). */
function staggerItem(index: number): CSSProperties {
  return { ["--stagger-i"]: Math.min(index, 22) } as CSSProperties;
}

function parseVcDigestLines(raw: string): { label: string; value: string }[] {
  const lines = raw.split(/\r?\n/).filter((l) => l.trim());
  const out: { label: string; value: string }[] = [];
  for (const line of lines) {
    const idx = line.indexOf(":");
    if (idx === -1) continue;
    out.push({
      label: line.slice(0, idx).trim(),
      value: line.slice(idx + 1).trim(),
    });
  }
  return out;
}

function vcRelevanceTier(n: number): "hot" | "warm" | "watch" {
  if (n >= 8) return "hot";
  if (n >= 5) return "warm";
  return "watch";
}

function RadarDigest({ text, compact }: { text: string; compact?: boolean }) {
  const rows = parseVcDigestLines(text);
  if (rows.length === 0) {
    return <p className="radar-digest-fallback">{text}</p>;
  }
  return (
    <div className={`radar-digest ${compact ? "radar-digest--compact" : ""}`}>
      {rows.map((row, j) => {
        const isScore = /VC relevance score/i.test(row.label);
        const scoreMatch = row.value.match(/(\d+)/);
        const scoreNum = scoreMatch ? parseInt(scoreMatch[1], 10) : NaN;
        const tier = Number.isFinite(scoreNum) ? vcRelevanceTier(scoreNum) : null;
        const isName = /^company name$/i.test(row.label);
        const isSector = /^sector$/i.test(row.label);
        const isStage = /^stage$/i.test(row.label);
        const isWhy = /^why it qualifies/i.test(row.label);
        return (
          <div
            key={j}
            className={[
              "radar-digest__row",
              isName ? "radar-digest__row--name" : "",
              isWhy ? "radar-digest__row--why" : "",
              isScore ? "radar-digest__row--score" : "",
              tier && isScore ? `radar-digest__row--${tier}` : "",
            ]
              .filter(Boolean)
              .join(" ")}
          >
            <span className="radar-digest__label">{row.label}</span>
            {isScore && Number.isFinite(scoreNum) ? (
              <span className={`radar-score-chip radar-score-chip--${tier ?? "warm"}`} title={`VC relevance ${scoreNum}/10`}>
                <span className="radar-score-chip__num">{scoreNum}</span>
                <span className="radar-score-chip__den">/10</span>
              </span>
            ) : (
              <span
                className={[
                  "radar-digest__value",
                  isSector ? "radar-digest__value--pill radar-digest__value--sector" : "",
                  isStage ? "radar-digest__value--pill radar-digest__value--stage" : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
              >
                {row.value}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}

function SkeletonRadarBoard() {
  return (
    <div className="radar-grid" aria-busy="true" aria-label="Loading leaderboard">
      {Array.from({ length: 6 }, (_, i) => (
        <div key={i} className="skeleton-card-radar">
          <div className="skeleton-card-radar__top">
            <span className="skeleton skeleton-card-radar__line" style={{ width: "2.25rem" }} />
          </div>
          <span className="skeleton skeleton-block skeleton-block--wide" style={{ height: "0.7rem", marginBottom: "0.45rem" }} />
          <span className="skeleton skeleton-block skeleton-block--wide" style={{ height: "0.7rem", marginBottom: "0.45rem" }} />
          <span className="skeleton skeleton-block" style={{ width: "88%", height: "0.7rem", marginBottom: "0.45rem" }} />
          <span className="skeleton skeleton-block" style={{ width: "72%", height: "0.7rem", marginBottom: "0.45rem" }} />
          <span className="skeleton skeleton-block" style={{ width: "40%", height: "0.7rem" }} />
        </div>
      ))}
    </div>
  );
}

function SkeletonDealTerminal() {
  return (
    <section className="skeleton-terminal" aria-busy="true" aria-label="Loading deal queue">
      <div className="skeleton-terminal__strip" />
      {Array.from({ length: 7 }, (_, i) => (
        <div key={i} className="skeleton-terminal__row">
          <span className="skeleton skeleton-block" style={{ width: "1.75rem", height: "1.25rem" }} />
          <div style={{ minWidth: 0 }}>
            <span className="skeleton skeleton-block skeleton-block--narrow" style={{ marginBottom: "0.45rem" }} />
            <span className="skeleton skeleton-block skeleton-block--wide" style={{ height: "6px" }} />
          </div>
          <span className="skeleton skeleton-block" style={{ width: "3.25rem", height: "1.5rem", borderRadius: "999px" }} />
        </div>
      ))}
    </section>
  );
}

function SkeletonMemoPickGrid() {
  return (
    <div className="card-grid card-grid--memos" aria-busy="true" aria-label="Loading companies">
      {Array.from({ length: 8 }, (_, i) => (
        <div
          key={i}
          className="skeleton-card-radar"
          style={{ minHeight: "5.5rem", padding: "var(--space-4) var(--space-5)" }}
        >
          <span className="skeleton skeleton-card-radar__line skeleton-card-radar__line--lg" style={{ marginBottom: "0.5rem" }} />
          <span className="skeleton skeleton-card-radar__line" style={{ width: "55%", marginBottom: "0.65rem" }} />
          <span className="skeleton" style={{ width: "4rem", height: "1.35rem", borderRadius: "6px" }} />
        </div>
      ))}
    </div>
  );
}

function SkeletonMemoDocument() {
  return (
    <article className="memo-consulting" aria-busy="true" aria-label="Loading memorandum">
      <div className="skeleton-memo-sheet">
        <div className="skeleton-memo-sheet__head">
          <span className="skeleton skeleton-block" style={{ width: "40%", height: "0.65rem", marginBottom: "1rem" }} />
          <span className="skeleton skeleton-block" style={{ width: "85%", height: "1.35rem", marginBottom: "0.65rem" }} />
          <span className="skeleton skeleton-block" style={{ width: "62%", height: "0.75rem" }} />
        </div>
        {[0, 1, 2].map((b) => (
          <div key={b} className="skeleton-memo-sheet__block">
            <span className="skeleton skeleton-block" style={{ width: "28%", height: "0.7rem", marginBottom: "0.85rem" }} />
            <span className="skeleton skeleton-block skeleton-block--wide" style={{ marginBottom: "0.5rem" }} />
            <span className="skeleton skeleton-block" style={{ width: "92%", marginBottom: "0.5rem" }} />
            <span className="skeleton skeleton-block" style={{ width: "78%" }} />
          </div>
        ))}
      </div>
    </article>
  );
}

function SkeletonTrends() {
  return (
    <div aria-busy="true" aria-label="Loading trends">
      <div className="skeleton trends-skeleton-hero hero-metric">
        <span className="skeleton skeleton-block" style={{ width: "70%", height: "1.1rem", marginBottom: "0.75rem" }} />
        <span className="skeleton skeleton-block" style={{ width: "12rem", height: "0.8rem" }} />
      </div>
      <div className="trends-deck">
        {Array.from({ length: 4 }, (_, i) => (
          <div key={i} className="trend-card" style={{ pointerEvents: "none" }}>
            <span className="skeleton skeleton-block" style={{ width: "55%", height: "1rem", marginBottom: "0.65rem" }} />
            <span className="skeleton skeleton-block skeleton-block--wide" style={{ marginBottom: "0.45rem" }} />
            <span className="skeleton skeleton-block" style={{ width: "88%", marginBottom: "1rem" }} />
            <span className="skeleton skeleton-block" style={{ width: "6rem", height: "1.25rem" }} />
          </div>
        ))}
      </div>
    </div>
  );
}

function ViewRadar({ onError }: { onError: (e: string | null) => void }) {
  const [rows, setRows] = useState<TopStartup[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    onError(null);
    setLoading(true);
    try {
      const data = await apiJson<TopStartup[]>("/api/radar/top-startups");
      setRows(data);
      setSelectedId((prev) => {
        if (prev != null && data.some((r) => r.id === prev)) return prev;
        return data[0]?.id ?? null;
      });
    } catch (e) {
      onError(e instanceof Error ? e.message : "Failed to load top startups");
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [onError]);

  useEffect(() => {
    void load();
  }, [load]);

  const selected = rows.find((r) => r.id === selectedId) ?? null;

  return (
    <>
      <PageHeader
        title="Radar"
        subtitle="Curated deal flow in real time — engagement, thesis fit, and momentum in one glance."
        actions={
          <button type="button" className="btn btn-secondary" onClick={() => void load()}>
            Refresh
          </button>
        }
      />
      <div className="workspace workspace--radar workspace--radar-live">
        <div className="workspace-primary workspace-primary--radar">
          {!loading && rows.length > 0 && (
            <div className="radar-live-strip">
              <span className="radar-live-strip__pulse" aria-hidden />
              <span className="radar-live-strip__title">Live signal</span>
              <span className="radar-live-strip__meta tabular">{rows.length} on the board</span>
            </div>
          )}
          {loading && (
            <div className="radar-live-strip radar-live-strip--sync">
              <span className="radar-live-strip__pulse" aria-hidden />
              <span className="radar-live-strip__title">Syncing feed…</span>
            </div>
          )}
          {loading && <SkeletonRadarBoard />}
          {!loading && rows.length === 0 && (
            <div className="empty-state empty-state--radar">
              <p className="empty-state__hook">No signals yet.</p>
              <p className="empty-state__hint">Run the pipeline or connect sources — your board will light up here.</p>
            </div>
          )}
          {!loading && rows.length > 0 && (
            <div className="radar-grid list-stagger">
              {rows.map((r, i) => (
                <button
                  key={r.id}
                  type="button"
                  style={staggerItem(i)}
                  className={`radar-card ${selectedId === r.id ? "radar-card--selected" : ""}`}
                  onClick={() => setSelectedId(r.id)}
                >
                  <div className="radar-card__top">
                    <span className="radar-card__rank-wrap">
                      <span className="radar-card__rank" aria-label={`Rank ${i + 1}`}>
                        #{String(i + 1).padStart(2, "0")}
                      </span>
                      {i === 0 ? (
                        <span className="radar-card__spotlight">Top pick</span>
                      ) : i < 3 ? (
                        <span className="radar-card__spotlight radar-card__spotlight--runner">Watch</span>
                      ) : null}
                    </span>
                  </div>
                  <RadarDigest text={r.vc_digest} compact />
                  {r.url ? (
                    <div className="radar-card__link-row">
                      <a
                        href={r.url}
                        target="_blank"
                        rel="noreferrer"
                        className="radar-card__cta-link"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <span>Open deal link</span>
                        <span className="radar-card__cta-arrow" aria-hidden>
                          →
                        </span>
                      </a>
                    </div>
                  ) : null}
                </button>
              ))}
            </div>
          )}
        </div>
        <aside className="workspace-detail workspace-detail--radar" aria-label="Selection detail">
          {!selected && (
            <div className="detail-placeholder detail-placeholder--radar">
              <span className="detail-placeholder__icon" aria-hidden>
                ◈
              </span>
              <p className="detail-placeholder__title">Pick a card</p>
              <p className="detail-placeholder__sub">Lock in the full digest and link on the right.</p>
            </div>
          )}
          {selected && (
            <div key={selected.id} className="detail-panel-enter">
              <div className="detail-card detail-card--glass detail-card--radar-pin">
                <div className="detail-card--radar-pin__shine" aria-hidden />
                <p className="detail-card__eyebrow detail-card__eyebrow--radar">Pinned</p>
                <RadarDigest text={selected.vc_digest} />
                {selected.url ? (
                  <a href={selected.url} target="_blank" rel="noreferrer" className="radar-pin-cta">
                    <span className="radar-pin-cta__label">Open source</span>
                    <span className="radar-pin-cta__url">{selected.url.replace(/^https?:\/\//, "")}</span>
                  </a>
                ) : null}
              </div>
            </div>
          )}
        </aside>
      </div>
    </>
  );
}

function ViewDeals({ onError }: { onError: (e: string | null) => void }) {
  const [industry, setIndustry] = useState("");
  const [stage, setStage] = useState("");
  const [rows, setRows] = useState<TopDeal[]>([]);
  const [selectedKey, setSelectedKey] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    onError(null);
    setLoading(true);
    try {
      const qs = new URLSearchParams();
      if (industry) qs.set("industry", industry);
      if (stage) qs.set("stage", stage);
      const path = `/api/deals/top${qs.toString() ? `?${qs}` : ""}`;
      const data = await apiJson<TopDeal[]>(path);
      setRows(data);
      setSelectedKey((prev) => {
        if (prev != null && data.some((d) => d.startup_id === prev)) return prev;
        return data[0]?.startup_id ?? null;
      });
    } catch (e) {
      onError(e instanceof Error ? e.message : "Failed to load top deals");
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [onError, industry, stage]);

  useEffect(() => {
    void load();
  }, [load]);

  const selected = rows.find((r) => r.startup_id === selectedKey) ?? null;

  return (
    <>
      <PageHeader
        title="Deal Finder"
        subtitle="Ranked intelligence — composite deal scores updated from live funnel data."
        actions={
          <button type="button" className="btn btn-secondary" onClick={() => void load()}>
            Refresh
          </button>
        }
      />
      <div className="intel-filters">
        <label className="filter-field">
          <span className="filter-label">Industry</span>
          <select
            className="filter-select"
            value={industry}
            onChange={(e) => setIndustry(e.target.value)}
            aria-label="Industry filter"
          >
            <option value="">All sectors</option>
            <option value="AI">AI</option>
            <option value="SaaS">SaaS</option>
            <option value="health">Health</option>
          </select>
        </label>
        <label className="filter-field">
          <span className="filter-label">Stage</span>
          <select className="filter-select" value={stage} onChange={(e) => setStage(e.target.value)} aria-label="Stage filter">
            <option value="">All stages</option>
            <option value="pre-seed">Pre-seed</option>
            <option value="seed">Seed</option>
          </select>
        </label>
      </div>
      <div className="workspace workspace--deals-terminal">
        <div className="workspace-primary">
          {loading && <SkeletonDealTerminal />}
          {!loading && rows.length === 0 && (
            <div className="empty-state">No deals match these filters. Broaden criteria or refresh data.</div>
          )}
          {!loading && rows.length > 0 && (
            <section className="intel-terminal" aria-label="Ranked deal opportunities">
              <header className="intel-terminal__strip">
                <span className="intel-terminal__strip-dot" aria-hidden />
                <span className="intel-terminal__strip-title">DEAL INTELLIGENCE</span>
                <span className="intel-terminal__strip-meta tabular">{rows.length} ISSUES · SORTED BY SCORE</span>
              </header>
              <div className="intel-terminal__columns" aria-hidden>
                <span>RANK</span>
                <span>SECURITY</span>
                <span className="intel-terminal__col-score">DEAL SCORE</span>
                <span>PROFILE</span>
              </div>
              <div className="intel-terminal__list list-stagger">
                {rows.map((r, idx) => {
                  const rank = idx + 1;
                  const tier = dealRankTier(rank);
                  const band = dealScoreBand(r.score);
                  const tierClass = tier ? `intel-row--${tier}` : "";
                  const rowSelected = selectedKey === r.startup_id;
                  return (
                    <button
                      key={r.startup_id}
                      type="button"
                      style={staggerItem(idx)}
                      className={["intel-row", tierClass, rowSelected ? "intel-row--selected" : ""].filter(Boolean).join(" ")}
                      onClick={() => setSelectedKey(r.startup_id)}
                    >
                      <div className="intel-row__rank-wrap">
                        <span className="intel-row__rank tabular">{rank}</span>
                        {tier ? (
                          <span className={`intel-tier-badge intel-tier-badge--${tier}`}>
                            {tier === "leader" ? "TOP" : tier === "runner" ? "2ND" : "3RD"}
                          </span>
                        ) : null}
                      </div>
                      <div className="intel-row__center">
                        <div className="intel-row__title-row">
                          <span className="intel-row__name">{r.name}</span>
                          <div className="intel-row__score-cluster">
                            <span className="intel-row__score-num tabular">{r.score.toFixed(1)}</span>
                            <span className="intel-row__score-denom">/100</span>
                          </div>
                        </div>
                        <div className={`intel-scoretrack intel-scoretrack--${band}`} aria-hidden>
                          <div className="intel-scoretrack__fill" style={{ width: `${Math.min(100, Math.max(0, r.score))}%` }} />
                        </div>
                        <p className="intel-row__rationale">{clipRationale(r.rationale)}</p>
                      </div>
                      <div className="intel-row__profile">
                        <span className={`stage-pill stage-pill--${r.stage}`}>{r.stage}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </section>
          )}
        </div>
        <aside className="workspace-detail workspace-detail--deals">
          {!selected && (
            <p className="detail-placeholder">Select a row for full thesis context and signal decomposition.</p>
          )}
          {selected && (
            <div key={selected.startup_id} className="detail-panel-enter">
              <div className="detail-card detail-card--terminal">
              <p className="detail-card__eyebrow">Selection detail</p>
              <h2 className="detail-card__name">{selected.name}</h2>
              <div className="stat-row">
                <div className="stat-block">
                  <span className="stat-label">Deal score</span>
                  <span className="stat-value tabular">{selected.score.toFixed(1)}</span>
                </div>
                <div className="stat-block">
                  <span className="stat-label">Readiness</span>
                  <span className="stat-value capitalize">{selected.stage}</span>
                </div>
              </div>
              <div className={`intel-scoretrack intel-scoretrack--sm intel-scoretrack--${dealScoreBand(selected.score)}`} aria-hidden>
                <div className="intel-scoretrack__fill" style={{ width: `${Math.min(100, selected.score)}%` }} />
              </div>
              <div className="callout callout-emerald">
                <span className="callout-label">Why this matters</span>
                <p>{selected.why_it_matters}</p>
              </div>
              <h3 className="detail-section-title">Signal breakdown</h3>
              <p className="detail-prose">{selected.rationale}</p>
              <div className="entity-meta" aria-label="Pipeline record identifier">
                <span className="entity-meta__label">Pipeline ID</span>
                <span className="entity-meta__value tabular">{selected.startup_id}</span>
              </div>
              </div>
            </div>
          )}
        </aside>
      </div>
    </>
  );
}

function ViewMemos({ onError }: { onError: (e: string | null) => void }) {
  const [startups, setStartups] = useState<Startup[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [memo, setMemo] = useState<Memo | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingMemo, setLoadingMemo] = useState(false);
  const [genBusy, setGenBusy] = useState(false);
  const [pdfBusy, setPdfBusy] = useState(false);

  const loadStartups = useCallback(async () => {
    onError(null);
    setLoadingList(true);
    try {
      const data = await apiJson<Startup[]>("/api/radar/startups");
      setStartups(data);
      setSelectedId((prev) => {
        if (prev != null && data.some((s) => s.id === prev)) return prev;
        return data[0]?.id ?? null;
      });
    } catch (e) {
      onError(e instanceof Error ? e.message : "Failed to load startups");
    } finally {
      setLoadingList(false);
    }
  }, [onError]);

  useEffect(() => {
    void loadStartups();
  }, [loadStartups]);

  useLayoutEffect(() => {
    if (selectedId != null) {
      setLoadingMemo(true);
      setMemo(null);
    } else {
      setLoadingMemo(false);
      setMemo(null);
    }
  }, [selectedId]);

  useEffect(() => {
    if (selectedId == null) return;
    let cancelled = false;
    void (async () => {
      try {
        const m = await apiJsonOrNull<Memo>(`/api/memo/${selectedId}`);
        if (!cancelled) setMemo(m);
      } catch (e) {
        if (!cancelled) {
          onError(e instanceof Error ? e.message : "Failed to load memo");
          setMemo(null);
        }
      } finally {
        if (!cancelled) setLoadingMemo(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedId, onError]);

  const selected = startups.find((s) => s.id === selectedId) ?? null;
  const memoForSelection = memo && memo.startup_id === selectedId ? memo : null;
  const consultingSections = memoForSelection ? buildConsultingMemoSections(memoForSelection) : [];

  async function generateMemo() {
    if (selectedId == null) return;
    onError(null);
    setGenBusy(true);
    try {
      await apiJson<Memo>("/api/memo/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ startup_id: selectedId }),
      });
      const m = await apiJson<Memo>(`/api/memo/${selectedId}`);
      setMemo(m);
    } catch (e) {
      onError(e instanceof Error ? e.message : "Generate failed");
    } finally {
      setGenBusy(false);
    }
  }

  async function exportPdf() {
    if (selectedId == null || !selected) return;
    onError(null);
    setPdfBusy(true);
    try {
      await downloadMemoPdf(selectedId, selected.name);
    } catch (e) {
      onError(e instanceof Error ? e.message : "PDF export failed");
    } finally {
      setPdfBusy(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Memos"
        subtitle="Confidential investment memoranda — structured diligence narrative. Generate from pipeline signals or export to PDF."
        actions={
          <>
            <button type="button" className="btn btn-secondary" onClick={() => void loadStartups()}>
              Refresh
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => void generateMemo()}
              disabled={selectedId == null || genBusy}
            >
              {genBusy ? "Generating…" : memoForSelection ? "Regenerate memo" : "Generate memo"}
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => void exportPdf()}
              disabled={!memoForSelection || pdfBusy}
            >
              {pdfBusy ? "Exporting…" : "Export PDF"}
            </button>
          </>
        }
      />
      <div className="workspace workspace--stack workspace--memos">
        <div className="workspace-primary">
          {loadingList && <SkeletonMemoPickGrid />}
          {!loadingList && startups.length === 0 && (
            <div className="empty-state">No companies on file. Add startups via API or seed data.</div>
          )}
          {!loadingList && startups.length > 0 && (
            <div className="card-grid card-grid--memos list-stagger">
              {startups.map((s, i) => (
                <button
                  key={s.id}
                  type="button"
                  style={staggerItem(i)}
                  className={`memo-pick-card ${selectedId === s.id ? "is-active" : ""}`}
                  onClick={() => setSelectedId(s.id)}
                >
                  <span className="memo-pick-card__name">{s.name}</span>
                  <span className="memo-pick-card__meta">
                    {(s.sector || "Sector —").slice(0, 28)}
                    {s.sector && s.sector.length > 28 ? "…" : ""}
                  </span>
                  <span className="chip chip-outline">{s.stage || "—"}</span>
                </button>
              ))}
            </div>
          )}
        </div>
        <aside className="workspace-detail workspace-detail--wide workspace-detail--memos">
          {!selected && <p className="detail-placeholder">Choose a company to load its latest memo.</p>}
          {selected && loadingMemo && (
            <div className="memo-consulting-aside__scroll">
              <SkeletonMemoDocument />
            </div>
          )}
          {selected && !loadingMemo && memo === null && (
            <div className="memo-consulting-aside__inner">
              <div className="detail-card detail-card--cta memo-consulting-cta">
                <p className="detail-prose">
                  No memo on file for <strong>{selected.name}</strong>. Generate a structured investment memorandum from
                  stored signals.
                </p>
                <button type="button" className="btn btn-primary btn-lg" onClick={() => void generateMemo()} disabled={genBusy}>
                  {genBusy ? "Generating…" : "Generate memo"}
                </button>
              </div>
            </div>
          )}
          {selected && !loadingMemo && memoForSelection && (
            <div className="memo-consulting-aside__scroll">
              <div key={selectedId ?? 0} className="detail-panel-enter">
              <article className="memo-consulting" aria-label="Investment memorandum">
                <div className="memo-consulting__sheet">
                  <header className="memo-consulting__doc-head">
                    <p className="memo-consulting__kicker">Confidential · investment memorandum</p>
                    <h1 className="memo-consulting__doc-title">{memoForSelection.title}</h1>
                    <p className="memo-consulting__doc-meta">
                      <span className="memo-consulting__company">{selected.name}</span>
                      <span className="memo-consulting__doc-meta-sep" aria-hidden>
                        ·
                      </span>
                      <span className="tabular">{memoForSelection.status}</span>
                      <span className="memo-consulting__doc-meta-sep" aria-hidden>
                        ·
                      </span>
                      <time dateTime={memoForSelection.created_at}>
                        {new Date(memoForSelection.created_at).toLocaleString(undefined, {
                          dateStyle: "medium",
                          timeStyle: "short",
                        })}
                      </time>
                    </p>
                  </header>
                  {consultingSections.map((sec, idx) => (
                    <section key={sec.id} className="memo-consulting__section">
                      <h2 className="memo-consulting__h2">
                        <span className="memo-consulting__section-num" aria-hidden>
                          {idx + 1}
                        </span>
                        {sec.title}
                      </h2>
                      {sec.blocks}
                    </section>
                  ))}
                  {consultingSections.length === 0 && (
                    <p className="memo-consulting__empty">
                      No narrative sections in this memo yet. Use Regenerate memo to refresh from pipeline data.
                    </p>
                  )}
                </div>
              </article>
              </div>
            </div>
          )}
        </aside>
      </div>
    </>
  );
}

function ViewTrends({ onError }: { onError: (e: string | null) => void }) {
  const [data, setData] = useState<TrendsPayload | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    onError(null);
    setLoading(true);
    try {
      const j = await apiJson<TrendsPayload>("/api/radar/trends");
      setData(j);
    } catch (e) {
      onError(e instanceof Error ? e.message : "Failed to load trends");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [onError]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <>
      <PageHeader
        title="Trends"
        subtitle="Cross-portfolio narrative clusters — surface themes for IC and thesis alignment."
        actions={
          <button type="button" className="btn btn-secondary" onClick={() => void load()}>
            Refresh
          </button>
        }
      />
      {loading && <SkeletonTrends />}
      {!loading && data && (
        <>
          <div className="hero-metric">
            <p className="hero-metric__text">{data.headline}</p>
            <span className="hero-metric__badge">
              <span className="tabular">{data.startup_pool_size}</span> companies analyzed
            </span>
          </div>
          {data.themes.length === 0 && (
            <div className="empty-state">No strong clusters yet. Enrich descriptions or expand coverage.</div>
          )}
          {data.themes.length > 0 && (
            <div className="trends-deck list-stagger">
              {data.themes.map((t, i) => (
                <article key={t.label} style={staggerItem(i)} className="trend-card">
                  <h3 className="trend-card__title">{t.label}</h3>
                  <p className="trend-card__desc">{t.description}</p>
                  <div className="trend-card__footer">
                    <span className="trend-stat tabular">
                      {t.count} <span className="trend-stat-muted">· {Math.round(t.share * 100)}%</span>
                    </span>
                  </div>
                  {t.examples.length > 0 && (
                    <ul className="trend-examples">
                      {t.examples.map((ex) => (
                        <li key={ex}>{ex}</li>
                      ))}
                    </ul>
                  )}
                </article>
              ))}
            </div>
          )}
        </>
      )}
    </>
  );
}

export default function App() {
  const [tab, setTab] = useState<Tab>("radar");
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="shell">
      <aside className="sidebar" aria-label="Primary navigation">
        <div className="sidebar-brand">
          <img className="sidebar-logo" src="/logo.svg" width={38} height={38} alt="" decoding="async" />
          <div className="sidebar-brand-text">
            <span className="sidebar-brand-name">ai-vc-analyst</span>
            <span className="sidebar-brand-tag">Command Center</span>
          </div>
        </div>
        <nav className="sidebar-nav">
          {NAV.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`nav-item ${tab === item.id ? "is-active" : ""}`}
              onClick={() => {
                setTab(item.id);
                setError(null);
              }}
            >
              <span className="nav-item-icon">
                <NavIcon tab={item.id} />
              </span>
              <span className="nav-item-label">{item.label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className="sidebar-footer-note">Local · FastAPI · SQLite</span>
        </div>
      </aside>

      <div className="main">
        <div className="main-inner">
          {error ? <div className="banner-error">{error}</div> : null}
          <div key={tab} className="tab-view">
            {tab === "radar" && <ViewRadar onError={setError} />}
            {tab === "deals" && <ViewDeals onError={setError} />}
            {tab === "memo" && <ViewMemos onError={setError} />}
            {tab === "trends" && <ViewTrends onError={setError} />}
          </div>
        </div>
      </div>
    </div>
  );
}
