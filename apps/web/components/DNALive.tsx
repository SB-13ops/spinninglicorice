"use client";

import { useEffect, useState } from "react";
import { API_BASE } from "../lib/api";

export default function DNALive(){
  const [data,setData]=useState<any>(null);
  const [message,setMessage]=useState("");

  async function load(){
    const r=await fetch(`${API_BASE}/dna`,{cache:"no-store"});
    const d=await r.json();setData(d);
  }
  useEffect(()=>{load().catch(()=>setMessage("Backend is not running."));},[]);

  async function rebuild(){
    setMessage("Rebuilding Collector DNA...");
    try{
      const r=await fetch(`${API_BASE}/dna/rebuild`,{method:"POST"});
      const d=await r.json();setData(d);setMessage("Collector DNA rebuilt.");
    }catch{setMessage("DNA rebuild failed.");}
  }

  const top=data?.music_dna?.top_artists||[];
  const yr=data?.music_dna?.year_span||{};
  const pr=data?.collector_dna?.typical_price_range||{};

  return (
    <>
      <div className="page-header">
        <h1>Collector DNA</h1>
        <p>What your collection says about your music and how you collect.</p>
      </div>

      <button className="btn light" onClick={rebuild}>REBUILD DNA</button>
      {message && <div className="status">{message}</div>}

      <div className="cards" style={{marginTop:16}}>
        <div className="card metric"><span className="metric-value">{data?.record_count||0}</span><span className="metric-label">RECORDS ANALYZED</span></div>
        <div className="card metric"><span className="metric-value">{yr.start&&yr.end?`${yr.start}–${yr.end}`:"—"}</span><span className="metric-label">ERA</span></div>
        <div className="card metric"><span className="metric-value">{pr.low!=null&&pr.high!=null?`$${pr.low}–$${pr.high}`:"—"}</span><span className="metric-label">BUY RANGE</span></div>
        <div className="card metric"><span className="metric-value">{data?.collector_dna?.preferred_condition||"—"}</span><span className="metric-label">CONDITION</span></div>
      </div>

      <div className="primary">
        <div className="card form-card">
          <div className="gold">MUSIC DNA</div>
          <h2>Top artist signals</h2>
          {top.map((a:any,i:number)=><div key={i} className="dna-row"><b>{i+1}. {a.name}</b>{a.count||""}</div>)}
        </div>
        <div className="card form-card">
          <div className="green">COLLECTOR DNA</div>
          <h2>How you collect</h2>
          <div className="dna-row"><b>Condition</b>{data?.collector_dna?.preferred_condition||"Learning..."}</div>
          <div className="dna-row"><b>Price behavior</b>{pr.low!=null&&pr.high!=null?`$${pr.low}–$${pr.high}`:"Learning..."}</div>
        </div>
      </div>
    </>
  );
}
