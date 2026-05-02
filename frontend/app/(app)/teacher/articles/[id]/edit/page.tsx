"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { teacherApi } from "@/lib/api";
import { useT } from "@/lib/i18n";

// ── Types ─────────────────────────────────────────────────────────────────────

type BlockType = "h2" | "h3" | "p" | "ul" | "callout" | "table" | "image";

type Block =
  | { type: "h2"; content: string }
  | { type: "h3"; content: string }
  | { type: "p"; content: string }
  | { type: "ul"; items: string[] }
  | { type: "callout"; variant: "warning" | "info" | "tip"; content: string }
  | { type: "table"; headers: string[]; rows: string[][] }
  | { type: "image"; url: string; caption: string; alt: string };

const CATEGORIES = [
  ["diseases", "Diseases & Conditions"],
  ["drugs", "Drugs & Medications"],
  ["procedures", "Procedures & Techniques"],
  ["symptoms", "Symptoms & Signs"],
  ["diagnostics", "Diagnostics & Lab Tests"],
  ["emergency", "Emergency Medicine"],
  ["nutrition", "Nutrition & Prevention"],
  ["pediatrics", "Pediatrics"],
  ["cardiology", "Cardiology"],
  ["neurology", "Neurology"],
  ["oncology", "Oncology"],
  ["surgery", "Surgery"],
  ["psychiatry", "Psychiatry"],
  ["endocrinology", "Endocrinology"],
  ["infectious-diseases", "Infectious Diseases"],
  ["veterinary", "Veterinary Medicine"],
];

const SCHEMA_TYPES = ["MedicalCondition", "Drug", "MedicalProcedure", "MedicalWebPage"];

// ── Block editor helpers ──────────────────────────────────────────────────────

function defaultBlock(type: BlockType): Block {
  switch (type) {
    case "h2": return { type: "h2", content: "" };
    case "h3": return { type: "h3", content: "" };
    case "p":  return { type: "p", content: "" };
    case "ul": return { type: "ul", items: [""] };
    case "callout": return { type: "callout", variant: "info", content: "" };
    case "table": return { type: "table", headers: ["Column 1", "Column 2"], rows: [["", ""]] };
    case "image": return { type: "image", url: "", caption: "", alt: "" };
  }
}

const BLOCK_LABELS: Record<BlockType, string> = {
  h2: "H2 Heading", h3: "H3 Subheading", p: "Paragraph", ul: "Bullet List",
  callout: "Callout", table: "Table", image: "Image",
};

const BLOCK_ICONS: Record<BlockType, string> = {
  h2: "H2", h3: "H3", p: "¶", ul: "•", callout: "!", table: "⊞", image: "🖼",
};

// ── Block editor component ────────────────────────────────────────────────────

function BlockEditor({
  block,
  index,
  articleId,
  onChange,
  onDelete,
  onMoveUp,
  onMoveDown,
  showToast,
}: {
  block: Block;
  index: number;
  articleId: string | null;
  onChange: (i: number, b: Block) => void;
  onDelete: (i: number) => void;
  onMoveUp: (i: number) => void;
  onMoveDown: (i: number) => void;
  showToast: (msg: string, type?: "ok" | "err") => void;
}) {
  const t = useT();
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const set = (patch: Partial<Block>) => onChange(index, { ...block, ...patch } as Block);

  const uploadImage = async (file: File) => {
    if (!articleId) {
      showToast(t("teacher.articles.editor.save_first"), "err");
      return;
    }
    setUploading(true);
    try {
      const res = await teacherApi.uploadArticleImage(articleId, file);
      onChange(index, { ...block, url: res.url } as Block);
      showToast(t("teacher.articles.editor.uploaded"));
    } catch {
      showToast(t("teacher.articles.editor.upload_err"), "err");
    } finally {
      setUploading(false);
    }
  };

  const controlBar = (
    <div className="flex items-center gap-1 mb-2">
      <span className="text-[10px] font-syne font-semibold text-ink-3 uppercase tracking-wider bg-surface-2 border border-border rounded px-1.5 py-0.5">
        {BLOCK_LABELS[block.type]}
      </span>
      <div className="ml-auto flex gap-1">
        <button onClick={() => onMoveUp(index)} title="Move up" className="text-ink-3 hover:text-ink text-xs px-1">↑</button>
        <button onClick={() => onMoveDown(index)} title="Move down" className="text-ink-3 hover:text-ink text-xs px-1">↓</button>
        <button onClick={() => onDelete(index)} title="Delete block" className="text-red/50 hover:text-red text-xs px-1">✕</button>
      </div>
    </div>
  );

  switch (block.type) {
    case "h2":
    case "h3":
      return (
        <div className="bg-surface border border-border rounded-lg p-3">
          {controlBar}
          <input
            value={block.content}
            onChange={e => set({ content: e.target.value })}
            placeholder={block.type === "h2" ? "Section heading…" : "Subheading…"}
            className={`input w-full ${block.type === "h2" ? "font-bold text-lg" : "font-semibold text-base"}`}
          />
        </div>
      );

    case "p":
      return (
        <div className="bg-surface border border-border rounded-lg p-3">
          {controlBar}
          <textarea
            value={block.content}
            onChange={e => set({ content: e.target.value })}
            placeholder="Write paragraph text…"
            rows={4}
            className="input w-full resize-y font-serif"
          />
        </div>
      );

    case "ul":
      return (
        <div className="bg-surface border border-border rounded-lg p-3">
          {controlBar}
          <div className="space-y-1.5">
            {block.items.map((item, j) => (
              <div key={j} className="flex gap-1.5 items-center">
                <span className="text-ink-3 text-sm">•</span>
                <input
                  value={item}
                  onChange={e => {
                    const items = [...block.items];
                    items[j] = e.target.value;
                    set({ items });
                  }}
                  placeholder={`Item ${j + 1}`}
                  className="input flex-1 text-sm"
                />
                <button
                  onClick={() => set({ items: block.items.filter((_, k) => k !== j) })}
                  className="text-red/50 hover:text-red text-xs"
                >✕</button>
              </div>
            ))}
            <button
              onClick={() => set({ items: [...block.items, ""] })}
              className="text-xs font-syne text-ink-3 hover:text-ink border border-dashed border-border rounded px-2 py-1 mt-1"
            >
              + Add item
            </button>
          </div>
        </div>
      );

    case "callout":
      return (
        <div className="bg-surface border border-border rounded-lg p-3">
          {controlBar}
          <div className="flex gap-2 mb-2">
            {(["info", "warning", "tip"] as const).map(v => (
              <button
                key={v}
                onClick={() => set({ variant: v })}
                className={`text-xs font-syne font-semibold border rounded px-2.5 py-0.5 capitalize transition-colors ${
                  block.variant === v ? "bg-ink text-white border-ink" : "border-border text-ink-3 hover:text-ink"
                }`}
              >
                {v === "warning" ? "⚠️" : v === "tip" ? "💡" : "ℹ️"} {v}
              </button>
            ))}
          </div>
          <textarea
            value={block.content}
            onChange={e => set({ content: e.target.value })}
            placeholder="Callout text…"
            rows={2}
            className="input w-full resize-y font-serif text-sm"
          />
        </div>
      );

    case "table":
      return (
        <div className="bg-surface border border-border rounded-lg p-3">
          {controlBar}
          <div className="overflow-x-auto">
            <table className="w-full text-sm mb-2">
              <thead>
                <tr>
                  {block.headers.map((h, j) => (
                    <th key={j} className="px-1 pb-1">
                      <input
                        value={h}
                        onChange={e => {
                          const headers = [...block.headers];
                          headers[j] = e.target.value;
                          set({ headers });
                        }}
                        className="input w-full text-xs font-semibold"
                        placeholder={`Header ${j + 1}`}
                      />
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {block.rows.map((row, j) => (
                  <tr key={j}>
                    {row.map((cell, k) => (
                      <td key={k} className="px-1 py-0.5">
                        <input
                          value={cell}
                          onChange={e => {
                            const rows = block.rows.map(r => [...r]);
                            rows[j][k] = e.target.value;
                            set({ rows });
                          }}
                          className="input w-full text-xs"
                        />
                      </td>
                    ))}
                    <td className="px-1">
                      <button
                        onClick={() => set({ rows: block.rows.filter((_, r) => r !== j) })}
                        className="text-red/50 hover:text-red text-xs"
                      >✕</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex gap-2 flex-wrap">
            <button
              onClick={() => set({ rows: [...block.rows, block.headers.map(() => "")] })}
              className="text-xs font-syne text-ink-3 hover:text-ink border border-dashed border-border rounded px-2 py-1"
            >
              + Row
            </button>
            <button
              onClick={() => set({
                headers: [...block.headers, `Column ${block.headers.length + 1}`],
                rows: block.rows.map(r => [...r, ""]),
              })}
              className="text-xs font-syne text-ink-3 hover:text-ink border border-dashed border-border rounded px-2 py-1"
            >
              + Column
            </button>
          </div>
        </div>
      );

    case "image":
      return (
        <div className="bg-surface border border-border rounded-lg p-3">
          {controlBar}
          <div className="space-y-2">
            {/* Upload or URL */}
            <div className="flex gap-2 items-center">
              <input
                value={block.url}
                onChange={e => set({ url: e.target.value })}
                placeholder="Image URL…"
                className="input flex-1 text-sm font-mono"
              />
              <input ref={fileRef} type="file" accept="image/*" className="hidden"
                onChange={e => {
                  const file = e.target.files?.[0];
                  if (file) uploadImage(file);
                  e.target.value = "";
                }}
              />
              <button
                onClick={() => fileRef.current?.click()}
                disabled={uploading}
                className="text-xs font-syne font-semibold border border-border rounded px-3 py-1.5 hover:border-ink hover:text-ink transition-colors"
              >
                {uploading ? t("teacher.articles.editor.uploading") : t("teacher.articles.editor.upload")}
              </button>
            </div>

            {/* Preview */}
            {block.url && (
              <div className="rounded-lg border border-border overflow-hidden bg-surface-2 max-h-48 flex items-center justify-center">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={block.url}
                  alt={block.alt || "preview"}
                  className="max-h-48 object-contain"
                />
              </div>
            )}

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[10px] font-syne text-ink-3 uppercase tracking-wider">Caption</label>
                <input
                  value={block.caption}
                  onChange={e => set({ caption: e.target.value })}
                  placeholder="Optional caption…"
                  className="input w-full text-sm mt-0.5"
                />
              </div>
              <div>
                <label className="text-[10px] font-syne text-ink-3 uppercase tracking-wider">Alt text</label>
                <input
                  value={block.alt}
                  onChange={e => set({ alt: e.target.value })}
                  placeholder="For accessibility…"
                  className="input w-full text-sm mt-0.5"
                />
              </div>
            </div>
          </div>
        </div>
      );
  }
}

// ── Add block bar ─────────────────────────────────────────────────────────────

function AddBlockBar({ onAdd }: { onAdd: (type: BlockType) => void }) {
  const t = useT();
  return (
    <div className="flex items-center gap-1.5 flex-wrap py-2">
      <span className="text-[10px] font-syne text-ink-3 uppercase tracking-wider mr-1">{t("teacher.articles.editor.add_block")}</span>
      {(Object.keys(BLOCK_ICONS) as BlockType[]).map(t => (
        <button
          key={t}
          onClick={() => onAdd(t)}
          title={BLOCK_LABELS[t]}
          className="text-xs font-syne font-semibold border border-border rounded px-2 py-0.5 text-ink-2 hover:border-ink hover:text-ink transition-colors"
        >
          {BLOCK_ICONS[t]} {BLOCK_LABELS[t]}
        </button>
      ))}
    </div>
  );
}

// ── Main editor ───────────────────────────────────────────────────────────────

export default function ArticleEditorPage() {
  const t = useT();
  const params = useParams();
  const router = useRouter();

  const articleId = params?.id as string | undefined;
  const isNew = articleId === "new";

  const [title, setTitle] = useState("");
  const [excerpt, setExcerpt] = useState("");
  const [category, setCategory] = useState("diseases");
  const [schemaType, setSchemaType] = useState("MedicalCondition");
  const [keywords, setKeywords] = useState("");
  const [readingTime, setReadingTime] = useState(5);
  const [displayName, setDisplayName] = useState("");
  const [bio, setBio] = useState("");
  const [body, setBody] = useState<Block[]>([]);

  const [saving, setSaving] = useState(false);
  const [savedId, setSavedId] = useState<string | null>(isNew ? null : (articleId ?? null));
  const [toast, setToast] = useState<{ msg: string; type: "ok" | "err" } | null>(null);

  const showToast = (msg: string, type: "ok" | "err" = "ok") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 3000);
  };

  // Load existing article
  useEffect(() => {
    if (!isNew && articleId) {
      teacherApi.getMyArticle(articleId).then(a => {
        setTitle(a.title ?? "");
        setExcerpt(a.excerpt ?? "");
        setCategory(a.category ?? "diseases");
        setSchemaType(a.schema_type ?? "MedicalCondition");
        setKeywords((a.keywords ?? []).join(", "));
        setReadingTime(a.reading_time_minutes ?? 5);
        setDisplayName(a.author_display_name ?? "");
        setBio(a.author_bio ?? "");
        setBody(a.body ?? []);
        setSavedId(a.id);
      }).catch(() => showToast(t("teacher.articles.editor.load_err"), "err"));
    }
  }, [isNew, articleId]);

  const slugify = (str: string) =>
    str.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 80);

  const buildPayload = (withSlug?: string) => ({
    title,
    excerpt,
    category,
    schema_type: schemaType,
    keywords: keywords.split(",").map(k => k.trim()).filter(Boolean),
    reading_time_minutes: readingTime,
    author_display_name: displayName || undefined,
    author_bio: bio || undefined,
    body,
    ...(withSlug ? { slug: withSlug } : {}),
  });

  const save = useCallback(async () => {
    if (!title.trim()) { showToast(t("teacher.articles.editor.title_required"), "err"); return; }
    setSaving(true);
    try {
      if (!savedId) {
        const slug = slugify(title) || `article-${Date.now()}`;
        const res = await teacherApi.createArticle({ ...buildPayload(), slug, body });
        setSavedId(res.id);
        showToast(t("teacher.articles.editor.created"));
        router.replace(`/teacher/articles/${res.id}/edit`);
      } else {
        await teacherApi.updateArticle(savedId, buildPayload());
        showToast(t("teacher.articles.editor.saved"));
      }
    } catch (err: any) {
      showToast(err.response?.data?.detail ?? t("teacher.articles.editor.save_err"), "err");
    } finally {
      setSaving(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [title, excerpt, category, schemaType, keywords, readingTime, displayName, bio, body, savedId]);

  const addBlock = (type: BlockType) => {
    setBody(prev => [...prev, defaultBlock(type)]);
  };

  const changeBlock = (i: number, b: Block) => {
    setBody(prev => prev.map((x, j) => j === i ? b : x));
  };

  const deleteBlock = (i: number) => {
    setBody(prev => prev.filter((_, j) => j !== i));
  };

  const moveUp = (i: number) => {
    if (i === 0) return;
    setBody(prev => {
      const arr = [...prev];
      [arr[i - 1], arr[i]] = [arr[i], arr[i - 1]];
      return arr;
    });
  };

  const moveDown = (i: number) => {
    setBody(prev => {
      if (i >= prev.length - 1) return prev;
      const arr = [...prev];
      [arr[i], arr[i + 1]] = [arr[i + 1], arr[i]];
      return arr;
    });
  };

  return (
    <div className="flex-1 overflow-y-auto">
      {/* Toast */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-2 rounded shadow font-syne font-semibold text-sm text-white animate-fade-up ${
          toast.type === "ok" ? "bg-green" : "bg-red"
        }`}>
          {toast.msg}
        </div>
      )}

      {/* Sticky toolbar */}
      <div className="sticky top-0 z-40 bg-surface border-b border-border px-6 py-3 flex items-center gap-3">
        <button
          onClick={() => router.push("/teacher/articles")}
          className="text-ink-3 hover:text-ink text-sm font-serif"
        >
          {t("teacher.articles.editor.back")}
        </button>
        <span className="text-border">|</span>
        <span className="font-syne font-semibold text-sm text-ink flex-1 truncate">
          {title || (isNew ? t("teacher.articles.editor.new_title") : t("teacher.articles.editor.edit_title"))}
        </span>
        <button
          onClick={save}
          disabled={saving}
          className="bg-ink text-white font-syne font-semibold text-sm px-4 py-1.5 rounded-lg hover:bg-ink-2 transition-colors disabled:opacity-50"
        >
          {saving ? t("teacher.articles.editor.saving") : t("teacher.articles.editor.save")}
        </button>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-8 space-y-8">
        {/* Article metadata */}
        <section className="card p-6 space-y-4">
          <h2 className="font-syne font-bold text-sm text-ink-2 uppercase tracking-wider">{t("teacher.articles.editor.article_info")}</h2>

          <div>
            <label className="text-xs font-syne text-ink-3 uppercase tracking-wider block mb-1">Title *</label>
            <input
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder="e.g. Understanding Atrial Fibrillation: Causes, Diagnosis and Treatment"
              className="input w-full text-base font-syne font-semibold"
            />
          </div>

          <div>
            <label className="text-xs font-syne text-ink-3 uppercase tracking-wider block mb-1">Excerpt / Description *</label>
            <textarea
              value={excerpt}
              onChange={e => setExcerpt(e.target.value)}
              placeholder="A 1–2 sentence summary shown in article cards and search results…"
              rows={3}
              className="input w-full resize-y font-serif"
            />
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div>
              <label className="text-xs font-syne text-ink-3 uppercase tracking-wider block mb-1">Category</label>
              <select value={category} onChange={e => setCategory(e.target.value)} className="input w-full">
                {CATEGORIES.map(([val, label]) => <option key={val} value={val}>{label}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-syne text-ink-3 uppercase tracking-wider block mb-1">Schema type</label>
              <select value={schemaType} onChange={e => setSchemaType(e.target.value)} className="input w-full">
                {SCHEMA_TYPES.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="text-xs font-syne text-ink-3 uppercase tracking-wider block mb-1">Read time (min)</label>
              <input
                type="number"
                min={1}
                max={60}
                value={readingTime}
                onChange={e => setReadingTime(Number(e.target.value))}
                className="input w-full"
              />
            </div>
            <div>
              <label className="text-xs font-syne text-ink-3 uppercase tracking-wider block mb-1">Keywords (comma-sep)</label>
              <input
                value={keywords}
                onChange={e => setKeywords(e.target.value)}
                placeholder="arrhythmia, heart, ECG…"
                className="input w-full text-sm"
              />
            </div>
          </div>
        </section>

        {/* Author info */}
        <section className="card p-6 space-y-4">
          <h2 className="font-syne font-bold text-sm text-ink-2 uppercase tracking-wider">{t("teacher.articles.editor.author_title")}</h2>
          <p className="text-xs font-serif text-ink-3">
            Leave blank to use your account name. Fill in to show credentials or a pen name.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-syne text-ink-3 uppercase tracking-wider block mb-1">Display name override</label>
              <input
                value={displayName}
                onChange={e => setDisplayName(e.target.value)}
                placeholder="e.g. Dr. Jane Smith, MD, FACC"
                className="input w-full"
              />
            </div>
            <div>
              <label className="text-xs font-syne text-ink-3 uppercase tracking-wider block mb-1">Short bio / credentials</label>
              <input
                value={bio}
                onChange={e => setBio(e.target.value)}
                placeholder="e.g. Cardiologist at St. Mary's Hospital, 15 years experience"
                className="input w-full"
              />
            </div>
          </div>
        </section>

        {/* Article body */}
        <section className="space-y-3">
          <h2 className="font-syne font-bold text-sm text-ink-2 uppercase tracking-wider">{t("teacher.articles.editor.body_title")}</h2>

          {body.length === 0 && (
            <div className="text-center py-8 text-ink-3 font-serif text-sm border-2 border-dashed border-border rounded-xl">
              {t("teacher.articles.editor.body_empty")}
            </div>
          )}

          <div className="space-y-3">
            {body.map((block, i) => (
              <BlockEditor
                key={i}
                block={block}
                index={i}
                articleId={savedId}
                onChange={changeBlock}
                onDelete={deleteBlock}
                onMoveUp={moveUp}
                onMoveDown={moveDown}
                showToast={showToast}
              />
            ))}
          </div>

          <AddBlockBar onAdd={addBlock} />
        </section>

        {/* Save button at bottom */}
        <div className="flex justify-end pb-8">
          <button
            onClick={save}
            disabled={saving}
            className="bg-ink text-white font-syne font-semibold px-6 py-2.5 rounded-lg hover:bg-ink-2 transition-colors disabled:opacity-50"
          >
            {saving ? t("teacher.articles.editor.saving") : t("teacher.articles.editor.save_article")}
          </button>
        </div>
      </div>
    </div>
  );
}
