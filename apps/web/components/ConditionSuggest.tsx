"use client";

import { useState } from "react";
import { apiUpload } from "../lib/api";

type Suggestion = { suggested_grade: string | null; observations: string; confidence: string };

/**
 * A small "suggest from photo" helper attached next to a condition dropdown.
 * Deliberately framed as a suggestion to review, not an authoritative grade —
 * condition affects real value, and a photo can only show so much (it can
 * never assess the actual vinyl playing surface, only what's visibly in the
 * cover/label photo).
 */
export default function ConditionSuggest({
  onApply,
  onError,
}: {
  onApply: (grade: string) => void;
  onError: (s: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Suggestion | null>(null);

  async function onFile(file: File) {
    setBusy(true);
    setResult(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await apiUpload<Suggestion>("/collection/suggest-condition", formData);
      setResult(res);
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="condition-suggest">
      <label className="link-btn" style={{ cursor: busy ? "default" : "pointer" }}>
        {busy ? "checking…" : "📷 suggest from photo"}
        <input
          type="file"
          accept="image/*"
          capture="environment"
          style={{ display: "none" }}
          disabled={busy}
          onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])}
        />
      </label>

      {result && (
        <div className="condition-suggest-result">
          {result.suggested_grade ? (
            <>
              <div className="muted small">
                AI suggests <strong>{result.suggested_grade}</strong> ({result.confidence} confidence) based on
                what's visible in the photo — not the vinyl itself, just the cover/label shown.
              </div>
              {result.observations && <div className="muted small">{result.observations}</div>}
              <button
                type="button"
                className="btn-small"
                onClick={() => {
                  onApply(result.suggested_grade as string);
                  setResult(null);
                }}
              >
                Use this
              </button>
            </>
          ) : (
            <div className="muted small">
              Couldn't judge condition from that photo{result.observations ? ` — ${result.observations}` : "."} Try a clearer shot, or set it yourself.
            </div>
          )}
        </div>
      )}
    </div>
  );
}
