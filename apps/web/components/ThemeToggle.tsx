"use client";

import { useEffect, useState } from "react";

const THEME_KEY = "spinninglicorice.theme";

/** Light/dark toggle. Persists to localStorage; layout.tsx has a small inline
 * script that applies the stored choice before paint, so there's no flash of
 * the wrong theme on load. */
export default function ThemeToggle() {
  const [theme, setTheme] = useState<"light" | "dark">("light");

  useEffect(() => {
    const stored = typeof window !== "undefined" ? localStorage.getItem(THEME_KEY) : null;
    setTheme(stored === "dark" ? "dark" : "light");
  }, []);

  function toggle() {
    const next = theme === "dark" ? "light" : "dark";
    setTheme(next);
    localStorage.setItem(THEME_KEY, next);
    document.documentElement.setAttribute("data-theme", next);
  }

  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={toggle}
      aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
      title={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
    >
      {theme === "dark" ? "☀" : "☾"}
    </button>
  );
}
