"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuthStore } from "@/lib/store";

const CATEGORIES = [
  "cardiology", "oncology", "neurology", "infectious-disease", "endocrinology",
  "pulmonology", "nephrology", "gastroenterology", "psychiatry", "pediatrics",
  "surgery", "obstetrics", "public-health", "general-medicine",
];
const CAT_LABELS: Record<string, string> = {
  "cardiology": "Cardiology", "oncology": "Oncology", "neurology": "Neurology",
  "infectious-disease": "Infectious Disease", "endocrinology": "Endocrinology",
  "pulmonology": "Pulmonology", "nephrology": "Nephrology",
  "gastroenterology": "Gastroenterology", "psychiatry": "Psychiatry",
  "pediatrics": "Pediatrics", "surgery": "Surgery", "obstetrics": "Obstetrics",
  "public-health": "Public Health", "general-medicine": "General Medicine",
};

const API = process.env.NEXT_PUBLIC_API_URL ?? "/api/v1";

export default function TeacherNewsNewPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const editId = searchParams?.get("edit");
  const token = useAuthStore(s => s.token);

  const [form, setForm] = useState({
    source_url: "", source_name: "", source_doi: "",
    title: "", summary: "", category: "general-medicine",
    original_published_at: "",
  });
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving]         = useState(false);
  const [error, setError]           = useState("");
  const [genError, setGenError]     = useState("");
  const [charCount, setCharCount]   = useState(0);

  const isEdit = !!editId;

  // Load existing if editing
  useEffect(() => {
    if (!editId) return;
    fetch(`${API}/news/my`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
      .then((list: any[]) => {
        const item = list.find((n: any) => n.id === editId);
        if (item) {
          setForm({
            source_url: item.source_url ?? "",
            source_name: item.source_name ?? "",
            source_doi: item.source_doi ?? "",
            title: item.title ?? "",
            summary: item.summary ?? item.summary_excerpt ?? "",
            category: item.category ?? "general-medicine",
            original_published_at: item.original_published_at?.split("T")[0] ?? "",
          });
        }
      }).catch(() => {});
  }, [editId, token]);

  async function generateSummary() {
    if (!form.source_url.trim()) { setGenError("Enter source URL first."); return; }
    setGenError(""); setGenerating(true);
    try {
      const res = await fetch(`${API}/news/generate-summary`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          source_url: form.source_url,
          title: form.title || undefined,
          abstract: undefined,
        }),
      });
      if (!res.ok) {
        const d = await res.json();
        setGenError(d.detail ?? "Generation failed. Try providing title/abstract manually.");
        return;
      }
      const data = await res.json();
      setForm(f => ({
        ...f,
        title: f.title || data.title,
        summary: data.summary,
        category: data.category,
      }));
      setCharCount(data.summary.length);
    } catch { setGenError("Network error. Please try again."); }
    finally { setGenerating(false); }
  }

  async function save() {
    setError("");
    if (!form.source_url.trim() || !form.title.trim() || !form.summary.trim()) {
      setError("Source URL, title, and summary are required."); return;
    }
    setSaving(true);
    try {
      const payload = {
        source_url: form.source_url.trim(),
        source_name: form.source_name.trim() || "Other",
        source_doi: form.source_doi.trim() || undefined,
        title: form.title.trim(),
        summary: form.summary.trim(),
        category: form.category,
        original_published_at: form.original_published_at || undefined,
      };
      let res: Response;
      if (isEdit) {
        res = await fetch(`${API}/news/my/${editId}`, {
          method: "PATCH",
          headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
      } else {
        res = await fetch(`${API}/news/my`, {
          method: "POST",
          headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
      }
      if (res.ok || res.status === 201) {
        router.push("/teacher/news");
      } else {
        const d = await res.json();
        setError(d.detail ?? "Save failed.");
      }
    } catch { setError("Network error."); }
    finally { setSaving(false); }
  }

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
      <div className="mb-8">
        <h1 className="font-syne font-extrabold text-2xl text-ink mb-1">
          {isEdit ? "Edit news item" : "Add news item"}
        </h1>
        <p className="text-sm text-ink-2">
          Paste a source URL and let AI generate the summary, or write it yourself. All submissions go through editorial review.
        </p>
      </div>

      <div className="space-y-5">
        {/* Source URL */}
        <div>
          <label className="block font-syne font-semibold text-sm text-ink mb-1.5">
            Source URL <span className="text-red">*</span>
          </label>
          <div className="flex gap-2">
            <input type="url" value={form.source_url}
              onChange={e => setForm(f => ({ ...f, source_url: e.target.value }))}
              placeholder="https://pubmed.ncbi.nlm.nih.gov/... or https://who.int/..."
              className="flex-1 border border-border rounded-lg px-4 py-2.5 bg-bg text-ink text-sm focus:outline-none focus:ring-2 focus:ring-red/30"
            />
            <button onClick={generateSummary} disabled={generating}
              className="flex-shrink-0 font-syne font-bold text-sm px-4 py-2.5 bg-ink text-[#f0ede8] rounded-lg hover:bg-red transition-colors disabled:opacity-60 whitespace-nowrap">
              {generating ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                  </svg>
                  Generating…
                </span>
              ) : "✨ AI Generate"}
            </button>
          </div>
          {genError && <p className="text-xs text-red mt-1.5 font-syne">{genError}</p>}
          <p className="text-xs text-ink-3 mt-1.5">Paste any public URL — PubMed, WHO, medRxiv, journal, news site.</p>
        </div>

        {/* Source name */}
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className="block font-syne font-semibold text-sm text-ink mb-1.5">Source name</label>
            <input type="text" value={form.source_name}
              onChange={e => setForm(f => ({ ...f, source_name: e.target.value }))}
              placeholder="e.g. NEJM, WHO, The Lancet"
              className="w-full border border-border rounded-lg px-4 py-2.5 bg-bg text-ink text-sm focus:outline-none focus:ring-2 focus:ring-red/30"
            />
          </div>
          <div>
            <label className="block font-syne font-semibold text-sm text-ink mb-1.5">DOI (optional)</label>
            <input type="text" value={form.source_doi}
              onChange={e => setForm(f => ({ ...f, source_doi: e.target.value }))}
              placeholder="10.1056/NEJMoa2401..."
              className="w-full border border-border rounded-lg px-4 py-2.5 bg-bg text-ink text-sm font-mono focus:outline-none focus:ring-2 focus:ring-red/30"
            />
          </div>
        </div>

        {/* Title */}
        <div>
          <label className="block font-syne font-semibold text-sm text-ink mb-1.5">
            Title <span className="text-red">*</span>
          </label>
          <input type="text" value={form.title}
            onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
            placeholder="Clear, informative headline"
            className="w-full border border-border rounded-lg px-4 py-2.5 bg-bg text-ink text-sm focus:outline-none focus:ring-2 focus:ring-red/30"
          />
        </div>

        {/* Category + Date row */}
        <div className="grid sm:grid-cols-2 gap-4">
          <div>
            <label className="block font-syne font-semibold text-sm text-ink mb-1.5">Category</label>
            <select value={form.category}
              onChange={e => setForm(f => ({ ...f, category: e.target.value }))}
              className="w-full border border-border rounded-lg px-4 py-2.5 bg-bg text-ink text-sm focus:outline-none focus:ring-2 focus:ring-red/30">
              {CATEGORIES.map(c => <option key={c} value={c}>{CAT_LABELS[c]}</option>)}
            </select>
          </div>
          <div>
            <label className="block font-syne font-semibold text-sm text-ink mb-1.5">Original publication date</label>
            <input type="date" value={form.original_published_at}
              onChange={e => setForm(f => ({ ...f, original_published_at: e.target.value }))}
              className="w-full border border-border rounded-lg px-4 py-2.5 bg-bg text-ink text-sm focus:outline-none focus:ring-2 focus:ring-red/30"
            />
          </div>
        </div>

        {/* Summary */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="font-syne font-semibold text-sm text-ink">
              Summary <span className="text-red">*</span>
            </label>
            <span className="text-xs text-ink-3">{(form.summary || "").length} chars</span>
          </div>
          <textarea value={form.summary}
            onChange={e => { setForm(f => ({ ...f, summary: e.target.value })); setCharCount(e.target.value.length); }}
            rows={10}
            placeholder="Write a 300–500 word summary of the research: key finding, study context, results, clinical significance…"
            className="w-full border border-border rounded-lg px-4 py-3 bg-bg text-ink text-sm focus:outline-none focus:ring-2 focus:ring-red/30 resize-none leading-relaxed"
          />
          <p className="text-xs text-ink-3 mt-1.5">
            Keep to 300–500 words. Do not copy-paste verbatim from the source — write a transformative summary.
          </p>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700 font-syne">
            {error}
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-3 pt-2">
          <button onClick={save} disabled={saving}
            className="font-syne font-bold text-sm px-6 py-2.5 bg-ink text-[#f0ede8] rounded-xl hover:bg-red transition-colors disabled:opacity-60">
            {saving ? "Saving…" : isEdit ? "Save changes" : "Save as draft"}
          </button>
          <button onClick={() => router.push("/teacher/news")}
            className="font-syne font-semibold text-sm px-4 py-2.5 border border-border rounded-xl text-ink-2 hover:border-ink hover:text-ink transition-colors">
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
