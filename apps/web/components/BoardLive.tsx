"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost, apiSend } from "../lib/api";

type Post = {
  id: string;
  kind: "trade" | "looking_for";
  note: string | null;
  status: string;
  created_at: string;
  release: { id: string | null; title: string; artists: string[]; year: number | null; image_url: string | null };
  poster: { user_id: string; display_name: string };
  condition: string | null;
  max_price: number | null;
  comment_count: number;
  is_own_post: boolean;
};

type Comment = { id: string; message: string; author: string; created_at: string; user_id: string };

type WantlistPickerItem = {
  wantlist_item_id: string;
  release_id: string;
  title: string;
  artists: string[];
  year: number | null;
  image_url: string | null;
  max_price: number | null;
  minimum_media_condition: string | null;
};

export default function BoardLive() {
  const [posts, setPosts] = useState<Post[]>([]);
  const [filter, setFilter] = useState<"" | "trade" | "looking_for">("");
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [expandedComments, setExpandedComments] = useState<Record<string, Comment[]>>({});
  const [commentDraft, setCommentDraft] = useState<Record<string, string>>({});

  async function load() {
    try {
      const q = filter ? `?kind=${filter}` : "";
      const data = await apiGet<{ posts: Post[] }>(`/board${q}`);
      setPosts(data.posts);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  async function toggleComments(postId: string) {
    if (expandedComments[postId]) {
      setExpandedComments((p) => {
        const n = { ...p };
        delete n[postId];
        return n;
      });
      return;
    }
    try {
      const data = await apiGet<{ comments: Comment[] }>(`/board/${postId}/comments`);
      setExpandedComments((p) => ({ ...p, [postId]: data.comments }));
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function submitComment(postId: string) {
    const msg = (commentDraft[postId] || "").trim();
    if (!msg) return;
    try {
      await apiPost(`/board/${postId}/comments`, { message: msg });
      setCommentDraft((p) => ({ ...p, [postId]: "" }));
      const data = await apiGet<{ comments: Comment[] }>(`/board/${postId}/comments`);
      setExpandedComments((p) => ({ ...p, [postId]: data.comments }));
      load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function removePost(postId: string) {
    try {
      await apiSend("DELETE", `/board/${postId}`);
      load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>Collector Board</h1>
        <p className="muted">Trade with, or find records from, other SpinningLicorice collectors.</p>
      </div>

      <div className="board-welcome">
        👋 <strong>Welcome to the Collector Board.</strong> Mark a record in your collection as{" "}
        <strong>Open to Trade</strong>, or something on your wantlist as <strong>Looking For</strong> — it'll show up
        here for every SpinningLicorice collector to see. Comment on a posting to start a conversation.
      </div>

      {error && <div className="error">{error}</div>}

      <div className="board-controls">
        <div className="board-filter">
          <button className={filter === "" ? "tab active" : "tab"} onClick={() => setFilter("")}>All</button>
          <button className={filter === "trade" ? "tab active" : "tab"} onClick={() => setFilter("trade")}>Open to Trade</button>
          <button className={filter === "looking_for" ? "tab active" : "tab"} onClick={() => setFilter("looking_for")}>Looking For</button>
        </div>
        <button className="btn greenbtn" onClick={() => setShowCreate(true)}>+ POST TO BOARD</button>
      </div>

      {showCreate && (
        <CreatePostModal
          onClose={() => setShowCreate(false)}
          onCreated={() => {
            setShowCreate(false);
            load();
          }}
          onError={setError}
        />
      )}

      <div className="board-list">
        {posts.length === 0 && <div className="muted">Nothing posted yet — be the first!</div>}
        {posts.map((p) => (
          <div className="board-post" key={p.id}>
            <div className="board-post-thumb">
              {p.release.image_url ? (
                <img src={p.release.image_url} alt="" />
              ) : (
                <div className="board-post-thumb-empty">SPINNINGLICORICE</div>
              )}
            </div>
            <div className="board-post-body">
              <div className="board-post-header">
                <span className={p.kind === "trade" ? "badge good" : "badge"}>
                  {p.kind === "trade" ? "OPEN TO TRADE" : "LOOKING FOR"}
                </span>
                {p.condition && <span className="badge">{p.condition}</span>}
                {p.max_price != null && <span className="badge">up to ${p.max_price}</span>}
              </div>
              <div className="board-post-title">{p.release.title}</div>
              <div className="muted small">
                {p.release.artists.join(", ")}
                {p.release.year ? ` · ${p.release.year}` : ""}
              </div>
              {p.note && <div className="muted small board-post-note">&quot;{p.note}&quot;</div>}
              <div className="muted small">posted by {p.poster.display_name}</div>
              <div className="board-post-actions">
                <button className="link-btn" onClick={() => toggleComments(p.id)}>
                  {expandedComments[p.id] ? "hide" : `${p.comment_count} comment${p.comment_count === 1 ? "" : "s"}`}
                </button>
                {p.is_own_post && (
                  <button className="link-btn" onClick={() => removePost(p.id)}>
                    remove
                  </button>
                )}
              </div>

              {expandedComments[p.id] && (
                <div className="board-comments">
                  {expandedComments[p.id].map((c) => (
                    <div key={c.id} className="board-comment">
                      <strong>{c.author}:</strong> {c.message}
                    </div>
                  ))}
                  <div className="board-comment-form">
                    <input
                      placeholder="Say something…"
                      value={commentDraft[p.id] || ""}
                      onChange={(e) => setCommentDraft((prev) => ({ ...prev, [p.id]: e.target.value }))}
                      onKeyDown={(e) => e.key === "Enter" && submitComment(p.id)}
                    />
                    <button className="btn-small" onClick={() => submitComment(p.id)}>
                      SEND
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

function CreatePostModal({
  onClose,
  onCreated,
  onError,
}: {
  onClose: () => void;
  onCreated: () => void;
  onError: (s: string) => void;
}) {
  const [tab, setTab] = useState<"trade" | "looking_for">("trade");
  const [collectionItems, setCollectionItems] = useState<{ collection_item_id: string; title: string; artists: string[] }[]>([]);
  const [wantlistItems, setWantlistItems] = useState<WantlistPickerItem[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (tab === "trade") {
      apiGet<{ items: { collection_item_id: string; title: string; artists: string[] }[] }>("/collection")
        .then((d) => setCollectionItems(d.items))
        .catch((e) => onError((e as Error).message));
    } else {
      apiGet<{ items: WantlistPickerItem[] }>("/board/my-wantlist")
        .then((d) => setWantlistItems(d.items))
        .catch((e) => onError((e as Error).message));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  async function submit() {
    if (!selected) {
      onError("Pick a record first.");
      return;
    }
    setBusy(true);
    try {
      if (tab === "trade") {
        await apiPost("/board/trade", { collection_item_id: selected, note: note.trim() || null });
      } else {
        await apiPost("/board/looking-for", { wantlist_item_id: selected, note: note.trim() || null });
      }
      onCreated();
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="picker-overlay" onClick={onClose}>
      <div className="picker" onClick={(e) => e.stopPropagation()}>
        <div className="picker-head">
          <h3>Post to the board</h3>
          <button className="picker-close" onClick={onClose}>×</button>
        </div>
        <div className="picker-tabs">
          <button
            className={tab === "trade" ? "picker-tab active" : "picker-tab"}
            onClick={() => {
              setTab("trade");
              setSelected("");
            }}
          >
            Open to Trade
          </button>
          <button
            className={tab === "looking_for" ? "picker-tab active" : "picker-tab"}
            onClick={() => {
              setTab("looking_for");
              setSelected("");
            }}
          >
            Looking For
          </button>
        </div>

        {tab === "trade" ? (
          <div className="board-picker-list">
            {collectionItems.length === 0 && <div className="muted small">Nothing in your collection yet.</div>}
            {collectionItems.map((it) => (
              <label key={it.collection_item_id} className="board-picker-row">
                <input
                  type="radio"
                  name="pick"
                  checked={selected === it.collection_item_id}
                  onChange={() => setSelected(it.collection_item_id)}
                />
                {it.title} — {it.artists?.join(", ")}
              </label>
            ))}
          </div>
        ) : (
          <div className="board-picker-list">
            {wantlistItems.length === 0 && <div className="muted small">Nothing on your wantlist yet.</div>}
            {wantlistItems.map((it) => (
              <label key={it.wantlist_item_id} className="board-picker-row">
                <input
                  type="radio"
                  name="pick"
                  checked={selected === it.wantlist_item_id}
                  onChange={() => setSelected(it.wantlist_item_id)}
                />
                {it.title} — {it.artists?.join(", ")}
              </label>
            ))}
          </div>
        )}

        <textarea placeholder="Add a note (optional)" value={note} onChange={(e) => setNote(e.target.value)} />
        <button className="btn greenbtn" disabled={busy} onClick={submit}>
          {busy ? "POSTING…" : "POST TO BOARD"}
        </button>
      </div>
    </div>
  );
}
