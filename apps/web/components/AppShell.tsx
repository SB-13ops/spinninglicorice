"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "../lib/auth";
import AccountBar from "./AccountBar";

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

  // Public routes render without the app chrome or an auth requirement.
  const isPublic = pathname.startsWith("/login") || pathname.startsWith("/shared");

  // Redirect unauthenticated users to /login (once auth state has loaded).
  useEffect(() => {
    if (!isPublic && !loading && !token) {
      router.replace("/login");
    }
  }, [isPublic, loading, token, router]);

  if (isPublic) {
    return <>{children}</>;
  }

  if (loading || !token) {
    // Avoid flashing the app before we know the auth state.
    return <div className="app-loading">Loading Burnt Jacket…</div>;
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="logo">BURNT JACKET</div>
          <div className="tagline">Your collection. Your hunt. Your music.</div>
        </div>
        <div className="top-main">
          <div className="search-wrap">
            <input className="search" placeholder="Search records, artists, concerts or ask Burnt Jacket..." />
            <div className="try">
              Try:
              <span className="chip">Find Dead albums I&apos;m missing under $50</span>
              <span className="chip">Shows near me this weekend</span>
            </div>
          </div>
          <AccountBar />
        </div>
      </header>

      <aside className="sidebar">
        {nav.map(([href, icon, label]) => (
          <a key={href} className={`nav-item ${pathname === href ? "active" : ""}`} href={href}>
            <span className="nav-icon">{icon}</span>
            {label}
          </a>
        ))}
        <div className="sidebar-footer">
          Burnt Jacket V1<br />
          Beta
        </div>
      </aside>

      <main className="content">{children}</main>

      <footer className="footer">“Keep on truckin’...” – The Grateful Dead</footer>
    </div>
  );
}
