"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { apiGet } from "../lib/api";

type Hit = { collection_item_id: string; title: string; artists: string[] };

/**
 * The top-nav search. Searches the collection by title/artist/label as you
 * type (debounced) and shows a dropdown of matches; Enter or "see all
 * results" goes to the full Collection page filtered by the same term.
 */
export default function TopSearch() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [hits, setHits] = useState<Hit[]>([]);
  const boxRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!q.trim()) {
      setHits([]);
      setOpen(false);
      return;
    }
    if (debounceRef.current) clearTimeout(debounceRef.current);
    setLoading(true);
    setOpen(true);
    debounceRef.current = setTimeout(async () => {
      try {
        const data = await apiGet<{ items: Hit[] }>(`/collection?q=${encodeURIComponent(q.trim())}`);
        setHits((data.items || []).slice(0, 6));
      } catch {
        setHits([]);
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [q]);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  function goToResults(term: string) {
    setOpen(false);
    router.push(`/collection?q=${encodeURIComponent(term)}`);
  }

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (q.trim()) goToResults(q.trim());
  }

  return (
    <div className="search-wrap" ref={boxRef}>
      <form onSubmit={onSubmit}>
        <input
          className="search"
          placeholder="Now spinning — search your collection…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onFocus={() => hits.length > 0 && setOpen(true)}
        />
      </form>
      {open && (
        <div className="search-dropdown">
          {loading && <div className="search-dropdown-item muted">Now spinning…</div>}
          {!loading && hits.length === 0 && (
            <div className="search-dropdown-item muted">No matches in your collection yet.</div>
          )}
          {!loading &&
            hits.map((h) => (
              <div key={h.collection_item_id} className="search-dropdown-item" onClick={() => goToResults(h.title)}>
                <strong>{h.title}</strong>
                <span className="muted small"> — {h.artists?.join(", ") || "Unknown artist"}</span>
              </div>
            ))}
          {!loading && hits.length > 0 && (
            <div className="search-dropdown-item search-dropdown-more" onClick={() => goToResults(q.trim())}>
              See all results for &quot;{q.trim()}&quot;
            </div>
          )}
        </div>
      )}
    </div>
  );
}
