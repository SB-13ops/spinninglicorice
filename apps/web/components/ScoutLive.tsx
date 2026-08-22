"use client";

import { useEffect, useState } from "react";
import { API_BASE, apiGet, apiPost } from "../lib/api";
import TripPlanner from "./TripPlanner";

type Item = {
  recommendation_id:string;
  event_id:string; name:string; venue:string|null; city:string|null; region:string|null;
  starts_at:string; ticket_url:string|null; ticket_link?:{url:string;provider:string;affiliate:boolean}; match_score:number; match_label?:string; reason:string|null;
};

export default function ScoutLive(){
  const [items,setItems]=useState<Item[]>([]);
  const [message,setMessage]=useState("");
  const [busy,setBusy]=useState(false);

  async function load(){
    const d=await apiGet<{items:Item[]}>("/scout/recommendations");setItems(d.items||[]);
  }

  useEffect(()=>{load().catch(()=>setMessage("Backend is not running."));},[]);

  async function refresh(){
    setBusy(true);setMessage("");
    try{
      const d=await apiPost<{items:Item[];count:number}>("/scout/refresh");setItems(d.items||[]);
      setMessage(`Scout found ${d.count||0} matching events.`);
    }catch(e:any){setMessage(e.message||"Scout refresh failed.");}
    finally{setBusy(false);}
  }

  return (
    <>
      <div className="page-header">
        <h1>Scout</h1>
        <p>Live music selected from your collection and Music DNA.</p>
      </div>

      <div style={{display:"flex",justifyContent:"flex-end",marginBottom:14}}>
        <button className="btn light" onClick={refresh} disabled={busy}>
          {busy?"SCOUTING...":"REFRESH SCOUT"}
        </button>
      </div>

      {message && <div className="status">{message}</div>}

      <div className="scout-grid">
        {items.map(item=>(
          <article className="card form-card" key={item.event_id}>
            <div className="bigscore">{item.match_score}%</div>
            <div className="green">{item.match_label||"SCOUT MATCH"}</div>
            <h2>{item.name}</h2>
            <div className="meta">{[item.venue,item.city,item.region].filter(Boolean).join(" · ")}</div>
            <div className="meta">{new Date(item.starts_at).toLocaleString()}</div>
            <p>{item.reason}</p>
            {(item.ticket_link?.url || item.ticket_url) && (
              <a className="btn greenbtn"
                 href={item.ticket_link?.url || item.ticket_url || "#"}
                 target="_blank" rel="noreferrer nofollow sponsored">
                TICKETS / DETAILS
              </a>
            )}
            <TripPlanner recommendationId={item.recommendation_id} />
          </article>
        ))}
      </div>

      {!items.length && <div className="empty card">Add location preferences and configure Ticketmaster, then refresh Scout.</div>}
    </>
  );
}
