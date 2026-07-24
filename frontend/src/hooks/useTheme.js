import { useCallback, useEffect, useState } from "react";

const THEME_KEY = "tripweaver_theme";

function readInitialTheme() {
  try {
    const saved = localStorage.getItem(THEME_KEY);
    if (saved === "dark" || saved === "light") return saved;
  } catch {
    // localStorage can be blocked (private browsing) - fall through
  }
  if (typeof window !== "undefined" && window.matchMedia) {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  return "dark";
}

/**
 * Single source of truth for the colour scheme.
 *
 * The class lives on <html> (see the inline script in index.html, which
 * applies it before first paint so there's no flash). All theming is done
 * through CSS variables in index.css, so flipping this one class re-themes
 * every component at once.
 */
export function useTheme() {
  const [theme, setTheme] = useState(readInitialTheme);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("dark", theme === "dark");
    root.style.colorScheme = theme;
    try {
      localStorage.setItem(THEME_KEY, theme);
    } catch {
      // saving is a nicety, not a requirement
    }
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((t) => (t === "dark" ? "light" : "dark"));
  }, []);

  return { theme, toggleTheme };
}
