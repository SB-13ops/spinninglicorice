"use client";

import { useEffect, useState, useCallback } from "react";
import { apiGet, apiPost, apiSend } from "../lib/api";

type Invite = {
  id: string;
  role: string;
  token: string;
  invite_url: string;
  expires_at: string | null;
  max_uses: number | null;
  uses: number;
  revoked: boolean;
};
type Member = { member_id: string; email: string; display_name: string | null; role: string };
type PublicShare = { enabled: boolean; token: string | null; public_url: string | null };

export default function SharingManager() {
  const [members, setMembers] = useState<Member[]>([]);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [pub, setPub] = useState<PublicShare>({ enabled: false, token: null, public_url: null });
  const [role, setRole] = useState<"viewer" | "admin">("viewer");
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [m, i, p] = await Promise.all([
        apiGet<Member[]>("/sharing/members"),
        apiGet<Invite[]>("/sharing/invites"),
        apiGet<PublicShare>("/sharing/public"),
      ]);
      setMembers(m);
      setInvites(i);
      setPub(p);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function createInvite() {
    setError(null);
    try {
      await apiPost<Invite>("/sharing/invites", { role });
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function revokeInvite(id: string) {
    await apiSend("DELETE", `/sharing/invites/${id}`);
    await load();
  }

  async function changeRole(memberId: string, newRole: string) {
    await apiSend("PATCH", `/sharing/members/${memberId}`, { role: newRole });
    await load();
  }

  async function removeMember(memberId: string) {
    await apiSend("DELETE", `/sharing/members/${memberId}`);
    await load();
  }

  async function togglePublic(enabled: boolean) {
    const p = await apiSend<PublicShare>("PUT", "/sharing/public", { enabled });
    if (p) setPub(p);
  }

  async function regenPublic() {
    const p = await apiPost<PublicShare>("/sharing/public/regenerate");
    setPub(p);
  }

  function copy(text: string, key: string) {
    navigator.clipboard?.writeText(text);
    setCopied(key);
    setTimeout(() => setCopied(null), 1500);
  }

  return (
    <div className="share-page">
      <h1 className="share-title">Sharing</h1>
      <p className="share-sub">
        Give people access to your Burnt Jacket account — read-only or as an admin.
      </p>
      {error && <div className="auth-error">{error}</div>}

      {/* Invite links */}
      <section className="share-card">
        <h2>Invite someone</h2>
        <p className="share-hint">
          Creates a link. Whoever opens it and signs in becomes a member you can remove anytime.
        </p>
        <div className="share-row">
          <select value={role} onChange={(e) => setRole(e.target.value as "viewer" | "admin")}>
            <option value="viewer">Viewer (read-only)</option>
            <option value="admin">Admin (read &amp; write)</option>
          </select>
          <button className="btn-gold" onClick={createInvite}>
            Create invite link
          </button>
        </div>

        {invites.length > 0 && (
          <ul className="share-list">
            {invites.map((inv) => (
              <li key={inv.id}>
                <span className="pill">{inv.role}</span>
                <code className="share-link">{inv.invite_url}</code>
                <button className="btn-small" onClick={() => copy(inv.invite_url, inv.id)}>
                  {copied === inv.id ? "Copied" : "Copy"}
                </button>
                <span className="share-uses">
                  used {inv.uses}
                  {inv.max_uses ? `/${inv.max_uses}` : ""}
                </span>
                <button className="btn-small btn-danger" onClick={() => revokeInvite(inv.id)}>
                  Revoke
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Members */}
      <section className="share-card">
        <h2>People with access</h2>
        {members.length === 0 ? (
          <p className="share-hint">No one yet. Create an invite link above.</p>
        ) : (
          <ul className="share-list">
            {members.map((mem) => (
              <li key={mem.member_id}>
                <span className="member-name">{mem.display_name || mem.email}</span>
                <select value={mem.role} onChange={(e) => changeRole(mem.member_id, e.target.value)}>
                  <option value="viewer">Viewer</option>
                  <option value="admin">Admin</option>
                </select>
                <button className="btn-small btn-danger" onClick={() => removeMember(mem.member_id)}>
                  Remove
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Anonymous public link */}
      <section className="share-card">
        <h2>Public read-only link</h2>
        <p className="share-hint">
          When on, anyone with the link can view your collection — no sign-in needed. Turn it off
          anytime to make it private again.
        </p>
        <label className="share-toggle">
          <input
            type="checkbox"
            checked={pub.enabled}
            onChange={(e) => togglePublic(e.target.checked)}
          />
          <span>{pub.enabled ? "Public link is ON" : "Public link is OFF (private)"}</span>
        </label>

        {pub.enabled && pub.public_url && (
          <div className="share-row" style={{ marginTop: 12 }}>
            <code className="share-link">{pub.public_url}</code>
            <button className="btn-small" onClick={() => copy(pub.public_url!, "public")}>
              {copied === "public" ? "Copied" : "Copy"}
            </button>
            <button className="btn-small" onClick={regenPublic}>
              Regenerate
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
