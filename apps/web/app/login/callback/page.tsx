"use client";

import { useEffect, useState } from "react";
import { useAuth } from "../../../lib/auth";

/**
 * The API redirects here after social login with the token in the URL fragment
 * (#token=...&next=...). Fragments are never sent to servers or logged in
 * referrers, so this keeps the token out of server logs. We read it, store it,
 * and forward the user on.
 */
export default function LoginCallbackPage() {
  const { setToken } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const hash = window.location.hash.startsWith("#")
      ? window.location.hash.slice(1)
      : window.location.hash;
    const params = new URLSearchParams(hash);
    const token = params.get("token");
    const next = params.get("next") || "/";

    if (!token) {
      setError("No sign-in token was returned. Please try again.");
      return;
    }
    setToken(token);
    // Clear the fragment and go to the intended page.
    const dest = next.startsWith("/") ? next : "/";
    window.location.replace(dest);
  }, [setToken]);

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <div className="auth-logo">BURNT JACKET</div>
        {error ? (
          <>
            <div className="auth-error">{error}</div>
            <a className="auth-btn" href="/login">
              Back to sign in
            </a>
          </>
        ) : (
          <div className="auth-tagline">Signing you in…</div>
        )}
      </div>
    </div>
  );
}
