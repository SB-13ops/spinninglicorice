"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useAuth } from "../../../lib/auth";
import { apiPost } from "../../../lib/api";

export default function InviteAcceptPage() {
  const { token, loading } = useAuth();
  const params = useParams();
  const inviteToken = String(params.token || "");
  const [status, setStatus] = useState<"idle" | "accepting" | "done" | "error">("idle");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (loading) return;
    if (!token) {
      // Not signed in: remember the invite and send to login.
      localStorage.setItem("spinninglicorice.pendingInvite", inviteToken);
      window.location.href = "/login";
      return;
    }
    setStatus("accepting");
    apiPost(`/sharing/invites/${inviteToken}/accept`)
      .then(() => {
        setStatus("done");
        setMessage("You now have access. Redirecting…");
        setTimeout(() => (window.location.href = "/"), 1200);
      })
      .catch((e) => {
        setStatus("error");
        setMessage((e as Error).message || "This invite is no longer valid.");
      });
  }, [token, loading, inviteToken]);

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <div className="auth-logo">SPINNINGLICORICE</div>
        <div className="auth-tagline">
          {status === "error" ? message : status === "done" ? message : "Accepting invite…"}
        </div>
        {status === "error" && (
          <a className="auth-btn" href="/">
            Go home
          </a>
        )}
      </div>
    </div>
  );
}
