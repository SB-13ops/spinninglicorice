"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "../lib/api";
import HomeFeatureCard from "./HomeFeatureCard";

export default function ProfileLive(){
  const [status,setStatus]=useState<any>(null);
  const [message,setMessage]=useState("");

  async function load(){
    const r=await fetch(`${API_BASE}/integrations/discogs/status`,{cache:"no-store"});
    const d=await r.json();setStatus(d);
  }
  useEffect(()=>{load().catch(()=>setMessage("Backend is not running."));},[]);

  async function connect(){
    setMessage("Starting Discogs connection...");
    try{
      const r=await fetch(`${API_BASE}/integrations/discogs/connect`);
      const d=await r.json();
      if(d.authorization_url) window.location.href=d.authorization_url;
      else setMessage("Discogs OAuth is not configured yet.");
    }catch{setMessage("Could not start Discogs connection.");}
  }

  async function sync(){
    setMessage("Syncing Discogs...");
    try{
      const r=await fetch(`${API_BASE}/integrations/discogs/sync`,{method:"POST"});
      const d=await r.json();
      setMessage(`Sync complete. ${JSON.stringify(d.stats||{})}`);
      load();
    }catch{setMessage("Discogs sync failed.");}
  }

  return (
    <>
      <div className="page-header">
        <h1>Profile</h1>
        <p>Preferences and connected accounts.</p>
      </div>

      {message && <div className="status">{message}</div>}

      <div style={{ marginBottom: 16 }}>
        <HomeFeatureCard />
      </div>

      <div className="primary">
        <section className="card form-card">
          <div className="gold">PREFERENCES</div>
          <h2>Collector settings</h2>
          <input className="field" placeholder="Location / ZIP" />
          <input className="field" placeholder="Radius miles" />
          <input className="field" placeholder="Typical max price" />
          <input className="field" placeholder="Preferred condition" />
          <div className="muted" style={{fontSize:12,marginTop:8}}>
            Preference saving will be wired next.
          </div>
        </section>

        <section className="card form-card">
          <div className="green">CONNECTED ACCOUNTS</div>
          <h2>Discogs</h2>
          <p className="muted">
            {status?.connected
              ? `Connected as ${status.username || "Discogs user"}`
              : "Not connected"}
          </p>
          {!status?.connected ? (
            <button className="btn light" onClick={connect}>CONNECT DISCOGS</button>
          ) : (
            <button className="btn light" onClick={sync}>SYNC NOW</button>
          )}
          {status?.last_synced_at && <div className="meta">Last sync: {status.last_synced_at}</div>}
        </section>
      </div>
    </>
  );
}
