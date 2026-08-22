"use client";

import { useState } from "react";
import { apiPost } from "../lib/api";

type CostLine = { label: string; amount: number | null; detail: string | null; estimated: boolean };
type Plan = {
  destination: string;
  origin: string;
  mode: string;
  nights: number;
  itinerary: string[];
  costs: CostLine[];
  total_low: number | null;
  total_high: number | null;
  booking_links: { hotel: string; flight: string; car?: string; rideshare?: string; affiliate_active: boolean };
  notes: string[];
  citations: Array<{ url: string; title: string | null }>;
};

/**
 * Per-recommendation road-trip planner. Lets the user tweak mode/nights/origin,
 * then shows an itinerary + cost breakdown (gas is exact; hotel/flight are AI
 * estimates) with Expedia booking links. All figures are estimates.
 */
export default function TripPlanner({ recommendationId }: { recommendationId: string }) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState("compare");
  const [nights, setNights] = useState(1);
  const [origin, setOrigin] = useState("");
  const [travelers, setTravelers] = useState(1);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const body: Record<string, unknown> = { mode, nights, travelers };
      if (origin.trim()) body.origin = origin.trim();
      const p = await apiPost<Plan>(`/trips/plan/${recommendationId}`, body);
      setPlan(p);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  if (!open) {
    return (
      <button className="btn-small trip-btn" onClick={() => setOpen(true)}>
        ⛟ Plan a road trip
      </button>
    );
  }

  return (
    <div className="trip-panel">
      <div className="trip-controls">
        <select value={mode} onChange={(e) => setMode(e.target.value)}>
          <option value="compare">Drive vs. fly</option>
          <option value="drive">Drive</option>
          <option value="fly">Fly</option>
        </select>
        <input
          type="number"
          min={0}
          max={14}
          value={nights}
          onChange={(e) => setNights(parseInt(e.target.value || "0"))}
          title="Nights"
          style={{ width: 60 }}
        />
        <input
          type="number"
          min={1}
          max={12}
          value={travelers}
          onChange={(e) => setTravelers(parseInt(e.target.value || "1"))}
          title="Travelers"
          style={{ width: 60 }}
        />
        <input
          placeholder="Origin (optional — uses saved)"
          value={origin}
          onChange={(e) => setOrigin(e.target.value)}
          style={{ flex: 1, minWidth: 140 }}
        />
        <button className="btn-gold" onClick={run} disabled={loading}>
          {loading ? "Planning…" : "Plan"}
        </button>
      </div>

      {error && <div className="auth-error">{error}</div>}

      {plan && (
        <div className="trip-result">
          <div className="trip-route">
            {plan.origin} → {plan.destination} · {plan.mode} · {plan.nights} night(s)
          </div>

          <ol className="trip-itin">
            {plan.itinerary.map((step, i) => (
              <li key={i}>{step}</li>
            ))}
          </ol>

          <table className="trip-costs">
            <tbody>
              {plan.costs.map((c, i) => (
                <tr key={i}>
                  <td>{c.label}</td>
                  <td className="trip-amt">
                    {c.amount != null ? `$${c.amount.toFixed(2)}` : "—"}
                    {!c.estimated && <span className="trip-exact"> exact</span>}
                  </td>
                  <td className="trip-detail">{c.detail}</td>
                </tr>
              ))}
            </tbody>
            {plan.total_low != null && (
              <tfoot>
                <tr>
                  <td>Estimated total</td>
                  <td className="trip-amt">
                    ${plan.total_low.toFixed(0)}
                    {plan.total_high && plan.total_high !== plan.total_low
                      ? `–$${plan.total_high.toFixed(0)}`
                      : ""}
                  </td>
                  <td />
                </tr>
              </tfoot>
            )}
          </table>

          <div className="trip-book">
            <a className="btn-small" href={plan.booking_links.hotel} target="_blank" rel="noreferrer nofollow sponsored">
              Book hotel (Expedia)
            </a>
            {(plan.mode === "fly" || plan.mode === "compare") && (
              <a className="btn-small" href={plan.booking_links.flight} target="_blank" rel="noreferrer nofollow sponsored">
                Find flights (Expedia)
              </a>
            )}
            {plan.booking_links.car && (
              <a className="btn-small" href={plan.booking_links.car} target="_blank" rel="noreferrer nofollow sponsored">
                Rent a car
              </a>
            )}
            {plan.booking_links.rideshare && (
              <a className="btn-small" href={plan.booking_links.rideshare} target="_blank" rel="noreferrer nofollow sponsored">
                Rideshare
              </a>
            )}
          </div>

          {plan.notes.map((n, i) => (
            <div key={i} className="trip-note">{n}</div>
          ))}

          {plan.citations.length > 0 && (
            <div className="ai-cites">
              Estimate sources:{" "}
              {plan.citations.map((c, i) => (
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
