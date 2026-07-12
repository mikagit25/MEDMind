/**
 * Product analytics — self-hosted, privacy-first. No third-party trackers.
 *
 * Privacy rules (mirrors backend validation):
 * - meta MUST NOT contain free-form user text (prompts, queries, answers)
 * - Only structured metadata: mode, specialty, step, score, etc.
 * - Events are batched and sent via sendBeacon (survives page unload)
 * - IP never stored on backend
 */

const TRACK_URL = `${process.env.NEXT_PUBLIC_API_URL ?? "/api/v1"}/analytics/track`;

export type EventType =
  | "signup"
  | "onboarding_step"
  | "onboarding_completed"
  | "lesson_started"
  | "lesson_completed"
  | "module_started"
  | "module_completed"
  | "flashcard_review"
  | "ai_question"
  | "quiz_completed"
  | "public_page_view"
  | "search"
  | "app_open";

export interface AnalyticsEvent {
  event_type: EventType;
  entity_type?: string;
  entity_id?: string;
  /** Structured only — no free-form user text */
  meta?: Record<string, string | number | boolean>;
  locale?: string;
  platform?: "web" | "mobile";
  anon_id?: string;
}

// ── Stable anon ID (no PII — just a random UUID per browser) ─────────────────

function getAnonId(): string {
  if (typeof window === "undefined") return "";
  try {
    let id = localStorage.getItem("_mm_anon");
    if (!id) {
      id = crypto.randomUUID();
      localStorage.setItem("_mm_anon", id);
    }
    return id;
  } catch {
    return "";
  }
}

// ── Queue & flush ─────────────────────────────────────────────────────────────

let _queue: AnalyticsEvent[] = [];
let _timer: ReturnType<typeof setTimeout> | null = null;

function _flush() {
  if (_queue.length === 0) return;
  const batch = _queue.splice(0, 20);
  const anonId = getAnonId();
  const payload = JSON.stringify({
    events: batch.map((e) => ({ ...e, anon_id: e.anon_id ?? anonId })),
  });

  if (typeof navigator !== "undefined" && navigator.sendBeacon) {
    const sent = navigator.sendBeacon(
      TRACK_URL,
      new Blob([payload], { type: "application/json" }),
    );
    if (!sent) {
      fetch(TRACK_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: payload,
        keepalive: true,
      }).catch(() => {});
    }
  } else {
    fetch(TRACK_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: payload,
    }).catch(() => {});
  }
}

function _scheduleFlush() {
  if (_timer) return;
  _timer = setTimeout(() => {
    _timer = null;
    _flush();
  }, 2000);
}

if (typeof window !== "undefined") {
  window.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") _flush();
  });
  window.addEventListener("beforeunload", () => _flush());
}

// ── Core track function ───────────────────────────────────────────────────────

export function track(event: AnalyticsEvent): void {
  if (typeof window === "undefined") return;
  _queue.push(event);
  if (_queue.length >= 20) {
    if (_timer) { clearTimeout(_timer); _timer = null; }
    _flush();
  } else {
    _scheduleFlush();
  }
}

// ── Convenience wrappers ──────────────────────────────────────────────────────

export const analytics = {
  signup: (role: string) =>
    track({ event_type: "signup", meta: { role } }),

  onboardingStep: (step: number) =>
    track({ event_type: "onboarding_step", meta: { step } }),

  onboardingCompleted: (role: string, specialty?: string) =>
    track({ event_type: "onboarding_completed", meta: { role, ...(specialty ? { specialty } : {}) } }),

  lessonStarted: (lessonId: string, moduleId: string, locale?: string) =>
    track({ event_type: "lesson_started", entity_type: "lesson", entity_id: lessonId, meta: { module_id: moduleId }, locale }),

  lessonCompleted: (lessonId: string, moduleId: string, locale?: string) =>
    track({ event_type: "lesson_completed", entity_type: "lesson", entity_id: lessonId, meta: { module_id: moduleId }, locale }),

  moduleStarted: (moduleId: string, specialty?: string) =>
    track({ event_type: "module_started", entity_type: "module", entity_id: moduleId, meta: specialty ? { specialty } : undefined }),

  moduleCompleted: (moduleId: string, specialty?: string) =>
    track({ event_type: "module_completed", entity_type: "module", entity_id: moduleId, meta: specialty ? { specialty } : undefined }),

  aiQuestion: (mode: string, specialty?: string) =>
    track({ event_type: "ai_question", meta: { mode, ...(specialty ? { specialty } : {}) } }),

  flashcardReview: (cardId: string, rating: number) =>
    track({ event_type: "flashcard_review", entity_type: "flashcard", entity_id: cardId, meta: { rating } }),

  quizCompleted: (moduleId: string, score: number, total: number) =>
    track({ event_type: "quiz_completed", entity_type: "module", entity_id: moduleId, meta: { score, total } }),

  pageView: (slug: string, entityType?: string) =>
    track({ event_type: "public_page_view", entity_type: entityType ?? "page", entity_id: slug }),

  search: (entityType: string) =>
    track({ event_type: "search", entity_type: entityType }),
};

// ── Legacy shims (AnalyticsProvider uses these — kept as no-ops) ──────────────

/** @deprecated Use analytics.* helpers instead */
export function initAnalytics(): void {}

/** @deprecated No-op: user identity tracked server-side via JWT */
export function identifyUser(_userId: string, _traits?: Record<string, unknown>): void {}

/** @deprecated Use analytics.pageView() instead */
export function trackEvent(_event: string, _props?: Record<string, unknown>): void {}

/** @deprecated Use analytics.pageView() instead */
export function trackPageView(path: string): void {
  analytics.pageView(path);
}

/** @deprecated No-op */
export function resetUser(): void {}
