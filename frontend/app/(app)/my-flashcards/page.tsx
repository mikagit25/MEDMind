"use client";

import { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";

interface UserFlashcard {
  id: string;
  question: string;
  answer: string;
  tags: string[];
  difficulty: string;
  interval_days: number;
  repetitions: number;
  next_review_at: string | null;
  created_at: string;
}

const myCardsApi = {
  list: (q?: string) =>
    api.get("/my/flashcards", { params: q ? { q } : undefined }).then(r => r.data),
  create: (data: { question: string; answer: string; tags: string[]; difficulty: string }) =>
    api.post("/my/flashcards", data).then(r => r.data),
  update: (id: string, data: Partial<{ question: string; answer: string; tags: string[] }>) =>
    api.patch(`/my/flashcards/${id}`, data).then(r => r.data),
  delete: (id: string) => api.delete(`/my/flashcards/${id}`),
  getDue: () => api.get("/my/flashcards/due").then(r => r.data),
  review: (id: string, quality: number) =>
    api.post(`/my/flashcards/${id}/review`, { quality }).then(r => r.data),
};

// ── Review mode ──────────────────────────────────────────────────────────────
function ReviewSession({ cards, onDone }: { cards: UserFlashcard[]; onDone: () => void }) {
  const t = useT();
  const [idx, setIdx] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [done, setDone] = useState(false);

  const current = cards[idx];

  async function rate(quality: number) {
    await myCardsApi.review(current.id, quality).catch(() => null);
    if (idx + 1 >= cards.length) {
      setDone(true);
    } else {
      setIdx(i => i + 1);
      setFlipped(false);
    }
  }

  if (done) {
    return (
      <div className="text-center py-16">
        <div className="text-5xl mb-4">🎉</div>
        <h2 className="font-syne font-bold text-xl text-ink mb-2">{t("flashcards.session_complete")}</h2>
        <p className="text-ink-3 font-serif text-sm mb-6">You reviewed {cards.length} cards.</p>
        <button onClick={onDone} className="btn-primary px-6 py-2 rounded font-syne font-semibold text-sm">
          {t("common.back")}
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto py-8">
      <div className="flex items-center justify-between mb-6">
        <span className="font-syne font-semibold text-sm text-ink-3">{idx + 1} / {cards.length}</span>
        <button onClick={onDone} className="text-xs text-ink-3 hover:text-ink font-syne">✕ {t("common.close")}</button>
      </div>

      {/* Card flip */}
      <div
        className="card p-8 min-h-48 flex flex-col items-center justify-center cursor-pointer select-none mb-4 transition-all"
        onClick={() => setFlipped(f => !f)}
      >
        {!flipped ? (
          <>
            <p className="font-syne font-semibold text-base text-ink text-center mb-4">{current.question}</p>
            <span className="text-xs text-ink-3 font-serif">{t("flashcards.flip")}</span>
          </>
        ) : (
          <>
            <p className="font-serif text-sm text-ink-3 text-center mb-3">{current.question}</p>
            <div className="w-full border-t border-ink/10 my-3" />
            <p className="font-syne font-medium text-base text-ink text-center">{current.answer}</p>
          </>
        )}
      </div>

      {flipped && (
        <div className="grid grid-cols-4 gap-2">
          {[
            { q: 0, label: "Blackout", color: "bg-red-500" },
            { q: 2, label: "Hard", color: "bg-orange-400" },
            { q: 3, label: "OK", color: "bg-yellow-400" },
            { q: 5, label: "Easy", color: "bg-green-500" },
          ].map(({ q, label, color }) => (
            <button
              key={q}
              onClick={() => rate(q)}
              className={`${color} text-white font-syne font-semibold text-xs py-3 rounded transition-opacity hover:opacity-90`}
            >
              {label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Create / Edit form ───────────────────────────────────────────────────────
function CardForm({
  initial,
  onSave,
  onCancel,
}: {
  initial?: UserFlashcard;
  onSave: (data: { question: string; answer: string; tags: string[]; difficulty: string }) => Promise<void>;
  onCancel: () => void;
}) {
  const t = useT();
  const [question, setQuestion] = useState(initial?.question ?? "");
  const [answer, setAnswer] = useState(initial?.answer ?? "");
  const [tagsRaw, setTagsRaw] = useState((initial?.tags ?? []).join(", "));
  const [difficulty, setDifficulty] = useState(initial?.difficulty ?? "medium");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim() || !answer.trim()) {
      setError("Question and answer are required.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await onSave({
        question: question.trim(),
        answer: answer.trim(),
        tags: tagsRaw.split(",").map(t => t.trim()).filter(Boolean),
        difficulty,
      });
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="card p-6 space-y-4 max-w-lg mx-auto">
      <h2 className="font-syne font-bold text-base text-ink">
        {initial ? t("flashcards.my_cards") : t("flashcards.create")}
      </h2>
      {error && <p className="text-red-500 text-xs font-serif">{error}</p>}
      <div>
        <label className="font-syne font-semibold text-xs text-ink-3 mb-1 block">{t("flashcards.question_label")}</label>
        <textarea
          value={question}
          onChange={e => setQuestion(e.target.value)}
          rows={3}
          className="w-full border border-ink/10 rounded p-2 text-sm font-serif focus:outline-none focus:ring-1 focus:ring-blue"
          placeholder="e.g. What are the classic signs of aortic stenosis?"
        />
      </div>
      <div>
        <label className="font-syne font-semibold text-xs text-ink-3 mb-1 block">{t("flashcards.answer_label")}</label>
        <textarea
          value={answer}
          onChange={e => setAnswer(e.target.value)}
          rows={4}
          className="w-full border border-ink/10 rounded p-2 text-sm font-serif focus:outline-none focus:ring-1 focus:ring-blue"
          placeholder="e.g. Ejection systolic murmur, slow-rising pulse, narrow pulse pressure…"
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="font-syne font-semibold text-xs text-ink-3 mb-1 block">Tags</label>
          <input
            value={tagsRaw}
            onChange={e => setTagsRaw(e.target.value)}
            className="w-full border border-ink/10 rounded p-2 text-xs font-serif focus:outline-none focus:ring-1 focus:ring-blue"
            placeholder="cardiology, valves"
          />
        </div>
        <div>
          <label className="font-syne font-semibold text-xs text-ink-3 mb-1 block">{t("flashcards.difficulty")}</label>
          <select
            value={difficulty}
            onChange={e => setDifficulty(e.target.value)}
            className="w-full border border-ink/10 rounded p-2 text-xs font-syne focus:outline-none"
          >
            <option value="easy">{t("common.easy")}</option>
            <option value="medium">{t("common.medium")}</option>
            <option value="hard">{t("common.hard")}</option>
          </select>
        </div>
      </div>
      <div className="flex gap-3 pt-1">
        <button
          type="submit"
          disabled={saving}
          className="btn-primary px-4 py-2 rounded font-syne font-semibold text-sm disabled:opacity-60"
        >
          {saving ? t("common.saving") : t("flashcards.save_card")}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 rounded border border-ink/10 font-syne font-semibold text-sm text-ink-3 hover:text-ink"
        >
          {t("common.cancel")}
        </button>
      </div>
    </form>
  );
}

// ── Main page ────────────────────────────────────────────────────────────────
export default function MyFlashcardsPage() {
  const t = useT();
  const [cards, setCards] = useState<UserFlashcard[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [view, setView] = useState<"list" | "create" | "edit" | "review">("list");
  const [editing, setEditing] = useState<UserFlashcard | null>(null);
  const [dueCards, setDueCards] = useState<UserFlashcard[]>([]);

  const fetchCards = useCallback(async (q?: string) => {
    setLoading(true);
    try {
      const data = await myCardsApi.list(q);
      setCards(data.items);
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchCards(); }, [fetchCards]);

  // Debounce search
  useEffect(() => {
    const t = setTimeout(() => fetchCards(search || undefined), 350);
    return () => clearTimeout(t);
  }, [search, fetchCards]);

  async function startReview() {
    const due = await myCardsApi.getDue();
    setDueCards(due);
    setView("review");
  }

  async function handleCreate(data: any) {
    await myCardsApi.create(data);
    await fetchCards();
    setView("list");
  }

  async function handleEdit(data: any) {
    if (!editing) return;
    await myCardsApi.update(editing.id, data);
    await fetchCards();
    setView("list");
    setEditing(null);
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this flashcard?")) return;
    await myCardsApi.delete(id);
    setCards(c => c.filter(x => x.id !== id));
    setTotal(t => t - 1);
  }

  if (view === "review") {
    return (
      <div className="max-w-2xl mx-auto px-4 py-6">
        {dueCards.length === 0 ? (
          <div className="text-center py-16">
            <div className="text-4xl mb-3">✅</div>
            <p className="font-syne font-bold text-lg text-ink mb-1">{t("flashcards.session_complete")}</p>
            <p className="text-ink-3 font-serif text-sm mb-6">{t("flashcards.no_cards")}</p>
            <button onClick={() => setView("list")} className="btn-primary px-6 py-2 rounded font-syne font-semibold text-sm">
              {t("common.back")}
            </button>
          </div>
        ) : (
          <ReviewSession cards={dueCards} onDone={() => { setView("list"); fetchCards(); }} />
        )}
      </div>
    );
  }

  if (view === "create") {
    return (
      <div className="max-w-2xl mx-auto px-4 py-6">
        <CardForm onSave={handleCreate} onCancel={() => setView("list")} />
      </div>
    );
  }

  if (view === "edit" && editing) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-6">
        <CardForm initial={editing} onSave={handleEdit} onCancel={() => { setView("list"); setEditing(null); }} />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-syne font-black text-2xl text-ink">{t("flashcards.my_cards")}</h1>
          <p className="font-serif text-ink-3 text-sm mt-0.5">{total} {t("flashcards.cards_due")}</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={startReview}
            className="px-4 py-2 rounded bg-amber text-white font-syne font-semibold text-sm hover:bg-amber/90 transition-colors"
          >
            {t("flashcards.study_now")}
          </button>
          <button
            onClick={() => setView("create")}
            className="btn-primary px-4 py-2 rounded font-syne font-semibold text-sm"
          >
            + {t("flashcards.create")}
          </button>
        </div>
      </div>

      {/* Search */}
      <input
        value={search}
        onChange={e => setSearch(e.target.value)}
        placeholder={t("common.search")}
        className="w-full border border-ink/10 rounded px-4 py-2 text-sm font-serif mb-5 focus:outline-none focus:ring-1 focus:ring-blue"
      />

      {/* Cards grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="card p-4 animate-pulse h-28 bg-ink/5" />
          ))}
        </div>
      ) : cards.length === 0 ? (
        <div className="text-center py-20">
          <div className="text-5xl mb-4">📇</div>
          <p className="font-syne font-bold text-lg text-ink mb-2">{t("flashcards.no_cards")}</p>
          <p className="text-ink-3 font-serif text-sm mb-6">
            {t("flashcards.create_first")}
          </p>
          <button
            onClick={() => setView("create")}
            className="btn-primary px-6 py-2 rounded font-syne font-semibold text-sm"
          >
            {t("flashcards.create")}
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {cards.map(card => (
            <div key={card.id} className="card p-4 flex flex-col gap-2">
              <p className="font-syne font-semibold text-sm text-ink line-clamp-2">{card.question}</p>
              <p className="font-serif text-xs text-ink-3 line-clamp-2">{card.answer}</p>
              <div className="flex items-center gap-2 mt-auto pt-1">
                {card.tags.slice(0, 3).map(tag => (
                  <span key={tag} className="text-xs bg-blue-light text-blue font-syne px-2 py-0.5 rounded-full">{tag}</span>
                ))}
                <span className="ml-auto font-syne text-xs text-ink-3">
                  {card.next_review_at
                    ? `Due ${new Date(card.next_review_at) <= new Date() ? "now" : new Date(card.next_review_at).toLocaleDateString()}`
                    : "New"}
                </span>
                <button
                  onClick={() => { setEditing(card); setView("edit"); }}
                  className="text-xs text-ink-3 hover:text-ink font-syne px-2"
                >
                  {t("common.edit")}
                </button>
                <button
                  onClick={() => handleDelete(card.id)}
                  className="text-xs text-red-400 hover:text-red-600 font-syne"
                >
                  {t("common.delete")}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
