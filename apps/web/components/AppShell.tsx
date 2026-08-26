"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "../lib/auth";
import AccountBar from "./AccountBar";
import TopSearch from "./TopSearch";
import ThemeToggle from "./ThemeToggle";

const nav = [
  ["/", "⌂", "HOME"],
  ["/collection", "◉", "COLLECTION"],
  ["/hunter", "♧", "HUNTER"],
  ["/scout", "♪", "SCOUT"],
  ["/dna", "⚯", "DNA"],
  ["/insights", "$", "INSIGHTS"],
  ["/groups", "⚑", "GROUPS"],
  ["/sharing", "⇄", "SHARING"],
  ["/profile", "♙", "PROFILE"],
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { token, loading } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  // Close the mobile drawer whenever the route changes.
  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  // Public routes render without the app chrome or an auth requirement.
  const isPublic = pathname.startsWith("/login") || pathname.startsWith("/shared");

  // Redirect unauthenticated users to /login (once auth state has loaded).
  useEffect(() => {
    if (!isPublic && !loading && !token) {
      router.replace("/login");
    }
  }, [isPublic, loading, token, router]);

  // Safety net: if someone is already authenticated and lands on /login
  // anyway (e.g. a stale bookmark, or a redirect_path edge case), move them
  // forward instead of showing the sign-in form to an already-signed-in user.
  // /login/callback handles its own redirect, so it's excluded here.
  useEffect(() => {
    if (
      pathname.startsWith("/login") &&
      !pathname.startsWith("/login/callback") &&
      !loading &&
      token
    ) {
      router.replace("/");
    }
  }, [pathname, loading, token, router]);

  if (isPublic) {
    return <>{children}</>;
  }

  if (loading || !token) {
    // Avoid flashing the app before we know the auth state.
    return <div className="app-loading">Loading SpinningLicorice…</div>;
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <button
          type="button"
          className="hamburger"
          aria-label="Open menu"
          onClick={() => setMenuOpen((v) => !v)}
        >
          ☰
        </button>
        <div className="brand">
          <div className="logo">SPINNINGLICORICE</div>
          <div className="tagline">Your collection. Your hunt. Your music.</div>
        </div>
        <div className="top-main">
          <TopSearch />
          <ThemeToggle />
          <div className="search-wrap">
            <input className="search" placeholder="Search records, artists, concerts or ask SpinningLicorice..." />
            <div className="try">
              Try:
              <span className="chip">Find Dead albums I&apos;m missing under $50</span>
              <span className="chip">Shows near me this weekend</span>
            </div>
          </div>
          <AccountBar />
        </div>
      </header>

      {menuOpen && <div className="sidebar-backdrop" onClick={() => setMenuOpen(false)} />}

      <aside className={`sidebar ${menuOpen ? "open" : ""}`}>
        {nav.map(([href, icon, label]) => (
          <a key={href} className={`nav-item ${pathname === href ? "active" : ""}`} href={href}>
            <span className="nav-icon">{icon}</span>
            {label}
          </a>
        ))}
        <div className="sidebar-footer">
          SpinningLicorice V1<br />
          Beta
        </div>
      </aside>

      <main className="content">{children}</main>

      <footer className="footer">“Keep on truckin’...” – The Grateful Dead</footer>
    </div>
  );
}
