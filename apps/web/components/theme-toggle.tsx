"use client";

import { useTheme } from "next-themes";
import { useSyncExternalStore } from "react";

import { messages } from "@/lib/i18n";

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const mounted = useSyncExternalStore(
    () => () => undefined,
    () => true,
    () => false,
  );

  const isDark = mounted && resolvedTheme === "dark";
  const label = isDark ? messages["es-CO"].themeLight : messages["es-CO"].themeDark;

  return (
    <button
      className="icon-button"
      type="button"
      aria-label={label}
      title={label}
      disabled={!mounted}
      onClick={() => setTheme(isDark ? "light" : "dark")}
    >
      <span aria-hidden="true">{isDark ? "☼" : "◐"}</span>
    </button>
  );
}
