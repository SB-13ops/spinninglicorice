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

function EmailPasswordForm() {
  const { setToken } = useAuth();
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
    <form className="auth-email-form" onSubmit={submit}>
      {mode === "signup" && (
        <input
          className="auth-input"
          type="text"
          placeholder="Name (optional)"
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
        />
      )}
      <input
        className="auth-input"
        type="email"
        placeholder="Email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        autoComplete="email"
      />
      <input
        className="auth-input"
        type="password"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        autoComplete={mode === "signup" ? "new-password" : "current-password"}
      />
      {error && <div className="auth-error">{error}</div>}
      <button className="auth-btn auth-email" type="submit" disabled={busy}>
        {busy ? "Please wait…" : mode === "signup" ? "Create account" : "Sign in"}
      </button>
      <button
        type="button"
        className="auth-switch"
        onClick={() => {
          setMode(mode === "signin" ? "signup" : "signin");
          setError("");
        }}
      >
        {mode === "signin" ? "New here? Create an account" : "Already have an account? Sign in"}
      </button>
    </form>
  );
}

function LoginInner() {
  const { loginWith } = useAuth();
  const params = useSearchParams();
  const err = params.get("error");

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <div className="auth-logo">SPINNINGLICORICE</div>
        <div className="auth-tagline">Your collection. Your hunt. Your music.</div>

        {err && <div className="auth-error">{ERRORS[err] || "Sign-in failed. Please try again."}</div>}

        <EmailPasswordForm />

        <div className="auth-divider"><span>or</span></div>

        <button className="auth-btn auth-google" onClick={() => loginWith("google")}>
          Continue with Google
        </button>
        <button className="auth-btn auth-facebook" onClick={() => loginWith("facebook")}>
          Continue with Facebook
        </button>

        <div className="auth-fine">
          By continuing you agree to SpinningLicorice&apos;s terms. We only use your name and
          email to create your account.
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="auth-wrap" />}>
      <LoginInner />
    </Suspense>
  );
}
