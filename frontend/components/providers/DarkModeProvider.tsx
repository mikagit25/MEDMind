"use client";

import { useEffect } from "react";
import { useUIStore } from "@/lib/store";

/**
 * Applies the "dark" class to <html> on mount from persisted store state,
 * before the first paint, to avoid flash of wrong theme.
 */
export function DarkModeProvider({ children }: { children: React.ReactNode }) {
  const darkMode = useUIStore((s) => s.darkMode);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
  }, [darkMode]);

  return <>{children}</>;
}
