"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useT } from "@/lib/i18n";
import { notesApi } from "@/lib/api";
import { Pencil, Trash2, Check, X, Search } from "lucide-react";

type Note = {
  id: string;
  content: string;
  lesson_id: string | null;
  module_id: string | null;
  created_at: string;
  updated_at: string;
};

function formatDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

function NoteCard({
  note,
  onDelete,
  onUpdate,
}: {
  note: Note;
  onDelete: (id: string) => void;
  onUpdate: (id: string, content: string) => void;
}) {
  const t = useT();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(note.content);
  const [saving, setSaving] = useState(false);

  async function handleSave() {
    if (!draft.trim() || draft.trim() === note.content) {
      setEditing(false);
      setDraft(note.content);
      return;
    }
    setSaving(true);
    try {
      await notesApi.update(note.id, draft.trim());
      onUpdate(note.id, draft.trim());
      setEditing(false);
    } catch {
      // keep form open on error
    } finally {
      setSaving(false);
    }
  }

  function handleCancel() {
    setDraft(note.content);
    setEditing(false);
  }

  return (
    <div className="bg-surface border border-border rounded-xl p-4 space-y-2">
      {/* Top row */}
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs text-ink-3">{formatDate(note.updated_at)}</p>
        <div className="flex items-center gap-1 flex-shrink-0">
          {!editing && (
            <button
              onClick={() => setEditing(true)}
              aria-label={t("my_notes.edit")}
              className="p-1.5 text-ink-3 hover:text-primary transition-colors"
            >
              <Pencil size={14} strokeWidth={1.75} />
            </button>
          )}
          <button
            onClick={() => onDelete(note.id)}
            aria-label={t("my_notes.delete")}
            className="p-1.5 text-ink-3 hover:text-red-500 transition-colors"
          >
            <Trash2 size={14} strokeWidth={1.75} />
          </button>
        </div>
      </div>

      {/* Content or edit form */}
      {editing ? (
        <div className="space-y-2">
          <textarea
            value={draft}
            onChange={e => setDraft(e.target.value)}
            rows={4}
            autoFocus
            disabled={saving}
            className="w-full text-sm text-ink bg-transparent border border-border rounded-lg p-2 resize-none focus:outline-none focus:border-primary disabled:opacity-50"
          />
          <div className="flex gap-2">
            <button
              onClick={handleSave}
              disabled={saving || !draft.trim()}
              className="flex items-center gap-1 px-3 py-1.5 bg-primary text-white text-xs font-semibold rounded-lg disabled:opacity-50"
            >
              <Check size={13} /> {saving ? "…" : t("my_notes.save")}
            </button>
            <button
              onClick={handleCancel}
              disabled={saving}
              className="flex items-center gap-1 px-3 py-1.5 border border-border text-ink-2 text-xs rounded-lg hover:border-border-2"
            >
              <X size={13} /> {t("my_notes.cancel")}
            </button>
          </div>
        </div>
      ) : (
        <p className="text-sm text-ink whitespace-pre-wrap">{note.content}</p>
      )}

      {/* Context link */}
      {note.module_id && (
        <Link
          href={`/modules/${note.module_id}`}
          className="text-xs text-primary hover:underline"
        >
          {t("my_notes.go_to_module")} →
        </Link>
      )}
    </div>
  );
}

export default function MyNotesPage() {
  const t = useT();
  const [notes, setNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await notesApi.list();
      setNotes(data);
    } catch {
      setNotes([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleDelete(id: string) {
    await notesApi.remove(id).catch(() => {});
    setNotes(prev => prev.filter(n => n.id !== id));
  }

  function handleUpdate(id: string, content: string) {
    setNotes(prev => prev.map(n => n.id === id ? { ...n, content, updated_at: new Date().toISOString() } : n));
  }

  const filtered = query.trim()
    ? notes.filter(n => n.content.toLowerCase().includes(query.toLowerCase()))
    : notes;

  return (
    <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div>
        <h1 className="font-syne font-bold text-xl text-ink">{t("my_notes.title")}</h1>
        <p className="text-sm text-ink-2">{t("my_notes.subtitle")}</p>
      </div>

      {/* Search */}
      {notes.length > 3 && (
        <div className="relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-3" strokeWidth={1.75} />
          <input
            type="search"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder={t("my_notes.search_placeholder")}
            className="w-full pl-9 pr-3 py-2 text-sm bg-surface border border-border rounded-xl text-ink placeholder:text-ink-3 focus:outline-none focus:border-primary"
          />
        </div>
      )}

      {/* List */}
      {loading ? (
        <div className="text-center py-16 text-ink-2">{t("my_notes.loading")}</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 space-y-2">
          <p className="text-ink-2">{query ? t("my_notes.no_results") : t("my_notes.empty")}</p>
          {!query && (
            <p className="text-xs text-ink-3">{t("my_notes.empty_hint")}</p>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map(note => (
            <NoteCard
              key={note.id}
              note={note}
              onDelete={handleDelete}
              onUpdate={handleUpdate}
            />
          ))}
        </div>
      )}
    </div>
  );
}
