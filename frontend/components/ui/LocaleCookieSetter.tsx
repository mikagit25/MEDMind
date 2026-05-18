"use client";

import { useEffect } from "react";

/**
 * Syncs the ?lang= URL param to the medmind_locale cookie and localStorage.
 * When user navigates to ?lang=en, this resets the cookie so subsequent
 * pages (without explicit ?lang=) also use English.
 */
export function LocaleCookieSetter({ locale }: { locale: string }) {
  useEffect(() => {
    if (!locale) return;
    // Sync to localStorage so i18n provider picks it up
    localStorage.setItem("medmind_locale", locale);
    // Sync to cookie so SSR pages pick it up
    document.cookie = `medmind_locale=${locale};path=/;max-age=31536000;SameSite=Lax`;
  }, [locale]);

  return null;
}
