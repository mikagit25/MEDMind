/**
 * Google Analytics 4 (gtag.js) helpers.
 * No-op when NEXT_PUBLIC_GA_ID is not set.
 */

export const GA_ID = process.env.NEXT_PUBLIC_GA_ID ?? "G-GPK32JQ0NJ";

declare global {
  interface Window {
    gtag?: (...args: unknown[]) => void;
    dataLayer?: unknown[];
  }
}

export function gtagEvent(
  action: string,
  params?: Record<string, string | number | boolean>
) {
  if (typeof window === "undefined" || !window.gtag || !GA_ID) return;
  window.gtag("event", action, params);
}

// ── Typed event helpers ──────────────────────────────────────────────────────

export const ga = {
  lessonComplete: (lessonTitle: string, quizScore?: number) =>
    gtagEvent("lesson_complete", {
      lesson_title: lessonTitle,
      ...(quizScore !== undefined && { quiz_score: quizScore }),
    }),

  quizAnswered: (correct: boolean, moduleTitle: string) =>
    gtagEvent("quiz_answered", { correct, module_title: moduleTitle }),

  aiTutorMessage: (specialty: string) =>
    gtagEvent("ai_tutor_message", { specialty }),

  simulationStarted: (specialty: string, difficulty: string) =>
    gtagEvent("simulation_started", { specialty, difficulty }),

  simulationEvaluated: (specialty: string) =>
    gtagEvent("simulation_evaluated", { specialty }),

  flashcardReviewed: (rating: number) =>
    gtagEvent("flashcard_reviewed", { rating }),

  articleViewed: (slug: string, title: string) =>
    gtagEvent("article_view", { article_slug: slug, article_title: title }),

  moduleStarted: (moduleName: string) =>
    gtagEvent("module_started", { module_name: moduleName }),

  moduleCompleted: (moduleName: string) =>
    gtagEvent("module_completed", { module_name: moduleName }),

  signUp: (method: string) =>
    gtagEvent("sign_up", { method }),

  login: (method: string) =>
    gtagEvent("login", { method }),

  upgrade: (plan: string) =>
    gtagEvent("begin_checkout", { item_name: plan }),

  search: (query: string, context: string) =>
    gtagEvent("search", { search_term: query, context }),
};
