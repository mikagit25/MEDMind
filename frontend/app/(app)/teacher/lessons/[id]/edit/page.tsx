"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { teacherApi, imagingApi } from "@/lib/api";
import { MediaPickerModal } from "@/components/ui/MediaPickerModal";

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

type BlockType = "text" | "quiz" | "case" | "image" | "anatomy_3d";

interface TextContent { heading?: string; text: string }
interface QuizContent { question: string; options: Record<string, string>; correct: string; explanation: string }
interface CaseContent { presentation: string; questions: string[]; teaching_points: string[] }
interface ImageContent { url: string; caption?: string; alt?: string; image_id?: string; modality?: string }
interface Anatomy3DContent { viewer_id?: string; embed_url?: string; caption?: string; organ_system?: string }

type BlockContent = TextContent | QuizContent | CaseContent | ImageContent | Anatomy3DContent;

interface Block { type: BlockType; order: number; content: BlockContent }

interface LessonContent {
  title: string;
  blocks: Block[];
  estimated_minutes: number;
  learning_objectives: string[];
}

interface Lesson {
  id: string;
  module_id: string;
  title: string;
  status: "draft" | "review" | "published" | "archived";
  estimated_minutes: number;
  content: Record<string, unknown>;
  review_notes?: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────────────

const BLOCK_ICONS: Record<BlockType, string> = {
  text: "📝",
  quiz: "❓",
  case: "🩺",
  image: "🖼️",
  anatomy_3d: "🧊",
};

const BLOCK_LABELS: Record<BlockType, string> = {
  text: "Text Block",
  quiz: "Quiz",
  case: "Clinical Case",
  image: "Image",
  anatomy_3d: "3D Anatomy",
};

const AI_TASKS = [
  { value: "improve_clarity", label: "Improve clarity" },
  { value: "add_quiz", label: "Add quiz blocks" },
  { value: "simplify_language", label: "Simplify language" },
  { value: "add_clinical_case", label: "Add clinical case" },
  { value: "check_accuracy", label: "Check accuracy" },
];

const SPECIALTIES = [
  "Cardiology", "Neurology", "Surgery", "Obstetrics & Gynecology",
  "Pediatrics", "Internal Medicine", "Pharmacology",
  "Laboratory Diagnostics", "Respiratory Medicine", "Veterinary",
];

const LEVELS = ["beginner", "intermediate", "advanced"];

const STATUS_COLORS: Record<string, string> = {
  draft: "text-ink-3",
  review: "text-amber",
  published: "text-green",
  archived: "text-red",
};

// ─────────────────────────────────────────────────────────────────────────────
// Block editors
// ─────────────────────────────────────────────────────────────────────────────

function TextBlockEditor({
  block,
  onChange,
}: {
  block: Block;
  onChange: (b: Block) => void;
}) {
  const c = block.content as TextContent;
  return (
    <div className="space-y-2">
      <input
        type="text"
        value={c.heading ?? ""}
        onChange={(e) => onChange({ ...block, content: { ...c, heading: e.target.value } })}
        placeholder="Heading (optional)"
        className="w-full border border-border rounded-lg px-3 py-1.5 font-syne font-semibold text-sm text-ink bg-surface focus:outline-none focus:border-ink-3"
      />
      <textarea
        value={c.text}
        onChange={(e) => onChange({ ...block, content: { ...c, text: e.target.value } })}
        placeholder="Write the lesson text here..."
        rows={5}
        className="w-full border border-border rounded-lg px-3 py-2 font-serif text-sm text-ink bg-surface focus:outline-none focus:border-ink-3 resize-y"
      />
    </div>
  );
}

function QuizBlockEditor({
  block,
  onChange,
}: {
  block: Block;
  onChange: (b: Block) => void;
}) {
  const c = block.content as QuizContent;
  const opts = c.options ?? { A: "", B: "", C: "", D: "" };

  function setOption(key: string, val: string) {
    onChange({ ...block, content: { ...c, options: { ...opts, [key]: val } } });
  }

  return (
    <div className="space-y-2">
      <input
        type="text"
        value={c.question ?? ""}
        onChange={(e) => onChange({ ...block, content: { ...c, question: e.target.value } })}
        placeholder="Question *"
        className="w-full border border-border rounded-lg px-3 py-1.5 font-serif text-sm text-ink bg-surface focus:outline-none focus:border-ink-3"
      />
      <div className="grid grid-cols-2 gap-2">
        {["A", "B", "C", "D"].map((k) => (
          <div key={k} className="flex items-center gap-1.5">
            <span className="font-syne font-bold text-xs text-ink-3 w-4 shrink-0">{k}:</span>
            <input
              type="text"
              value={opts[k] ?? ""}
              onChange={(e) => setOption(k, e.target.value)}
              placeholder={`Option ${k}`}
              className="flex-1 border border-border rounded px-2 py-1 font-serif text-xs text-ink bg-surface focus:outline-none focus:border-ink-3"
            />
          </div>
        ))}
      </div>
      <div className="flex items-center gap-3">
        <span className="font-syne text-xs text-ink-3 shrink-0">Correct answer:</span>
        <select
          value={c.correct ?? "A"}
          onChange={(e) => onChange({ ...block, content: { ...c, correct: e.target.value } })}
          className="border border-border rounded px-2 py-1 font-syne text-xs text-ink bg-surface focus:outline-none"
        >
          {["A", "B", "C", "D"].map((k) => (
            <option key={k} value={k}>{k}</option>
          ))}
        </select>
      </div>
      <textarea
        value={c.explanation ?? ""}
        onChange={(e) => onChange({ ...block, content: { ...c, explanation: e.target.value } })}
        placeholder="Explanation of the correct answer..."
        rows={2}
        className="w-full border border-border rounded-lg px-3 py-1.5 font-serif text-xs text-ink bg-surface focus:outline-none focus:border-ink-3 resize-none"
      />
    </div>
  );
}

function CaseBlockEditor({
  block,
  onChange,
}: {
  block: Block;
  onChange: (b: Block) => void;
}) {
  const c = block.content as CaseContent;
  const questions = c.questions ?? [""];
  const points = c.teaching_points ?? [""];

  function updateList(key: "questions" | "teaching_points", idx: number, val: string) {
    const arr = key === "questions" ? [...questions] : [...points];
    arr[idx] = val;
    onChange({ ...block, content: { ...c, [key]: arr } });
  }
  function addItem(key: "questions" | "teaching_points") {
    const arr = key === "questions" ? [...questions, ""] : [...points, ""];
    onChange({ ...block, content: { ...c, [key]: arr } });
  }
  function removeItem(key: "questions" | "teaching_points", idx: number) {
    const arr = key === "questions"
      ? questions.filter((_, i) => i !== idx)
      : points.filter((_, i) => i !== idx);
    onChange({ ...block, content: { ...c, [key]: arr } });
  }

  return (
    <div className="space-y-3">
      <div>
        <label className="block font-syne text-xs text-ink-3 mb-1">Patient presentation *</label>
        <textarea
          value={c.presentation ?? ""}
          onChange={(e) => onChange({ ...block, content: { ...c, presentation: e.target.value } })}
          placeholder="Describe the clinical scenario..."
          rows={3}
          className="w-full border border-border rounded-lg px-3 py-2 font-serif text-sm text-ink bg-surface focus:outline-none focus:border-ink-3 resize-none"
        />
      </div>
      <div>
        <label className="block font-syne text-xs text-ink-3 mb-1">Discussion questions</label>
        {questions.map((q, i) => (
          <div key={i} className="flex gap-1.5 mb-1">
            <input
              type="text"
              value={q}
              onChange={(e) => updateList("questions", i, e.target.value)}
              placeholder={`Question ${i + 1}`}
              className="flex-1 border border-border rounded px-2 py-1 font-serif text-xs text-ink bg-surface focus:outline-none focus:border-ink-3"
            />
            {questions.length > 1 && (
              <button onClick={() => removeItem("questions", i)} className="text-red text-xs px-1.5 hover:bg-red-light rounded">✕</button>
            )}
          </div>
        ))}
        <button onClick={() => addItem("questions")} className="text-xs text-ink-3 font-syne hover:text-ink">+ Add question</button>
      </div>
      <div>
        <label className="block font-syne text-xs text-ink-3 mb-1">Teaching points</label>
        {points.map((p, i) => (
          <div key={i} className="flex gap-1.5 mb-1">
            <input
              type="text"
              value={p}
              onChange={(e) => updateList("teaching_points", i, e.target.value)}
              placeholder={`Teaching point ${i + 1}`}
              className="flex-1 border border-border rounded px-2 py-1 font-serif text-xs text-ink bg-surface focus:outline-none focus:border-ink-3"
            />
            {points.length > 1 && (
              <button onClick={() => removeItem("teaching_points", i)} className="text-red text-xs px-1.5 hover:bg-red-light rounded">✕</button>
            )}
          </div>
        ))}
        <button onClick={() => addItem("teaching_points")} className="text-xs text-ink-3 font-syne hover:text-ink">+ Add point</button>
      </div>
    </div>
  );
}

function ImageBlockEditor({
  block,
  onChange,
  onUpload,
  lessonTitle,
}: {
  block: Block;
  onChange: (b: Block) => void;
  onUpload: (lessonId: string, file: File) => Promise<string>;
  lessonId: string;
  lessonTitle?: string;
}) {
  const c = block.content as ImageContent;
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [showPicker, setShowPicker] = useState(false);
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadError("");
    try {
      const url = await onUpload((block as any)._lessonId ?? "", file);
      onChange({ ...block, content: { ...c, url } });
    } catch (err: any) {
      setUploadError(err?.response?.data?.detail ?? "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  async function loadSuggestions() {
    if (!lessonTitle) return;
    setLoadingSuggestions(true);
    setSuggestions([]);
    try {
      const res = await imagingApi.suggest(lessonTitle, undefined, 6);
      setSuggestions(res ?? []);
    } catch {
      setSuggestions([]);
    } finally {
      setLoadingSuggestions(false);
    }
  }

  return (
    <>
      {showPicker && (
        <MediaPickerModal
          onSelect={(url, caption, image_id) => {
            onChange({ ...block, content: { ...c, url, caption, image_id } });
            setShowPicker(false);
          }}
          onClose={() => setShowPicker(false)}
        />
      )}
      <div className="space-y-2">
        {c.url ? (
          <div className="relative">
            <img src={c.url} alt={c.alt ?? "lesson image"} className="rounded-lg max-h-48 object-contain border border-border" />
            <button
              onClick={() => onChange({ ...block, content: { ...c, url: "", image_id: undefined } })}
              className="absolute top-1 right-1 bg-ink/70 text-white text-xs px-2 py-0.5 rounded"
            >
              Remove
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {/* Suggest + browse */}
            <div className="flex gap-2">
              <button
                onClick={() => setShowPicker(true)}
                className="flex-1 flex items-center justify-center gap-2 h-16 border-2 border-dashed border-blue/40 rounded-lg hover:border-blue hover:bg-blue-light/30 transition-colors"
              >
                <span className="text-lg">🩻</span>
                <div className="text-left">
                  <div className="font-syne font-semibold text-xs text-blue">Browse Library</div>
                  <div className="font-serif text-[10px] text-ink-3">X-Ray, CT, MRI…</div>
                </div>
              </button>
              {lessonTitle && (
                <button
                  onClick={loadSuggestions}
                  disabled={loadingSuggestions}
                  className="flex-1 flex items-center justify-center gap-2 h-16 border-2 border-dashed border-green/40 rounded-lg hover:border-green hover:bg-green-light/30 transition-colors disabled:opacity-50"
                >
                  <span className="text-lg">✨</span>
                  <div className="text-left">
                    <div className="font-syne font-semibold text-xs text-green">
                      {loadingSuggestions ? "Searching…" : "Suggest Images"}
                    </div>
                    <div className="font-serif text-[10px] text-ink-3">Based on lesson topic</div>
                  </div>
                </button>
              )}
            </div>

            {/* Suggestions grid */}
            {suggestions.length > 0 && (
              <div>
                <div className="font-syne font-semibold text-xs text-ink-3 mb-1.5">Suggested for this lesson:</div>
                <div className="grid grid-cols-3 gap-1.5">
                  {suggestions.map((img: any) => (
                    <button
                      key={img.id}
                      onClick={() => {
                        const caption = img.attribution
                          ? `${img.title} — ${img.attribution}`
                          : `${img.title} — ${img.source_name}`;
                        onChange({ ...block, content: { ...c, url: img.image_url, caption, image_id: img.id } });
                        setSuggestions([]);
                      }}
                      className="rounded-lg overflow-hidden border border-border hover:border-green hover:shadow-sm transition-all text-left group"
                      title={img.title}
                    >
                      <div className="aspect-[4/3] bg-surface overflow-hidden">
                        <img src={img.thumbnail_url || img.image_url} alt={img.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
                      </div>
                      <div className="px-1 py-0.5">
                        <div className="font-syne text-[9px] font-semibold text-ink line-clamp-1">{img.title}</div>
                      </div>
                    </button>
                  ))}
                </div>
                <button onClick={() => setSuggestions([])} className="text-xs text-ink-3 font-serif mt-1 hover:text-ink">Clear suggestions</button>
              </div>
            )}

            <div className="flex items-center gap-2 text-ink-3">
              <div className="flex-1 h-px bg-border" />
              <span className="font-serif text-xs">or upload / paste URL</span>
              <div className="flex-1 h-px bg-border" />
            </div>

            <label className={`flex flex-col items-center justify-center h-16 border-2 border-dashed border-border rounded-lg cursor-pointer hover:border-ink-3 transition-colors ${uploading ? "opacity-50" : ""}`}>
              <span className="text-lg mb-0.5">🖼️</span>
              <span className="font-serif text-xs text-ink-3">{uploading ? "Uploading..." : "Upload your own image"}</span>
              <input type="file" accept="image/jpeg,image/png,image/svg+xml,image/webp" onChange={handleFile} disabled={uploading} className="hidden" />
            </label>
            {uploadError && <p className="text-red text-xs font-serif">{uploadError}</p>}

            <input
              type="url"
              value={c.url ?? ""}
              onChange={(e) => onChange({ ...block, content: { ...c, url: e.target.value } })}
              placeholder="Or paste image URL: https://..."
              className="w-full border border-border rounded px-2 py-1 font-serif text-xs text-ink bg-surface focus:outline-none focus:border-ink-3"
            />
          </div>
        )}
        <input
          type="text"
          value={c.caption ?? ""}
          onChange={(e) => onChange({ ...block, content: { ...c, caption: e.target.value } })}
          placeholder="Caption (optional)"
          className="w-full border border-border rounded px-2 py-1 font-serif text-xs text-ink bg-surface focus:outline-none focus:border-ink-3"
        />
      </div>
    </>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// 3D Anatomy block editor
// ─────────────────────────────────────────────────────────────────────────────

const ORGAN_SYSTEMS = [
  "cardiovascular", "nervous", "respiratory", "digestive",
  "musculoskeletal", "urinary", "endocrine", "reproductive", "lymphatic",
];

function Anatomy3DBlockEditor({ block, onChange }: { block: Block; onChange: (b: Block) => void }) {
  const c = block.content as Anatomy3DContent;
  const [viewers, setViewers] = useState<any[]>([]);
  const [loadingViewers, setLoadingViewers] = useState(false);
  const [systemFilter, setSystemFilter] = useState(c.organ_system ?? "");

  async function loadViewers(system?: string) {
    setLoadingViewers(true);
    try {
      const data = await imagingApi.listViewers(system || undefined);
      setViewers(data ?? []);
    } catch {
      setViewers([]);
    } finally {
      setLoadingViewers(false);
    }
  }

  useEffect(() => { loadViewers(systemFilter); }, [systemFilter]);

  function selectViewer(v: any) {
    onChange({
      ...block,
      content: {
        ...c,
        viewer_id: v.id,
        embed_url: v.embed_url || buildSketchfabEmbed(v.embed_type, v.embed_id),
        caption: c.caption || v.title,
        organ_system: v.organ_system,
      },
    });
  }

  function buildSketchfabEmbed(type: string, id: string): string {
    if (type === "sketchfab") return `https://sketchfab.com/models/${id}/embed`;
    if (type === "biodigital") return `https://human.biodigital.com/viewer/?id=${id}&ui-anatomy-descriptions=true`;
    return id;
  }

  const embedUrl = c.embed_url || (c.viewer_id ? "" : "");

  return (
    <div className="space-y-3">
      {/* Current embed preview */}
      {embedUrl ? (
        <div className="space-y-2">
          <div className="rounded-xl overflow-hidden border border-border bg-surface" style={{ aspectRatio: "16/9" }}>
            <iframe
              src={embedUrl}
              title={c.caption ?? "3D Anatomy Viewer"}
              allow="autoplay; fullscreen; xr-spatial-tracking"
              className="w-full h-full"
              frameBorder="0"
            />
          </div>
          <div className="flex items-center justify-between">
            <input
              type="text"
              value={c.caption ?? ""}
              onChange={e => onChange({ ...block, content: { ...c, caption: e.target.value } })}
              placeholder="Caption (optional)"
              className="flex-1 border border-border rounded px-2 py-1 font-serif text-xs text-ink bg-surface focus:outline-none focus:border-ink-3 mr-2"
            />
            <button
              onClick={() => onChange({ ...block, content: { embed_url: "", viewer_id: undefined, caption: "", organ_system: "" } })}
              className="font-syne text-xs text-red hover:text-red/70"
            >
              Remove
            </button>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {/* Library picker */}
          <div>
            <div className="font-syne font-semibold text-xs text-ink-3 mb-1.5">Browse 3D Anatomy Library</div>
            <div className="flex gap-1.5 overflow-x-auto pb-1 mb-2">
              <button
                onClick={() => setSystemFilter("")}
                className={`shrink-0 px-2.5 py-0.5 rounded-full font-syne text-[10px] border transition-colors ${!systemFilter ? "bg-ink text-white border-ink" : "border-border text-ink-3 hover:border-ink-3"}`}
              >
                All
              </button>
              {ORGAN_SYSTEMS.map(sys => (
                <button
                  key={sys}
                  onClick={() => setSystemFilter(sys)}
                  className={`shrink-0 px-2.5 py-0.5 rounded-full font-syne text-[10px] border capitalize transition-colors ${systemFilter === sys ? "bg-ink text-white border-ink" : "border-border text-ink-3 hover:border-ink-3"}`}
                >
                  {sys}
                </button>
              ))}
            </div>
            {loadingViewers ? (
              <div className="font-serif text-xs text-ink-3">Loading viewers…</div>
            ) : viewers.length === 0 ? (
              <div className="font-serif text-xs text-ink-3">No 3D viewers available{systemFilter ? ` for ${systemFilter}` : ""}.</div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 max-h-64 overflow-y-auto">
                {viewers.map((v: any) => (
                  <button
                    key={v.id}
                    onClick={() => selectViewer(v)}
                    className="rounded-lg overflow-hidden border border-border hover:border-blue hover:shadow-sm transition-all text-left group"
                    title={v.title}
                  >
                    {v.thumbnail_url ? (
                      <div className="aspect-[4/3] bg-surface overflow-hidden">
                        <img src={v.thumbnail_url} alt={v.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
                      </div>
                    ) : (
                      <div className="aspect-[4/3] bg-surface flex items-center justify-center text-3xl">🧊</div>
                    )}
                    <div className="p-1.5">
                      <div className="font-syne text-[9px] font-semibold text-ink line-clamp-2">{v.title}</div>
                      {v.organ_system && (
                        <div className="font-serif text-[9px] text-ink-3 capitalize">{v.organ_system}</div>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Or paste embed URL directly */}
          <div className="flex items-center gap-2 text-ink-3">
            <div className="flex-1 h-px bg-border" />
            <span className="font-serif text-xs">or paste embed URL</span>
            <div className="flex-1 h-px bg-border" />
          </div>
          <input
            type="url"
            value={c.embed_url ?? ""}
            onChange={e => onChange({ ...block, content: { ...c, embed_url: e.target.value } })}
            placeholder="https://sketchfab.com/models/.../embed"
            className="w-full border border-border rounded px-2 py-1 font-serif text-xs text-ink bg-surface focus:outline-none focus:border-ink-3"
          />
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Single block card
// ─────────────────────────────────────────────────────────────────────────────

function BlockCard({
  block,
  index,
  total,
  onChange,
  onRemove,
  onMove,
  onUpload,
  lessonId,
  lessonTitle,
}: {
  block: Block;
  index: number;
  total: number;
  onChange: (b: Block) => void;
  onRemove: () => void;
  onMove: (dir: -1 | 1) => void;
  onUpload: (lessonId: string, file: File) => Promise<string>;
  lessonId: string;
  lessonTitle?: string;
}) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="border border-border rounded-xl bg-surface">
      {/* Block header */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-border">
        <span className="text-base">{BLOCK_ICONS[block.type]}</span>
        <span className="font-syne font-semibold text-xs text-ink flex-1">{BLOCK_LABELS[block.type]}</span>
        <div className="flex items-center gap-0.5">
          <button
            onClick={() => onMove(-1)}
            disabled={index === 0}
            className="text-ink-3 hover:text-ink disabled:opacity-30 px-1.5 py-0.5 text-xs"
            title="Move up"
          >↑</button>
          <button
            onClick={() => onMove(1)}
            disabled={index === total - 1}
            className="text-ink-3 hover:text-ink disabled:opacity-30 px-1.5 py-0.5 text-xs"
            title="Move down"
          >↓</button>
          <button
            onClick={() => setCollapsed((v) => !v)}
            className="text-ink-3 hover:text-ink px-1.5 py-0.5 text-xs"
            title={collapsed ? "Expand" : "Collapse"}
          >{collapsed ? "▼" : "▲"}</button>
          <button
            onClick={onRemove}
            className="text-red hover:text-red/70 px-1.5 py-0.5 text-xs"
            title="Remove block"
          >✕</button>
        </div>
      </div>

      {/* Block content */}
      {!collapsed && (
        <div className="p-3">
          {block.type === "text" && <TextBlockEditor block={block} onChange={onChange} />}
          {block.type === "quiz" && <QuizBlockEditor block={block} onChange={onChange} />}
          {block.type === "case" && <CaseBlockEditor block={block} onChange={onChange} />}
          {block.type === "image" && (
            <ImageBlockEditor
              block={{ ...block, _lessonId: lessonId } as any}
              onChange={onChange}
              onUpload={onUpload}
              lessonId={lessonId}
              lessonTitle={lessonTitle}
            />
          )}
          {block.type === "anatomy_3d" && (
            <Anatomy3DBlockEditor block={block} onChange={onChange} />
          )}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main page
// ─────────────────────────────────────────────────────────────────────────────

function emptyBlock(type: BlockType, order: number): Block {
  if (type === "text") return { type, order, content: { text: "" } };
  if (type === "quiz") return { type, order, content: { question: "", options: { A: "", B: "", C: "", D: "" }, correct: "A", explanation: "" } };
  if (type === "case") return { type, order, content: { presentation: "", questions: [""], teaching_points: [""] } };
  if (type === "anatomy_3d") return { type, order, content: { embed_url: "", caption: "" } };
  return { type, order, content: { url: "", caption: "" } };
}

function lessonToEditorState(raw: Record<string, unknown>) {
  const blocks: Block[] = Array.isArray(raw.blocks)
    ? (raw.blocks as Block[]).map((b, i) => ({ ...b, order: i }))
    : [];
  return {
    title: (raw.title as string) ?? "",
    blocks,
    estimated_minutes: (raw.estimated_minutes as number) ?? 20,
    learning_objectives: Array.isArray(raw.learning_objectives)
      ? (raw.learning_objectives as string[])
      : [],
  };
}

function editorStateToContent(title: string, blocks: Block[], minutes: number, objectives: string[]) {
  return {
    title,
    blocks: blocks.map((b, i) => ({ ...b, order: i })),
    estimated_minutes: minutes,
    learning_objectives: objectives,
  };
}

export default function LessonEditPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [title, setTitle] = useState("");
  const [minutes, setMinutes] = useState(20);
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [objectives, setObjectives] = useState<string[]>([""]);

  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState("");
  const [error, setError] = useState("");
  const [workflowLoading, setWorkflowLoading] = useState(false);

  // Version history panel
  const [versionsOpen, setVersionsOpen] = useState(false);
  const [versions, setVersions] = useState<{ id: string; version_number: number; title: string; saved_at: string; note: string | null }[]>([]);
  const [versionsLoading, setVersionsLoading] = useState(false);
  const [previewVersion, setPreviewVersion] = useState<{ version_number: number; content: Record<string, unknown> } | null>(null);
  const [restoringVersion, setRestoringVersion] = useState<number | null>(null);

  // Share Preview
  const [previewLink, setPreviewLink] = useState<string | null>(null);
  const [previewLinkLoading, setPreviewLinkLoading] = useState(false);
  const [previewLinkModal, setPreviewLinkModal] = useState(false);

  // AI Improve panel
  const [aiOpen, setAiOpen] = useState(false);
  const [aiTask, setAiTask] = useState("improve_clarity");
  const [aiSpecialty, setAiSpecialty] = useState("Cardiology");
  const [aiLevel, setAiLevel] = useState("intermediate");
  const [aiLoading, setAiLoading] = useState(false);
  const [aiSuggestion, setAiSuggestion] = useState<{
    suggested: Record<string, unknown>;
    review_notes?: string;
  } | null>(null);

  useEffect(() => {
    teacherApi.getLesson(id)
      .then((l: Lesson) => {
        setLesson(l);
        const state = lessonToEditorState(l.content);
        setTitle(state.title || l.title);
        setMinutes(state.estimated_minutes || l.estimated_minutes);
        setBlocks(state.blocks.length > 0 ? state.blocks : [emptyBlock("text", 0)]);
        setObjectives(state.learning_objectives.length > 0 ? state.learning_objectives : [""]);
      })
      .catch(() => setError("Failed to load lesson"));
  }, [id]);

  function updateBlock(idx: number, b: Block) {
    setBlocks((bs) => bs.map((old, i) => (i === idx ? b : old)));
  }
  function removeBlock(idx: number) {
    setBlocks((bs) => bs.filter((_, i) => i !== idx).map((b, i) => ({ ...b, order: i })));
  }
  function moveBlock(idx: number, dir: -1 | 1) {
    setBlocks((bs) => {
      const next = [...bs];
      const swapIdx = idx + dir;
      if (swapIdx < 0 || swapIdx >= next.length) return bs;
      [next[idx], next[swapIdx]] = [next[swapIdx], next[idx]];
      return next.map((b, i) => ({ ...b, order: i }));
    });
  }
  function addBlock(type: BlockType) {
    setBlocks((bs) => [...bs, emptyBlock(type, bs.length)]);
  }

  function updateObjective(idx: number, val: string) {
    setObjectives((os) => os.map((o, i) => (i === idx ? val : o)));
  }
  function addObjective() { setObjectives((os) => [...os, ""]); }
  function removeObjective(idx: number) {
    setObjectives((os) => os.filter((_, i) => i !== idx));
  }

  async function handleSave() {
    if (!lesson) return;
    setSaving(true);
    setSaveMsg("");
    setError("");
    try {
      const content = editorStateToContent(title, blocks, minutes, objectives.filter(Boolean));
      const updated = await teacherApi.updateLesson(lesson.id, {
        title: title.trim() || lesson.title,
        content,
        estimated_minutes: minutes,
      });
      setLesson(updated);
      setSaveMsg("Saved");
      setTimeout(() => setSaveMsg(""), 2500);
    } catch {
      setError("Save failed. Check connection and try again.");
    } finally {
      setSaving(false);
    }
  }

  async function handleWorkflow(action: "submit" | "publish" | "unpublish") {
    if (!lesson) return;
    setWorkflowLoading(true);
    setError("");
    try {
      let updated: Lesson;
      if (action === "submit") updated = await teacherApi.submitForReview(lesson.id);
      else if (action === "publish") updated = await teacherApi.publishLesson(lesson.id);
      else updated = await teacherApi.unpublishLesson(lesson.id);
      setLesson(updated);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Action failed");
    } finally {
      setWorkflowLoading(false);
    }
  }

  async function handleSharePreview() {
    setPreviewLinkLoading(true);
    try {
      const data = await teacherApi.createPreviewLink(id);
      setPreviewLink(data.url ?? data.preview_url ?? data.link ?? "");
      setPreviewLinkModal(true);
    } catch {
      setError("Failed to generate preview link");
    } finally {
      setPreviewLinkLoading(false);
    }
  }

  async function loadVersions() {
    setVersionsLoading(true);
    try {
      const data = await teacherApi.listVersions(id);
      setVersions(data);
    } catch {
      // ignore — non-critical
    } finally {
      setVersionsLoading(false);
    }
  }

  async function handleRestoreVersion(versionNumber: number) {
    if (!confirm(`Restore version ${versionNumber}? Current content will be saved as a new version first.`)) return;
    setRestoringVersion(versionNumber);
    try {
      const updated = await teacherApi.restoreVersion(id, versionNumber);
      setLesson(updated);
      const state = lessonToEditorState(updated.content);
      setTitle(state.title || updated.title);
      setMinutes(state.estimated_minutes || updated.estimated_minutes);
      setBlocks(state.blocks.length > 0 ? state.blocks : [emptyBlock("text", 0)]);
      setObjectives(state.learning_objectives.length > 0 ? state.learning_objectives : [""]);
      setPreviewVersion(null);
      setSaveMsg(`Restored to version ${versionNumber}`);
      setTimeout(() => setSaveMsg(""), 3000);
      await loadVersions();
    } catch {
      setError("Failed to restore version");
    } finally {
      setRestoringVersion(null);
    }
  }

  async function handleUpload(lessonId: string, file: File): Promise<string> {
    const form = new FormData();
    form.append("file", file);
    const { api } = await import("@/lib/api");
    const res = await api.post(`/lessons/${lessonId}/upload-media`, form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return res.data.url;
  }

  async function handleAiImprove() {
    if (!lesson) return;
    setAiLoading(true);
    setAiSuggestion(null);
    setError("");
    try {
      // Save first so AI sees current content
      const content = editorStateToContent(title, blocks, minutes, objectives.filter(Boolean));
      await teacherApi.updateLesson(lesson.id, { title: title.trim() || lesson.title, content, estimated_minutes: minutes });

      const result = await teacherApi.aiImprove(lesson.id, {
        task: aiTask,
        specialty: aiSpecialty,
        target_level: aiLevel,
      });
      setAiSuggestion(result);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "AI improve failed");
    } finally {
      setAiLoading(false);
    }
  }

  function applyAiSuggestion() {
    if (!aiSuggestion) return;
    const state = lessonToEditorState(aiSuggestion.suggested);
    if (state.title) setTitle(state.title);
    if (state.blocks.length > 0) setBlocks(state.blocks);
    if (state.learning_objectives.length > 0) setObjectives(state.learning_objectives);
    setAiSuggestion(null);
    setAiOpen(false);
    setSaveMsg("AI suggestion applied — remember to save");
    setTimeout(() => setSaveMsg(""), 4000);
  }

  function applyAiBlock(block: Block) {
    setBlocks((bs) => [...bs, { ...block, order: bs.length }]);
    setSaveMsg("Block added — remember to save");
    setTimeout(() => setSaveMsg(""), 3000);
  }

  if (!lesson && !error) return <div className="p-6 text-ink-3 font-serif text-sm">Loading...</div>;
  if (error && !lesson) return <div className="p-6 text-red font-serif text-sm">{error}</div>;
  if (!lesson) return null;

  const isArchived = lesson.status === "archived";

  return (
    <div className="p-4 max-w-3xl mx-auto pb-20">
      {/* ── Header ─────────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-4 gap-3">
        <div className="min-w-0">
          <Link href={`/teacher/modules/${lesson.module_id}`} className="text-ink-3 text-sm font-syne hover:text-ink">
            ← Module
          </Link>
          <div className="flex items-center gap-2 mt-1">
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={isArchived}
              placeholder="Lesson title"
              className="font-syne font-black text-xl text-ink bg-transparent border-b border-transparent focus:border-ink-3 focus:outline-none disabled:opacity-50 flex-1 min-w-0"
            />
          </div>
          <span className={`font-syne text-xs font-semibold ${STATUS_COLORS[lesson.status]}`}>
            {lesson.status.toUpperCase()}
          </span>
        </div>

        {!isArchived && (
          <div className="flex gap-2 shrink-0 flex-wrap justify-end">
            {lesson.status === "draft" && (
              <>
                <button onClick={() => handleWorkflow("submit")} disabled={workflowLoading}
                  className="text-xs border border-amber/40 text-amber rounded-lg px-3 py-1.5 font-syne font-semibold hover:bg-amber-light disabled:opacity-50">
                  For Review
                </button>
                <button onClick={() => handleWorkflow("publish")} disabled={workflowLoading}
                  className="btn-primary text-xs px-3 py-1.5 rounded-lg font-syne font-semibold disabled:opacity-50">
                  Publish
                </button>
              </>
            )}
            {lesson.status === "review" && (
              <button onClick={() => handleWorkflow("publish")} disabled={workflowLoading}
                className="btn-primary text-xs px-3 py-1.5 rounded-lg font-syne font-semibold disabled:opacity-50">
                Publish
              </button>
            )}
            {lesson.status === "published" && (
              <button onClick={() => handleWorkflow("unpublish")} disabled={workflowLoading}
                className="text-xs border border-border text-ink-3 rounded-lg px-3 py-1.5 font-syne hover:border-ink-3 disabled:opacity-50">
                Unpublish
              </button>
            )}
          </div>
        )}
      </div>

      {/* ── Notifications ──────────────────────────────────────── */}
      {error && (
        <div className="mb-3 p-3 rounded-lg bg-red-light border border-red/20 text-red text-sm font-serif flex justify-between">
          {error}
          <button onClick={() => setError("")} className="underline text-xs shrink-0 ml-2">dismiss</button>
        </div>
      )}
      {saveMsg && (
        <div className="mb-3 p-2 rounded-lg bg-green-light border border-green/20 text-green text-sm font-syne">
          {saveMsg}
        </div>
      )}

      {/* ── Metadata strip ─────────────────────────────────────── */}
      <div className="card p-3 mb-4 flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <label className="font-syne text-xs text-ink-3 shrink-0">Duration</label>
          <input
            type="number"
            value={minutes}
            onChange={(e) => setMinutes(Number(e.target.value))}
            min={5}
            max={180}
            disabled={isArchived}
            className="w-16 border border-border rounded px-2 py-1 font-serif text-xs text-ink bg-surface focus:outline-none disabled:opacity-50"
          />
          <span className="font-serif text-xs text-ink-3">min</span>
        </div>
        <div className="flex-1 min-w-0">
          <label className="font-syne text-xs text-ink-3 block mb-1">Learning objectives</label>
          <div className="space-y-1">
            {objectives.map((obj, i) => (
              <div key={i} className="flex gap-1">
                <input
                  type="text"
                  value={obj}
                  onChange={(e) => updateObjective(i, e.target.value)}
                  disabled={isArchived}
                  placeholder={`Objective ${i + 1}`}
                  className="flex-1 border border-border rounded px-2 py-1 font-serif text-xs text-ink bg-surface focus:outline-none focus:border-ink-3 disabled:opacity-50"
                />
                {objectives.length > 1 && !isArchived && (
                  <button onClick={() => removeObjective(i)} className="text-red text-xs px-1 hover:bg-red-light rounded">✕</button>
                )}
              </div>
            ))}
            {!isArchived && (
              <button onClick={addObjective} className="text-xs text-ink-3 font-syne hover:text-ink">+ Add objective</button>
            )}
          </div>
        </div>
      </div>

      {/* ── Blocks ─────────────────────────────────────────────── */}
      <div className="space-y-3 mb-4">
        {blocks.map((block, i) => (
          <BlockCard
            key={i}
            block={block}
            index={i}
            total={blocks.length}
            onChange={(b) => updateBlock(i, b)}
            onRemove={() => removeBlock(i)}
            onMove={(dir) => moveBlock(i, dir)}
            onUpload={handleUpload}
            lessonId={lesson.id}
            lessonTitle={title}
          />
        ))}
      </div>

      {/* ── Add block ──────────────────────────────────────────── */}
      {!isArchived && (
        <div className="card p-3 mb-4">
          <p className="font-syne text-xs text-ink-3 mb-2">Add block</p>
          <div className="flex gap-2 flex-wrap">
            {(["text", "quiz", "case", "image", "anatomy_3d"] as BlockType[]).map((type) => (
              <button
                key={type}
                onClick={() => addBlock(type)}
                className="flex items-center gap-1.5 border border-border rounded-lg px-3 py-1.5 font-syne text-xs text-ink hover:border-ink-3 hover:bg-surface transition-colors"
              >
                <span>{BLOCK_ICONS[type]}</span>
                {BLOCK_LABELS[type]}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Save + AI bar ──────────────────────────────────────── */}
      {!isArchived && (
        <div className="flex gap-3 mb-4">
          <button
            onClick={handleSave}
            disabled={saving}
            className="btn-primary py-2.5 px-6 rounded-lg font-syne font-semibold text-sm disabled:opacity-50 flex-1"
          >
            {saving ? "Saving..." : "Save Changes"}
          </button>
          <button
            onClick={handleSharePreview}
            disabled={previewLinkLoading}
            className="border border-border rounded-lg px-4 py-2.5 font-syne font-semibold text-sm text-ink hover:border-ink-3 transition-colors disabled:opacity-50"
            title="Generate a shareable preview link"
          >
            {previewLinkLoading ? "..." : "🔗 Share Preview"}
          </button>
          <button
            onClick={() => setAiOpen((v) => !v)}
            className={`border rounded-lg px-4 py-2.5 font-syne font-semibold text-sm transition-colors ${aiOpen ? "border-blue/40 bg-blue-light text-blue" : "border-border text-ink hover:border-ink-3"}`}
          >
            {aiOpen ? "Hide AI" : "AI Improve"}
          </button>
        </div>
      )}

      {/* ── Share Preview Modal ─────────────────────────────────── */}
      {previewLinkModal && previewLink && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-2xl shadow-xl p-6 max-w-md w-full mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-syne font-bold text-base text-ink">Preview Link</h3>
              <button onClick={() => setPreviewLinkModal(false)} className="text-ink-3 hover:text-ink text-lg leading-none">✕</button>
            </div>
            <p className="font-serif text-xs text-ink-3 mb-3">
              Share this link to let anyone preview the lesson without an account. Valid for 24 hours.
            </p>
            <div className="flex items-center gap-2 bg-surface border border-border rounded-lg px-3 py-2 mb-4">
              <span className="font-mono text-xs text-ink flex-1 truncate">{previewLink}</span>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => { navigator.clipboard.writeText(previewLink); }}
                className="btn-primary flex-1 py-2 rounded-lg font-syne font-semibold text-sm"
              >
                Copy Link
              </button>
              <button
                onClick={() => setPreviewLinkModal(false)}
                className="border border-border rounded-lg px-4 py-2 font-syne font-semibold text-sm text-ink hover:border-ink-3 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── AI Improve panel ───────────────────────────────────── */}
      {aiOpen && !isArchived && (
        <div className="card p-4 border-blue/30 mb-4" style={{ backgroundColor: "rgba(219, 234, 254, 0.2)" }}>
          <h3 className="font-syne font-bold text-sm text-ink mb-3">AI Content Improvement</h3>
          <p className="font-serif text-xs text-ink-3 mb-3">
            Lesson will be saved automatically before AI analysis.
          </p>
          <div className="grid grid-cols-3 gap-2 mb-3">
            <div>
              <label className="block font-syne text-xs text-ink-3 mb-1">Task</label>
              <select value={aiTask} onChange={(e) => setAiTask(e.target.value)}
                className="w-full border border-border rounded px-2 py-1.5 font-serif text-xs text-ink bg-surface focus:outline-none">
                {AI_TASKS.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
            <div>
              <label className="block font-syne text-xs text-ink-3 mb-1">Specialty</label>
              <select value={aiSpecialty} onChange={(e) => setAiSpecialty(e.target.value)}
                className="w-full border border-border rounded px-2 py-1.5 font-serif text-xs text-ink bg-surface focus:outline-none">
                {SPECIALTIES.map((s) => <option key={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="block font-syne text-xs text-ink-3 mb-1">Level</label>
              <select value={aiLevel} onChange={(e) => setAiLevel(e.target.value)}
                className="w-full border border-border rounded px-2 py-1.5 font-serif text-xs text-ink bg-surface focus:outline-none">
                {LEVELS.map((l) => <option key={l} value={l}>{l}</option>)}
              </select>
            </div>
          </div>
          <button onClick={handleAiImprove} disabled={aiLoading}
            className="btn-primary text-sm px-4 py-2 rounded-lg font-syne font-semibold disabled:opacity-50 mb-3">
            {aiLoading ? "Claude is analysing..." : "Run AI Improve"}
          </button>

          {aiSuggestion && (
            <AiSuggestionPreview
              suggestion={aiSuggestion}
              currentBlocks={blocks}
              onApplyAll={applyAiSuggestion}
              onApplyBlock={applyAiBlock}
              onDiscard={() => setAiSuggestion(null)}
            />
          )}
        </div>
      )}

      {/* ── Review notes ───────────────────────────────────────── */}
      {lesson.review_notes && (
        <div className="card p-3 border-amber/30 bg-amber-light/40 mb-4">
          <p className="font-syne font-semibold text-xs text-amber mb-1">Review Notes</p>
          <p className="font-serif text-sm text-ink">{lesson.review_notes}</p>
        </div>
      )}

      {/* ── Version history ────────────────────────────────────── */}
      <div className="card overflow-hidden">
        <button
          onClick={() => {
            const next = !versionsOpen;
            setVersionsOpen(next);
            if (next && versions.length === 0) loadVersions();
          }}
          className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-surface/50 transition-colors"
        >
          <span className="font-syne font-bold text-sm text-ink">Version History</span>
          <span className="text-ink-3 text-xs font-syne">{versionsOpen ? "Hide ▲" : "Show ▼"}</span>
        </button>

        {versionsOpen && (
          <div className="border-t border-border">
            {versionsLoading ? (
              <div className="p-4 text-ink-3 font-serif text-sm">Loading versions...</div>
            ) : versions.length === 0 ? (
              <div className="p-4 text-ink-3 font-serif text-sm">No saved versions yet. Versions are created automatically when you save.</div>
            ) : (
              <div className="divide-y divide-border">
                {versions.map((v) => (
                  <div key={v.id} className="px-4 py-3">
                    <div className="flex items-center justify-between gap-2">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-syne font-semibold text-xs text-ink">v{v.version_number}</span>
                          <span className="font-serif text-xs text-ink-3 truncate">{v.title}</span>
                        </div>
                        <div className="flex items-center gap-2 mt-0.5">
                          <span className="font-serif text-xs text-ink-3">
                            {new Date(v.saved_at).toLocaleString()}
                          </span>
                          {v.note && <span className="font-serif text-xs text-ink-3 italic">— {v.note}</span>}
                        </div>
                      </div>
                      <div className="flex gap-2 shrink-0">
                        <button
                          onClick={async () => {
                            if (previewVersion?.version_number === v.version_number) {
                              setPreviewVersion(null);
                            } else {
                              const data = await teacherApi.getVersion(id, v.version_number);
                              setPreviewVersion({ version_number: v.version_number, content: data.content });
                            }
                          }}
                          className="text-xs font-syne text-ink-3 hover:text-ink border border-border rounded px-2 py-0.5 transition-colors"
                        >
                          {previewVersion?.version_number === v.version_number ? "Hide" : "Preview"}
                        </button>
                        <button
                          onClick={() => handleRestoreVersion(v.version_number)}
                          disabled={restoringVersion === v.version_number}
                          className="text-xs font-syne text-blue hover:text-blue/70 border border-blue/30 rounded px-2 py-0.5 transition-colors disabled:opacity-50"
                        >
                          {restoringVersion === v.version_number ? "..." : "Restore"}
                        </button>
                      </div>
                    </div>
                    {previewVersion?.version_number === v.version_number && (
                      <div className="mt-2 rounded-lg bg-surface border border-border p-3">
                        <pre className="font-mono text-xs text-ink overflow-auto max-h-48">
                          {JSON.stringify(previewVersion.content, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// AI Suggestion Preview Component
// ─────────────────────────────────────────────────────────────────────────────

function AiSuggestionPreview({
  suggestion,
  currentBlocks,
  onApplyAll,
  onApplyBlock,
  onDiscard,
}: {
  suggestion: { suggested: Record<string, unknown>; review_notes?: string };
  currentBlocks: Block[];
  onApplyAll: () => void;
  onApplyBlock: (block: Block) => void;
  onDiscard: () => void;
}) {
  const suggested = suggestion.suggested as Partial<LessonContent>;
  const suggestedBlocks: Block[] = (suggested.blocks as Block[]) ?? [];
  const suggestedTitle = suggested.title;
  const suggestedObjectives = suggested.learning_objectives ?? [];

  const existingTexts = new Set(
    currentBlocks.map((b) => JSON.stringify(b.content))
  );
  const newBlocks = suggestedBlocks.filter(
    (b) => !existingTexts.has(JSON.stringify(b.content))
  );

  return (
    <div className="border border-green/40 rounded-lg p-3 bg-green-light/20">
      <div className="flex items-center justify-between mb-2">
        <span className="font-syne font-semibold text-sm text-ink">
          AI Suggestion
          {newBlocks.length > 0 && (
            <span className="ml-2 text-xs font-normal text-green">
              {newBlocks.length} new block{newBlocks.length !== 1 ? "s" : ""}
            </span>
          )}
        </span>
        <div className="flex gap-2">
          <button onClick={onDiscard} className="text-xs text-ink-3 font-syne hover:text-ink">
            Discard
          </button>
          <button onClick={onApplyAll} className="text-xs text-green font-syne font-semibold hover:underline">
            Apply All
          </button>
        </div>
      </div>

      {suggestion.review_notes && (
        <p className="font-serif text-xs text-ink-3 mb-3 italic border-b border-border pb-2">
          {suggestion.review_notes}
        </p>
      )}

      {suggestedTitle && (
        <div className="mb-2 text-xs font-syne text-ink-3">
          Title: <span className="text-ink font-semibold">{suggestedTitle}</span>
        </div>
      )}

      {suggestedObjectives.length > 0 && (
        <div className="mb-3">
          <div className="font-syne text-xs font-semibold text-ink-3 mb-1">Learning objectives</div>
          <ul className="space-y-0.5">
            {suggestedObjectives.map((obj, i) => (
              <li key={i} className="font-serif text-xs text-ink flex items-start gap-1">
                <span className="text-green mt-0.5">•</span> {obj}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="space-y-2 max-h-72 overflow-y-auto">
        {suggestedBlocks.map((block, i) => {
          const isNew = !existingTexts.has(JSON.stringify(block.content));
          return (
            <div
              key={i}
              className={`rounded p-2 border ${isNew ? "border-green/40 bg-green-light/30" : "border-border bg-surface/60"}`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className="text-xs">{BLOCK_ICONS[block.type as BlockType] ?? "📄"}</span>
                    <span className="font-syne text-xs font-semibold text-ink-3 uppercase">{block.type}</span>
                    {isNew && <span className="text-xs text-green font-syne">New</span>}
                  </div>
                  <SuggestionBlockBody block={block} />
                </div>
                {isNew && (
                  <button
                    onClick={() => onApplyBlock(block)}
                    className="text-xs text-green font-syne font-semibold hover:underline shrink-0"
                  >
                    + Add
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function SuggestionBlockBody({ block }: { block: Block }) {
  if (block.type === "text") {
    const c = block.content as TextContent;
    return (
      <div>
        {c.heading && <div className="font-syne font-bold text-xs text-ink mb-0.5">{c.heading}</div>}
        <p className="font-serif text-xs text-ink-3 line-clamp-3">{c.text}</p>
      </div>
    );
  }
  if (block.type === "quiz") {
    const c = block.content as QuizContent;
    return (
      <div>
        <p className="font-serif text-xs text-ink mb-1 line-clamp-2">{c.question}</p>
        <div className="grid grid-cols-2 gap-1">
          {Object.entries(c.options ?? {}).map(([k, v]) => (
            <div key={k} className={`text-xs font-serif px-1.5 py-0.5 rounded ${k === c.correct ? "bg-green-light text-green" : "text-ink-3"}`}>
              {k}: {v as string}
            </div>
          ))}
        </div>
      </div>
    );
  }
  if (block.type === "case") {
    const c = block.content as CaseContent;
    return (
      <div>
        <p className="font-serif text-xs text-ink line-clamp-2">{c.presentation}</p>
        {c.teaching_points?.length > 0 && (
          <p className="font-serif text-xs text-ink-3 mt-0.5">
            {c.teaching_points.length} teaching point{c.teaching_points.length !== 1 ? "s" : ""}
          </p>
        )}
      </div>
    );
  }
  if (block.type === "image") {
    const c = block.content as ImageContent;
    return <p className="font-serif text-xs text-ink-3 truncate">{c.caption ?? c.url}</p>;
  }
  return null;
}
