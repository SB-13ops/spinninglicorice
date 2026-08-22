"use client";

import { useEffect, useState } from "react";
import { useAuth } from "../lib/auth";
import { apiGet } from "../lib/api";

type SharedAccount = { owner_id: string; label: string; role: string };

/**
 * Shows the signed-in user and a switcher to act on accounts shared with them.
 * "My account" is always first. Selecting a shared account sets the
 * X-Account-Id the API client sends on every request.
 */
export default function AccountBar() {
  const { me, activeAccountId, setActiveAccountId, logout } = useAuth();
  const [shared, setShared] = useState<SharedAccount[]>([]);

  useEffect(() => {
    // Best-effort: accounts shared *with* me. Endpoint is optional; ignore errors.
    apiGet<SharedAccount[]>("/sharing/shared-with-me")
      .then(setShared)
      .catch(() => setShared([]));
  }, []);

  return (
    <div className="account-bar">
      {shared.length > 0 && (
        <select
          className="account-select"
          value={activeAccountId}
          onChange={(e) => {
            setActiveAccountId(e.target.value);
            window.location.reload();
          }}
        >
          <option value="">My account</option>
          {shared.map((s) => (
            <option key={s.owner_id} value={s.owner_id}>
              {s.label} ({s.role})
            </option>
          ))}
        </select>
      )}
      <span className="account-name">{me?.display_name || me?.email}</span>
      <button className="account-logout" onClick={logout}>
        Sign out
      </button>
    </div>
  );
}
