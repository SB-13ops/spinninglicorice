"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useAuth } from "../../lib/auth";
import { API_BASE, apiPost } from "../../lib/api";

const ERRORS: Record<string, string> = {
  access_denied: "Sign-in was cancelled.",
  provider_error: "We couldn't complete sign-in with that provider. Please try again.",
  inactive: "This account is inactive.",
};

function AuthCard() {
  const { loginWith, setToken } = useAuth();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!email.trim() || !password) {
      setError("Enter your email and password.");
      return;
    }
    setBusy(true);
    try {
      if (mode === "signup") {
        const body: Record<string, string> = { email: email.trim(), password };
        if (displayName.trim()) body.display_name = displayName.trim();
        const res = await apiPost<{ access_token: string }>("/auth/register", body);
        setToken(res.access_token);
      } else {
        // /auth/login expects OAuth2 form-encoded fields (username, password),
        // not JSON, so this one call bypasses apiPost's JSON body.
        const form = new URLSearchParams();
        form.set("username", email.trim());
        form.set("password", password);
        const resp = await fetch(`${API_BASE}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: form.toString(),
        });
        if (!resp.ok) {
          const detail = await resp.json().catch(() => null);
          throw new Error(detail?.detail || "Incorrect email or password.");
        }
        const data = await resp.json();
        setToken(data.access_token);
      }
      if (typeof window !== "undefined") window.location.href = "/";
    } catch (err) {
      setError((err as Error).message || "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="sl-card" id="signin">
      <h2 className="sl-card-title">{mode === "signup" ? "Create your account" : "Welcome back"}</h2>
      <p className="sl-card-sub">
        {mode === "signup" ? "Start tracking your collection today." : "Sign in to pick up where your shelf left off."}
      </p>

      <button type="button" className="sl-oauth-btn" onClick={() => loginWith("google")}>
        <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
          <path fill="#4285F4" d="M23 12.3c0-.8-.1-1.5-.2-2.3H12v4.5h6.2a5.3 5.3 0 0 1-2.3 3.5v2.9h3.7c2.2-2 3.4-5 3.4-8.6z" />
          <path fill="#34A853" d="M12 23.5c3.1 0 5.7-1 7.6-2.8l-3.7-2.9c-1 .7-2.3 1.1-3.9 1.1-3 0-5.5-2-6.4-4.7H1.8v3A11.5 11.5 0 0 0 12 23.5z" />
          <path fill="#FBBC05" d="M5.6 14.2a6.9 6.9 0 0 1 0-4.4v-3H1.8a11.5 11.5 0 0 0 0 10.4l3.8-3z" />
          <path fill="#EA4335" d="M12 5.1c1.7 0 3.2.6 4.4 1.7l3.3-3.3A11.5 11.5 0 0 0 1.8 6.8l3.8 3C6.5 7.1 9 5.1 12 5.1z" />
        </svg>
        Continue with Google
      </button>
      <button type="button" className="sl-oauth-btn" onClick={() => loginWith("facebook")}>
        <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
          <path fill="#1877F2" d="M24 12a12 12 0 1 0-13.9 11.9v-8.4H7.1V12h3V9.4c0-3 1.8-4.6 4.5-4.6 1.3 0 2.6.2 2.6.2v2.9h-1.5c-1.5 0-1.9.9-1.9 1.8V12h3.3l-.5 3.5h-2.8v8.4A12 12 0 0 0 24 12z" />
        </svg>
        Continue with Facebook
      </button>

      <div className="sl-divider">or</div>

      <form onSubmit={submit}>
        <div className="sl-field">
          {mode === "signup" && (
            <div>
              <label htmlFor="displayName">Name (optional)</label>
              <input
                id="displayName"
                className="sl-input"
                type="text"
                placeholder="Your name"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
              />
            </div>
          )}
          <div>
            <label htmlFor="email">Email</label>
            <input
              id="email"
              className="sl-input"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
            />
          </div>
          <div>
            <label htmlFor="password">Password</label>
            <input
              id="password"
              className="sl-input"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={mode === "signup" ? "new-password" : "current-password"}
            />
          </div>
          {error && <div className="sl-form-error">{error}</div>}
          <button type="submit" className="sl-btn-primary" disabled={busy}>
            {busy ? "Please wait…" : mode === "signup" ? "Create account" : "Sign in"}
          </button>
        </div>
      </form>

      <p className="sl-linkrow">
        {mode === "signin" ? (
          <button type="button" className="sl-switch" onClick={() => { setMode("signup"); setError(""); }}>
            New here? Create an account
          </button>
        ) : (
          <button type="button" className="sl-switch" onClick={() => { setMode("signin"); setError(""); }}>
            Already have an account? Sign in
          </button>
        )}
      </p>
    </div>
  );
}

function LoginInner() {
  const params = useSearchParams();
  const err = params.get("error");

  return (
    <div className="sl-landing">
      <nav className="sl-nav">
        <a href="#about">What it is</a>
        <a href="#features">Features</a>
        <a href="#hunt">Hunt</a>
        <a href="#signin" className="sl-btn-primary" style={{ display: "inline-block", width: "auto", padding: "0 20px" }}>
          Sign in
        </a>
      </nav>

      <div className="sl-container">
        <section className="sl-hero">
          <div className="sl-hero-blob" />
          <div className="sl-hero-text">
            <img
              src="/spinninglicorice-badge.png"
              alt="SpinningLicorice — records, music, connections"
              className="sl-disc"
            />
            <h1 className="sl-hero-h1">Your collection. Your hunt. Your music.</h1>
            <p className="sl-hero-sub">
              SpinningLicorice is the home for your vinyl — track what you own, hunt down what
              you&apos;re missing, and see your collection the way a real collector does.
            </p>
          </div>

          <div>
            {err && <div className="sl-form-error" style={{ marginBottom: 16 }}>{ERRORS[err] || "Sign-in failed. Please try again."}</div>}
            <AuthCard />
          </div>
        </section>

        <section id="about" style={{ padding: "24px 0 88px" }}>
          <span className="sl-eyebrow">What it is</span>
          <p className="sl-about-p">
            SpinningLicorice turns a shelf of records into a living collection. Add what you own
            by hand, scan a barcode, or search Discogs — rate it, note the pressing, track what
            you paid. From there, SpinningLicorice shows you what your collection is actually
            worth over time, which artists you&apos;re closest to completing, and gives you a
            shareable card that sums up your taste in one image. When you&apos;re ready to add to
            the stack, Hunter watches Discogs for deals that match what you&apos;re after,
            described in plain English.
          </p>
        </section>

        <section id="features" className="sl-features">
          <div>
            <div className="sl-feature-dot" style={{ background: "var(--color-accent)" }} />
            <h2 className="sl-feature-h2">Build your collection</h2>
            <ul className="sl-feature-list">
              <li>Add records three ways — type them in, search Discogs, or scan the barcode with your camera</li>
              <li>Rate and note every record, track condition and what you paid</li>
              <li>Keep a wantlist separate from what you actually own</li>
            </ul>
          </div>

          <div>
            <div className="sl-feature-dot" style={{ background: "var(--color-accent-2-500)" }} />
            <h2 className="sl-feature-h2">Know your collection</h2>
            <ul className="sl-feature-list">
              <li>See your collection&apos;s total worth, tracked over time, with your biggest gainers and droppers</li>
              <li>Find out how close you are to completing any artist&apos;s catalog — and what&apos;s missing</li>
              <li>Get a shareable Collector Card: your top labels, era, rarity, and worth in one image</li>
            </ul>
          </div>

          <div id="hunt">
            <div className="sl-feature-dot" style={{ background: "var(--color-accent)" }} />
            <h2 className="sl-feature-h2">Hunt smarter</h2>
            <ul className="sl-feature-list">
              <li>Tell Hunter what you&apos;re after in plain English — it parses your request and watches for matches</li>
              <li>AI-assisted research on pressings and rare finds</li>
            </ul>
          </div>

          <div>
            <div className="sl-feature-dot" style={{ background: "var(--color-accent-2-500)" }} />
            <h2 className="sl-feature-h2">Beyond the shelf</h2>
            <ul className="sl-feature-list">
              <li>Concert Scout surfaces shows tied to artists in your collection</li>
              <li>Plan the trip — gas costs calculated exactly, hotel and flight estimates for the ones further out</li>
              <li>Share your collection or invite others to help manage it together</li>
            </ul>
          </div>
        </section>

        <footer className="sl-footer">
          <span>© SpinningLicorice</span>
          <a href="#signin">Contact</a>
          <a href="#signin">Privacy</a>
          <a href="#signin">Terms</a>
        </footer>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="sl-landing" />}>
      <LoginInner />
    </Suspense>
  );
}
