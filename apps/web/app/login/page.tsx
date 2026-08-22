"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useAuth } from "../../lib/auth";

const ERRORS: Record<string, string> = {
  access_denied: "Sign-in was cancelled.",
  provider_error: "We couldn't complete sign-in with that provider. Please try again.",
  inactive: "This account is inactive.",
};

function LoginInner() {
  const { loginWith } = useAuth();
  const params = useSearchParams();
  const err = params.get("error");

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <div className="auth-logo">BURNT JACKET</div>
        <div className="auth-tagline">Your collection. Your hunt. Your music.</div>

        {err && <div className="auth-error">{ERRORS[err] || "Sign-in failed. Please try again."}</div>}

        <button className="auth-btn auth-google" onClick={() => loginWith("google")}>
          Continue with Google
        </button>
        <button className="auth-btn auth-facebook" onClick={() => loginWith("facebook")}>
          Continue with Facebook
        </button>

        <div className="auth-fine">
          By continuing you agree to Burnt Jacket&apos;s terms. We only use your name and
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
