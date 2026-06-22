"use client";

import { useState, useRef, useCallback } from "react";
import {
  Upload, FileText, Image, Loader2, X, AlertTriangle, Microscope, Download
} from "lucide-react";
import { API_URL } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface AnalysisResult {
  analysis: string;
  filename: string;
  file_type: string;
  model: string;
  disclaimer: string;
}

const ACCEPT = "image/jpeg,image/png,image/webp,image/gif,application/pdf,text/plain";
const MAX_MB = 10;

const EXAMPLE_QUESTIONS = [
  "Explain the key findings and what they suggest clinically",
  "What values are abnormal and what do they indicate?",
  "What would a clinician consider next based on these findings?",
  "Explain this as if teaching a medical student",
];

export function DocumentAnalyzer() {
  const { user } = useAuthStore();
  const [file,     setFile]     = useState<File | null>(null);
  const [preview,  setPreview]  = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [result,   setResult]   = useState<AnalysisResult | null>(null);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState("");
  const [drag,     setDrag]     = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const isFree = user?.subscription_tier === "free";
  const isPro  = ["pro", "clinic", "lifetime"].includes(user?.subscription_tier ?? "");

  const handleFile = useCallback((f: File) => {
    if (f.size > MAX_MB * 1024 * 1024) {
      setError(`File too large. Maximum ${MAX_MB} MB.`);
      return;
    }
    setFile(f);
    setResult(null);
    setError("");
    if (f.type.startsWith("image/")) {
      const reader = new FileReader();
      reader.onload = e => setPreview(e.target?.result as string);
      reader.readAsDataURL(f);
    } else {
      setPreview(null);
    }
  }, []);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDrag(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }, [handleFile]);

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) handleFile(f);
  };

  async function handleAnalyze() {
    if (!file || loading) return;
    setLoading(true);
    setError("");
    setResult(null);

    const form = new FormData();
    form.append("file", file);
    form.append("question", question.trim() || EXAMPLE_QUESTIONS[0]);

    try {
      const token = localStorage.getItem("access_token") ?? "";
      const res = await fetch(`${API_URL}/ai/analyze-document`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      });

      if (res.status === 429) { setError("Daily AI limit reached. Upgrade for more access."); return; }
      if (res.status === 415) { setError("Unsupported file type. Use JPEG, PNG, WebP, PDF, or plain text."); return; }
      if (res.status === 413) { setError(`File too large. Maximum ${MAX_MB} MB.`); return; }
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? "Analysis failed");
      }
      setResult(await res.json());
    } catch (e: any) {
      setError(e.message ?? "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  function handleClear() {
    setFile(null);
    setPreview(null);
    setResult(null);
    setError("");
    setQuestion("");
    if (inputRef.current) inputRef.current.value = "";
  }

  function handleCopyAnalysis() {
    if (result?.analysis) {
      navigator.clipboard.writeText(result.analysis);
    }
  }

  return (
    <div className="flex flex-col gap-5 h-full overflow-y-auto px-4 py-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="font-syne font-bold text-base text-ink flex items-center gap-2">
            <Microscope size={16} className="text-red" />
            Document Analysis
          </h2>
          <p className="font-serif text-xs text-ink-3 mt-0.5">
            Upload lab results, ECGs, imaging reports, or clinical notes — AI explains the findings for educational purposes
          </p>
        </div>
        {isPro && (
          <span className="text-[10px] font-syne font-bold text-gold bg-gold/10 border border-gold/30 px-2 py-0.5 rounded-full flex-shrink-0">
            Claude Sonnet
          </span>
        )}
      </div>

      {/* Drop zone */}
      {!file && (
        <div
          onDrop={onDrop}
          onDragOver={e => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onClick={() => inputRef.current?.click()}
          className={`border-2 border-dashed rounded-2xl p-8 flex flex-col items-center gap-3 cursor-pointer transition-colors ${
            drag
              ? "border-red bg-red/5"
              : "border-border hover:border-ink-3 hover:bg-bg"
          }`}
        >
          <div className="w-12 h-12 rounded-2xl bg-surface border border-border flex items-center justify-center">
            <Upload size={20} className="text-ink-3" />
          </div>
          <div className="text-center">
            <p className="font-syne font-semibold text-sm text-ink">Drop file here or click to upload</p>
            <p className="font-serif text-xs text-ink-3 mt-1">
              Supported: JPEG · PNG · WebP · PDF · TXT · up to {MAX_MB} MB
            </p>
          </div>
          <div className="flex flex-wrap gap-2 justify-center mt-1">
            {["Lab results", "ECG strip", "Radiology report", "Clinical note", "Blood panel"].map(tag => (
              <span key={tag} className="text-[11px] font-syne text-ink-3 bg-surface border border-border rounded-full px-2.5 py-0.5">
                {tag}
              </span>
            ))}
          </div>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT}
            onChange={onInputChange}
            className="hidden"
          />
        </div>
      )}

      {/* File preview */}
      {file && (
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-3 bg-surface border border-border rounded-xl px-4 py-3">
            {preview ? (
              <img src={preview} alt="preview" className="w-14 h-14 object-cover rounded-lg border border-border flex-shrink-0" />
            ) : (
              <div className="w-14 h-14 rounded-lg border border-border bg-bg flex items-center justify-center flex-shrink-0">
                <FileText size={24} className="text-ink-3" />
              </div>
            )}
            <div className="flex-1 min-w-0">
              <p className="font-syne font-semibold text-sm text-ink truncate">{file.name}</p>
              <p className="font-serif text-xs text-ink-3 mt-0.5">
                {file.type || "unknown"} · {(file.size / 1024).toFixed(0)} KB
              </p>
            </div>
            <button
              onClick={handleClear}
              className="text-ink-3 hover:text-red transition-colors flex-shrink-0"
              title="Remove file"
            >
              <X size={16} />
            </button>
          </div>

          {/* Question field */}
          <div className="flex flex-col gap-1.5">
            <label className="font-syne text-xs font-semibold text-ink-3">
              What do you want to know? (optional)
            </label>
            <input
              value={question}
              onChange={e => setQuestion(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleAnalyze()}
              placeholder={EXAMPLE_QUESTIONS[0]}
              className="px-3 py-2.5 rounded-xl border border-border bg-bg text-ink font-serif text-sm focus:outline-none focus:border-ink-3 transition-colors"
            />
            {/* Quick question chips */}
            <div className="flex flex-wrap gap-1.5 mt-1">
              {EXAMPLE_QUESTIONS.slice(1).map(q => (
                <button
                  key={q}
                  onClick={() => setQuestion(q)}
                  className="text-[11px] font-syne text-ink-3 bg-surface border border-border rounded-full px-2.5 py-0.5 hover:border-ink-3 hover:text-ink transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={handleAnalyze}
            disabled={loading}
            className="btn-primary py-2.5 rounded-xl font-syne font-semibold text-sm flex items-center justify-center gap-2 disabled:opacity-40"
          >
            {loading ? (
              <><Loader2 size={15} className="animate-spin" /> Analysing…</>
            ) : (
              <><Microscope size={15} /> Analyse Document</>
            )}
          </button>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 text-xs font-serif text-red bg-red/5 border border-red/20 rounded-lg px-3 py-2">
          <AlertTriangle size={13} className="flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="flex flex-col gap-4 animate-fade-up">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green" />
              <span className="font-syne font-semibold text-sm text-ink">Analysis complete</span>
              <span className="text-[10px] font-syne text-ink-3 bg-surface border border-border rounded px-1.5 py-0.5">
                {result.model.includes("sonnet") ? "Sonnet" : "Haiku"}
              </span>
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleCopyAnalysis}
                title="Copy analysis"
                className="text-xs font-syne text-ink-3 hover:text-ink border border-border rounded-lg px-2.5 py-1 transition-colors"
              >
                Copy
              </button>
              <button
                onClick={handleClear}
                className="text-xs font-syne text-ink-3 hover:text-ink border border-border rounded-lg px-2.5 py-1 transition-colors"
              >
                New file
              </button>
            </div>
          </div>

          <div className="bg-surface border border-border rounded-xl px-5 py-4 font-serif text-sm text-ink leading-relaxed">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                h1: ({ children }) => <p className="font-syne font-bold text-base mt-3 mb-1.5">{children}</p>,
                h2: ({ children }) => <p className="font-syne font-bold text-sm mt-3 mb-1">{children}</p>,
                h3: ({ children }) => <p className="font-syne font-semibold text-sm mt-2 mb-0.5">{children}</p>,
                p:  ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                strong: ({ children }) => <strong className="font-semibold text-ink">{children}</strong>,
                ul: ({ children }) => <ul className="my-1.5 pl-4 list-disc space-y-0.5">{children}</ul>,
                ol: ({ children }) => <ol className="my-1.5 pl-4 list-decimal space-y-0.5">{children}</ol>,
                li: ({ children }) => <li className="leading-relaxed">{children}</li>,
                hr: () => <hr className="my-3 border-border" />,
                code: ({ children }) => <code className="bg-bg-2 rounded px-1 py-0.5 text-xs font-mono">{children}</code>,
                blockquote: ({ children }) => (
                  <blockquote className="border-l-2 border-red/40 pl-3 italic text-ink-2 my-2">{children}</blockquote>
                ),
                table: ({ children }) => (
                  <div className="overflow-x-auto my-2">
                    <table className="text-xs border-collapse w-full">{children}</table>
                  </div>
                ),
                th: ({ children }) => <th className="border border-border px-2 py-1 bg-bg font-syne font-semibold text-left">{children}</th>,
                td: ({ children }) => <td className="border border-border px-2 py-1">{children}</td>,
              }}
            >
              {result.analysis}
            </ReactMarkdown>
          </div>

          <p className="text-[11px] font-serif text-ink-3 italic flex items-start gap-1.5">
            <AlertTriangle size={11} className="flex-shrink-0 mt-0.5 text-amber-500" />
            {result.disclaimer}
          </p>
        </div>
      )}
    </div>
  );
}
