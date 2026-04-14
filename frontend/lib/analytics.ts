/**
 * PostHog analytics wrapper.
 * All calls are no-ops when NEXT_PUBLIC_POSTHOG_KEY is not set,
 * so analytics is purely opt-in and never crashes the app.
 */
import posthog from "posthog-js";

let initialized = false;

export function initAnalytics() {
  if (initialized || typeof window === "undefined") return;
  const key = process.env.NEXT_PUBLIC_POSTHOG_KEY;
  if (!key) return;

  posthog.init(key, {
    api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://app.posthog.com",
    capture_pageview: false,   // we capture manually via usePageView
    capture_pageleave: true,
    autocapture: false,        // only track explicitly — avoids capturing PII
    persistence: "localStorage+cookie",
    sanitize_properties: (props) => {
      // Strip any fields that could contain PII before sending
      delete props.$ip;
      return props;
    },
  });
  initialized = true;
}

export function identifyUser(userId: string, traits?: Record<string, unknown>) {
  if (!initialized) return;
  posthog.identify(userId, traits);
}

export function trackEvent(event: string, properties?: Record<string, unknown>) {
  if (!initialized) return;
  posthog.capture(event, properties);
}

export function trackPageView(path: string) {
  if (!initialized) return;
  posthog.capture("$pageview", { $current_url: path });
}

export function resetUser() {
  if (!initialized) return;
  posthog.reset();
}
