"use client";

import { useEffect, useState } from "react";
import { API_BASE, apiGet, apiPost } from "../../lib/api";

type Mover = { title: string; change: number; change_pct: number | null; value: number };
type ValueSummary = {
  total_value: number;
  item_count: number;
  valued_count: number;
  coverage_pct: number;
  change_amount: number | null;
  change_pct: number | null;
  history: Array<{ date: string; total: number }>;
  best_movers: Mover[];
  worst_movers: Mover[];
};
type ArtistCompletion = {
  artist: string;
  owned: number;
  known: number;
  missing_count: number;
  completion_pct: number;
  missing: Array<{ title: string; year: number | null }>;
};

function Sparkline({ points }: { points: Array<{ date: string; total: number }> }) {
  if (points.length < 2) return <div className="muted small">Capture a few snapshots to see your history chart.</div>;
  const w = 520, h = 120, pad = 8;
  const xs = points.map((_, i) => i);
  const ys = points.map((p) => p.total);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const nx = (i: number) => pad + (i / (xs.length - 1)) * (w - pad * 2);
  const ny = (v: number) => h - pad - ((v - minY) / (maxY - minY || 1)) * (h - pad * 2);
  const d = points.map((p, i) => `${i === 0 ? "M" : "L"}${nx(i).toFixed(1)},${ny(p.total).toFixed(1)}`).join(" ");
  return (
    <svg width="100%" viewBox={`0 0 ${w} ${h}`} className="spark">
      <path d={d} fill="none" stroke="#d09b4c" strokeWidth="2.5" />
      <path d={`${d} L${nx(xs.length - 1)},${h - pad} L${nx(0)},${h - pad} Z`} fill="#d09b4c" opacity="0.08" />
    </svg>
  );
}

export default function InsightsPage() {
  const [value, setValue] = useState<ValueSummary | null>(null);
  const [artists, setArtists] = useState<ArtistCompletion[]>([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [cardUrl, setCardUrl] = useState<string | null>(null);

  async function load() {
    try {
      const [v, c] = await Promise.all([
        apiGet<ValueSummary>("/insights/value"),
        apiGet<{ artists: ArtistCompletion[] }>("/insights/completion"),
      ]);
      setValue(v);
      setArtists(c.artists);
    } catch (e) {
      setMsg((e as Error).message);
    }
  }
  useEffect(() => {
    load();
  }, []);

  async function snapshot() {
    setBusy(true);
    setMsg("");
    try {
      await apiPost("/insights/value/snapshot");
      await load();
      setMsg("Snapshot captured.");
    } catch (e) {
      setMsg((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function showCard() {
    // The card endpoint returns SVG (not JSON), so fetch it directly with the
    // same auth the api helper uses, then object-URL it into an <img>.
    const token = localStorage.getItem("spinninglicorice.token");
    const acct = localStorage.getItem("spinninglicorice.account");
    const headers: Record<string, string> = {};
    if (token) headers.Authorization = `Bearer ${token}`;
    if (acct) headers["X-Account-Id"] = acct;
    fetch(`${API_BASE}/insights/card`, { headers })
      .then((r) => r.text())
      .then((svg) => {
        const blob = new Blob([svg], { type: "image/svg+xml" });
        setCardUrl(URL.createObjectURL(blob));
      })
      .catch((e) => setMsg((e as Error).message));
  }

  const up = (n: number | null) => (n != null && n >= 0);

  return (
    <>
      <div className="page-header">
        <h1>Insights</h1>
        <p>What your collection is worth, what's missing, and a card worth sharing.</p>
      </div>

      {msg && <div className="status">{msg}</div>}

      {/* ---- Value ---- */}
      <section className="card form-card">
        <div className="insights-value-head">
          <div>
            <div className="muted small">ESTIMATED WORTH</div>
            <div className="big-worth">
              ${value ? value.total_value.toLocaleString(undefined, { maximumFractionDigits: 0 }) : "—"}
            </div>
            {value && value.change_amount != null && (
              <div className={up(value.change_amount) ? "delta-up" : "delta-down"}>
                {up(value.change_amount) ? "▲" : "▼"} ${Math.abs(value.change_amount).toFixed(0)}
                {value.change_pct != null && ` (${value.change_pct}%)`} since last snapshot
              </div>
            )}
          </div>
          <button className="btn light" onClick={snapshot} disabled={busy}>
            {busy ? "CAPTURING…" : "CAPTURE SNAPSHOT"}
          </button>
        </div>

        {value && (
          <div className="muted small" style={{ marginBottom: 10 }}>
            {value.item_count} records · {value.coverage_pct}% valued from market data
          </div>
        )}

        {value && <Sparkline points={value.history} />}

        {value && (value.best_movers.length > 0 || value.worst_movers.length > 0) && (
          <div className="movers">
            <div>
              <div className="muted small">BIGGEST GAINS</div>
              {value.best_movers.map((m, i) => (
                <div key={i} className="mover-row">
                  <span>{m.title}</span>
                  <span className="delta-up">+${m.change.toFixed(0)}{m.change_pct != null && ` (${m.change_pct}%)`}</span>
                </div>
              ))}
              {value.best_movers.length === 0 && <div className="muted small">—</div>}
            </div>
            <div>
              <div className="muted small">BIGGEST DROPS</div>
              {value.worst_movers.map((m, i) => (
                <div key={i} className="mover-row">
                  <span>{m.title}</span>
                  <span className="delta-down">${m.change.toFixed(0)}{m.change_pct != null && ` (${m.change_pct}%)`}</span>
                </div>
              ))}
              {value.worst_movers.length === 0 && <div className="muted small">—</div>}
            </div>
          </div>
        )}
      </section>

      {/* ---- Complete the collection ---- */}
      <section className="card form-card">
        <h2>Complete the collection</h2>
        <p className="muted small">Artists you collect, and the releases you're still missing.</p>
        {artists.length === 0 && <div className="muted small">Add some records to see gaps by artist.</div>}
        {artists.map((a) => (
          <div key={a.artist} className="completion-row">
            <div className="completion-head">
              <strong>{a.artist}</strong>
              <span className="muted small">{a.owned}/{a.known} · {a.completion_pct}%</span>
            </div>
            <div className="completion-bar">
              <div className="completion-fill" style={{ width: `${a.completion_pct}%` }} />
            </div>
            {a.missing.length > 0 && (
              <div className="missing-list">
                Missing: {a.missing.map((mm) => mm.title + (mm.year ? ` (${mm.year})` : "")).join(" · ")}
              </div>
            )}
          </div>
        ))}
      </section>

      {/* ---- Shareable card ---- */}
      <section className="card form-card">
        <h2>Your Collector Card</h2>
        <p className="muted small">A shareable snapshot of your collection — worth, era, top labels, rarity.</p>
        <button className="btn greenbtn" onClick={showCard}>GENERATE CARD</button>
        {cardUrl && (
          <div style={{ marginTop: 14 }}>
            <img src={cardUrl} alt="Collector Card" style={{ width: "100%", borderRadius: 12 }} />
            <a className="btn light" href={cardUrl} download="spinninglicorice-collector-card.svg" style={{ marginTop: 10 }}>
              DOWNLOAD
            </a>
          </div>
        )}
      </section>
    </>
  );
}
