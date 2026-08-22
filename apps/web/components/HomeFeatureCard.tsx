"use client";

import { useEffect, useState } from "react";
import { apiGet } from "../lib/api";
import FeaturePicker from "./FeaturePicker";
import type { Hero } from "./HomeHero";

/**
 * A compact card for the Profile page showing the current home hero with a
 * button to personalize it. Uses the same picker as the inline home edit.
 */
export default function HomeFeatureCard() {
  const [hero, setHero] = useState<Hero | null>(null);
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    apiGet<Hero>("/home/feature").then(setHero).catch(() => {});
  }, []);

  return (
    <div className="share-card">
      <h2>Home page</h2>
      <p className="share-hint">
        Choose what greets you on your home page — a favorite album, an artist, or your own image.
      </p>

      {hero && (
        <div className="profile-hero-preview">
          {hero.image_url && <img src={hero.image_url} alt="" className="picker-thumb" />}
          <div>
            <div className="member-name">
              {hero.type === "default" ? "Default Burnt Jacket banner" : hero.title}
            </div>
            {hero.subtitle && <div className="share-hint" style={{ margin: 0 }}>{hero.subtitle}</div>}
          </div>
        </div>
      )}

      <button className="btn-gold" style={{ marginTop: 12 }} onClick={() => setEditing(true)}>
        Personalize home page
      </button>

      {editing && (
        <FeaturePicker
          onClose={() => setEditing(false)}
          onSaved={(h) => {
            setHero(h);
            setEditing(false);
          }}
        />
      )}
    </div>
  );
}
