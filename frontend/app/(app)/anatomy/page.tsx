"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { imagingApi } from "@/lib/api";

type Viewer = {
  id: string;
  title: string;
  description: string | null;
  organ_system: string | null;
  anatomy_region: string | null;
  embed_type: string;
  embed_id: string;
  embed_url: string | null;
  thumbnail_url: string | null;
  source_name: string | null;
  source_url: string | null;
  license: string | null;
  attribution: string | null;
};

const SYSTEM_LABELS: Record<string, string> = {
  cardiovascular: "Cardiovascular",
  nervous: "Nervous System",
  respiratory: "Respiratory",
  digestive: "Digestive",
  musculoskeletal: "Musculoskeletal",
  urinary: "Urinary",
  endocrine: "Endocrine",
  reproductive: "Reproductive",
};

const SYSTEM_ICONS: Record<string, string> = {
  cardiovascular: "🫀",
  nervous: "🧠",
  respiratory: "🫁",
  digestive: "🫃",
  musculoskeletal: "🦴",
  urinary: "💧",
  endocrine: "⚗️",
  reproductive: "🔬",
};

function SketchfabEmbed({ embedUrl, title }: { embedUrl: string; title: string }) {
  const [loaded, setLoaded] = useState(false);
  const [started, setStarted] = useState(false);
  const [thumbError, setThumbError] = useState(false);

  if (!started) {
    return (
      <div className="relative w-full aspect-[4/3] bg-surface rounded-xl overflow-hidden flex items-center justify-center border border-border">
        <div className="text-center p-4">
          <div className="text-5xl mb-3">🧊</div>
          <div className="font-syne font-semibold text-sm text-ink mb-1">{title}</div>
          <div className="font-serif text-xs text-ink-3 mb-3">Interactive 3D model — click to load</div>
          <button
            onClick={() => setStarted(true)}
            className="btn-primary text-xs px-4 py-2"
          >
            Load 3D Viewer
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full aspect-[4/3] bg-black rounded-xl overflow-hidden">
      {!loaded && (
        <div className="absolute inset-0 flex items-center justify-center bg-surface">
          <div className="text-ink-3 font-serif text-sm">Loading 3D viewer...</div>
        </div>
      )}
      <iframe
        title={title}
        src={embedUrl}
        className="w-full h-full"
        allow="autoplay; fullscreen; xr-spatial-tracking"
        allowFullScreen
        onLoad={() => setLoaded(true)}
        style={{ border: "none" }}
      />
    </div>
  );
}

function ViewerCard({
  viewer,
  active,
  onClick,
}: {
  viewer: Viewer;
  active: boolean;
  onClick: () => void;
}) {
  const [thumbError, setThumbError] = useState(false);

  return (
    <button
      onClick={onClick}
      className={`card p-0 overflow-hidden text-left w-full transition-all ${
        active ? "ring-2 ring-ink shadow-lg" : "hover:shadow-md"
      }`}
    >
      <div className="aspect-[4/3] bg-surface overflow-hidden relative">
        {viewer.thumbnail_url && !thumbError ? (
          <img
            src={viewer.thumbnail_url}
            alt={viewer.title}
            onError={() => setThumbError(true)}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <span className="text-3xl">
              {SYSTEM_ICONS[viewer.organ_system ?? ""] ?? "🧊"}
            </span>
          </div>
        )}
        {active && (
          <div className="absolute inset-0 bg-ink/10 flex items-center justify-center">
            <span className="bg-ink text-white font-syne text-xs px-2 py-1 rounded-full">Active</span>
          </div>
        )}
      </div>
      <div className="p-2.5">
        <div className="font-syne font-semibold text-xs text-ink line-clamp-1">{viewer.title}</div>
        {viewer.organ_system && (
          <div className="font-serif text-[10px] text-ink-3 mt-0.5 capitalize">
            {SYSTEM_ICONS[viewer.organ_system]} {SYSTEM_LABELS[viewer.organ_system] ?? viewer.organ_system}
          </div>
        )}
      </div>
    </button>
  );
}

export default function AnatomyPage() {
  const [viewers, setViewers] = useState<Viewer[]>([]);
  const [activeSystem, setActiveSystem] = useState<string>("");
  const [activeViewer, setActiveViewer] = useState<Viewer | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    imagingApi.listViewers()
      .then((data: Viewer[]) => {
        setViewers(data);
        if (data.length > 0) setActiveViewer(data[0]);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const systems = Array.from(new Set(viewers.map(v => v.organ_system).filter(Boolean))) as string[];
  const filtered = activeSystem ? viewers.filter(v => v.organ_system === activeSystem) : viewers;

  function getEmbedUrl(viewer: Viewer): string {
    if (viewer.embed_url) return viewer.embed_url;
    if (viewer.embed_type === "sketchfab") {
      return `https://sketchfab.com/models/${viewer.embed_id}/embed?autospin=0.2&autostart=1&ui_theme=dark`;
    }
    return viewer.embed_id;
  }

  return (
    <div className="p-4 max-w-6xl mx-auto pb-10">
      {/* Header */}
      <div className="mb-5">
        <div className="flex items-center gap-3 mb-1">
          <Link href="/imaging" className="text-ink-3 text-sm font-syne hover:text-ink">← Imaging Library</Link>
        </div>
        <h1 className="font-syne font-black text-2xl text-ink">3D Anatomy Atlas</h1>
        <p className="font-serif text-ink-3 text-sm">
          Interactive 3D models of human organ systems — rotate, zoom, explore
        </p>
      </div>

      {/* System filter tabs */}
      <div className="flex gap-2 overflow-x-auto pb-1 mb-5">
        <button
          onClick={() => setActiveSystem("")}
          className={`shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-full font-syne text-xs border transition-colors ${
            !activeSystem ? "bg-ink text-white border-ink" : "border-border text-ink-3 hover:border-ink-3 hover:text-ink"
          }`}
        >
          All Systems
        </button>
        {systems.map(sys => (
          <button
            key={sys}
            onClick={() => setActiveSystem(sys === activeSystem ? "" : sys)}
            className={`shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-full font-syne text-xs border transition-colors ${
              activeSystem === sys ? "bg-ink text-white border-ink" : "border-border text-ink-3 hover:border-ink-3 hover:text-ink"
            }`}
          >
            <span>{SYSTEM_ICONS[sys] ?? ""}</span>
            {SYSTEM_LABELS[sys] ?? sys}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-ink-3 font-serif text-sm p-8 text-center">Loading anatomy viewers...</div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Model grid — left column */}
          <div className="lg:col-span-1">
            <h2 className="font-syne font-bold text-xs text-ink-3 uppercase tracking-widest mb-3">
              {filtered.length} Model{filtered.length !== 1 ? "s" : ""}
            </h2>
            <div className="grid grid-cols-2 lg:grid-cols-1 gap-3 max-h-[calc(100vh-280px)] overflow-y-auto pr-1">
              {filtered.map(v => (
                <ViewerCard
                  key={v.id}
                  viewer={v}
                  active={activeViewer?.id === v.id}
                  onClick={() => setActiveViewer(v)}
                />
              ))}
            </div>
          </div>

          {/* Active viewer — right panel */}
          <div className="lg:col-span-2">
            {activeViewer ? (
              <div>
                <div className="flex items-start justify-between mb-3 gap-3">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      {activeViewer.organ_system && (
                        <span className="font-syne text-xs font-semibold px-2.5 py-1 rounded-full bg-ink text-white">
                          {SYSTEM_ICONS[activeViewer.organ_system]} {SYSTEM_LABELS[activeViewer.organ_system] ?? activeViewer.organ_system}
                        </span>
                      )}
                      {activeViewer.anatomy_region && (
                        <span className="font-syne text-xs px-2.5 py-1 rounded-full border border-border text-ink-3 capitalize">
                          {activeViewer.anatomy_region}
                        </span>
                      )}
                    </div>
                    <h2 className="font-syne font-black text-xl text-ink">{activeViewer.title}</h2>
                    {activeViewer.description && (
                      <p className="font-serif text-sm text-ink-3 mt-1 leading-relaxed">{activeViewer.description}</p>
                    )}
                  </div>
                  {activeViewer.source_url && (
                    <a
                      href={activeViewer.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-ghost text-xs px-3 py-1.5 shrink-0"
                    >
                      Full view ↗
                    </a>
                  )}
                </div>

                {/* 3D embed */}
                <SketchfabEmbed
                  embedUrl={getEmbedUrl(activeViewer)}
                  title={activeViewer.title}
                />

                {/* Controls hint */}
                <div className="flex items-center gap-4 mt-3 px-1">
                  <div className="flex items-center gap-1.5">
                    <span className="font-syne text-xs text-ink-3">🖱️ Drag</span>
                    <span className="font-serif text-xs text-ink-3">— rotate</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="font-syne text-xs text-ink-3">⚙️ Scroll</span>
                    <span className="font-serif text-xs text-ink-3">— zoom</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="font-syne text-xs text-ink-3">✋ Right-drag</span>
                    <span className="font-serif text-xs text-ink-3">— pan</span>
                  </div>
                </div>

                {/* Attribution */}
                {activeViewer.attribution && (
                  <div className="mt-3 p-3 rounded-xl bg-surface border border-border">
                    <div className="font-syne font-bold text-xs text-ink-3 uppercase tracking-wider mb-1">Attribution</div>
                    <p className="font-serif text-xs text-ink">{activeViewer.attribution}</p>
                    {activeViewer.license && (
                      <span className="inline-block mt-1.5 font-syne text-xs px-2 py-0.5 rounded bg-green-light text-green border border-green/20">
                        {activeViewer.license}
                      </span>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div className="card p-10 text-center">
                <div className="text-5xl mb-3">🧊</div>
                <div className="font-syne font-semibold text-ink">Select a model to view</div>
                <div className="font-serif text-sm text-ink-3 mt-1">
                  Choose an anatomy model from the list to load the 3D viewer.
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* OpenAnatomy / external resources footer */}
      <div className="mt-8 pt-6 border-t border-border">
        <h2 className="font-syne font-bold text-xs text-ink-3 uppercase tracking-widest mb-3">External 3D Resources</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { name: "Visible Body", desc: "Complete human atlas", url: "https://www.visiblebody.com", icon: "🫀" },
            { name: "BioDigital Human", desc: "Interactive anatomy", url: "https://human.biodigital.com", icon: "🧬" },
            { name: "Zygote Body", desc: "Free 3D anatomy", url: "https://www.zygotebody.com", icon: "🦴" },
            { name: "OpenAnatomy (Harvard)", desc: "Brain & heart atlases", url: "https://www.openanatomy.org", icon: "🧠" },
          ].map(r => (
            <a
              key={r.name}
              href={r.url}
              target="_blank"
              rel="noopener noreferrer"
              className="card p-3 hover:shadow-md transition-shadow"
            >
              <div className="text-2xl mb-1.5">{r.icon}</div>
              <div className="font-syne font-semibold text-xs text-ink">{r.name}</div>
              <div className="font-serif text-xs text-ink-3">{r.desc}</div>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
