"use client";

import { useEffect, useState } from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";

type HunterPick = {
  hunt_name: string;
  title: string;
  price: number;
  score: number;
  deal_label: string;
  explanation: string | null;
  image_url?: string | null;
  url: string;
  owned: boolean;
  on_wantlist: boolean;
};

type HomeFeed = {
  collection_snapshot: { records: number; wantlist: number; ai_picks: number };
  spinninglicorice_pick: HunterPick | null;
  hunter_found: HunterPick[];
  collector_dna: any;
  concert_scout: null | {
    name: string;
    venue: string | null;
    city: string | null;
    region: string | null;
    starts_at: string;
    ticket_url: string | null;
    match_score: number;
    reason: string | null;
  };
  notifications: Array<{ title: string; body: string; type: string }>;
};

export default function HomeLive() {
  const [feed, setFeed] = useState<HomeFeed | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/home/feed`, { cache: "no-store" })
      .then((r) => r.json())
      .then(setFeed)
      .catch(() => {});
  }, []);

  if (!feed) return <p className="muted">Loading SpinningLicorice...</p>;

  const pick = feed.spinninglicorice_pick;

  return (
    <>
      <section className="cards">
        <div className="card">
          <div className="metric">{feed.collection_snapshot.records}</div>
          <div className="muted">RECORDS</div>
        </div>
        <div className="card">
          <div className="metric">{feed.collection_snapshot.wantlist}</div>
          <div className="muted">WANTLIST</div>
        </div>
        <div className="card">
          <div className="metric">{feed.collection_snapshot.ai_picks}</div>
          <div className="muted">HUNTER PICKS</div>
        </div>
        <div className="card">
          <div className="metric">
            {feed.concert_scout ? `${feed.concert_scout.match_score}%` : "—"}
          </div>
          <div className="muted">TOP SCOUT MATCH</div>
        </div>
      </section>

      <section className="section-grid">
        <div className="card pick">
          <div className="orange">🔥 SPINNINGLICORICE PICK</div>
          {pick ? (
            <>
              <h2>{pick.title}</h2>
              <h3 className="green">{pick.score} · {pick.deal_label}</h3>
              <p>Current market: <strong>${pick.price.toFixed(0)}</strong></p>
              {pick.explanation && <p className="muted">{pick.explanation}</p>}
              <a className="btn primary" href={pick.url} target="_blank" rel="noreferrer">
                VIEW MARKET
              </a>
            </>
          ) : (
            <>
              <h2>No Hunter opportunity yet</h2>
              <p className="muted">Create and run a Hunt to populate this card.</p>
              <a className="green" href="/hunter">Open Hunter →</a>
            </>
          )}
        </div>

        <div className="card">
          <div className="gold">🎸 CONCERT SCOUT</div>
          {feed.concert_scout ? (
            <>
              <h2>{feed.concert_scout.name}</h2>
              <h3 className="green">{feed.concert_scout.match_score}% MATCH</h3>
              <p className="muted">
                {[feed.concert_scout.venue, feed.concert_scout.city, feed.concert_scout.region]
                  .filter(Boolean).join(" · ")}
              </p>
              {feed.concert_scout.reason && <p>{feed.concert_scout.reason}</p>}
              <a className="green" href="/scout">Open Scout →</a>
            </>
          ) : (
            <>
              <h2>Ready to discover live music</h2>
              <p className="muted">Refresh Scout after setting your location.</p>
              <a className="green" href="/scout">Open Scout →</a>
            </>
          )}
        </div>
      </section>

      {!!feed.notifications.length && (
        <section className="card" style={{ marginTop: 18 }}>
          <div className="gold">ALERTS</div>
          <div className="notification-list">
            {feed.notifications.map((n, i) => (
              <div className="notification-row" key={`${n.type}-${i}`}>
                <strong>{n.title}</strong>
                <span className="muted">{n.body}</span>
              </div>
            ))}
          </div>
        </section>
      )}
    </>
  );
}
