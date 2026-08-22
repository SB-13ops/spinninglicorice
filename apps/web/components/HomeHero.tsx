"use client";

import { useState } from "react";
import FeaturePicker from "./FeaturePicker";

export type Hero = {
  type: "album" | "artist" | "custom" | "default";
  title: string;
  subtitle: string | null;
  image_url: string | null;
  ref_id: string | null;
};

/**
 * Full-width themed hero shown atop the home dashboard. When an image is
 * present it's used as a blurred, darkened full-bleed backdrop with the cover
 * shown crisp alongside the title — giving the whole banner a color mood pulled
 * from the artwork. An edit button opens the picker inline.
 */
export default function HomeHero({
  hero,
  editable,
  onChanged,
}: {
  hero: Hero;
  editable: boolean;
  onChanged: (h: Hero) => void;
}) {
  const [editing, setEditing] = useState(false);
  const hasImage = Boolean(hero.image_url);

  return (
    <div className={`home-hero ${hero.type === "default" ? "home-hero-default" : ""}`}>
      {hasImage && (
        <div
          className="home-hero-bg"
          style={{ backgroundImage: `url(${hero.image_url})` }}
          aria-hidden
        />
      )}
      <div className="home-hero-scrim" aria-hidden />

      <div className="home-hero-inner">
        {hasImage && hero.type !== "custom" && (
          <img className="home-hero-cover" src={hero.image_url!} alt="" />
        )}
        <div className="home-hero-text">
          {hero.type !== "default" && <span className="home-hero-kicker">{heroKicker(hero.type)}</span>}
          <h1 className="home-hero-title">{hero.title}</h1>
          {hero.subtitle && <p className="home-hero-sub">{hero.subtitle}</p>}
        </div>

        {editable && (
          <button className="home-hero-edit" onClick={() => setEditing(true)}>
            {hero.type === "default" ? "Personalize" : "Change"}
          </button>
        )}
      </div>

      {editing && (
        <FeaturePicker
          onClose={() => setEditing(false)}
          onSaved={(h) => {
            onChanged(h);
            setEditing(false);
          }}
        />
      )}
    </div>
  );
}

function heroKicker(type: Hero["type"]): string {
  if (type === "album") return "Now featuring";
  if (type === "artist") return "Featured artist";
  return "Featured";
}
