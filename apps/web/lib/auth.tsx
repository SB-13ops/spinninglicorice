"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  ReactNode,
} from "react";
import { API_BASE, setAuthAccessors } from "./api";

const TOKEN_KEY = "spinninglicorice.token";
const ACCOUNT_KEY = "spinninglicorice.account"; // active account id (X-Account-Id), "" = own

type Me = { id: string; email: string; display_name: string | null };

type AuthState = {
  token: string | null;
  me: Me | null;
  activeAccountId: string; // "" means own account
  loading: boolean;
  loginWith: (provider: "google" | "facebook") => void;
  logout: () => void;
  setActiveAccountId: (id: string) => void;
  setToken: (t: string) => void;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(null);
  const [me, setMe] = useState<Me | null>(null);
  const [activeAccountId, setActiveAccountIdState] = useState<string>("");
  const [loading, setLoading] = useState(true);

  // Wire the API client to read the current token + active account.
  useEffect(() => {
    setAuthAccessors(
      () => token,
      () => activeAccountId,
      () => logout()
    );
  }, [token, activeAccountId]);

  // Load persisted state on mount.
  useEffect(() => {
    const t = typeof window !== "undefined" ? localStorage.getItem(TOKEN_KEY) : null;
    const a = typeof window !== "undefined" ? localStorage.getItem(ACCOUNT_KEY) : null;
    if (a) setActiveAccountIdState(a);
    if (t) {
      setTokenState(t);
    } else {
      setLoading(false);
    }
  }, []);

  // Fetch /auth/me whenever the token changes.
  useEffect(() => {
    if (!token) {
      setMe(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/auth/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error("bad token");
        const data = await res.json();
        if (!cancelled) setMe(data);
      } catch {
        if (!cancelled) {
          localStorage.removeItem(TOKEN_KEY);
          setTokenState(null);
          setMe(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  const setToken = useCallback((t: string) => {
    localStorage.setItem(TOKEN_KEY, t);
    setTokenState(t);
    setLoading(true);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(ACCOUNT_KEY);
    setTokenState(null);
    setMe(null);
    setActiveAccountIdState("");
    if (typeof window !== "undefined") window.location.href = "/login";
  }, []);

  const setActiveAccountId = useCallback((id: string) => {
    if (id) localStorage.setItem(ACCOUNT_KEY, id);
    else localStorage.removeItem(ACCOUNT_KEY);
    setActiveAccountIdState(id);
  }, []);

  const loginWith = useCallback((provider: "google" | "facebook") => {
    const next = typeof window !== "undefined" ? window.location.pathname : "/";
    window.location.href = `${API_BASE}/auth/${provider}/login?redirect_path=${encodeURIComponent(
      next
    )}`;
  }, []);

  return (
    <AuthContext.Provider
      value={{
        token,
        me,
        activeAccountId,
        loading,
        loginWith,
        logout,
        setActiveAccountId,
        setToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
