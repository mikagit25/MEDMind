"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { imagingApi } from "@/lib/api";

type Image = {
  id: string;
  title: string;
  description: string | null;
  modality: string;
  anatomy_region: string | null;
  specialty: string | null;
  image_url: string;
  thumbnail_url: string | null;
  source_name: string;
  source_url: string | null;
  license: string | null;
  attribution: string | null;
  tags: string[];
  view_count: number;
};

const MODALITY_LABELS: Record<string, string> = {
  xray: "X-Ray",
  ct: "CT Scan",
  mri: "MRI",
  ultrasound: "Ultrasound",
  anatomy: "Anatomy Illustration",
  histology: "Histology",
  "3d": "3D Model",
  other: "Image",
};

export default function ImageDetailPage() {
  const t = useT();
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [img, setImg] = useState<Image | null>(null);
  const [loading, setLoading] = useState(true);
  const [lightbox, setLightbox] = useState(false);
  const [imgError, setImgError] = useState(false);
  const [analysis, setAnalysis] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [question, setQuestion] = useState("");

  const runAnalysis = async () => {
    if (!img) return;
    setAnalyzing(true);
    setAnalysis(null);
    try {
      const res = await imagingApi.analyzeImage({
        image_url: img.image_url,
        modality: img.modality,
        image_id: img.id,
        question: question.trim() || undefined,
      });
      setAnalysis(res.analysis);
    } catch {
      setAnalysis("AI analysis could not be completed. The image may not be accessible or the AI service encountered an error.");
    } finally {
      setAnalyzing(false);
    }
  };

  useEffect(() => {
    imagingApi.get(id)
      .then(setImg)
      .catch(() => router.push("/imaging"))
      .finally(() => setLoading(false));
  }, [id, router]);

  if (loading) return <div className="p-6 text-ink-3 font-serif text-sm">Loading...</div>;
  if (!img) return null;

  const modLabel = MODALITY_LABELS[img.modality] ?? img.modality;

  return (
    <>
      {/* Lightbox */}
      {lightbox && (
        <div
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4"
          onClick={() => setLightbox(false)}
        >
          <button
            className="absolute top-4 right-4 text-white/60 hover:text-white font-syne text-lg"
            onClick={() => setLightbox(false)}
          >
            ✕ Close
          </button>
          <img
            src={img.image_url}
            alt={img.title}
            className="max-w-full max-h-[90vh] object-contain rounded-lg"
            onClick={e => e.stopPropagation()}
          />
        </div>
      )}

      <div className="p-4 max-w-4xl mx-auto pb-10">
        {/* Back */}
        <div className="mb-4">
          <Link href="/imaging" className="text-ink-3 text-sm font-syne hover:text-ink">
            ← Imaging Library
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Image panel */}
          <div>
            <div
              className="card overflow-hidden cursor-zoom-in group"
              onClick={() => !imgError && setLightbox(true)}
              title="Click to enlarge"
            >
              {imgError ? (
                <div className="aspect-square flex items-center justify-center bg-surface">
                  <div className="text-center text-ink-3">
                    <div className="text-4xl mb-2">🩻</div>
                    <div className="font-serif text-sm">Image unavailable</div>
                    {img.source_url && (
                      <a
                        href={img.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-syne text-xs text-blue hover:underline"
                        onClick={e => e.stopPropagation()}
                      >
                        View at source ↗
                      </a>
                    )}
                  </div>
                </div>
              ) : (
                <div className="relative">
                  <img
                    src={img.image_url}
                    alt={img.title}
                    onError={() => setImgError(true)}
                    className="w-full object-contain max-h-[500px] bg-surface group-hover:opacity-95 transition-opacity"
                  />
                  <div className="absolute bottom-2 right-2 bg-black/50 text-white text-[10px] font-syne px-2 py-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity">
                    Click to enlarge
                  </div>
                </div>
              )}
            </div>

            {/* Attribution card */}
            <div className="mt-3 p-3 rounded-xl bg-surface border border-border">
              <div className="font-syne font-bold text-xs text-ink-3 uppercase tracking-wider mb-2">Attribution</div>
              <p className="font-serif text-xs text-ink leading-relaxed">
                {img.attribution ?? img.source_name}
              </p>
              <div className="flex items-center gap-3 mt-2">
                {img.license && (
                  <span className="font-syne text-xs px-2 py-0.5 rounded bg-green-light text-green border border-green/20">
                    {img.license}
                  </span>
                )}
                {img.source_url && (
                  <a
                    href={img.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-syne text-xs text-blue hover:underline flex items-center gap-1"
                  >
                    View source ↗
                  </a>
                )}
              </div>
            </div>
          </div>

          {/* Metadata panel */}
          <div>
            {/* Type badge */}
            <div className="flex items-center gap-2 mb-3">
              <span className="font-syne text-xs font-semibold px-2.5 py-1 rounded-full bg-ink text-white">
                {modLabel}
              </span>
              {img.anatomy_region && (
                <span className="font-syne text-xs px-2.5 py-1 rounded-full border border-border text-ink-3 capitalize">
                  {img.anatomy_region}
                </span>
              )}
              {img.specialty && (
                <span className="font-syne text-xs px-2.5 py-1 rounded-full border border-border text-ink-3 capitalize">
                  {img.specialty}
                </span>
              )}
            </div>

            <h1 className="font-syne font-black text-xl text-ink mb-3 leading-snug">
              {img.title}
            </h1>

            {img.description && (
              <div className="mb-4">
                <p className="font-serif text-sm text-ink leading-relaxed">{img.description}</p>
              </div>
            )}

            {/* Tags */}
            {img.tags.length > 0 && (
              <div className="mb-4">
                <div className="font-syne font-bold text-xs text-ink-3 uppercase tracking-wider mb-2">Tags</div>
                <div className="flex flex-wrap gap-1.5">
                  {img.tags.map((tag, i) => (
                    <Link
                      key={i}
                      href={`/imaging?q=${encodeURIComponent(tag)}`}
                      className="font-serif text-xs px-2 py-0.5 rounded-full bg-surface border border-border text-ink-3 hover:border-ink-3 hover:text-ink transition-colors"
                    >
                      {tag}
                    </Link>
                  ))}
                </div>
              </div>
            )}

            {/* Stats */}
            <div className="flex items-center gap-4 mb-4">
              <div className="text-center">
                <div className="font-syne font-black text-lg text-ink">{img.view_count}</div>
                <div className="font-serif text-xs text-ink-3">Views</div>
              </div>
              <div className="text-center">
                <div className="font-syne font-black text-lg text-ink capitalize">{img.source_name}</div>
                <div className="font-serif text-xs text-ink-3">Source</div>
              </div>
            </div>

            {/* Clinical tip box */}
            <div className="p-4 rounded-xl bg-blue-light border border-blue/20">
              <div className="font-syne font-bold text-xs text-blue uppercase tracking-wider mb-1.5">
                📚 Study Tips
              </div>
              <ul className="font-serif text-xs text-ink-3 space-y-1 list-disc list-inside">
                <li>Identify key anatomical landmarks first</li>
                <li>Note any abnormalities or asymmetries</li>
                <li>Compare with the normal anatomy in our library</li>
                <li>Correlate imaging findings with clinical presentation</li>
              </ul>
            </div>

            {/* Actions */}
            <div className="flex gap-2 mt-4">
              {!imgError && (
                <button
                  onClick={() => setLightbox(true)}
                  className="btn-primary text-sm px-4 py-2"
                >
                  Enlarge Image
                </button>
              )}
              {img.source_url && (
                <a
                  href={img.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-ghost text-sm px-4 py-2"
                >
                  Original Source ↗
                </a>
              )}
            </div>
          </div>
        </div>

        {/* AI Analysis Panel */}
        <div className="mt-6 card p-5">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xl">🔬</span>
            <h2 className="font-syne font-black text-base text-ink">AI Image Interpretation</h2>
            <span className="font-syne text-xs text-ink-3 bg-blue-light text-blue px-2 py-0.5 rounded-full border border-blue/20">Claude Vision</span>
          </div>
          <p className="font-serif text-xs text-ink-3 mb-3">
            Ask Claude to analyse this {MODALITY_LABELS[img.modality] ?? img.modality} image — findings, interpretation, differential diagnosis, and teaching points.
          </p>

          <div className="flex gap-2 mb-3">
            <input
              type="text"
              value={question}
              onChange={e => setQuestion(e.target.value)}
              placeholder="Ask a specific question, or leave blank for full analysis…"
              className="flex-1 border border-border rounded-lg px-3 py-2 font-serif text-sm text-ink bg-surface focus:outline-none focus:border-ink-3"
              onKeyDown={e => e.key === "Enter" && !analyzing && runAnalysis()}
            />
            <button
              onClick={runAnalysis}
              disabled={analyzing || imgError}
              className="px-4 py-2 rounded-lg bg-blue text-white font-syne font-semibold text-sm hover:bg-blue/90 transition-colors disabled:opacity-50"
            >
              {analyzing ? "Analysing…" : "Analyse"}
            </button>
          </div>

          {analyzing && (
            <div className="p-4 rounded-xl bg-blue-light/30 border border-blue/20">
              <div className="font-serif text-sm text-ink-3 animate-pulse">
                Claude is analysing the image… This may take 10–20 seconds.
              </div>
            </div>
          )}

          {analysis && !analyzing && (
            <div className="p-4 rounded-xl bg-blue-light/20 border border-blue/20">
              <div className="font-syne font-bold text-xs text-blue uppercase tracking-wide mb-2">AI Analysis</div>
              <p className="font-serif text-sm text-ink leading-relaxed whitespace-pre-wrap">{analysis}</p>
              <div className="mt-3 pt-3 border-t border-blue/10 flex items-start gap-2">
                <span className="text-amber">⚠️</span>
                <p className="font-serif text-xs text-ink-3">
                  This is an AI-generated educational interpretation, not a clinical report. Always correlate with patient history and consult a qualified radiologist for diagnostic purposes.
                </p>
              </div>
              <button
                onClick={() => { setAnalysis(null); setQuestion(""); }}
                className="mt-2 font-syne text-xs text-ink-3 hover:text-ink"
              >
                Clear analysis
              </button>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
