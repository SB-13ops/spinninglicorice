"use client";

import { useEffect, useState, useCallback } from "react";
import { apiGet, apiPost } from "../lib/api";

type Group = {
  id: string;
  name: string;
  description: string | null;
  role: string;
  member_count: number;
};

export default function GroupsList() {
  const [groups, setGroups] = useState<Group[]>([]);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [desc, setDesc] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    apiGet<Group[]>("/groups").then(setGroups).catch((e) => setError((e as Error).message));
  }, []);
  useEffect(() => load(), [load]);

  async function create() {
    if (!name.trim()) return;
    try {
      const g = await apiPost<Group>("/groups", { name, description: desc || null });
      window.location.href = `/groups/${g.id}`;
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <div className="share-page">
      <div className="share-head-row">
        <div>
          <h1 className="share-title">Friend Groups</h1>
          <p className="share-sub">Trade records, swap, and chat with your crew.</p>
        </div>
        <button className="btn-gold" onClick={() => setCreating((v) => !v)}>
          {creating ? "Cancel" : "New group"}
        </button>
      </div>

      {error && <div className="auth-error">{error}</div>}

      {creating && (
        <div className="share-card">
          <h2>Create a group</h2>
          <input
            className="picker-search"
            placeholder="Group name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <input
            className="picker-search"
            placeholder="Description (optional)"
            value={desc}
            onChange={(e) => setDesc(e.target.value)}
          />
          <button className="btn-gold" onClick={create}>
            Create group
          </button>
        </div>
      )}

      {groups.length === 0 ? (
        <p className="share-hint">You&apos;re not in any groups yet. Create one or accept an invite link.</p>
      ) : (
        <div className="group-grid">
          {groups.map((g) => (
            <a key={g.id} className="group-card" href={`/groups/${g.id}`}>
              <div className="group-card-name">{g.name}</div>
              {g.description && <div className="group-card-desc">{g.description}</div>}
              <div className="group-card-meta">
                <span className="pill">{g.role}</span>
                <span>{g.member_count} member{g.member_count === 1 ? "" : "s"}</span>
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
