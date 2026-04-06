"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { contentApi, progressApi } from "@/lib/api";

type Card = {
  id: string;
  question: string;
  answer: string;
  difficulty: string;
  category?: string;
};

type Phase = "loading" | "pick_specialty" | "pick_module" | "review" | "done";

const QUALITY_LABELS = [
  { q: 0, label: "Blank", color: "bg-red text-white" },
  { q: 1, label: "Wrong", color: "bg-red-2 text-white" },
  { q: 2, label: "Hard", color: "bg-amber-2 text-white" },
  { q: 3, label: "Okay", color: "bg-amber text-ink" },
  { q: 4, label: "Good", color: "bg-green-2 text-white" },
  { q: 5, label: "Easy", color: "bg-green text-white" },
];

function FlashcardsInner() {
  const searchParams = useSearchParams();
  const [specialties, setSpecialties] = useState<any[]>([]);
  const [modules, setModules] = useState<any[]>([]);
  const [selectedSpecialty, setSelectedSpecialty] = useState<string | null>(null);
  const [moduleId, setModuleId] = useState<string | null>(null);
  const [moduleTitle, setModuleTitle] = useState("");
  const [cards, setCards] = useState<Card[]>([]);
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [phase, setPhase] = useState<Phase>("loading");
  const [sessionDone, setSessionDone] = useState(0);
  const [sessionXp, setSessionXp] = useState(0);

  useEffect(() => {
    contentApi.getSpecialties().then((r) => {
      setSpecialties(r.data ?? []);
      const moduleParam = searchParams.get("module");
      if (moduleParam) {
        // Direct link from module detail page — load cards immediately
        loadCards(moduleParam);
      } else {
        setPhase("pick_specialty");
      }
    });
  }, [searchParams]);

  const loadModules = useCallback(async (specialtyId: string) => {
    setSelectedSpecialty(specialtyId);
    setPhase("loading");
    try {
      const res = await contentApi.getModules(specialtyId);
      setModules(res.data ?? []);
      setPhase("pick_module");
    } catch {
      setPhase("pick_specialty");
    }
  }, []);

  const loadCards = useCallback(async (mid: string, title?: string) => {
    setModuleId(mid);
    if (title) setModuleTitle(title);
    setPhase("loading");
    try {
      const res = await contentApi.getFlashcards(mid, true);
      const data: Card[] = res.data ?? [];
      if (data.length === 0) {
        // No due cards — load all cards instead
        const allRes = await contentApi.getFlashcards(mid, false);
        const allData: Card[] = allRes.data ?? [];
        if (allData.length === 0) {
          setPhase("done");
          setSessionDone(0);
        } else {
          setCards(allData);
          setIndex(0);
          setFlipped(false);
          setPhase("review");
        }
      } else {
        setCards(data);
        setIndex(0);
        setFlipped(false);
        setPhase("review");
      }
    } catch {
      setPhase("pick_specialty");
    }
    setSessionDone(0);
    setSessionXp(0);
  }, []);

  const grade = async (quality: number) => {
    const card = cards[index];
    try {
      const res = await progressApi.reviewFlashcard(card.id, quality);
      setSessionXp((p) => p + (res.data?.xp_earned ?? 0));
    } catch {/* ignore */}

    setSessionDone((p) => p + 1);
    if (index + 1 >= cards.length) {
      setPhase("done");
    } else {
      setIndex(index + 1);
      setFlipped(false);
    }
  };

  const currentCard = cards[index];
  const progress = cards.length > 0 ? (index / cards.length) * 100 : 0;

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-border bg-surface flex-shrink-0">
        <h1 className="font-syne font-black text-lg text-ink mr-auto">
          Flashcards{moduleTitle ? ` — ${moduleTitle}` : ""}
        </h1>
        {cards.length > 0 && phase === "review" && (
          <span className="font-syne text-xs text-ink-3">{index + 1} / {cards.length}</span>
        )}
        {sessionDone > 0 && (
          <span className="badge bg-green-light text-green">+{sessionXp} XP</span>
        )}
        {phase === "review" && (
          <button
            onClick={() => { setPhase("pick_specialty"); setSelectedSpecialty(null); setCards([]); }}
            className="text-xs font-syne text-ink-3 hover:text-ink transition-colors"
          >
            Change module
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-6 flex flex-col items-center">

        {/* Step 1: Pick specialty */}
        {(phase === "pick_specialty" || (phase === "loading" && !selectedSpecialty)) && (
          <div className="w-full max-w-lg">
            <h2 className="font-syne font-bold text-xl text-ink mb-1 text-center">Choose a specialty</h2>
            <p className="font-serif text-ink-3 text-sm text-center mb-6">Select a specialty to browse modules</p>
            <div className="grid grid-cols-2 gap-3">
              {specialties.map((spec) => (
                <button
                  key={spec.id}
                  onClick={() => loadModules(String(spec.id))}
                  className="card text-left hover:border-ink-3 transition-colors"
                >
                  <div className="font-syne font-bold text-sm text-ink">{spec.name}</div>
                  <div className="font-serif text-ink-3 text-xs mt-0.5">{spec.module_count ?? 0} modules</div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 2: Pick module */}
        {phase === "pick_module" && (
          <div className="w-full max-w-lg">
            <div className="flex items-center gap-2 mb-4">
              <button
                onClick={() => { setPhase("pick_specialty"); setSelectedSpecialty(null); }}
                className="text-ink-3 hover:text-ink text-xs font-syne transition-colors"
              >
                ← Back
              </button>
              <h2 className="font-syne font-bold text-xl text-ink">Choose a module</h2>
            </div>
            {modules.length === 0 ? (
              <p className="font-serif text-ink-3 text-sm text-center py-8">No modules found in this specialty.</p>
            ) : (
              <div className="space-y-2">
                {modules.map((mod) => (
                  <button
                    key={mod.id}
                    onClick={() => loadCards(String(mod.id), mod.title)}
                    className="card w-full text-left hover:border-ink-3 transition-colors"
                  >
                    <div className="font-syne font-bold text-sm text-ink">{mod.title}</div>
                    <div className="flex gap-3 mt-1 text-xs font-syne text-ink-3">
                      {mod.flashcard_count > 0 && <span>🃏 {mod.flashcard_count} cards</span>}
                      {mod.lesson_count > 0 && <span>📖 {mod.lesson_count} lessons</span>}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Loading */}
        {phase === "loading" && (
          <div className="text-center font-serif text-ink-3 text-sm animate-pulse pt-16">
            Loading cards…
          </div>
        )}

        {/* Flashcard review */}
        {phase === "review" && currentCard && (
          <div className="w-full max-w-lg">
            {/* Progress bar */}
            <div className="h-1.5 bg-bg-2 rounded-full mb-6 overflow-hidden">
              <div
                className="h-full bg-ink rounded-full transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>

            {/* Card */}
            <div
              className="relative w-full cursor-pointer select-none"
              style={{ perspective: "1000px", minHeight: "260px" }}
              onClick={() => setFlipped(!flipped)}
            >
              <div
                className="w-full transition-all duration-500"
                style={{
                  transformStyle: "preserve-3d",
                  transform: flipped ? "rotateY(180deg)" : "rotateY(0deg)",
                }}
              >
                {/* Front */}
                <div
                  className="absolute inset-0 card flex flex-col items-center justify-center p-6 text-center"
                  style={{ backfaceVisibility: "hidden" }}
                >
                  <div className="text-xs font-syne font-bold text-ink-3 uppercase tracking-wider mb-4">Question</div>
                  <p className="font-serif text-ink text-lg leading-relaxed">{currentCard.question}</p>
                  <div className="mt-6 text-xs font-syne text-ink-3">Tap to reveal answer</div>
                </div>

                {/* Back */}
                <div
                  className="absolute inset-0 card flex flex-col items-center justify-center p-6 text-center"
                  style={{
                    backfaceVisibility: "hidden",
                    transform: "rotateY(180deg)",
                    backgroundColor: "#f7f4f0",
                    borderColor: "#a09888",
                  }}
                >
                  <div className="text-xs font-syne font-bold text-ink-3 uppercase tracking-wider mb-4">Answer</div>
                  <p className="font-serif text-ink text-lg leading-relaxed">{currentCard.answer}</p>
                </div>
              </div>
            </div>

            {/* Grade buttons */}
            {flipped && (
              <div className="mt-6 animate-fade-up">
                <p className="font-syne font-bold text-xs text-ink-3 text-center mb-3 uppercase tracking-wider">
                  How well did you know this?
                </p>
                <div className="grid grid-cols-3 gap-2">
                  {QUALITY_LABELS.map(({ q, label, color }) => (
                    <button
                      key={q}
                      onClick={() => grade(q)}
                      className={`py-2.5 rounded font-syne font-bold text-sm transition-opacity hover:opacity-90 ${color}`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Done */}
        {phase === "done" && (
          <div className="w-full max-w-lg text-center pt-8">
            <div className="text-6xl mb-4">🎉</div>
            <h2 className="font-syne font-bold text-2xl text-ink mb-2">Session complete!</h2>
            <p className="font-serif text-ink-3 mb-6">
              You reviewed <strong>{sessionDone}</strong> cards
              {sessionXp > 0 && <> and earned <strong className="text-green">{sessionXp} XP</strong></>}
            </p>
            <div className="flex gap-3 justify-center">
              <button
                onClick={() => { setPhase("pick_specialty"); setSelectedSpecialty(null); setCards([]); }}
                className="btn-secondary px-5"
              >
                Another module
              </button>
              {moduleId && (
                <button onClick={() => loadCards(moduleId, moduleTitle)} className="btn-primary px-5">
                  Review again
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function FlashcardsPage() {
  return (
    <Suspense fallback={<div className="flex-1 flex items-center justify-center"><span className="font-serif text-ink-3 text-sm animate-pulse">Loading…</span></div>}>
      <FlashcardsInner />
    </Suspense>
  );
}
