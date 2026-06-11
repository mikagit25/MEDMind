"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

type Card = { question: string; answer: string; difficulty: string };
type DeckData = {
  token: string;
  name: string;
  description: string | null;
  card_count: number;
  cards: Card[];
  view_count: number;
  created_at: string | null;
};

type CardState = "question" | "answer";

export default function SharedDeckPage() {
  const params = useParams();
  const token = params?.token as string;

  const [deck, setDeck] = useState<DeckData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cardIndex, setCardIndex] = useState(0);
  const [cardState, setCardState] = useState<CardState>("question");
  const [mode, setMode] = useState<"browse" | "study">("browse");

  useEffect(() => {
    if (!token) return;
    fetch(`${API_URL}/public/decks/${token}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then(setDeck)
      .catch((e) => setError(e === 404 ? "This deck link is no longer active." : "Failed to load deck."))
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return (
      <div className="min-h-screen bg-bg flex items-center justify-center">
        <div className="font-syne font-bold text-ink animate-pulse">Loading deck…</div>
      </div>
    );
  }

  if (error || !deck) {
    return (
      <div className="min-h-screen bg-bg flex items-center justify-center px-4">
        <div className="max-w-md w-full text-center">
          <div className="text-5xl mb-4">🔗</div>
          <h1 className="font-syne font-black text-xl text-ink mb-2">Deck Not Found</h1>
          <p className="font-serif text-sm text-ink-3 mb-6">{error ?? "This link may have been deactivated."}</p>
          <Link
            href="/register"
            className="inline-block px-6 py-2.5 rounded-xl bg-ink text-white font-syne font-bold text-sm hover:bg-ink-2 transition-colors"
          >
            Create Your Own Deck
          </Link>
        </div>
      </div>
    );
  }

  const card = deck.cards[cardIndex];

  function flip() {
    setCardState((s) => (s === "question" ? "answer" : "question"));
  }

  function next() {
    setCardIndex((i) => Math.min(i + 1, deck!.cards.length - 1));
    setCardState("question");
  }

  function prev() {
    setCardIndex((i) => Math.max(i - 1, 0));
    setCardState("question");
  }

  const DIFFICULTY_COLOR: Record<string, string> = {
    easy: "text-green-600 bg-green-50 border-green-200",
    medium: "text-amber-600 bg-amber-50 border-amber-200",
    hard: "text-red-600 bg-red-50 border-red-200",
  };

  return (
    <div className="min-h-screen bg-bg">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-3">
            <span className="font-syne font-semibold text-xs text-ink-3 bg-bg-2 px-2 py-0.5 rounded">
              Shared Deck
            </span>
            <span className="font-serif text-xs text-ink-3/60">
              {deck.view_count} views
            </span>
          </div>
          <h1 className="font-syne font-black text-2xl sm:text-3xl text-ink mb-2">
            {deck.name}
          </h1>
          {deck.description && (
            <p className="font-serif text-sm text-ink-3">{deck.description}</p>
          )}
          <p className="font-serif text-xs text-ink-3/60 mt-1">
            {deck.card_count} cards
          </p>
        </div>

        {/* Mode toggle */}
        <div className="flex items-center gap-2 mb-6">
          <button
            onClick={() => setMode("browse")}
            className={`px-4 py-1.5 rounded-lg font-syne font-semibold text-sm transition-colors ${
              mode === "browse" ? "bg-ink text-white" : "bg-surface border border-border text-ink-2 hover:border-ink"
            }`}
          >
            Browse All
          </button>
          <button
            onClick={() => { setMode("study"); setCardIndex(0); setCardState("question"); }}
            className={`px-4 py-1.5 rounded-lg font-syne font-semibold text-sm transition-colors ${
              mode === "study" ? "bg-ink text-white" : "bg-surface border border-border text-ink-2 hover:border-ink"
            }`}
          >
            Study Mode
          </button>
        </div>

        {/* Study mode — flashcard */}
        {mode === "study" && card && (
          <div className="mb-8">
            <div className="text-center text-xs font-syne font-semibold text-ink-3 mb-4">
              Card {cardIndex + 1} of {deck.cards.length}
            </div>

            {/* Card */}
            <div
              onClick={flip}
              className="cursor-pointer select-none bg-surface border-2 border-border hover:border-ink rounded-2xl p-8 min-h-48 flex flex-col items-center justify-center text-center transition-all"
            >
              <div className="font-syne font-bold text-xs text-ink-3 uppercase tracking-widest mb-4">
                {cardState === "question" ? "Question — tap to reveal" : "Answer"}
              </div>
              <p className="font-serif text-base text-ink leading-relaxed">
                {cardState === "question" ? card.question : card.answer}
              </p>
              {card.difficulty && (
                <span className={`mt-4 px-2 py-0.5 rounded-md border font-syne font-semibold text-xs ${DIFFICULTY_COLOR[card.difficulty] ?? ""}`}>
                  {card.difficulty}
                </span>
              )}
            </div>

            {/* Navigation */}
            <div className="flex items-center justify-between mt-5">
              <button
                onClick={prev}
                disabled={cardIndex === 0}
                className="px-5 py-2 rounded-xl border border-border font-syne font-bold text-sm text-ink hover:border-ink disabled:opacity-30 transition-colors"
              >
                ← Prev
              </button>
              <button
                onClick={flip}
                className="px-5 py-2 rounded-xl bg-surface border border-border font-syne font-bold text-sm text-ink hover:border-ink transition-colors"
              >
                Flip
              </button>
              <button
                onClick={next}
                disabled={cardIndex === deck.cards.length - 1}
                className="px-5 py-2 rounded-xl border border-border font-syne font-bold text-sm text-ink hover:border-ink disabled:opacity-30 transition-colors"
              >
                Next →
              </button>
            </div>
          </div>
        )}

        {/* Browse mode — card list */}
        {mode === "browse" && (
          <div className="space-y-3 mb-8">
            {deck.cards.map((c, i) => (
              <div
                key={i}
                className="bg-surface border border-border rounded-xl p-4"
              >
                <div className="flex items-start justify-between gap-3 mb-2">
                  <p className="font-syne font-bold text-sm text-ink">{c.question}</p>
                  {c.difficulty && (
                    <span className={`shrink-0 px-2 py-0.5 rounded-md border font-syne font-semibold text-xs ${DIFFICULTY_COLOR[c.difficulty] ?? ""}`}>
                      {c.difficulty}
                    </span>
                  )}
                </div>
                <p className="font-serif text-sm text-ink-2 border-t border-border pt-2 mt-2">
                  {c.answer}
                </p>
              </div>
            ))}
          </div>
        )}

        {/* CTA */}
        <div className="text-center bg-surface border border-border rounded-2xl p-8">
          <h2 className="font-syne font-black text-xl text-ink mb-2">
            Save This Deck to Your Account
          </h2>
          <p className="font-serif text-sm text-ink-3 mb-5">
            Create a free MedMind account to save this deck, add your own cards, and study with spaced repetition.
          </p>
          <Link
            href="/register"
            className="inline-block px-8 py-3 rounded-xl bg-ink text-white font-syne font-bold text-sm hover:bg-ink-2 transition-colors"
          >
            Save & Sign Up Free →
          </Link>
        </div>
      </div>
    </div>
  );
}
