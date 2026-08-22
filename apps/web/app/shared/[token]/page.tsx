"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { API_BASE } from "../../../lib/api";

type CollectionResp = {
  items: Array<{
    collection_item_id: string;
    title: string;
    artists: string[];
    year: number | null;
    label: string | null;
  }>;
  summary: { records: number };
};

export default function SharedViewPage() {
  const params = useParams();
  const token = String(params.token || "");
  const [data, setData] = useState<CollectionResp | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/public/${token}/collection`, { cache: "no-store" })
      .then((r) => {
        if (!r.ok) throw new Error("This shared link is not available.");
        return r.json();
      })
      .then(setData)
      .catch((e) => setError((e as Error).message));
  }, [token]);

  if (error) {
    return (
      <div className="auth-wrap">
        <div className="auth-card">
          <div className="auth-logo">BURNT JACKET</div>
          <div className="auth-error">{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="shared-view">
      <div className="shared-header">
        <div className="auth-logo">BURNT JACKET</div>
        <span className="pill">Shared collection · read-only</span>
      </div>
      {!data ? (
        <p>Loading…</p>
      ) : (
        <>
          <p className="share-sub">{data.summary.records} records</p>
          <table className="shared-table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Artist</th>
                <th>Year</th>
                <th>Label</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((it) => (
                <tr key={it.collection_item_id}>
                  <td>{it.title}</td>
                  <td>{it.artists.join(", ")}</td>
                  <td>{it.year ?? "—"}</td>
                  <td>{it.label ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
