"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

type Hunt = {
  id: string;
  name: string;
  query: string;
  auto_hunt: boolean;
  active: boolean;
  criteria: Record<string, unknown>;
};

type Result = {
  result_id: string;
  title: string;
  price: number;
  shipping: number | null;
  condition: string | null;
  source?: string;
  estimated_value_low?: number | null;
  estimated_value_high?: number | null;
  num_for_sale?: number | null;
  owned?: boolean;
  on_wantlist?: boolean;
  match_confidence?: number | null;
  image_url?: string | null;
  score: number;
  deal_label: string;
  explanation: string | null;
  seller: string | null;
  url: string;
};

export default function HunterClient() {
  const [hunts, setHunts] = useState<Hunt[]>([]);
  const [selectedHuntId, setSelectedHuntId] = useState<string | null>(null);
  const [results, setResults] = useState<Result[]>([]);
  const [query, setQuery] = useState(
    "Grateful Dead records I don't own under $50 VG+"
  );
  const [name, setName] = useState("Grateful Dead under $50");
  const [autoHunt, setAutoHunt] = useState(true);
  const [parsed, setParsed] = useState<Record<string, unknown> | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function loadHunts() {
    const response = await fetch(`${API_BASE}/hunter/hunts`, { cache: "no-store" });
    const data = await response.json();
    setHunts(data.items || []);
    if (!selectedHuntId && data.items?.length) setSelectedHuntId(data.items[0].id);
  }

  async function loadResults(huntId: string) {
    const response = await fetch(`${API_BASE}/hunter/hunts/${huntId}/results`, { cache: "no-store" });
    const data = await response.json();
    setResults(data.items || []);
  }

  useEffect(() => {
    loadHunts().catch(() => setMessage("Start the Burnt Jacket API to use Hunter."));
  }, []);

  useEffect(() => {
    if (selectedHuntId) loadResults(selectedHuntId).catch(() => {});
    else setResults([]);
  }, [selectedHuntId]);

  async function previewQuery() {
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch(`${API_BASE}/hunter/parse`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });
      const data = await response.json();
      setParsed(data.criteria);
    } catch {
      setMessage("Could not reach the Burnt Jacket API.");
    } finally {
      setBusy(false);
    }
  }

  async function createHunt(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch(`${API_BASE}/hunter/hunts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, query, auto_hunt: autoHunt }),
      });
      if (!response.ok) throw new Error("Create failed");
      const hunt = await response.json();
      await loadHunts();
      setSelectedHuntId(hunt.id);
      setMessage("Hunt created.");
    } catch {
      setMessage("Could not create Hunt. Make sure the API is running.");
    } finally {
      setBusy(false);
    }
  }

  async function refreshSelected() {
    if (!selectedHuntId) return;
    setBusy(true);
    setMessage("");
    try {
      const response = await fetch(`${API_BASE}/hunter/hunts/${selectedHuntId}/refresh`, {
        method: "POST",
      });
      const data = await response.json();
      setResults(data.results || []);
      setMessage(`Found ${(data.results || []).length} matching opportunities.`);
    } catch {
      setMessage("Hunter refresh failed.");
    } finally {
      setBusy(false);
    }
  }

  const selected = useMemo(
    () => hunts.find((h) => h.id === selectedHuntId),
    [hunts, selectedHuntId]
  );

  return (
    <>
      <section className="hunter-create card">
        <div className="orange">🔥 WHAT ARE YOU HUNTING?</div>
        <h2>Tell Burnt Jacket what you want.</h2>

        <form onSubmit={createHunt} className="hunter-form">
          <input
            className="field"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Hunt name"
          />
          <textarea
            className="field hunter-query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Find interesting Grateful Dead records I don't own for under $50."
          />
          <div className="hunter-actions">
            <label className="auto-toggle">
              <input
                type="checkbox"
                checked={autoHunt}
                onChange={(e) => setAutoHunt(e.target.checked)}
              />
              Auto Hunt
            </label>
            <button className="btn" type="button" onClick={previewQuery} disabled={busy}>
              PREVIEW CRITERIA
            </button>
            <button className="btn primary" type="submit" disabled={busy}>
              CREATE HUNT
            </button>
          </div>
        </form>

        {parsed && (
          <div className="parsed-box">
            <strong>Burnt Jacket understood:</strong>
            <div className="criteria-chips">
              {Object.entries(parsed)
                .filter(([key, value]) =>
                  value !== null &&
                  value !== false &&
                  key !== "raw_query" &&
                  !(Array.isArray(value) && !value.length)
                )
                .map(([key, value]) => (
                  <span className="badge" key={key}>
                    {key.replaceAll("_", " ")}:{" "}
                    {Array.isArray(value) ? value.join(", ") : String(value)}
                  </span>
                ))}
            </div>
          </div>
        )}
      </section>

      <section className="hunter-layout">
        <aside className="card">
          <div className="gold">MY HUNTS</div>
          <div className="hunt-list">
            {hunts.map((hunt) => (
              <button
                className={`hunt-row ${selectedHuntId === hunt.id ? "selected" : ""}`}
                key={hunt.id}
                onClick={() => setSelectedHuntId(hunt.id)}
              >
                <span>
                  <strong>{hunt.name}</strong>
                  <small>{hunt.query}</small>
                </span>
                {hunt.auto_hunt && <span className="green">AUTO</span>}
              </button>
            ))}
          </div>
          {!hunts.length && <p className="muted">Create your first Hunt above.</p>}
        </aside>

        <div className="card">
          <div className="hunter-result-head">
            <div>
              <div className="orange">HUNTER FOUND</div>
              <h2>{selected?.name || "Select a Hunt"}</h2>
            </div>
            <button
              className="btn primary"
              onClick={refreshSelected}
              disabled={!selectedHuntId || busy}
            >
              {busy ? "HUNTING..." : "RUN HUNT"}
            </button>
          </div>

          {message && <p className="muted">{message}</p>}

          <div className="result-list">
            {results.map((result) => (
              <article className="hunter-result" key={result.result_id}>
                <div className="score-circle">{result.score}</div>

                {result.image_url && (
                  <div className="hunter-thumb">
                    <img src={result.image_url} alt="" />
                  </div>
                )}

                <div>
                  <div className="result-badges">
                    <span className="badge">{(result.source || "market").toUpperCase()}</span>
                    {result.on_wantlist && <span className="badge green-border">WANTLIST</span>}
                    {result.owned && <span className="badge">OWNED</span>}
                    {!result.owned && result.source === "discogs" && (
                      <span className="badge green-border">NOT OWNED</span>
                    )}
                  </div>

                  <div className="record-title">{result.title}</div>

                  <div className="record-meta">
                    {result.condition || "Marketplace floor"} · {result.seller || "Marketplace"}
                    {result.num_for_sale != null ? ` · ${result.num_for_sale} for sale` : ""}
                  </div>

                  {result.estimated_value_low != null &&
                    result.estimated_value_high != null && (
                      <div className="record-meta">
                        Estimated value ${result.estimated_value_low.toFixed(0)}–
                        ${result.estimated_value_high.toFixed(0)}
                      </div>
                    )}

                  {result.match_confidence != null && result.match_confidence > 0 && (
                    <div className="record-meta">
                      Pressing match confidence: {result.match_confidence}%
                    </div>
                  )}

                  {result.explanation && (
                    <div className="record-meta">{result.explanation}</div>
                  )}
                </div>

                <div className="result-price">
                  <strong>${result.price.toFixed(0)}</strong>
                  {result.shipping != null ? (
                    <small>+ ${result.shipping.toFixed(0)} ship</small>
                  ) : (
                    <small>lowest current price</small>
                  )}
                  <span className={result.score >= 80 ? "green" : "gold"}>
                    {result.deal_label}
                  </span>
                  <a className="btn" href={result.url} target="_blank" rel="noreferrer">
                    VIEW MARKET
                  </a>
                </div>
              </article>
            ))}

            {selectedHuntId && !results.length && (
              <div className="empty-result">
                <h3>Ready to hunt.</h3>
                <p className="muted">
                  Run this Hunt to score current demo opportunities through the full Hunter pipeline.
                </p>
              </div>
            )}
          </div>
        </div>
      </section>
    </>
  );
}
