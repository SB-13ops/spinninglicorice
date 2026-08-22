"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost, apiSend } from "../lib/api";
import BarcodeScanner from "./BarcodeScanner";

type Item = {
  collection_item_id: string;
  title: string;
  artists: string[];
  year: number | null;
  country: string | null;
  catalog_number: string | null;
  label: string | null;
  pressing: string | null;
  image_url: string | null;
  media_condition: string | null;
  sleeve_condition: string | null;
  purchase_price: number | null;
  personal_rating: number | null;
  personal_notes: string | null;
  source: string;
};

type DiscogsHit = {
  discogs_id: number;
  title: string;
  year: number | null;
  country: string | null;
  label: string | null;
  catno: string | null;
  thumb: string | null;
};

const CONDITIONS = [
  "Mint (M)", "Near Mint (NM or M-)", "Very Good Plus (VG+)", "Very Good (VG)",
  "Good Plus (G+)", "Good (G)", "Fair (F)", "Poor (P)",
];

function Stars({ value, onRate }: { value: number | null; onRate?: (n: number) => void }) {
  return (
    <div className="stars">
      {[1, 2, 3, 4, 5].map((n) => (
        <span
          key={n}
          className={`star ${value && n <= value ? "on" : ""} ${onRate ? "clickable" : ""}`}
          onClick={onRate ? () => onRate(n) : undefined}
          role={onRate ? "button" : undefined}
          title={onRate ? `Rate ${n}` : undefined}
        >
          ★
        </span>
      ))}
    </div>
  );
}

export default function CollectionLive() {
  const [items, setItems] = useState<Item[]>([]);
  const [summary, setSummary] = useState<any>({ records: 0, years: [], countries: [] });
  const [error, setError] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [tab, setTab] = useState<"manual" | "discogs" | "scan">("manual");
  const [editing, setEditing] = useState<string | null>(null);

  async function load() {
    try {
      const data = await apiGet<{ items: Item[]; summary: any }>("/collection");
      setItems(data.items || []);
      setSummary(data.summary || {});
    } catch {
      setError("Could not load collection. Start the backend and sign in.");
    }
  }
  useEffect(() => {
    load();
  }, []);

  async function rate(id: string, n: number) {
    try {
      await apiSend("PATCH", `/collection/${id}`, { personal_rating: n });
      setItems((prev) => prev.map((it) => (it.collection_item_id === id ? { ...it, personal_rating: n } : it)));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>Collection</h1>
        <p>Your records. Your story.</p>
      </div>

      <div className="cards" style={{ marginBottom: 16 }}>
        <div className="card metric"><span className="metric-value">{summary.records || 0}</span><span className="metric-label">RECORDS</span></div>
        <div className="card metric"><span className="metric-value">{summary.years?.length || 0}</span><span className="metric-label">RELEASE YEARS</span></div>
        <div className="card metric"><span className="metric-value">{summary.countries?.length || 0}</span><span className="metric-label">COUNTRIES</span></div>
      </div>

      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 14 }}>
        <button className="btn greenbtn" onClick={() => setShowAdd((s) => !s)}>
          {showAdd ? "CLOSE" : "+ ADD RECORD"}
        </button>
      </div>

      {showAdd && (
        <div className="card form-card" style={{ marginBottom: 16 }}>
          <div className="tabs">
            <button className={tab === "manual" ? "tab active" : "tab"} onClick={() => setTab("manual")}>Type it in</button>
            <button className={tab === "discogs" ? "tab active" : "tab"} onClick={() => setTab("discogs")}>Search Discogs</button>
            <button className={tab === "scan" ? "tab active" : "tab"} onClick={() => setTab("scan")}>Scan barcode</button>
          </div>
          {tab === "manual" && <ManualForm onAdded={() => { setShowAdd(false); load(); }} onError={setError} />}
          {tab === "discogs" && <DiscogsSearch onAdded={() => { setShowAdd(false); load(); }} onError={setError} />}
          {tab === "scan" && <BarcodeScanner onAdded={() => { setShowAdd(false); load(); }} onError={setError} />}
        </div>
      )}

      {error && <div className="status error">{error}</div>}

      <div className="grid">
        {items.map((item) => (
          <article className="card record" key={item.collection_item_id}>
            {item.image_url ? (
              <img src={item.image_url} alt={item.title} />
            ) : (
              <div style={{ aspectRatio: "1", display: "grid", placeItems: "center", background: "#0e0c09" }}>BURNT JACKET</div>
            )}
            <div className="record-body">
              <div className="record-title">{item.title}</div>
              <div className="meta">{item.artists?.join(", ") || "Unknown artist"}</div>
              <div className="meta">{[item.year, item.country, item.label].filter(Boolean).join(" · ")}</div>

              <div className="rating-row">
                <Stars value={item.personal_rating} onRate={(n) => rate(item.collection_item_id, n)} />
                <button className="link-btn" onClick={() => setEditing(editing === item.collection_item_id ? null : item.collection_item_id)}>
                  {editing === item.collection_item_id ? "cancel" : "edit"}
                </button>
              </div>

              {editing === item.collection_item_id ? (
                <EditForm
                  item={item}
                  onSaved={(updated) => {
                    setItems((prev) => prev.map((it) => (it.collection_item_id === updated.collection_item_id ? { ...it, ...updated } : it)));
                    setEditing(null);
                  }}
                  onError={setError}
                />
              ) : (
                <>
                  {item.personal_notes && <div className="notes">{item.personal_notes}</div>}
                  <div className="badges">
                    {item.media_condition && <span className="badge good">{item.media_condition}</span>}
                    {item.purchase_price != null && <span className="badge">${item.purchase_price.toFixed(0)}</span>}
                    <span className="badge">{item.source.toUpperCase()}</span>
                  </div>
                </>
              )}
            </div>
          </article>
        ))}
      </div>

      {!items.length && !error && (
        <div className="empty card">No records yet — add one by hand or search Discogs above, or connect Discogs and sync.</div>
      )}
    </>
  );
}

function ManualForm({ onAdded, onError }: { onAdded: () => void; onError: (s: string) => void }) {
  const [f, setF] = useState<any>({ title: "", artist_name: "", year: "", label_name: "", media_condition: "", purchase_price: "", personal_rating: 0, personal_notes: "", target: "collection", max_price: "" });
  const [busy, setBusy] = useState(false);
  const set = (k: string, v: any) => setF((p: any) => ({ ...p, [k]: v }));
  const wantlist = f.target === "wantlist";

  async function submit() {
    if (!f.title.trim()) { onError("Title is required."); return; }
    setBusy(true);
    try {
      const body: any = { title: f.title.trim(), target: f.target };
      if (f.artist_name.trim()) body.artist_name = f.artist_name.trim();
      if (f.year) body.year = parseInt(f.year);
      if (f.label_name.trim()) body.label_name = f.label_name.trim();
      if (f.media_condition) body.media_condition = f.media_condition;
      if (wantlist) {
        if (f.max_price) body.max_price = parseFloat(f.max_price);
      } else {
        if (f.purchase_price) body.purchase_price = parseFloat(f.purchase_price);
        if (f.personal_rating) body.personal_rating = f.personal_rating;
        if (f.personal_notes.trim()) body.personal_notes = f.personal_notes.trim();
      }
      await apiPost("/collection", body);
      onAdded();
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="add-form">
      <TargetToggle value={f.target} onChange={(t) => set("target", t)} />
      <input placeholder="Title *" value={f.title} onChange={(e) => set("title", e.target.value)} />
      <input placeholder="Artist" value={f.artist_name} onChange={(e) => set("artist_name", e.target.value)} />
      <div className="add-row">
        <input placeholder="Year" value={f.year} onChange={(e) => set("year", e.target.value)} style={{ width: 90 }} />
        <input placeholder="Label" value={f.label_name} onChange={(e) => set("label_name", e.target.value)} />
      </div>
      <div className="add-row">
        <select value={f.media_condition} onChange={(e) => set("media_condition", e.target.value)}>
          <option value="">{wantlist ? "Min condition…" : "Condition…"}</option>
          {CONDITIONS.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        {wantlist ? (
          <input placeholder="Max $ you'd pay" value={f.max_price} onChange={(e) => set("max_price", e.target.value)} style={{ width: 130 }} />
        ) : (
          <input placeholder="Paid $" value={f.purchase_price} onChange={(e) => set("purchase_price", e.target.value)} style={{ width: 100 }} />
        )}
      </div>
      {!wantlist && (
        <>
          <div className="add-row" style={{ alignItems: "center", gap: 10 }}>
            <span className="muted small">Rating:</span>
            <Stars value={f.personal_rating || null} onRate={(n) => set("personal_rating", n)} />
          </div>
          <textarea placeholder="Notes" value={f.personal_notes} onChange={(e) => set("personal_notes", e.target.value)} />
        </>
      )}
      <button className="btn greenbtn" onClick={submit} disabled={busy}>
        {busy ? "ADDING…" : wantlist ? "ADD TO WANTLIST" : "ADD TO COLLECTION"}
      </button>
    </div>
  );
}

function TargetToggle({ value, onChange }: { value: string; onChange: (t: string) => void }) {
  return (
    <div className="target-toggle">
      <button className={value === "collection" ? "tgl active" : "tgl"} onClick={() => onChange("collection")} type="button">
        In my collection
      </button>
      <button className={value === "wantlist" ? "tgl active" : "tgl"} onClick={() => onChange("wantlist")} type="button">
        On my wantlist
      </button>
    </div>
  );
}

function DiscogsSearch({ onAdded, onError }: { onAdded: () => void; onError: (s: string) => void }) {
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<DiscogsHit[]>([]);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");
  const [target, setTarget] = useState("collection");

  async function search() {
    setBusy(true);
    setNote("");
    try {
      const r = await apiGet<{ results: DiscogsHit[] }>(`/collection/search?q=${encodeURIComponent(q)}`);
      setHits(r.results);
      if (!r.results.length) setNote("No matches.");
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function add(hit: DiscogsHit) {
    try {
      await apiPost("/collection/from-discogs", { discogs_release_id: hit.discogs_id, target });
      onAdded();
    } catch (e) {
      onError((e as Error).message);
    }
  }

  return (
    <div className="add-form">
      <TargetToggle value={target} onChange={setTarget} />
      <div className="add-row">
        <input placeholder="Search Discogs (artist, album)…" value={q} onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && q.trim() && search()} style={{ flex: 1 }} />
        <button className="btn light" onClick={search} disabled={busy || !q.trim()}>{busy ? "…" : "SEARCH"}</button>
      </div>
      <div className="muted small">Requires a connected Discogs account. Adding to: <strong>{target === "wantlist" ? "wantlist" : "collection"}</strong>.</div>
      {note && <div className="muted small">{note}</div>}
      <div className="hit-list">
        {hits.map((hit) => (
          <div className="hit" key={hit.discogs_id}>
            {hit.thumb && <img src={hit.thumb} alt="" />}
            <div className="hit-body">
              <div>{hit.title}</div>
              <div className="muted small">{[hit.year, hit.country, hit.label, hit.catno].filter(Boolean).join(" · ")}</div>
            </div>
            <button className="btn-small" onClick={() => add(hit)}>ADD</button>
          </div>
        ))}
      </div>
    </div>
  );
}

function EditForm({ item, onSaved, onError }: { item: Item; onSaved: (u: Item) => void; onError: (s: string) => void }) {
  const [f, setF] = useState({
    media_condition: item.media_condition || "",
    purchase_price: item.purchase_price != null ? String(item.purchase_price) : "",
    personal_notes: item.personal_notes || "",
  });
  const [busy, setBusy] = useState(false);
  const set = (k: string, v: any) => setF((p) => ({ ...p, [k]: v }));

  async function save() {
    setBusy(true);
    try {
      const body: any = {
        media_condition: f.media_condition || null,
        purchase_price: f.purchase_price ? parseFloat(f.purchase_price) : null,
        personal_notes: f.personal_notes || null,
      };
      const res = await apiSend<any>("PATCH", `/collection/${item.collection_item_id}`, body);
      onSaved({ ...item, ...(res || {}), collection_item_id: item.collection_item_id });
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="add-form">
      <select value={f.media_condition} onChange={(e) => set("media_condition", e.target.value)}>
        <option value="">Condition…</option>
        {CONDITIONS.map((c) => <option key={c} value={c}>{c}</option>)}
      </select>
      <input placeholder="Paid $" value={f.purchase_price} onChange={(e) => set("purchase_price", e.target.value)} />
      <textarea placeholder="Notes" value={f.personal_notes} onChange={(e) => set("personal_notes", e.target.value)} />
      <button className="btn greenbtn" onClick={save} disabled={busy}>{busy ? "SAVING…" : "SAVE"}</button>
    </div>
  );
}
