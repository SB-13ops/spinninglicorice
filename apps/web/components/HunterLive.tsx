"use client";

import { useEffect, useMemo, useState } from "react";
import { API_BASE } from "../lib/api";

type Hunt = {
  id: string; name: string; query: string; auto_hunt: boolean; active: boolean; criteria: any;
};
type Result = {
  result_id: string; title: string; price: number; shipping: number | null; condition: string | null;
  source?: string; estimated_value_low?: number | null; estimated_value_high?: number | null;
  num_for_sale?: number | null; owned?: boolean; on_wantlist?: boolean; match_confidence?: number | null;
  image_url?: string | null; score: number; deal_label: string; explanation: string | null; seller: string | null; url: string;
};

export default function HunterLive(){
  const [hunts,setHunts]=useState<Hunt[]>([]);
  const [selected,setSelected]=useState<string | null>(null);
  const [results,setResults]=useState<Result[]>([]);
  const [name,setName]=useState("Grateful Dead under $50");
  const [query,setQuery]=useState("Grateful Dead records I don't own under $50 VG+");
  const [auto,setAuto]=useState(true);
  const [message,setMessage]=useState("");
  const [busy,setBusy]=useState(false);

  const selectedHunt=useMemo(()=>hunts.find(h=>h.id===selected),[hunts,selected]);

  async function loadHunts(){
    const r=await fetch(`${API_BASE}/hunter/hunts`,{cache:"no-store"});
    const d=await r.json();
    setHunts(d.items||[]);
    if(!selected && d.items?.length) setSelected(d.items[0].id);
  }

  async function loadResults(id:string){
    const r=await fetch(`${API_BASE}/hunter/hunts/${id}/results`,{cache:"no-store"});
    const d=await r.json();
    setResults(d.items||[]);
  }

  useEffect(()=>{loadHunts().catch(()=>setMessage("Backend is not running."));},[]);
  useEffect(()=>{if(selected) loadResults(selected).catch(()=>{});},[selected]);

  async function createHunt(){
    setBusy(true);setMessage("");
    try{
      const r=await fetch(`${API_BASE}/hunter/hunts`,{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({name,query,auto_hunt:auto})
      });
      if(!r.ok) throw new Error(await r.text());
      const h=await r.json();
      await loadHunts(); setSelected(h.id); setMessage("Hunt created.");
    }catch(e:any){setMessage(e.message||"Could not create Hunt.");}
    finally{setBusy(false);}
  }

  async function runHunt(){
    if(!selected) return;
    setBusy(true);setMessage("");
    try{
      const r=await fetch(`${API_BASE}/hunter/hunts/${selected}/refresh`,{method:"POST"});
      if(!r.ok) throw new Error(await r.text());
      const d=await r.json();
      setResults(d.results||[]);
      setMessage(`Hunter found ${(d.results||[]).length} opportunities using ${d.provider||"market"} data.`);
    }catch(e:any){setMessage(e.message||"Hunter failed.");}
    finally{setBusy(false);}
  }

  return (
    <>
      <div className="page-header">
        <h1>Hunter</h1>
        <p>Tell Burnt Jacket what you want. We'll score the opportunities.</p>
      </div>

      <div className="card form-card">
        <div className="orange">🔥 WHAT ARE YOU HUNTING?</div>
        <input className="field" value={name} onChange={e=>setName(e.target.value)} />
        <textarea className="field" value={query} onChange={e=>setQuery(e.target.value)} />
        <label className="muted">
          <input type="checkbox" checked={auto} onChange={e=>setAuto(e.target.checked)} /> Auto Hunt
        </label>
        <div style={{marginTop:10}}>
          <button className="btn light" onClick={createHunt} disabled={busy}>CREATE HUNT</button>
        </div>
      </div>

      {message && <div className="status">{message}</div>}

      <div className="hunter-layout">
        <aside className="card form-card">
          <div className="gold">MY HUNTS</div>
          {hunts.map(h=>(
            <div key={h.id} onClick={()=>setSelected(h.id)} className={`hunt-row ${selected===h.id?"active":""}`}>
              <b>{h.name}</b>
              <div className="meta">{h.query}</div>
              {h.auto_hunt && <div className="green" style={{fontSize:10,marginTop:5}}>AUTO HUNT</div>}
            </div>
          ))}
        </aside>

        <section className="card form-card">
          <div style={{display:"flex",justifyContent:"space-between",gap:12,alignItems:"center"}}>
            <div>
              <div className="orange">HUNTER FOUND</div>
              <h2>{selectedHunt?.name || "Select a Hunt"}</h2>
            </div>
            <button className="btn light" onClick={runHunt} disabled={!selected||busy}>
              {busy?"HUNTING...":"RUN HUNT"}
            </button>
          </div>

          {results.map(r=>(
            <article className="result-row" key={r.result_id}>
              <div className="result-score">{r.score}</div>
              {r.image_url ? <img className="result-thumb" src={r.image_url} alt="" /> :
                <div className="result-thumb" style={{display:"grid",placeItems:"center"}}>DW</div>}
              <div>
                <div className="badges">
                  <span className="badge">{(r.source||"market").toUpperCase()}</span>
                  {r.on_wantlist && <span className="badge good">WANTLIST</span>}
                  {r.owned && <span className="badge">OWNED</span>}
                  {!r.owned && r.source==="discogs" && <span className="badge good">NOT OWNED</span>}
                </div>
                <div className="record-title">{r.title}</div>
                <div className="meta">{r.explanation}</div>
                {r.match_confidence!=null && <div className="meta">Pressing match: {r.match_confidence}%</div>}
              </div>
              <div className="result-price">
                <div style={{fontSize:23,fontWeight:800}}>${r.price.toFixed(0)}</div>
                <div className={r.score>=80?"green":"gold"}>{r.deal_label}</div>
                <a className="btn" href={r.url} target="_blank">VIEW MARKET</a>
              </div>
            </article>
          ))}

          {!results.length && <div className="empty">Run the selected Hunt to load current results.</div>}
        </section>
      </div>
    </>
  );
}
