"use client";

import { useEffect, useState } from "react";
import { apiGet, apiSend } from "../lib/api";
import type { Hero } from "./HomeHero";

type Options = {
  albums: Array<{ release_id: string; title: string; image_url: string | null }>;
  artists: Array<{ artist_id: string; name: string }>;
};

type Tab = "album" | "artist" | "custom" | "default";

export default function FeaturePicker({
  onClose,
  onSaved,
}: {
  onClose: () => void;
  onSaved: (h: Hero) => void;
}) {
  const [tab, setTab] = useState<Tab>("album");
  const [q, setQ] = useState("");
  const [options, setOptions] = useState<Options>({ albums: [], artists: [] });
  const [custom, setCustom] = useState({ title: "", subtitle: "", image_url: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const t = setTimeout(() => {
      apiGet<Options>(`/home/feature/options${q ? `?q=${encodeURIComponent(q)}` : ""}`)
        .then(setOptions)
        .catch(() => {});
    }, 200);
    return () => clearTimeout(t);
  }, [q]);

  async function save(body: Record<string, unknown>) {
    setSaving(true);
    setError(null);
    try {
      const h = await apiSend<Hero>("PUT", "/home/feature", body);
      if (h) onSaved(h);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="picker-overlay" onClick={onClose}>
      <div className="picker" onClick={(e) => e.stopPropagation()}>
        <div className="picker-head">
          <h3>Personalize your home page</h3>
          <button className="picker-x" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="picker-tabs">
          {(["album", "artist", "custom", "default"] as Tab[]).map((t) => (
            <button
              key={t}
              className={`picker-tab ${tab === t ? "active" : ""}`}
              onClick={() => setTab(t)}
            >
              {t === "default" ? "Default" : t[0].toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>

        {error && <div className="auth-error">{error}</div>}

        {(tab === "album" || tab === "artist") && (
          <>
            <input
              className="picker-search"
              placeholder={`Search your ${tab}s…`}
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
            <div className="picker-list">
              {tab === "album" &&
                options.albums.map((a) => (
                  <button
                    key={a.release_id}
                    className="picker-item"
                    disabled={saving}
                    onClick={() => save({ feature_type: "album", release_id: a.release_id })}
                  >
                    {a.image_url ? (
                      <img src={a.image_url} alt="" className="picker-thumb" />
                    ) : (
                      <span className="picker-thumb picker-thumb-empty">♪</span>
                    )}
                    <span>{a.title}</span>
                  </button>
                ))}
              {tab === "artist" &&
                options.artists.map((a) => (
                  <button
                    key={a.artist_id}
                    className="picker-item"
                    disabled={saving}
                    onClick={() => save({ feature_type: "artist", artist_id: a.artist_id })}
                  >
                    <span className="picker-thumb picker-thumb-empty">☺</span>
                    <span>{a.name}</span>
                  </button>
                ))}
              {tab === "album" && options.albums.length === 0 && (
                <p className="share-hint">No albums found. Sync your collection first.</p>
              )}
              {tab === "artist" && options.artists.length === 0 && (
                <p className="share-hint">No artists found. Sync your collection first.</p>
              )}
            </div>
          </>
        )}

        {tab === "custom" && (
          <div className="picker-custom">
            <label>Title</label>
            <input
              className="picker-search"
              value={custom.title}
              onChange={(e) => setCustom({ ...custom, title: e.target.value })}
              placeholder="e.g. Cornell '77"
            />
            <label>Subtitle</label>
            <input
              className="picker-search"
              value={custom.subtitle}
              onChange={(e) => setCustom({ ...custom, subtitle: e.target.value })}
              placeholder="Optional"
            />
            <label>Image URL</label>
            <input
              className="picker-search"
              value={custom.image_url}
              onChange={(e) => setCustom({ ...custom, image_url: e.target.value })}
              placeholder="https://…"
            />
            <button
              className="btn-gold"
              disabled={saving || !custom.title}
              onClick={() =>
                save({
                  feature_type: "custom",
                  custom_title: custom.title,
                  custom_subtitle: custom.subtitle || null,
                  custom_image_url: custom.image_url || null,
                })
              }
            >
              Save custom hero
            </button>
          </div>
        )}

        {tab === "default" && (
          <div className="picker-custom">
            <p className="share-hint">Reset your home page to the default Burnt Jacket banner.</p>
            <button
              className="btn-small"
              disabled={saving}
              onClick={() => save({ feature_type: "default" })}
            >
              Use default
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
