"use client";

import { useEffect, useState } from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

type ScoutItem = {
  recommendation_id?: string;
  event_id: string;
  name: string;
  venue: string | null;
  city: string | null;
  region: string | null;
  starts_at: string;
  ticket_url: string | null;
  match_score: number;
  match_label?: string;
  reason: string | null;
  matched_artist?: string;
  genre?: string | null;
};

export default function ScoutClient() {
  const [items, setItems] = useState<ScoutItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function load() {
    const r = await fetch(`${API_BASE}/scout/recommendations`, { cache: "no-store" });
    const data = await r.json();
    setItems(data.items || []);
  }

  useEffect(() => {
    load().catch(() => setMessage("Start the Burnt Jacket API to use Scout."));
  }, []);

  async function refresh() {
    setBusy(true);
    setMessage("");
    try {
      const r = await fetch(`${API_BASE}/scout/refresh`, { method: "POST" });
      const data = await r.json();
      setItems(data.items || []);
      setMessage(
        data.count
          ? `Scout found ${data.count} events matched to your collection.`
          : "No Scout matches yet. Add a location and rebuild Collector DNA."
      );
    } catch {
      setMessage("Scout refresh failed. Check your Ticketmaster API key and API connection.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="scout-toolbar">
        <div>
          <div className="gold">LIVE MUSIC INTELLIGENCE</div>
          <p className="muted">
            Scout uses your strongest artist signals to find nearby shows.
          </p>
        </div>
        <button className="btn primary" onClick={refresh} disabled={busy}>
          {busy ? "SCOUTING..." : "REFRESH SCOUT"}
        </button>
      </div>

      {message && <p className="muted">{message}</p>}

      <div className="scout-grid">
        {items.map((item) => (
          <article className="card scout-card" key={item.event_id}>
            <div className="scout-score">{item.match_score}%</div>
            <div className="green">{item.match_label || "SCOUT MATCH"}</div>
            <h2>{item.name}</h2>
            <p className="muted">
              {[item.venue, item.city, item.region].filter(Boolean).join(" · ")}
            </p>
            <p className="record-meta">{new Date(item.starts_at).toLocaleString()}</p>
            {item.reason && <p>{item.reason}</p>}
            {item.genre && <span className="badge">{item.genre}</span>}
            {item.ticket_url && (
              <div style={{ marginTop: 14 }}>
                <a className="btn primary" href={item.ticket_url} target="_blank" rel="noreferrer">
                  TICKETS / DETAILS
                </a>
              </div>
            )}
          </article>
        ))}
      </div>

      {!items.length && (
        <div className="card empty-state">
          <div className="gold">CONCERT SCOUT</div>
          <h2>Burnt Jacket is ready to scout.</h2>
          <p className="muted">
            Add your location in Profile, configure a Ticketmaster API key, and refresh Scout.
          </p>
        </div>
      )}
    </>
  );
}
