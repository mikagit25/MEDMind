"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { contentApi, progressApi, notesApi, imagingApi, teacherApi, srsApi, certificatesApi } from "@/lib/api";
import LessonQuizPanel from "@/components/ui/LessonQuizPanel";
import { useI18n, useT } from "@/lib/i18n";
import { ga } from "@/lib/gtag";
import { analytics } from "@/lib/analytics";

type LessonContent = {
  intro?: string;
  sections?: { heading: string; text: string }[];
  clinical_pearl?: string;
  key_points?: string[];
};
type GlossaryTerm = { term: string; simple_definition: string };
type Lesson = {
  id: string; title: string; content: LessonContent | string; lesson_order: number;
  lay_summary?: string | null; lay_glossary?: GlossaryTerm[] | null;
};
type Note = { id: string; content: string; lesson_id?: string; module_id?: string };

type Block = { type: string; order: number; content: Record<string, unknown> };

// ── Image Block with Lightbox + AI Analysis ────────────────────────────────
function ImageBlockRenderer({
  url, caption, modality, imageId,
}: {
  url: string; caption?: string; modality?: string; imageId?: string;
}) {
  const t = useT();
  const [lightbox, setLightbox] = useState(false);
  const [analysis, setAnalysis] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [showAnalysis, setShowAnalysis] = useState(false);

  const analyze = async () => {
    if (analysis) { setShowAnalysis(true); return; }
    setAnalyzing(true);
    setShowAnalysis(true);
    try {
      const res = await imagingApi.analyzeImage({ image_url: url, modality, image_id: imageId });
      setAnalysis(res.analysis);
    } catch (e: any) {
      setAnalysis(
        e?.response?.status === 429
          ? "Daily AI limit reached. Upgrade your plan for more access."
          : "AI analysis could not be completed. Please try again."
      );
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <>
      {lightbox && (
        <div
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4"
          onClick={() => setLightbox(false)}
        >
          <button className="absolute top-4 right-4 text-white/60 hover:text-white font-syne text-sm px-3 py-1 rounded-full bg-white/10" onClick={() => setLightbox(false)}>
            ✕ Close
          </button>
          <img src={url} alt={caption ?? "Medical image"} className="max-w-full max-h-[90vh] object-contain rounded-lg" onClick={e => e.stopPropagation()} />
        </div>
      )}
      <figure className="my-3">
        <div
          className="relative group cursor-zoom-in rounded-xl overflow-hidden border border-border bg-surface"
          onClick={() => setLightbox(true)}
        >
          <img
            src={url}
            alt={caption ?? "Medical image"}
            className="w-full object-contain max-h-[420px] group-hover:opacity-95 transition-opacity"
          />
          <div className="absolute inset-0 flex items-end justify-end p-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <span className="bg-black/60 text-white font-syne text-[10px] px-2 py-0.5 rounded-full">Click to enlarge</span>
          </div>
        </div>
        <div className="flex items-center justify-between mt-2 gap-3">
          {caption && <figcaption className="font-serif text-xs text-ink-3 flex-1">{caption}</figcaption>}
          <button
            onClick={analyze}
            className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-blue/30 bg-blue-light text-blue font-syne font-semibold text-xs hover:bg-blue/10 transition-colors"
          >
            🔬 AI Analysis
          </button>
        </div>
        {showAnalysis && (
          <div className="mt-3 rounded-xl border border-blue/20 bg-blue-light/20 p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="font-syne font-bold text-xs text-blue uppercase tracking-wide">{t("modules.ai_analysis") as string || "AI Interpretation"}</span>
              <button onClick={() => setShowAnalysis(false)} className="text-ink-3 text-xs hover:text-ink">✕</button>
            </div>
            {analyzing ? (
              <div className="font-serif text-sm text-ink-3 animate-pulse">{t("modules.ai_interpreting") as string || "Analysing image with Claude Vision…"}</div>
            ) : (
              <p className="font-serif text-sm text-ink leading-relaxed whitespace-pre-wrap">{analysis}</p>
            )}
            <p className="font-serif text-xs text-ink-3 mt-3 italic">
              {t("modules.ai_disclaimer") as string || "⚠️ AI interpretation is for educational purposes only. Always verify with a qualified clinician."}
            </p>
          </div>
        )}
      </figure>
    </>
  );
}

function QuizBlock({ block, idx }: { block: Block; idx: number }) {
  const c = block.content as { question: string; options: Record<string, string>; correct: string; explanation: string };
  const [selected, setSelected] = useState<string | null>(null);
  const answered = selected !== null;
  return (
    <div className="border border-border rounded-xl p-4 bg-surface">
      <div className="font-syne font-bold text-xs text-ink-3 uppercase tracking-wider mb-2">Question {idx + 1}</div>
      <p className="font-serif text-sm text-ink mb-3">{c.question}</p>
      <div className="space-y-2">
        {Object.entries(c.options ?? {}).map(([k, v]) => {
          const isCorrect = k === c.correct;
          const isSelected = selected === k;
          let cls = "border border-border rounded-lg px-3 py-2 font-serif text-sm cursor-pointer transition-colors";
          if (answered) {
            cls += isCorrect ? " bg-green-light border-green/40 text-green" : isSelected ? " bg-red-light border-red/30 text-red" : " text-ink-3";
          } else {
            cls += " hover:border-ink-3 text-ink";
          }
          return (
            <div key={k} className={cls} onClick={() => !answered && setSelected(k)}>
              <span className="font-syne font-bold mr-2">{k}.</span>{v}
            </div>
          );
        })}
      </div>
      {answered && c.explanation && (
        <div className="mt-3 p-3 rounded-lg bg-blue-light border border-blue/20">
          <p className="font-serif text-xs text-ink-3">{c.explanation}</p>
        </div>
      )}
    </div>
  );
}

function FlashcardBlock({ block }: { block: Block }) {
  const c = block.content as { question: string; answer: string; difficulty?: string };
  const [flipped, setFlipped] = useState(false);
  const diffColor = c.difficulty === "easy" ? "text-green border-green/30 bg-green-light"
    : c.difficulty === "hard" ? "text-red border-red/30 bg-red-light"
    : "text-amber border-amber/30 bg-amber-light";
  return (
    <div className="my-3">
      <div
        className="relative cursor-pointer rounded-xl border border-border overflow-hidden select-none"
        style={{ minHeight: 120 }}
        onClick={() => setFlipped(v => !v)}
      >
        <div className={`absolute inset-0 flex flex-col items-center justify-center p-5 transition-opacity duration-200 ${flipped ? "opacity-0 pointer-events-none" : "opacity-100"}`}>
          <div className="font-syne font-bold text-xs text-ink-3 uppercase tracking-wider mb-3">Question — tap to reveal</div>
          <p className="font-serif text-sm text-ink text-center leading-relaxed">{c.question}</p>
        </div>
        <div className={`absolute inset-0 flex flex-col items-center justify-center p-5 bg-blue-light transition-opacity duration-200 ${flipped ? "opacity-100" : "opacity-0 pointer-events-none"}`}>
          <div className="font-syne font-bold text-xs text-blue uppercase tracking-wider mb-3">Answer</div>
          <p className="font-serif text-sm text-ink text-center leading-relaxed">{c.answer}</p>
        </div>
        {/* Spacer to set height */}
        <div className="invisible p-5">
          <p className="font-serif text-sm">{c.question.length > c.answer.length ? c.question : c.answer}</p>
        </div>
      </div>
      <div className="flex items-center justify-between mt-1.5 px-1">
        {c.difficulty && (
          <span className={`font-syne text-[10px] px-2 py-0.5 rounded-full border capitalize ${diffColor}`}>{c.difficulty}</span>
        )}
        <button onClick={() => setFlipped(false)} className="font-syne text-[10px] text-ink-3 hover:text-ink ml-auto">Reset</button>
      </div>
    </div>
  );
}

function LessonContentRenderer({ content }: { content: LessonContent | string }) {
  // Handle plain string (legacy or HTML fallback)
  if (typeof content === "string") {
    return (
      <div
        className="font-serif text-ink text-sm leading-relaxed"
        dangerouslySetInnerHTML={{ __html: content }}
      />
    );
  }
  if (!content || typeof content !== "object") {
    return <p className="font-serif text-ink-3 text-sm">No content available.</p>;
  }

  // New block-based format from teacher editor
  const raw = content as Record<string, unknown>;
  if (Array.isArray(raw.blocks)) {
    const blocks = (raw.blocks as Block[]).slice().sort((a, b) => a.order - b.order);
    let quizIdx = 0;
    return (
      <div className="space-y-5">
        {Array.isArray(raw.learning_objectives) && (raw.learning_objectives as string[]).filter(Boolean).length > 0 && (
          <div className="bg-blue-light border border-blue/20 rounded-lg p-4">
            <div className="font-syne font-bold text-xs text-blue uppercase tracking-wider mb-2">Learning Objectives</div>
            <ul className="list-disc list-inside space-y-1 font-serif text-sm text-ink">
              {(raw.learning_objectives as string[]).filter(Boolean).map((o, i) => <li key={i}>{o}</li>)}
            </ul>
          </div>
        )}
        {blocks.map((block, i) => {
          if (block.type === "text") {
            const c = block.content as { heading?: string; text: string };
            return (
              <div key={i}>
                {c.heading && <h3 className="font-syne font-bold text-base text-ink mb-1.5">{c.heading}</h3>}
                <p className="font-serif text-sm text-ink leading-relaxed whitespace-pre-wrap">{c.text}</p>
              </div>
            );
          }
          if (block.type === "quiz") {
            quizIdx++;
            return <QuizBlock key={i} block={block} idx={quizIdx - 1} />;
          }
          if (block.type === "case") {
            const c = block.content as { presentation: string; questions: string[]; teaching_points: string[] };
            return (
              <div key={i} className="border border-amber/30 rounded-xl p-4 bg-amber-light/20">
                <div className="font-syne font-bold text-xs text-amber uppercase tracking-wider mb-2">Clinical Case</div>
                <p className="font-serif text-sm text-ink mb-3">{c.presentation}</p>
                {c.questions?.filter(Boolean).length > 0 && (
                  <div className="mb-3">
                    <div className="font-syne font-semibold text-xs text-ink-3 mb-1.5">Questions to consider:</div>
                    <ol className="list-decimal list-inside space-y-1 font-serif text-sm text-ink">
                      {c.questions.filter(Boolean).map((q, qi) => <li key={qi}>{q}</li>)}
                    </ol>
                  </div>
                )}
                {c.teaching_points?.filter(Boolean).length > 0 && (
                  <div>
                    <div className="font-syne font-semibold text-xs text-ink-3 mb-1.5">Teaching points:</div>
                    <ul className="list-disc list-inside space-y-1 font-serif text-sm text-ink">
                      {c.teaching_points.filter(Boolean).map((p, pi) => <li key={pi}>{p}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            );
          }
          if (block.type === "image") {
            const c = block.content as { url?: string; image_url?: string; caption?: string; modality?: string; image_id?: string };
            const url = c.url || c.image_url || "";
            if (!url) return null;
            return (
              <ImageBlockRenderer
                key={i}
                url={url}
                caption={c.caption}
                modality={c.modality}
                imageId={c.image_id}
              />
            );
          }
          if (block.type === "anatomy_3d") {
            const c = block.content as { embed_url?: string; caption?: string; organ_system?: string };
            if (!c.embed_url) return null;
            return (
              <figure key={i} className="my-3">
                <div className="rounded-xl overflow-hidden border border-border bg-surface" style={{ aspectRatio: "16/9" }}>
                  <iframe
                    src={c.embed_url}
                    title={c.caption ?? "3D Anatomy Viewer"}
                    allow="autoplay; fullscreen; xr-spatial-tracking"
                    className="w-full h-full"
                    style={{ border: 0 }}
                  />
                </div>
                <div className="flex items-center gap-2 mt-2">
                  {c.organ_system && (
                    <span className="font-syne text-[10px] px-2 py-0.5 rounded-full bg-surface border border-border text-ink-3 capitalize">{c.organ_system}</span>
                  )}
                  {c.caption && (
                    <figcaption className="font-serif text-xs text-ink-3">{c.caption}</figcaption>
                  )}
                </div>
              </figure>
            );
          }
          if (block.type === "flashcard") {
            return <FlashcardBlock key={i} block={block} />;
          }
          if (block.type === "dosage_table") {
            const c = block.content as { drug_name?: string; unit?: string; rows?: { species: string; dose: string; route: string; frequency?: string; warning?: string }[]; clinical_warning?: string };
            if (!c.rows?.length) return null;
            return (
              <div key={i} className="rounded-xl border border-border overflow-hidden my-3">
                <div className="flex items-center gap-2 px-4 py-2.5 bg-surface border-b border-border">
                  <span className="text-base">💊</span>
                  <span className="font-syne font-bold text-sm text-ink">{c.drug_name ?? "Dosage Table"}</span>
                  {c.unit && <span className="font-serif text-xs text-ink-3">({c.unit})</span>}
                </div>
                {c.clinical_warning && (
                  <div className="px-4 py-2 bg-amber-light/30 border-b border-amber/20 flex items-start gap-2">
                    <span className="text-amber text-sm">⚠️</span>
                    <p className="font-serif text-xs text-ink">{c.clinical_warning}</p>
                  </div>
                )}
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-surface border-b border-border">
                        <th className="font-syne font-semibold text-ink-3 text-left px-3 py-2">Species</th>
                        <th className="font-syne font-semibold text-ink-3 text-left px-3 py-2">Dose</th>
                        <th className="font-syne font-semibold text-ink-3 text-left px-3 py-2">Route</th>
                        <th className="font-syne font-semibold text-ink-3 text-left px-3 py-2">Frequency</th>
                        <th className="font-syne font-semibold text-ink-3 text-left px-3 py-2">Warning</th>
                      </tr>
                    </thead>
                    <tbody>
                      {c.rows.map((row, ri) => (
                        <tr key={ri} className="border-b border-border last:border-0 hover:bg-surface/50 transition-colors">
                          <td className="px-3 py-2 font-syne font-semibold text-ink capitalize">{row.species}</td>
                          <td className="px-3 py-2 font-serif text-ink">{row.dose} {c.unit}</td>
                          <td className="px-3 py-2 font-syne text-ink-3">{row.route}</td>
                          <td className="px-3 py-2 font-serif text-ink-3">{row.frequency ?? "—"}</td>
                          <td className="px-3 py-2">
                            {row.warning
                              ? <span className="font-serif text-red text-[11px]">⚠ {row.warning}</span>
                              : <span className="text-ink-3">—</span>}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            );
          }
          return null;
        })}
      </div>
    );
  }

  // Legacy format
  const { intro, sections, clinical_pearl, key_points } = content as LessonContent;
  return (
    <div className="space-y-5 font-serif text-ink text-sm leading-relaxed">
      {intro && <p>{intro}</p>}
      {sections && sections.map((sec, i) => (
        <div key={i}>
          <h3 className="font-syne font-bold text-base text-ink mb-1.5">{sec.heading}</h3>
          <p className="whitespace-pre-wrap">{sec.text}</p>
        </div>
      ))}
      {clinical_pearl && (
        <div className="bg-amber-light border border-amber/20 rounded-lg p-4">
          <div className="font-syne font-bold text-xs text-amber uppercase tracking-wider mb-1">
            💡 Clinical Pearl
          </div>
          <p>{clinical_pearl}</p>
        </div>
      )}
      {key_points && key_points.length > 0 && (
        <div className="bg-blue-light border border-blue/20 rounded-lg p-4">
          <div className="font-syne font-bold text-xs text-blue uppercase tracking-wider mb-2">
            🔑 Key Points
          </div>
          <ul className="list-disc list-inside space-y-1">
            {key_points.map((point, i) => (
              <li key={i}>{point}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ── Plain-language (Lay) View ─────────────────────────────────────────────────
function LayView({ data }: { data: { lay_summary?: string | null; lay_glossary?: GlossaryTerm[] | null } }) {
  const t = useT();
  return (
    <div className="space-y-5">
      {/* Disclaimer banner */}
      <div className="flex items-start gap-2 p-3 rounded-lg bg-green-light border border-green/20">
        <span className="text-green text-base flex-shrink-0">ℹ</span>
        <p className="font-serif text-xs text-green leading-relaxed">
          <strong>{t("modules.lay_mode_title") as string || "Simple language mode."}</strong> {t("modules.lay_mode_desc") as string || "This is an educational summary written for everyone, not just medical professionals. It does not replace advice from a doctor or healthcare provider."}
        </p>
      </div>

      {/* Summary */}
      {data.lay_summary && (
        <div className="card p-5">
          <div className="font-syne font-bold text-xs text-ink-2 uppercase tracking-wider mb-3">{t("modules.lay_plain_language") as string || "In Plain Language"}</div>
          <p className="font-serif text-sm text-ink leading-relaxed whitespace-pre-wrap">{data.lay_summary}</p>
        </div>
      )}

      {/* Glossary */}
      {data.lay_glossary && data.lay_glossary.length > 0 && (
        <div className="card p-5">
          <div className="font-syne font-bold text-xs text-ink-2 uppercase tracking-wider mb-3">{t("modules.lay_key_terms") as string || "Key Terms Explained"}</div>
          <div className="space-y-3">
            {data.lay_glossary.map((item, i) => (
              <div key={i} className="flex gap-3 py-2 border-b border-border last:border-0">
                <span className="font-syne font-bold text-xs text-ink w-28 flex-shrink-0 pt-0.5">{item.term}</span>
                <span className="font-serif text-xs text-ink-2 leading-relaxed">{item.simple_definition}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Disclaimer footer */}
      <p className="font-serif text-xs text-ink-3 text-center italic">
        {t("modules.lay_footer") as string || "⚕️ This information is for educational purposes only and does not replace professional medical advice. Always consult a qualified healthcare provider."}
      </p>
    </div>
  );
}

export default function ModuleDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { locale } = useI18n();
  const [mod, setMod] = useState<any>(null);
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [activeLesson, setActiveLesson] = useState<Lesson | null>(null);
  const [lessonDone, setLessonDone] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [paywalled, setPaywalled] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [moduleComplete, setModuleComplete] = useState(false);
  const [completionXp, setCompletionXp] = useState(0);
  const [completionAchievements, setCompletionAchievements] = useState<string[]>([]);
  const lessonStartRef = useRef<number>(Date.now());

  // Plain-language mode (Phase 1)
  const [layMode, setLayMode] = useState<boolean>(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("medmind_lay_mode") === "1";
    }
    return false;
  });
  const [layData, setLayData] = useState<{ lay_summary?: string | null; lay_glossary?: GlossaryTerm[] | null } | null>(null);
  const [layLoading, setLayLoading] = useState(false);

  // Notes state
  const [showNotes, setShowNotes] = useState(false);
  const [notes, setNotes] = useState<Note[]>([]);
  const [noteText, setNoteText] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");
  const [savingNote, setSavingNote] = useState(false);
  const [showSrsPrompt, setShowSrsPrompt] = useState(false);
  const [srsLessonId, setSrsLessonId] = useState<string | null>(null);
  const [certCode, setCertCode] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    Promise.all([
      contentApi.getModule(id, locale !== "en" ? locale : undefined),
      contentApi.getLessons(id, locale !== "en" ? locale : undefined),
    ]).then(([modRes, lessonRes]) => {
      setMod(modRes);
      const ls: Lesson[] = lessonRes ?? [];
      ls.sort((a, b) => a.lesson_order - b.lesson_order);
      setLessons(ls);
      if (ls.length > 0) {
        // Load first lesson with full content (translated if locale set)
        contentApi.getLesson(ls[0].id, locale !== "en" ? locale : undefined).then((full: any) => {
          setActiveLesson({ ...ls[0], content: full?.content ?? null });
        }).catch(() => setActiveLesson(ls[0]));
      }
      setLoading(false);
    }).catch((err: any) => {
      if (err?.response?.status === 403) {
        setPaywalled(true);
      }
      setLoading(false);
    });

    // Load existing certificate for this module (if already earned)
    certificatesApi.list().then((certs: any[]) => {
      const existing = certs?.find((c: any) => c.module_id === id);
      if (existing?.verification_code) setCertCode(existing.verification_code);
    }).catch(() => {});

    // Restore already-completed lessons so cert check works across sessions
    progressApi.getModuleProgress(id).then((prog: any) => {
      if (prog?.lessons_completed_ids?.length) {
        setLessonDone(new Set(prog.lessons_completed_ids));
      }
    }).catch(() => {});
  }, [id, locale]);

  // Load full lesson content when active lesson changes (no content yet)
  useEffect(() => {
    if (!activeLesson?.id || activeLesson.content) return;
    contentApi.getLesson(activeLesson.id).then((full: any) => {
      if (full?.content) {
        setActiveLesson((prev) => prev ? { ...prev, content: full.content } : prev);
      }
    }).catch(() => {});
  }, [activeLesson?.id]);

  // Re-fetch active lesson with translation when locale changes
  useEffect(() => {
    if (!activeLesson || locale === "en") return;
    teacherApi.getLesson(activeLesson.id, locale).then((data: any) => {
      if (data?.title) {
        setActiveLesson((prev) => prev ? { ...prev, title: data.title, content: data.content } : prev);
      }
    }).catch(() => {/* fallback to English silently */});
  }, [locale, activeLesson?.id]);

  const loadNotes = useCallback(() => {
    if (!activeLesson) return;
    notesApi.list({ lesson_id: activeLesson.id }).then((r) => setNotes(r ?? []));
  }, [activeLesson]);

  useEffect(() => {
    if (showNotes && activeLesson) loadNotes();
  }, [showNotes, activeLesson, loadNotes]);

  // Reset lesson timer and fire lesson_started whenever the active lesson changes
  useEffect(() => {
    lessonStartRef.current = Date.now();
    if (activeLesson?.id && mod?.id) {
      analytics.lessonStarted(activeLesson.id, mod.id);
    }
  }, [activeLesson?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // Persist lay mode preference
  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("medmind_lay_mode", layMode ? "1" : "0");
    }
  }, [layMode]);

  // Fetch lay view when switching to lay mode or changing lesson
  useEffect(() => {
    if (!layMode || !activeLesson) return;
    // Use cached data from lesson if available
    if (activeLesson.lay_summary) {
      setLayData({ lay_summary: activeLesson.lay_summary, lay_glossary: activeLesson.lay_glossary });
      return;
    }
    setLayLoading(true);
    setLayData(null);
    contentApi.getLessonLay(activeLesson.id)
      .then((data: any) => setLayData(data))
      .catch(() => setLayData(null))
      .finally(() => setLayLoading(false));
  }, [layMode, activeLesson?.id]);

  const completeLesson = async () => {
    if (!activeLesson || completing) return;
    setCompleting(true);
    const timeSpent = Math.round((Date.now() - lessonStartRef.current) / 1000);
    try {
      await progressApi.completeLesson(activeLesson.id);
      progressApi.recordLessonCompletion(activeLesson.id, { time_spent_seconds: timeSpent });
      ga.lessonComplete(activeLesson.title || "");
      analytics.lessonCompleted(activeLesson.id, mod?.id ?? "");
      const newDone = new Set(Array.from(lessonDone).concat(activeLesson.id));
      setLessonDone(newDone);
      // Show SRS reinforce prompt
      setSrsLessonId(activeLesson.id);
      setShowSrsPrompt(true);
      const idx = lessons.findIndex((l) => l.id === activeLesson.id);
      if (idx < lessons.length - 1) {
        setActiveLesson(lessons[idx + 1]);
        lessonStartRef.current = Date.now();
      }
      // Auto-issue certificate when all lessons done
      if (newDone.size >= lessons.length && mod?.id && !certCode) {
        certificatesApi.issue(mod.id)
          .then((c: any) => { if (c?.verification_code) setCertCode(c.verification_code); })
          .catch(() => {/* not yet eligible — ignore */});
      }
    } catch {/* ignore */} finally {
      setCompleting(false);
    }
  };

  const handleSrsEnqueue = async () => {
    if (!srsLessonId) return;
    try { await srsApi.enqueue("lesson", srsLessonId); } catch {/* ignore */}
    setShowSrsPrompt(false);
  };

  const saveNote = async () => {
    if (!noteText.trim() || !activeLesson) return;
    setSavingNote(true);
    try {
      await notesApi.create({ content: noteText.trim(), lesson_id: activeLesson.id });
      setNoteText("");
      loadNotes();
    } finally {
      setSavingNote(false);
    }
  };

  const updateNote = async (noteId: string) => {
    if (!editText.trim()) return;
    await notesApi.update(noteId, editText.trim());
    setEditingId(null);
    loadNotes();
  };

  const deleteNote = async (noteId: string) => {
    await notesApi.remove(noteId);
    loadNotes();
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="font-serif text-ink-3 text-sm animate-pulse">Loading…</div>
      </div>
    );
  }

  if (paywalled) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="max-w-sm w-full text-center space-y-5">
          <div className="w-16 h-16 rounded-full bg-amber-light border border-amber/30 flex items-center justify-center mx-auto text-3xl">
            🔒
          </div>
          <div>
            <h2 className="font-syne font-black text-xl text-ink mb-2">Upgrade to access this module</h2>
            <p className="font-serif text-sm text-ink-3 leading-relaxed">
              This is a specialty module available on Student and Pro plans. Free accounts can access all Foundation modules.
            </p>
          </div>
          <div className="flex flex-col gap-2">
            <a
              href="/pricing"
              className="btn-primary font-syne font-bold text-sm px-6 py-2.5 rounded-lg inline-block"
            >
              View plans →
            </a>
            <button
              onClick={() => router.back()}
              className="font-syne text-sm text-ink-3 hover:text-ink transition-colors"
            >
              ← Go back
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Lesson sidebar */}
      <div className="w-56 flex-shrink-0 border-r border-border bg-surface overflow-y-auto">
        <div className="p-3 border-b border-border">
          <button onClick={() => router.back()} className="text-ink-3 hover:text-ink text-xs font-syne mb-1 block">
            ← Back
          </button>
          <div className="font-syne font-bold text-sm text-ink line-clamp-2">{mod?.title}</div>
        </div>
        {lessons.map((lesson, i) => (
          <button
            key={lesson.id}
            onClick={() => setActiveLesson(lesson)}
            className={`w-full text-left px-3 py-2.5 border-b border-border/50 transition-colors ${
              activeLesson?.id === lesson.id ? "bg-ink text-white" : "hover:bg-bg-2 text-ink-2"
            }`}
          >
            <div className="flex items-center gap-2">
              <span
                className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold flex-shrink-0 ${
                  lessonDone.has(lesson.id)
                    ? "bg-green text-white"
                    : activeLesson?.id === lesson.id
                    ? "bg-white/20 text-white"
                    : "bg-border text-ink-3"
                }`}
              >
                {lessonDone.has(lesson.id) ? "✓" : i + 1}
              </span>
              <span className="font-syne font-semibold text-xs leading-tight">{lesson.title}</span>
            </div>
          </button>
        ))}

        {/* Links to other content types */}
        <div className="p-3 mt-2 space-y-1.5">
          <Link
            href={`/flashcards?module=${id}`}
            className="flex items-center gap-2 text-xs font-syne font-semibold text-blue hover:text-blue-2 transition-colors"
          >
            🃏 Review flashcards
          </Link>
          <Link
            href={`/quiz/${id}`}
            className="flex items-center gap-2 text-xs font-syne font-semibold text-green hover:text-green-2 transition-colors"
          >
            📝 Take quiz
          </Link>
          <Link
            href={`/cases?module=${id}`}
            className="flex items-center gap-2 text-xs font-syne font-semibold text-amber hover:text-amber-2 transition-colors"
          >
            🩺 Clinical cases
          </Link>
          <Link
            href={`/ai-tutor`}
            className="flex items-center gap-2 text-xs font-syne font-semibold text-red hover:text-red-2 transition-colors"
          >
            🤖 Ask AI Tutor
          </Link>
          {mod?.code && (
            <a
              href={`/articles?search=${encodeURIComponent(mod.title ?? "")}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-xs font-syne font-semibold text-ink-3 hover:text-ink transition-colors"
            >
              📰 Related articles ↗
            </a>
          )}
        </div>
      </div>

      {/* Lesson content */}
      <div className="flex-1 overflow-y-auto">
        {activeLesson ? (
          <div className="max-w-2xl mx-auto p-6">
            <div className="flex items-start justify-between mb-4 gap-3">
              <h2 className="font-syne font-black text-2xl text-ink">{activeLesson.title}</h2>
              <div className="flex items-center gap-2 flex-shrink-0">
                {/* Plain-language toggle */}
                <button
                  onClick={() => setLayMode((v) => !v)}
                  title={layMode ? "Switch to professional view" : "Switch to plain language (for everyone)"}
                  className={`flex items-center gap-1.5 text-xs font-syne font-bold px-3 py-1.5 rounded border transition-colors ${
                    layMode
                      ? "bg-green-light text-green border-green/30"
                      : "bg-bg-2 text-ink-2 hover:bg-green-light hover:text-green border-border"
                  }`}
                >
                  {layMode ? "🟢 Simple" : "🔬 Pro"}
                </button>
                <button
                  onClick={() => setShowNotes((v) => !v)}
                  className={`flex items-center gap-1.5 text-xs font-syne font-bold px-3 py-1.5 rounded border transition-colors ${
                    showNotes
                      ? "bg-amber-light text-amber border-amber/30"
                      : "bg-bg-2 text-ink-2 hover:bg-amber-light hover:text-amber border-border"
                  }`}
                >
                  📝 Notes {notes.length > 0 && !showNotes ? `(${notes.length})` : ""}
                </button>
              </div>
            </div>

            {/* Lay mode view */}
            {layMode ? (
              <div>
                {layLoading ? (
                  <div className="space-y-3 animate-pulse">
                    <div className="h-4 bg-bg-2 rounded w-3/4" />
                    <div className="h-4 bg-bg-2 rounded w-full" />
                    <div className="h-4 bg-bg-2 rounded w-5/6" />
                    <div className="h-4 bg-bg-2 rounded w-2/3" />
                  </div>
                ) : layData?.lay_summary ? (
                  <LayView data={layData} />
                ) : (
                  <div className="card p-6 text-center">
                    <p className="font-serif text-ink-3 text-sm mb-2">
                      Simple language version not yet available for this lesson.
                    </p>
                    <button
                      onClick={() => setLayMode(false)}
                      className="text-xs font-syne font-semibold text-ink-2 underline"
                    >
                      View professional content
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <LessonContentRenderer content={activeLesson.content} />
            )}

            {/* Notes panel */}
            {showNotes && (
              <div className="mt-8 border border-amber/30 rounded-xl bg-amber-light/30 p-4">
                <h3 className="font-syne font-bold text-sm text-ink mb-3">📝 My Notes</h3>

                {/* Add note */}
                <div className="mb-4">
                  <textarea
                    value={noteText}
                    onChange={(e) => setNoteText(e.target.value)}
                    placeholder="Write a note about this lesson…"
                    rows={3}
                    className="w-full text-sm font-serif bg-white border border-border rounded-lg px-3 py-2 resize-none focus:outline-none focus:border-amber"
                  />
                  <button
                    onClick={saveNote}
                    disabled={savingNote || !noteText.trim()}
                    className="mt-2 btn-primary text-xs px-4 py-1.5 disabled:opacity-50"
                  >
                    {savingNote ? "Saving…" : "Save note"}
                  </button>
                </div>

                {/* Existing notes */}
                {notes.length === 0 ? (
                  <p className="text-xs font-serif text-ink-3">No notes yet for this lesson.</p>
                ) : (
                  <div className="space-y-3">
                    {notes.map((note) => (
                      <div key={note.id} className="bg-white rounded-lg border border-border p-3">
                        {editingId === note.id ? (
                          <div>
                            <textarea
                              value={editText}
                              onChange={(e) => setEditText(e.target.value)}
                              rows={3}
                              className="w-full text-sm font-serif bg-bg-2 border border-border rounded px-2 py-1.5 resize-none focus:outline-none"
                            />
                            <div className="flex gap-2 mt-2">
                              <button
                                onClick={() => updateNote(note.id)}
                                className="text-xs font-syne font-bold text-green border border-green/30 bg-green-light px-3 py-1 rounded"
                              >
                                Save
                              </button>
                              <button
                                onClick={() => setEditingId(null)}
                                className="text-xs font-syne text-ink-3 hover:text-ink"
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div>
                            <p className="text-sm font-serif text-ink whitespace-pre-wrap">{note.content}</p>
                            <div className="flex gap-3 mt-2">
                              <button
                                onClick={() => { setEditingId(note.id); setEditText(note.content); }}
                                className="text-xs font-syne text-ink-3 hover:text-blue"
                              >
                                Edit
                              </button>
                              <button
                                onClick={() => deleteNote(note.id)}
                                className="text-xs font-syne text-ink-3 hover:text-red"
                              >
                                Delete
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* AI Practice Questions */}
            <LessonQuizPanel lessonId={activeLesson.id} lessonTitle={activeLesson.title} />

            {/* Lesson navigation footer */}
            <div className="mt-8 border-t border-border pt-5 space-y-4">
              {/* Prev / Next lesson labels */}
              {(() => {
                const idx = lessons.findIndex((l) => l.id === activeLesson.id);
                const prevL = idx > 0 ? lessons[idx - 1] : null;
                const nextL = idx < lessons.length - 1 ? lessons[idx + 1] : null;
                return (
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      {prevL && (
                        <button
                          onClick={() => setActiveLesson(prevL)}
                          className="group w-full text-left p-3 rounded-lg border border-border hover:border-ink transition-all"
                        >
                          <div className="text-[10px] font-syne text-ink-3 uppercase tracking-wider mb-0.5">← Previous</div>
                          <div className="text-xs font-syne font-semibold text-ink-2 group-hover:text-ink line-clamp-2">
                            {prevL.title}
                          </div>
                        </button>
                      )}
                    </div>
                    <div>
                      {nextL && (
                        <button
                          onClick={() => setActiveLesson(nextL)}
                          className="group w-full text-right p-3 rounded-lg border border-border hover:border-ink transition-all"
                        >
                          <div className="text-[10px] font-syne text-ink-3 uppercase tracking-wider mb-0.5">Next →</div>
                          <div className="text-xs font-syne font-semibold text-ink-2 group-hover:text-ink line-clamp-2">
                            {nextL.title}
                          </div>
                        </button>
                      )}
                    </div>
                  </div>
                );
              })()}

              {certCode && (
                <div className="mt-4 p-4 rounded-lg border border-green/30 bg-green-light/30 space-y-2">
                  <p className="font-syne font-bold text-sm text-green">Certificate earned!</p>
                  <p className="font-serif text-xs text-green/80">
                    You completed this module. Your certificate is ready.
                  </p>
                  <div className="flex gap-2">
                    <a
                      href="/settings"
                      className="font-syne font-bold text-xs px-3 py-1.5 rounded bg-green text-white hover:bg-green/90 transition-colors"
                    >
                      View in Settings →
                    </a>
                    <a
                      href={`/verify/${certCode}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-syne font-bold text-xs px-3 py-1.5 rounded border border-green/30 text-green hover:bg-green-light transition-colors"
                    >
                      Verify
                    </a>
                  </div>
                </div>
              )}

              {showSrsPrompt && srsLessonId === activeLesson.id && (
                <div className="mt-4 p-4 rounded-lg border border-blue/20 bg-blue/5 flex items-center justify-between gap-4">
                  <div>
                    <p className="font-syne font-bold text-sm text-ink-1">Reinforce this lesson?</p>
                    <p className="text-xs font-serif text-ink-3 mt-0.5">3 quick questions will be added to your spaced-repetition queue.</p>
                  </div>
                  <div className="flex gap-2 shrink-0">
                    <button
                      onClick={handleSrsEnqueue}
                      className="font-syne font-bold text-xs px-3 py-1.5 rounded bg-blue text-white hover:bg-blue/90 transition-colors"
                    >
                      Yes, add
                    </button>
                    <button
                      onClick={() => setShowSrsPrompt(false)}
                      className="font-syne text-xs px-3 py-1.5 rounded border border-ink-4 text-ink-3 hover:border-ink-3 transition-colors"
                    >
                      Skip
                    </button>
                  </div>
                </div>
              )}

              <div className="flex items-center justify-between">
                <div className="text-xs font-serif text-ink-3">
                  Lesson {lessons.findIndex((l) => l.id === activeLesson.id) + 1} of {lessons.length}
                </div>
                <button
                  onClick={completeLesson}
                  disabled={completing || lessonDone.has(activeLesson.id)}
                  className={`font-syne font-bold text-sm px-5 py-2 rounded transition-colors ${
                    lessonDone.has(activeLesson.id)
                      ? "bg-green-light text-green border border-green/20 cursor-default"
                      : "btn-primary"
                  }`}
                >
                  {lessonDone.has(activeLesson.id)
                    ? "✓ Completed"
                    : completing
                    ? "Saving…"
                    : "Mark complete & continue →"}
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <p className="font-serif text-ink-3 text-sm">Select a lesson to begin</p>
          </div>
        )}
      </div>
    </div>
  );
}
