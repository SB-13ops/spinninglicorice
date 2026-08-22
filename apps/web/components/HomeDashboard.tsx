"use client";

import { useEffect, useState } from "react";
import { API_BASE, apiGet } from "../lib/api";
import HomeHero, { Hero } from "./HomeHero";
import { useAuth } from "../lib/auth";

type Pick = {
  title: string;
  price: number;
  score: number;
  deal_label: string;
  explanation: string | null;
  image_url?: string | null;
  url: string;
  owned?: boolean;
  on_wantlist?: boolean;
};

type Feed = {
  hero: Hero;
  collection_snapshot: { records: number; wantlist: number; ai_picks: number };
  spinninglicorice_pick: Pick | null;
  hunter_found: Pick[];
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

const fallbackImg = "data:image/svg+xml;charset=UTF-8," + encodeURIComponent(
  `<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400">
   <rect width="100%" height="100%" fill="#11100d"/>
   <circle cx="200" cy="200" r="120" fill="#2b2117"/>
   <circle cx="200" cy="200" r="38" fill="#c89145"/>
   <text x="200" y="365" text-anchor="middle" fill="#eee0c2" font-size="30" font-family="Georgia">SPINNINGLICORICE</text>
   </svg>`
);

export default function HomeDashboard() {
  const [feed, setFeed] = useState<Feed | null>(null);
  const [hero, setHero] = useState<Hero | null>(null);
  const [error, setError] = useState("");
  const { activeAccountId } = useAuth();
  // You can edit the hero on your own account. On a shared account, the API
  // enforces admin/owner anyway (a viewer's PUT returns 403), so we allow the
  // button on your own account and let the server be the source of truth.
  const editable = activeAccountId === "";

  useEffect(() => {
    apiGet<Feed>("/home/feed")
      .then((f) => {
        setFeed(f);
        setHero(f.hero);
      })
      .catch(() => setError("SpinningLicorice backend is not running yet."));
  }, []);

  if (error) {
    return (
      <div>
        <div className="greeting">
          <h1>Good evening.</h1>
          <p>SpinningLicorice is ready — start the backend to load live data.</p>
        </div>
        <div className="status error">{error}</div>
      </div>
    );
  }

  if (!feed) {
    return <div className="status">Loading your SpinningLicorice feed...</div>;
  }

  const pick = feed.spinninglicorice_pick;
  const dna = feed.collector_dna || {};
  const topArtist = dna?.music_dna?.top_artists?.[0]?.name || "Learning...";
  const era = dna?.music_dna?.year_span;
  const eraText = era?.start && era?.end ? `${era.start} – ${era.end}` : "Learning...";
  const buyRange = dna?.collector_dna?.typical_price_range;
  const buyText =
    buyRange?.low != null && buyRange?.high != null
      ? `$${buyRange.low} – $${buyRange.high}`
      : "Learning...";

  return (
    <div className="right-grid">
      {hero && (
        <div className="hero-col">
          <HomeHero hero={hero} editable={editable} onChanged={setHero} />
        </div>
      )}
      <div>
        <div className="greeting">
          <h1>Good evening.</h1>
          <p>Here's what SpinningLicorice found for you.</p>
          <div className="quote">“The music never stops.”<br />– Jerry Garcia</div>
        </div>

        <div className="cards">
          <div className="card metric">
            <div className="metric-icon">◉</div>
            <span className="metric-value">{feed.collection_snapshot.records}</span>
            <span className="metric-label">RECORDS</span>
            <div className="metric-link"><a href="/collection">View collection →</a></div>
          </div>
          <div className="card metric">
            <div className="metric-icon green">$</div>
            <span className="metric-value">LIVE</span>
            <span className="metric-label">MARKET DATA</span>
            <div className="metric-link"><a href="/hunter">Open Hunter →</a></div>
          </div>
          <div className="card metric">
            <div className="metric-icon" style={{color:"#e85e62"}}>♥</div>
            <span className="metric-value">{feed.collection_snapshot.wantlist}</span>
            <span className="metric-label">WANTLIST</span>
            <div className="metric-link"><a href="/collection">View wantlist →</a></div>
          </div>
          <div className="card metric">
            <div className="metric-icon" style={{color:"#c69ae8"}}>✦</div>
            <span className="metric-value">{feed.collection_snapshot.ai_picks}</span>
            <span className="metric-label">AI PICKS</span>
            <div className="metric-link"><a href="/hunter">View recommendations →</a></div>
          </div>
        </div>

        <div className="primary">
          <section className="card">
            <div className="panel-title"><span className="orange">🔥</span> SPINNINGLICORICE PICK</div>
            {pick ? (
              <>
                <div className="pick">
                  <img className="pick-img" src={pick.image_url || fallbackImg} alt="" />
                  <div>
                    <div style={{fontSize:17}}>{pick.title.split("—")[0]?.trim() || "SpinningLicorice Pick"}</div>
                    <div className="album">{pick.title.split("—")[1]?.trim() || pick.title}</div>
                    <div className="muted" style={{fontSize:12,marginTop:7}}>
                      Exact pressing opportunity
                    </div>
                    <div className="match green">
                      ★ {pick.score}% MATCH <span className="deal">🔥 {pick.deal_label}</span>
                    </div>
                    <div className="prices">
                      <div>
                        <small className="muted">FOUND</small>
                        <div className="price green">${pick.price.toFixed(0)}</div>
                      </div>
                    </div>
                    <div className="why">
                      <b>Why SpinningLicorice picked this</b><br />
                      {pick.explanation || "Strong fit for your collection and current Hunt criteria."}
                    </div>
                  </div>
                </div>
                <div className="actions">
                  <a className="btn light" href={pick.url} target="_blank">VIEW MARKET</a>
                  <a className="btn" href="/hunter">♧ HUNT</a>
                </div>
              </>
            ) : (
              <div className="empty">
                Run a Hunt and your best current opportunity will appear here.
              </div>
            )}
          </section>

          <section className="card">
            <div className="panel-title">HUNTER FOUND <span style={{float:"right",fontSize:10,fontWeight:400}}><a href="/hunter">View all →</a></span></div>
            <div className="hcards">
              {feed.hunter_found.slice(0,3).map((x, i) => (
                <div className="hcard" key={i}>
                  <img src={x.image_url || fallbackImg} alt="" />
                  <h3>{x.title}</h3>
                  <p className="muted">{x.explanation || "Marketplace match"}</p>
                  <div className="hprice">${x.price.toFixed(0)}</div>
                  <div className="score">🔥 {x.score} &nbsp; {x.deal_label}</div>
                </div>
              ))}
              {!feed.hunter_found.length && (
                <div className="empty">Create and run Hunts to populate this section.</div>
              )}
            </div>
          </section>
        </div>

        <div className="bottom">
          <section className="card mini">
            <h3>RECENTLY ADDED</h3>
            <div className="muted" style={{fontSize:11,lineHeight:1.6}}>
              Your latest Discogs collection additions will appear here after sync.
            </div>
          </section>

          <section className="card mini">
            <h3>COLLECTION GAPS</h3>
            <div className="muted" style={{fontSize:11}}>Complete My Collection analysis is next.</div>
            <div className="gap"><span className="circle" />Artist discography gaps</div>
            <div className="gap"><span className="circle" />Important missing pressings</div>
            <a className="btn" href="/hunter">♧ HUNT THE GAPS</a>
          </section>

          <section className="card mini">
            <h3>YOUR COLLECTOR DNA</h3>
            <div className="dna-row"><b>▣ Era</b>{eraText}</div>
            <div className="dna-row"><b>⚯ Top Artist</b>{topArtist}</div>
            <div className="dna-row"><b>⌁ Buying Range</b>{buyText}</div>
            <div className="dna-row"><b>◯ Condition</b>{dna?.collector_dna?.preferred_condition || "Learning..."}</div>
          </section>

          <section className="card mini">
            <h3>BECAUSE YOU OWN...</h3>
            <div className="because muted">
              Personalized recommendation chains will populate from Collector DNA.
            </div>
          </section>
        </div>
      </div>

      <aside className="right-column">
        <section className="card scout-card">
          <div className="panel-title">CONCERT SCOUT <span style={{float:"right",fontSize:10,fontWeight:400}}><a href="/scout">View all →</a></span></div>
          {feed.concert_scout ? (
            <>
              <div className="scout-body">
                <div>
                  <div><span className="bigscore">{feed.concert_scout.match_score}%</span> <span className="green">MATCH</span></div>
                  <div className="show">{feed.concert_scout.name}</div>
                  <div className="event">
                    {feed.concert_scout.venue || "Venue"}<br />
                    {[feed.concert_scout.city, feed.concert_scout.region].filter(Boolean).join(", ")}<br />
                    {new Date(feed.concert_scout.starts_at).toLocaleString()}
                  </div>
                </div>
                <div className="scout-img" style={{display:"grid",placeItems:"center",color:"var(--muted)"}}>LIVE MUSIC</div>
              </div>
              <div style={{padding:"5px 15px",fontSize:12}}>Why you'll probably like them</div>
              <div className="tags">
                <span className="tag2">{feed.concert_scout.reason || "Collector DNA match"}</span>
              </div>
              <div className="scout-actions">
                <a className="btn" href="/scout">DETAILS</a>
                {feed.concert_scout.ticket_url && <a className="btn greenbtn" href={feed.concert_scout.ticket_url} target="_blank">TICKETS</a>}
              </div>
            </>
          ) : (
            <div className="empty">
              Set your location and refresh Scout to find nearby shows.
            </div>
          )}
        </section>

        <section className="card notes">
          <div className="panel-title">NOTIFICATIONS</div>
          {feed.notifications.map((n, i) => (
            <div className="note" key={i}>
              <div className="note-icon">{n.type === "scout_match" ? "♪" : "🔥"}</div>
              <div>
                <b>{n.title}</b>
                <p>{n.body}</p>
              </div>
              <div className="ago">NEW</div>
            </div>
          ))}
          {!feed.notifications.length && <div className="empty">No alerts yet.</div>}
        </section>
      </aside>
    </div>
  );
}
