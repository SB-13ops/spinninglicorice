"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams } from "next/navigation";
import { apiGet, apiPost, apiSend } from "../lib/api";

type Group = {
  id: string;
  name: string;
  description: string | null;
  facebook_group_url: string | null;
  role: string;
  member_count: number;
};
type Message = { id: string; user_id: string; author: string; body: string; created_at: string };
type Member = { user_id: string; display_name: string | null; email: string; role: string };
type Listing = {
  id: string;
  kind: "swap" | "sale";
  title: string;
  image_url: string | null;
  condition: string | null;
  price: number | null;
  currency: string;
  swap_wants: string | null;
  note: string | null;
  status: string;
  seller_id: string;
  seller_name: string | null;
  seller_venmo: string | null;
  seller_paypal: string | null;
  interest_count: number;
};

type Tab = "chat" | "market" | "members";

export default function GroupDetail() {
  const params = useParams();
  const gid = String(params.id || "");
  const [group, setGroup] = useState<Group | null>(null);
  const [tab, setTab] = useState<Tab>("chat");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<Group>(`/groups/${gid}`).then(setGroup).catch((e) => setError((e as Error).message));
  }, [gid]);

  if (error) {
    return (
      <div className="share-page">
        <div className="auth-error">{error}</div>
        <a className="btn-small" href="/groups">← Back to groups</a>
      </div>
    );
  }
  if (!group) return <div className="status">Loading group…</div>;

  return (
    <div className="share-page">
      <div className="share-head-row">
        <div>
          <a className="group-back" href="/groups">← Groups</a>
          <h1 className="share-title">{group.name}</h1>
          {group.description && <p className="share-sub">{group.description}</p>}
        </div>
      </div>

      {group.facebook_group_url && (
        <a className="fb-link" href={group.facebook_group_url} target="_blank" rel="noreferrer">
          Open Facebook group ↗
        </a>
      )}

      <div className="picker-tabs" style={{ marginTop: 12 }}>
        {(["chat", "market", "members"] as Tab[]).map((t) => (
          <button key={t} className={`picker-tab ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>
            {t === "chat" ? "Chat" : t === "market" ? "Market" : "Members"}
          </button>
        ))}
      </div>

      {tab === "chat" && <ChatTab gid={gid} />}
      {tab === "market" && <MarketTab gid={gid} />}
      {tab === "members" && <MembersTab gid={gid} isAdmin={group.role === "admin"} />}
    </div>
  );
}

/* ---- Chat ---- */
function ChatTab({ gid }: { gid: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [body, setBody] = useState("");
  const lastTs = useRef<string | null>(null);
  const boxRef = useRef<HTMLDivElement>(null);

  const initialLoad = useCallback(() => {
    apiGet<Message[]>(`/groups/${gid}/messages`).then((m) => {
      setMessages(m);
      if (m.length) lastTs.current = m[m.length - 1].created_at;
    });
  }, [gid]);

  useEffect(() => {
    initialLoad();
    // Poll for new messages every 4s (structured so WebSockets can replace this later).
    const iv = setInterval(() => {
      if (!lastTs.current) return;
      apiGet<Message[]>(`/groups/${gid}/messages?since=${encodeURIComponent(lastTs.current)}`)
        .then((m) => {
          if (m.length) {
            setMessages((prev) => [...prev, ...m]);
            lastTs.current = m[m.length - 1].created_at;
          }
        })
        .catch(() => {});
    }, 4000);
    return () => clearInterval(iv);
  }, [gid, initialLoad]);

  useEffect(() => {
    boxRef.current?.scrollTo(0, boxRef.current.scrollHeight);
  }, [messages]);

  async function send() {
    if (!body.trim()) return;
    const msg = await apiPost<Message>(`/groups/${gid}/messages`, { body });
    setMessages((prev) => [...prev, msg]);
    lastTs.current = msg.created_at;
    setBody("");
  }

  return (
    <div className="share-card">
      <div className="chat-box" ref={boxRef}>
        {messages.length === 0 ? (
          <p className="share-hint">No messages yet. Say hello!</p>
        ) : (
          messages.map((m) => (
            <div key={m.id} className="chat-msg">
              <span className="chat-author">{m.author}</span>
              <span className="chat-body">{m.body}</span>
            </div>
          ))
        )}
      </div>
      <div className="share-row" style={{ marginTop: 10 }}>
        <input
          className="picker-search"
          style={{ margin: 0, flex: 1 }}
          placeholder="Message the group…"
          value={body}
          onChange={(e) => setBody(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
        />
        <button className="btn-gold" onClick={send}>
          Send
        </button>
      </div>
    </div>
  );
}

/* ---- Market ---- */
function MarketTab({ gid }: { gid: string }) {
  const [listings, setListings] = useState<Listing[]>([]);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ kind: "swap", title: "", price: "", condition: "", swap_wants: "", note: "" });

  const load = useCallback(() => {
    apiGet<Listing[]>(`/groups/${gid}/listings`).then(setListings).catch(() => {});
  }, [gid]);
  useEffect(() => load(), [load]);

  async function create() {
    if (!form.title.trim()) return;
    const body: Record<string, unknown> = {
      kind: form.kind,
      title: form.title,
      condition: form.condition || null,
      note: form.note || null,
    };
    if (form.kind === "sale") body.price = parseFloat(form.price || "0");
    else body.swap_wants = form.swap_wants || null;
    await apiPost(`/groups/${gid}/listings`, body);
    setForm({ kind: "swap", title: "", price: "", condition: "", swap_wants: "", note: "" });
    setCreating(false);
    load();
  }

  async function express(id: string) {
    await apiPost(`/groups/${gid}/listings/${id}/interest`, { message: null });
    load();
  }

  return (
    <div>
      <div className="share-head-row">
        <h2 style={{ margin: 0 }}>Swap &amp; sale</h2>
        <button className="btn-gold" onClick={() => setCreating((v) => !v)}>
          {creating ? "Cancel" : "List a record"}
        </button>
      </div>

      {creating && (
        <div className="share-card">
          <div className="share-row">
            <select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
              <option value="swap">Swap</option>
              <option value="sale">Sale</option>
            </select>
            <input
              className="picker-search"
              style={{ margin: 0, flex: 1 }}
              placeholder="Record title"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
            />
          </div>
          <div className="share-row" style={{ marginTop: 8 }}>
            <input className="picker-search" style={{ margin: 0 }} placeholder="Condition (e.g. VG+)" value={form.condition} onChange={(e) => setForm({ ...form, condition: e.target.value })} />
            {form.kind === "sale" ? (
              <input className="picker-search" style={{ margin: 0 }} placeholder="Price" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} />
            ) : (
              <input className="picker-search" style={{ margin: 0 }} placeholder="Looking to swap for…" value={form.swap_wants} onChange={(e) => setForm({ ...form, swap_wants: e.target.value })} />
            )}
          </div>
          <button className="btn-gold" style={{ marginTop: 10 }} onClick={create}>
            Post listing
          </button>
        </div>
      )}

      {listings.length === 0 ? (
        <p className="share-hint">No open listings. Be the first to list a record.</p>
      ) : (
        <div className="listing-grid">
          {listings.map((l) => (
            <div key={l.id} className="listing-card">
              {l.image_url && <img src={l.image_url} alt="" className="listing-img" />}
              <div className="listing-body">
                <div className="listing-top">
                  <span className={`pill ${l.kind === "sale" ? "pill-sale" : "pill-swap"}`}>{l.kind}</span>
                  {l.kind === "sale" && l.price != null && (
                    <span className="listing-price">
                      ${l.price} {l.currency}
                    </span>
                  )}
                </div>
                <div className="listing-title">{l.title}</div>
                {l.condition && <div className="share-hint" style={{ margin: 0 }}>Condition: {l.condition}</div>}
                {l.swap_wants && <div className="share-hint" style={{ margin: 0 }}>Wants: {l.swap_wants}</div>}
                <div className="listing-seller">from {l.seller_name}</div>
                <div className="listing-actions">
                  <button className="btn-small" onClick={() => express(l.id)}>
                    I&apos;m interested
                  </button>
                  <span className="share-uses">{l.interest_count} interested</span>
                </div>
                {(l.seller_venmo || l.seller_paypal) && (
                  <div className="listing-pay">
                    Pay via{" "}
                    {l.seller_venmo && <span>Venmo {l.seller_venmo} </span>}
                    {l.seller_paypal && <span>· PayPal {l.seller_paypal}</span>}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ---- Members ---- */
function MembersTab({ gid, isAdmin }: { gid: string; isAdmin: boolean }) {
  const [members, setMembers] = useState<Member[]>([]);
  const [invite, setInvite] = useState<string | null>(null);

  const load = useCallback(() => {
    apiGet<Member[]>(`/groups/${gid}/members`).then(setMembers).catch(() => {});
  }, [gid]);
  useEffect(() => load(), [load]);

  async function makeInvite() {
    const inv = await apiPost<{ invite_url: string }>(`/groups/${gid}/invites`);
    setInvite(inv.invite_url);
  }
  async function remove(uid: string) {
    await apiSend("DELETE", `/groups/${gid}/members/${uid}`);
    load();
  }

  return (
    <div className="share-card">
      <div className="share-head-row">
        <h2 style={{ margin: 0 }}>Members ({members.length})</h2>
        {isAdmin && (
          <button className="btn-gold" onClick={makeInvite}>
            Create invite link
          </button>
        )}
      </div>
      {invite && (
        <div className="share-row" style={{ marginTop: 10 }}>
          <code className="share-link">{invite}</code>
          <button className="btn-small" onClick={() => navigator.clipboard?.writeText(invite)}>
            Copy
          </button>
        </div>
      )}
      <ul className="share-list">
        {members.map((m) => (
          <li key={m.user_id}>
            <span className="member-name">{m.display_name || m.email}</span>
            <span className="pill">{m.role}</span>
            {isAdmin && (
              <button className="btn-small btn-danger" onClick={() => remove(m.user_id)}>
                Remove
              </button>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
