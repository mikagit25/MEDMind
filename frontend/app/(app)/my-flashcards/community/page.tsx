"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { communityFlashcardsApi } from "@/lib/api";
import { useT } from "@/lib/i18n";

interface CommunityCard {
  id: string;
  question: string;
  answer: string;
  tags: string[];
  difficulty: string;
  author: string;
  created_at: string;
}

const DIFFICULTIES = ["easy", "medium", "hard"] as const;
const PAGE_SIZE = 20;

function DifficultyBadge({ difficulty }: { difficulty: string }) {
  const colors: Record<string, string> = {
    easy: "bg-green/15 text-green",
    medium: "bg-amber-2/15 text-amber-600",
    hard: "bg-red/15 text-red",
  };
  return (
    <span className={`text-xs font-syne font-semibold px-2 py-0.5 rounded-full ${colors[difficulty] ?? "bg-bg-2 text-ink-3"}`}>
      {difficulty}
    </span>
  );
}

export default function CommunityCardsPage() {
  const t = useT();
  const [cards, setCards] = useState<CommunityCard[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [cloning, setCloning] = useState<Record<string, "cloning" | "cloned">>({});
  const [error, setError] = useState("");

  const fetchCards = useCallback(
    async (searchVal: string, diffVal: string, off: number, append = false) => {
      if (off === 0) setLoading(true); else setLoadingMore(true);
      setError("");
      try {
        const params: Record<string, unknown> = { limit: PAGE_SIZE, offset: off };
        if (searchVal) params.search = searchVal;
        if (diffVal) params.difficulty = diffVal;
        const data = await communityFlashcardsApi.browse(params);
        const fetched: CommunityCard[] = data.cards ?? [];
        setTotal(data.total ?? 0);
        setCards(prev => (append ? [...prev, ...fetched] : fetched));
        setOffset(off + fetched.length);
      } catch {
        setError(t("common.error_retry"));
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [t]
  );

  useEffect(() => {
    setOffset(0);
    fetchCards(search, difficulty, 0, false);
  }, [search, difficulty]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleClone(cardId: string) {
    setCloning(prev => ({ ...prev, [cardId]: "cloning" }));
    try {
      await communityFlashcardsApi.clone(cardId);
      setCloning(prev => ({ ...prev, [cardId]: "cloned" }));
    } catch {
      setCloning(prev => { const next = { ...prev }; delete next[cardId]; return next; });
    }
  }

  return (
    <div className="flex-1 overflow-y-auto p-3 sm:p-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-1">
        <Link href="/my-flashcards" className="text-ink-3 hover:text-ink font-syne text-sm">
          ← {t("nav.items.my_cards")}
        </Link>
      </div>
      <h1 className="font-syne font-black text-2xl text-ink mb-1">{t("flashcards.community_title")}</h1>
      <p className="font-serif text-ink-3 text-sm mb-6">{t("flashcards.community_subtitle")}</p>

      {/* Search + difficulty filter */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder={t("flashcards.community_search")}
          className="flex-1 bg-bg-2 border border-stroke rounded px-3 py-2 font-serif text-sm text-ink placeholder:text-ink-3 focus:outline-none focus:ring-2 focus:ring-red/30"
        />
        <select
          value={difficulty}
          onChange={e => setDifficulty(e.target.value)}
          className="bg-bg-2 border border-stroke rounded px-3 py-2 font-syne text-sm text-ink focus:outline-none focus:ring-2 focus:ring-red/30"
        >
          <option value="">{t("flashcards.community_filter_all")}</option>
          {DIFFICULTIES.map(d => (
            <option key={d} value={d}>{t(`common.${d}`)}</option>
          ))}
        </select>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 text-sm text-red font-serif">{error}</div>
      )}

      {/* Loading skeleton */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="card p-4 h-32 animate-pulse bg-bg-2" />
          ))}
        </div>
      ) : cards.length === 0 ? (
        <div className="text-center py-20 space-y-3">
          <div className="text-5xl">🌐</div>
          <h3 className="font-syne font-bold text-xl text-ink">{t("flashcards.community_no_results")}</h3>
          <p className="font-serif text-ink-3 text-sm max-w-xs mx-auto">
            {t("flashcards.community_subtitle")}
          </p>
          <a href="/my-flashcards" className="inline-block px-5 py-2 bg-ink text-white rounded-lg font-syne font-semibold text-sm hover:bg-red transition-colors">
            {t("flashcards.my_cards")} →
          </a>
        </div>
      ) : (
        <>
          <p className="font-serif text-xs text-ink-3 mb-4">{total} {t("common.results")}</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {cards.map(card => {
              const state = cloning[card.id];
              return (
                <div key={card.id} className="card p-4 flex flex-col gap-2">
                  <p className="font-syne font-semibold text-sm text-ink line-clamp-2">{card.question}</p>
                  <p className="font-serif text-xs text-ink-3 line-clamp-2">{card.answer}</p>
                  <div className="flex items-center gap-2 flex-wrap mt-auto pt-2">
                    <DifficultyBadge difficulty={card.difficulty} />
                    {card.tags.slice(0, 2).map(tag => (
                      <span key={tag} className="text-xs bg-blue-light text-blue font-syne px-2 py-0.5 rounded-full">{tag}</span>
                    ))}
                    <span className="font-serif text-xs text-ink-3 ml-auto">
                      {t("flashcards.community_by")} {card.author}
                    </span>
                    <button
                      onClick={() => handleClone(card.id)}
                      disabled={!!state}
                      className="btn-primary text-xs px-3 py-1 rounded font-syne font-semibold disabled:opacity-60"
                    >
                      {state === "cloning"
                        ? t("flashcards.cloning")
                        : state === "cloned"
                        ? t("flashcards.cloned")
                        : t("flashcards.clone")}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Load more */}
          {offset < total && (
            <div className="flex justify-center mt-6">
              <button
                onClick={() => fetchCards(search, difficulty, offset, true)}
                disabled={loadingMore}
                className="btn-secondary px-6 py-2 rounded font-syne font-semibold text-sm disabled:opacity-60"
              >
                {loadingMore ? t("common.loading") : t("common.view_all")}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
