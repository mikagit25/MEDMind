/**
 * PostHog analytics wrapper.
 * All calls are no-ops when NEXT_PUBLIC_POSTHOG_KEY is not set,
 * so analytics is purely opt-in and never crashes the app.
 * posthog-js is an optional dependency — gracefully absent in dev.
 */

// eslint-disable-next-line @typescript-eslint/no-explicit-any
let ph: any = null;
let initialized = false;

function getPosthog() {
  if (ph !== null) return ph;
  try {
    // Dynamic require so TS doesn't error if package is absent
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    ph = require("posthog-js").default;
  } catch {
    ph = undefined;
  }
  return ph;
}

export function initAnalytics() {
  if (initialized || typeof window === "undefined") return;
  const key = process.env.NEXT_PUBLIC_POSTHOG_KEY;
  if (!key) return;

  const posthog = getPosthog();
  if (!posthog) return;

  posthog.init(key, {
    api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://app.posthog.com",
    capture_pageview: false,
    capture_pageleave: true,
    autocapture: false,
    persistence: "localStorage+cookie",
    sanitize_properties: (props: Record<string, unknown>) => {
      delete props.$ip;
      return props;
    },
  });
  initialized = true;
}

export function identifyUser(userId: string, traits?: Record<string, unknown>) {
  if (!initialized) return;
  getPosthog()?.identify(userId, traits);
}

export function trackEvent(event: string, properties?: Record<string, unknown>) {
  if (!initialized) return;
  getPosthog()?.capture(event, properties);
}

export function trackPageView(path: string) {
  if (!initialized) return;
  getPosthog()?.capture("$pageview", { $current_url: path });
}

export function resetUser() {
  if (!initialized) return;
  getPosthog()?.reset();
}
