"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { contentApi, progressApi, notesApi } from "@/lib/api";

type LessonContent = {
  intro?: string;
  sections?: { heading: string; text: string }[];
  clinical_pearl?: string;
  key_points?: string[];
};
type Lesson = { id: string; title: string; content: LessonContent | string; lesson_order: number };
type Note = { id: string; content: string; lesson_id?: string; module_id?: string };

type Block = { type: string; order: number; content: Record<string, unknown> };

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
            const c = block.content as { url: string; caption?: string };
            if (!c.url) return null;
            return (
              <figure key={i} className="my-2">
                <img src={c.url} alt={c.caption ?? ""} className="rounded-lg max-w-full border border-border" />
                {c.caption && <figcaption className="font-serif text-xs text-ink-3 mt-1.5 text-center">{c.caption}</figcaption>}
              </figure>
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

export default function ModuleDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [mod, setMod] = useState<any>(null);
  const [lessons, setLessons] = useState<Lesson[]>([]);
  const [activeLesson, setActiveLesson] = useState<Lesson | null>(null);
  const [lessonDone, setLessonDone] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [completing, setCompleting] = useState(false);
  const lessonStartRef = useRef<number>(Date.now());

  // Notes state
  const [showNotes, setShowNotes] = useState(false);
  const [notes, setNotes] = useState<Note[]>([]);
  const [noteText, setNoteText] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");
  const [savingNote, setSavingNote] = useState(false);

  useEffect(() => {
    if (!id) return;
    Promise.all([
      contentApi.getModule(id),
      contentApi.getLessons(id),
    ]).then(([modRes, lessonRes]) => {
      setMod(modRes.data);
      const ls: Lesson[] = lessonRes.data ?? [];
      ls.sort((a, b) => a.lesson_order - b.lesson_order);
      setLessons(ls);
      if (ls.length > 0) setActiveLesson(ls[0]);
      setLoading(false);
    });
  }, [id]);

  const loadNotes = useCallback(() => {
    if (!activeLesson) return;
    notesApi.list({ lesson_id: activeLesson.id }).then((r) => setNotes(r.data ?? []));
  }, [activeLesson]);

  useEffect(() => {
    if (showNotes && activeLesson) loadNotes();
  }, [showNotes, activeLesson, loadNotes]);

  // Reset lesson timer whenever the active lesson changes
  useEffect(() => {
    lessonStartRef.current = Date.now();
  }, [activeLesson?.id]);

  const completeLesson = async () => {
    if (!activeLesson || completing) return;
    setCompleting(true);
    const timeSpent = Math.round((Date.now() - lessonStartRef.current) / 1000);
    try {
      await progressApi.completeLesson(activeLesson.id);
      progressApi.recordLessonCompletion(activeLesson.id, { time_spent_seconds: timeSpent });
      setLessonDone((p) => new Set(Array.from(p).concat(activeLesson.id)));
      const idx = lessons.findIndex((l) => l.id === activeLesson.id);
      if (idx < lessons.length - 1) {
        setActiveLesson(lessons[idx + 1]);
        lessonStartRef.current = Date.now();
      }
    } catch {/* ignore */} finally {
      setCompleting(false);
    }
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
        </div>
      </div>

      {/* Lesson content */}
      <div className="flex-1 overflow-y-auto">
        {activeLesson ? (
          <div className="max-w-2xl mx-auto p-6">
            <div className="flex items-start justify-between mb-4 gap-3">
              <h2 className="font-syne font-black text-2xl text-ink">{activeLesson.title}</h2>
              <button
                onClick={() => setShowNotes((v) => !v)}
                className={`flex-shrink-0 flex items-center gap-1.5 text-xs font-syne font-bold px-3 py-1.5 rounded transition-colors ${
                  showNotes
                    ? "bg-amber-light text-amber border border-amber/30"
                    : "bg-bg-2 text-ink-2 hover:bg-amber-light hover:text-amber border border-border"
                }`}
              >
                📝 Notes {notes.length > 0 && !showNotes ? `(${notes.length})` : ""}
              </button>
            </div>
            <LessonContentRenderer content={activeLesson.content} />

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

            <div className="mt-8 flex items-center justify-between border-t border-border pt-5">
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
        ) : (
          <div className="flex items-center justify-center h-full">
            <p className="font-serif text-ink-3 text-sm">Select a lesson to begin</p>
          </div>
        )}
      </div>
    </div>
  );
}
