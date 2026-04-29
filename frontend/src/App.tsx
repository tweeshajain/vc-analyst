import { useCallback, useEffect, useLayoutEffect, useState } from "react";
import { apiJson, apiJsonOrNull } from "./api";

type Tab = "radar" | "memo" | "deals" | "trends";

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

const MEMO_SECTIONS: { key: keyof Memo; label: string }[] = [
  { key: "summary", label: "Executive summary" },
  { key: "company_overview", label: "Company overview" },
  { key: "market_opportunity", label: "Market opportunity" },
  { key: "business_model", label: "Business model" },
  { key: "competitive_landscape", label: "Competitive landscape" },
  { key: "differentiation_analysis", label: "Differentiation" },
  { key: "competitive_strengths", label: "Strengths vs competitors" },
  { key: "competition", label: "Market structure & competition" },
  { key: "risks", label: "Risks" },
  { key: "investment_thesis", label: "Investment thesis" },
];

function EmptyDetail({ message }: { message: string }) {
  return <p className="detail-empty">{message}</p>;
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

function TabStartupRadar({
  onError,
}: {
  onError: (e: string | null) => void;
}) {
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
    <div className="tab-head">
      <div className="tab-title-row">
        <h2>Startup Radar</h2>
        <button type="button" className="btn-ghost" onClick={() => void load()}>
          Refresh
        </button>
      </div>
      <p className="tab-lead muted">
        Top 10 from engagement and ranking rules. Select a row for detail.
      </p>

      <div className="split">
        <div className="table-panel">
          {loading && <p className="muted">Loading…</p>}
          {!loading && rows.length === 0 && (
            <p className="muted">No startups yet. Run the pipeline or add data via the API.</p>
          )}
          {!loading && rows.length > 0 && (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th className="col-rank">#</th>
                    <th>Name</th>
                    <th className="col-num">Score</th>
                    <th className="col-sm">Source</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r, i) => (
                    <tr
                      key={r.id}
                      className={selectedId === r.id ? "selected" : ""}
                      onClick={() => setSelectedId(r.id)}
                    >
                      <td className="col-rank">{i + 1}</td>
                      <td className="cell-name">{r.name}</td>
                      <td className="col-num">{r.score.toFixed(0)}</td>
                      <td className="col-sm">{r.source}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <aside className="detail-panel" aria-label="Startup detail">
          {!selected && <EmptyDetail message="Select a startup from the list." />}
          {selected && (
            <>
              <h3 className="detail-title">{selected.name}</h3>
              <dl className="detail-dl">
                <div>
                  <dt>Rank score</dt>
                  <dd>{selected.score.toFixed(1)} / 100</dd>
                </div>
                <div>
                  <dt>Engagement (radar)</dt>
                  <dd>{selected.radar_score.toFixed(1)}</dd>
                </div>
                <div>
                  <dt>Signals</dt>
                  <dd>↑{selected.upvotes} · {selected.comments_count} comments</dd>
                </div>
                <div>
                  <dt>Source</dt>
                  <dd>{selected.source}</dd>
                </div>
                {selected.url && (
                  <div>
                    <dt>Link</dt>
                    <dd>
                      <a href={selected.url} target="_blank" rel="noreferrer" className="link">
                        {selected.url.replace(/^https?:\/\//, "")}
                      </a>
                    </dd>
                  </div>
                )}
              </dl>
              <p className="detail-reason">{selected.ranking_reason}</p>
              {selected.description && (
                <p className="detail-body">{selected.description}</p>
              )}
            </>
          )}
        </aside>
      </div>
    </div>
  );
}

function TabInvestmentMemos({
  onError,
}: {
  onError: (e: string | null) => void;
}) {
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
  const memoForSelection =
    memo && memo.startup_id === selectedId ? memo : null;

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
    <div className="tab-head">
      <div className="tab-title-row">
        <h2>Investment Memos</h2>
        <div className="tab-actions">
          <button type="button" className="btn-ghost" onClick={() => void loadStartups()}>
            Refresh
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => void exportPdf()}
            disabled={!memoForSelection || pdfBusy}
            title={
              memoForSelection ? "Download memo as PDF" : "Generate a memo before exporting"
            }
          >
            {pdfBusy ? "Exporting…" : "Export PDF"}
          </button>
        </div>
      </div>
      <p className="tab-lead muted">
        Choose a startup, then read the latest memo or generate one.
      </p>

      <div className="split">
        <div className="table-panel">
          {loadingList && <p className="muted">Loading…</p>}
          {!loadingList && startups.length === 0 && (
            <p className="muted">No startups. Seed the database or add companies via the API.</p>
          )}
          {!loadingList && startups.length > 0 && (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Sector</th>
                    <th>Stage</th>
                  </tr>
                </thead>
                <tbody>
                  {startups.map((s) => (
                    <tr
                      key={s.id}
                      className={selectedId === s.id ? "selected" : ""}
                      onClick={() => setSelectedId(s.id)}
                    >
                      <td className="cell-name">{s.name}</td>
                      <td>{s.sector || "—"}</td>
                      <td className="col-sm">{s.stage || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <aside className="detail-panel detail-panel--memo" aria-label="Memo content">
          {!selected && <EmptyDetail message="Select a startup." />}
          {selected && loadingMemo && <p className="muted">Loading memo…</p>}
          {selected && !loadingMemo && memo === null && (
            <div>
              <p className="muted" style={{ marginBottom: "1rem" }}>
                No memo for <strong>{selected.name}</strong>. Generate a structured memo from
                pipeline data.
              </p>
              <button
                type="button"
                className="btn-primary"
                onClick={() => void generateMemo()}
                disabled={genBusy}
              >
                {genBusy ? "Generating…" : "Generate memo"}
              </button>
            </div>
          )}
          {selected && !loadingMemo && memoForSelection && (
            <article className="memo-article">
              <header className="memo-header">
                <h3 className="detail-title">{memoForSelection.title}</h3>
                <p className="memo-meta">
                  {memoForSelection.status} ·{" "}
                  {new Date(memoForSelection.created_at).toLocaleString()}
                </p>
              </header>
              {MEMO_SECTIONS.map(({ key, label }) => {
                const v = memoForSelection[key];
                if (typeof v !== "string" || !v.trim()) return null;
                return (
                  <section key={key} className="memo-section">
                    <h4>{label}</h4>
                    <div className="memo-prose">{v}</div>
                  </section>
                );
              })}
            </article>
          )}
        </aside>
      </div>
    </div>
  );
}

function TabDealFinder({
  onError,
}: {
  onError: (e: string | null) => void;
}) {
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
    <div className="tab-head">
      <div className="tab-title-row">
        <h2>Deal Finder</h2>
        <button type="button" className="btn-ghost" onClick={() => void load()}>
          Refresh
        </button>
      </div>
      <p className="tab-lead muted">
        Top opportunities by composite deal score. Optional filters match the API query params.
      </p>

      <div className="toolbar">
        <label className="toolbar-field">
          <span className="muted">Industry</span>
          <select
            value={industry}
            onChange={(e) => setIndustry(e.target.value)}
            aria-label="Industry filter"
          >
            <option value="">Any</option>
            <option value="AI">AI</option>
            <option value="SaaS">SaaS</option>
            <option value="health">Health</option>
          </select>
        </label>
        <label className="toolbar-field">
          <span className="muted">Stage</span>
          <select
            value={stage}
            onChange={(e) => setStage(e.target.value)}
            aria-label="Stage filter"
          >
            <option value="">Any</option>
            <option value="pre-seed">Pre-seed</option>
            <option value="seed">Seed</option>
          </select>
        </label>
      </div>

      <div className="split">
        <div className="table-panel">
          {loading && <p className="muted">Loading…</p>}
          {!loading && rows.length === 0 && (
            <p className="muted">No matches for these filters (or empty pipeline).</p>
          )}
          {!loading && rows.length > 0 && (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th className="col-num">Score</th>
                    <th className="col-sm">Stage</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((r) => (
                    <tr
                      key={r.startup_id}
                      className={selectedKey === r.startup_id ? "selected" : ""}
                      onClick={() => setSelectedKey(r.startup_id)}
                    >
                      <td className="cell-name">{r.name}</td>
                      <td className="col-num">{r.score.toFixed(1)}</td>
                      <td className="col-sm">{r.stage}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <aside className="detail-panel" aria-label="Deal detail">
          {!selected && <EmptyDetail message="Select a row to see rationale and score." />}
          {selected && (
            <>
              <h3 className="detail-title">{selected.name}</h3>
              <dl className="detail-dl">
                <div>
                  <dt>Deal score</dt>
                  <dd>{selected.score.toFixed(1)} / 100</dd>
                </div>
                <div>
                  <dt>Readiness</dt>
                  <dd>{selected.stage}</dd>
                </div>
                <div>
                  <dt>Startup ID</dt>
                  <dd>{selected.startup_id}</dd>
                </div>
              </dl>
              <div className="callout-why">
                <span className="callout-why-label">Why this matters</span>
                <p className="callout-why-text">{selected.why_it_matters}</p>
              </div>
              <h4 className="detail-sub">Signal breakdown</h4>
              <p className="detail-body">{selected.rationale}</p>
            </>
          )}
        </aside>
      </div>
    </div>
  );
}

function TabTopTrends({ onError }: { onError: (e: string | null) => void }) {
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
    <div className="tab-head">
      <div className="tab-title-row">
        <h2>Top Trends</h2>
        <button type="button" className="btn-ghost" onClick={() => void load()}>
          Refresh
        </button>
      </div>
      <p className="tab-lead muted">
        Recurring themes inferred from startup names, sectors, and descriptions—useful for IC framing.
      </p>

      {loading && <p className="muted">Analyzing portfolio narratives…</p>}
      {!loading && data && (
        <>
          <div className="trends-hero">
            <p className="trends-headline">{data.headline}</p>
            <span className="trends-pool">
              Sample size: <strong>{data.startup_pool_size}</strong> startups
            </span>
          </div>
          {data.themes.length === 0 && (
            <p className="muted">No dominant clusters yet—expand descriptions or run the pipeline.</p>
          )}
          {data.themes.length > 0 && (
            <div className="trends-grid">
              {data.themes.map((t) => (
                <article key={t.label} className="theme-card">
                  <h3 className="theme-card-title">{t.label}</h3>
                  <p className="theme-card-desc">{t.description}</p>
                  <div className="theme-card-stats">
                    <span className="theme-pill">
                      {t.count} companies · {Math.round(t.share * 100)}%
                    </span>
                  </div>
                  {t.examples.length > 0 && (
                    <ul className="theme-examples">
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
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState<Tab>("radar");
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand-mark" aria-hidden="true" />
        <div>
          <h1>ai-vc-analyst</h1>
          <p>Radar, memos, deals, and cross-portfolio themes—demo dashboard</p>
        </div>
      </header>

      <nav className="tabs" aria-label="Sections">
        <button
          type="button"
          className={tab === "radar" ? "active" : ""}
          onClick={() => {
            setTab("radar");
            setError(null);
          }}
        >
          Startup Radar
        </button>
        <button
          type="button"
          className={tab === "memo" ? "active" : ""}
          onClick={() => {
            setTab("memo");
            setError(null);
          }}
        >
          Investment Memos
        </button>
        <button
          type="button"
          className={tab === "deals" ? "active" : ""}
          onClick={() => {
            setTab("deals");
            setError(null);
          }}
        >
          Deal Finder
        </button>
        <button
          type="button"
          className={tab === "trends" ? "active" : ""}
          onClick={() => {
            setTab("trends");
            setError(null);
          }}
        >
          Top Trends
        </button>
      </nav>

      <section className="panel" aria-live="polite">
        {error && <div className="err">{error}</div>}
        {tab === "radar" && <TabStartupRadar onError={setError} />}
        {tab === "memo" && <TabInvestmentMemos onError={setError} />}
        {tab === "deals" && <TabDealFinder onError={setError} />}
        {tab === "trends" && <TabTopTrends onError={setError} />}
      </section>
    </div>
  );
}
