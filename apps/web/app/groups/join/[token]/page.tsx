"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useAuth } from "../../../../lib/auth";
import { apiPost } from "../../../../lib/api";

export default function JoinGroupPage() {
  const { token: authToken, loading } = useAuth();
  const params = useParams();
  const joinToken = String(params.token || "");
  const [msg, setMsg] = useState("Joining group…");

  useEffect(() => {
    if (loading) return;
    if (!authToken) {
      localStorage.setItem("spinninglicorice.pendingGroupInvite", joinToken);
      window.location.href = "/login";
      return;
    }
    apiPost<{ id: string; name: string }>(`/groups/join/${joinToken}`)
      .then((g) => {
        setMsg(`Joined ${g.name}! Redirecting…`);
        setTimeout(() => (window.location.href = `/groups/${g.id}`), 900);
      })
      .catch((e) => setMsg((e as Error).message || "This invite is no longer valid."));
  }, [authToken, loading, joinToken]);

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <div className="auth-logo">SPINNINGLICORICE</div>
        <div className="auth-tagline">{msg}</div>
      </div>
    </div>
  );
}
