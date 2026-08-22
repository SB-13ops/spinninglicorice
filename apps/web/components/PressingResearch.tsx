"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "../lib/api";

type Enrichment = { text: string; citations: Array<{ url: string; title: string | null }> };

/**
 * A small "Ask Burnt Jacket AI about this pressing" action. Only renders when the
 * server reports AI is enabled (GET /ai/status), so it disappears cleanly when
 * no Anthropic key is configured.
 */
export default function PressingResearch({
  title,
  artist,
  year,
}: {
  title: string;
  artist?: string | null;
  year?: number | null;
}) {
  const [enabled, setEnabled] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Enrichment | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiGet<{ enabled: boolean }>("/ai/status")
      .then((s) => setEnabled(s.enabled))
      .catch(() => setEnabled(false));
  }, []);

  if (!enabled) return null;

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const r = await apiPost<Enrichment>("/ai/pressing/research", {
        title,
        artist: artist ?? null,
        year: year ?? null,
      });
      setResult(r);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="ai-research">
      {!result && (
        <button className="btn-small ai-btn" onClick={run} disabled={loading}>
          {loading ? "Researching…" : "✦ Research this pressing"}
        </button>
      )}
      {error && <div className="auth-error">{error}</div>}
      {result && (
        <div className="ai-result">
          <p>{result.text}</p>
          {result.citations.length > 0 && (
            <div className="ai-cites">
              Sources:{" "}
              {result.citations.map((c, i) => (
                <a key={i} href={c.url} target="_blank" rel="noreferrer">
                  {c.title || new URL(c.url).hostname}
                </a>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
