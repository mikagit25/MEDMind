"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import Link from "next/link";
import { imagingApi } from "@/lib/api";

type VetImage = {
  id: string;
  title: string;
  description: string | null;
  modality: string;
  anatomy_region: string | null;
  specialty: string | null;
  image_url: string;
  thumbnail_url: string | null;
  source_name: string;
  license: string | null;
  tags: string[];
  view_count: number;
};

const MODALITY_LABELS: Record<string, string> = {
  anatomy: "Anatomy",
  xray: "X-Ray",
  histology: "Histology",
  ultrasound: "Ultrasound",
  dermatoscopy: "Dermatology",
  fundoscopy: "Ophthalmology",
  ct: "CT Scan",
  mri: "MRI",
  other: "Other",
};

const MODALITY_ICONS: Record<string, string> = {
  anatomy: "🐾",
  xray: "🩻",
  histology: "🔬",
  ultrasound: "〰️",
  dermatoscopy: "🔍",
  fundoscopy: "👁️",
  ct: "💡",
  mri: "🧲",
  other: "📷",
};

const SPECIES_FILTERS = [
  { key: "", label: "All Species", icon: "🌐" },
  { key: "dog", label: "Dog", icon: "🐕" },
  { key: "cat", label: "Cat", icon: "🐈" },
  { key: "horse", label: "Horse", icon: "🐎" },
  { key: "cattle", label: "Cattle", icon: "🐄" },
  { key: "rabbit", label: "Rabbit", icon: "🐇" },
  { key: "bird", label: "Bird", icon: "🦜" },
  { key: "pig", label: "Pig", icon: "🐖" },
  { key: "reptile", label: "Reptile", icon: "🦎" },
  { key: "general", label: "General", icon: "📚" },
];

const REGION_ICONS: Record<string, string> = {
  cardiovascular: "🫀",
  digestive: "🫁",
  "nervous system": "🧠",
  musculoskeletal: "🦴",
  respiratory: "🫁",
  reproductive: "🔬",
  urinary: "💧",
  endocrine: "⚗️",
  integument: "🐾",
  sensory: "👁️",
  general: "📋",
  comparative: "📊",
  tissue: "🔬",
  thorax: "🫀",
  spine: "🦴",
  oral: "🦷",
  parasite: "🦠",
  eye: "👁️",
  skin: "🔍",
  abdomen: "🫁",
};

function ImageCard({ img }: { img: VetImage }) {
  const [imgError, setImgError] = useState(false);
  const thumb = img.thumbnail_url || img.image_url;

  const descPreview = img.description
    ? img.description.split(/\n|\.(?:\s|$)/)[0]?.trim() + "."
    : "";

  const species = img.tags?.find(t =>
    ["dog","cat","horse","cattle","rabbit","bird","pig","reptile","snake","guinea pig","ferret"].includes(t.toLowerCase())
  );

  return (
    <Link
      href={`/imaging/${img.id}`}
      className="card overflow-hidden hover:shadow-lg transition-all duration-200 group block"
    >
      <div className="aspect-[4/3] bg-surface overflow-hidden relative">
        {imgError ? (
          <div className="w-full h-full flex flex-col items-center justify-center text-ink-3 bg-surface gap-2">
            <span className="text-4xl">{MODALITY_ICONS[img.modality] ?? "📷"}</span>
            <span className="text-xs font-serif text-center px-3 line-clamp-2">{img.title}</span>
          </div>
        ) : (
          <img
            src={thumb}
            alt={img.title}
            onError={() => setImgError(true)}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />
        )}
        {/* Modality badge */}
        <div className="absolute top-2 left-2">
          <span className="inline-flex items-center gap-1 text-xs font-syne px-1.5 py-0.5 rounded bg-surface/90 border border-border text-ink-3 backdrop-blur-sm">
            <span>{MODALITY_ICONS[img.modality] ?? "📷"}</span>
            {MODALITY_LABELS[img.modality] ?? img.modality}
          </span>
        </div>
        {/* Species badge */}
        {species && (
          <div className="absolute top-2 right-2 bg-black/50 text-white text-[9px] font-syne px-1.5 py-0.5 rounded-full capitalize backdrop-blur-sm">
            {species}
          </div>
        )}
      </div>
      <div className="p-3.5">
        <h3 className="font-syne font-semibold text-sm text-ink line-clamp-2 mb-1.5 group-hover:text-accent transition-colors leading-snug">
          {img.title}
        </h3>
        {descPreview && (
          <p className="font-serif text-xs text-ink-3 line-clamp-2 leading-relaxed">
            {descPreview}
          </p>
        )}
        <div className="flex items-center justify-between mt-2 pt-2 border-t border-border">
          <div className="flex items-center gap-1.5">
            <span className="font-serif text-[10px] text-ink-3">{img.source_name}</span>
            {img.license && (
              <span className="font-syne text-[9px] px-1.5 py-0.5 rounded bg-green-light text-green border border-green/20">
                {img.license.replace("Public Domain", "PD")}
              </span>
            )}
          </div>
          {img.anatomy_region && (
            <span className="text-[10px] font-syne text-ink-3 capitalize flex items-center gap-0.5">
              {REGION_ICONS[img.anatomy_region] ?? "📋"} {img.anatomy_region}
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}

export default function VetImagingPage() {
  const [images, setImages] = useState<VetImage[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [searchQ, setSearchQ] = useState("");
  const [activeModality, setActiveModality] = useState("");
  const [activeSpecies, setActiveSpecies] = useState("");
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [error, setError] = useState("");
  const [modalities, setModalities] = useState<{ modality: string; count: number }[]>([]);
  const searchRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const LIMIT = 32;

  const loadImages = useCallback(async (modality: string, species: string, reset = true) => {
    if (reset) {
      setLoading(true);
      setImages([]);
      setOffset(0);
    } else {
      setLoadingMore(true);
    }
    try {
      const currentOffset = reset ? 0 : offset;
      // Use specialty=veterinary + optional modality/species filters
      const data = await imagingApi.browse({
        specialty: "veterinary",
        modality: modality || undefined,
        limit: LIMIT,
        offset: currentOffset,
        // species filter via tags not directly supported — filter client-side for now
      });
      const filtered = species
        ? data.filter((img: VetImage) => img.tags?.some((t: string) => t.toLowerCase() === species.toLowerCase()))
        : data;

      if (reset) {
        setImages(filtered);
      } else {
        setImages(prev => [...prev, ...filtered]);
      }
      setHasMore(data.length === LIMIT);
      if (!reset) setOffset(currentOffset + LIMIT);
    } catch {
      setError("Failed to load veterinary images");
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [offset]);

  useEffect(() => {
    // Load modalities filtered to veterinary specialty
    imagingApi.browse({ specialty: "veterinary", limit: 500, offset: 0 })
      .then((data: VetImage[]) => {
        const counts: Record<string, number> = {};
        data.forEach((img: VetImage) => {
          counts[img.modality] = (counts[img.modality] || 0) + 1;
        });
        setModalities(
          Object.entries(counts)
            .map(([modality, count]) => ({ modality, count }))
            .sort((a, b) => b.count - a.count)
        );
      })
      .catch(() => {});
    loadImages("", "", true);
  }, []);

  function handleModalityChange(mod: string) {
    setActiveModality(mod);
    setSearchQ("");
    loadImages(mod, activeSpecies, true);
  }

  function handleSpeciesChange(sp: string) {
    setActiveSpecies(sp);
    setSearchQ("");
    loadImages(activeModality, sp, true);
  }

  function handleSearch(q: string) {
    setSearchQ(q);
    if (searchRef.current) clearTimeout(searchRef.current);
    if (!q.trim()) {
      loadImages(activeModality, activeSpecies, true);
      return;
    }
    searchRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await imagingApi.search(q, "veterinary");
        const filtered = activeSpecies
          ? data.filter((img: VetImage) => img.tags?.some((t: string) => t.toLowerCase() === activeSpecies.toLowerCase()))
          : data;
        setImages(filtered);
        setHasMore(false);
      } catch {
        setError("Search failed");
      } finally {
        setLoading(false);
      }
    }, 400);
  }

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <aside className="w-52 shrink-0 border-r border-border p-4 hidden md:flex flex-col gap-4 overflow-y-auto">
        {/* Modality filter */}
        <div>
          <h2 className="font-syne font-bold text-xs text-ink-3 uppercase tracking-widest mb-2">Modality</h2>
          <div className="space-y-0.5">
            <button
              onClick={() => handleModalityChange("")}
              className={`w-full text-left px-2 py-1.5 rounded-lg font-syne text-xs transition-colors ${!activeModality ? "bg-ink text-white" : "text-ink hover:bg-surface"}`}
            >
              All
            </button>
            {modalities.map(m => (
              <button
                key={m.modality}
                onClick={() => handleModalityChange(m.modality)}
                className={`w-full text-left px-2 py-1.5 rounded-lg font-syne text-xs transition-colors flex items-center justify-between ${activeModality === m.modality ? "bg-ink text-white" : "text-ink hover:bg-surface"}`}
              >
                <span className="flex items-center gap-1.5">
                  <span>{MODALITY_ICONS[m.modality] ?? "📷"}</span>
                  {MODALITY_LABELS[m.modality] ?? m.modality}
                </span>
                <span className={`text-[10px] ${activeModality === m.modality ? "text-white/60" : "text-ink-3"}`}>
                  {m.count}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Species filter */}
        <div>
          <h2 className="font-syne font-bold text-xs text-ink-3 uppercase tracking-widest mb-2">Species</h2>
          <div className="space-y-0.5">
            {SPECIES_FILTERS.map(sp => (
              <button
                key={sp.key}
                onClick={() => handleSpeciesChange(sp.key)}
                className={`w-full text-left px-2 py-1.5 rounded-lg font-syne text-xs transition-colors ${activeSpecies === sp.key ? "bg-ink text-white" : "text-ink hover:bg-surface"}`}
              >
                <span className="flex items-center gap-1.5">
                  <span>{sp.icon}</span>
                  {sp.label}
                </span>
              </button>
            ))}
          </div>
        </div>

        <div className="mt-auto pt-4 border-t border-border">
          <Link href="/imaging" className="flex items-center gap-2 px-2 py-1.5 rounded-lg font-syne text-xs text-ink hover:bg-surface transition-colors">
            <span>🩻</span> Human Imaging
          </Link>
          <Link href="/veterinary" className="flex items-center gap-2 px-2 py-1.5 rounded-lg font-syne text-xs text-ink hover:bg-surface transition-colors mt-1">
            <span>🐾</span> Vet Reference
          </Link>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 min-w-0 flex flex-col">
        {/* Header */}
        <div className="px-4 pt-4 pb-3 border-b border-border">
          <div className="flex items-center gap-3 mb-3">
            <div>
              <h1 className="font-syne font-black text-xl text-ink flex items-center gap-2">
                <span>🐾</span> Veterinary Anatomy & Imaging
              </h1>
              <p className="font-serif text-xs text-ink-3 mt-0.5">
                Animal anatomy illustrations · Radiographs · Histology · Open-access with attribution
              </p>
            </div>
            <Link href="/imaging" className="ml-auto btn-ghost text-xs px-3 py-1.5 flex items-center gap-1.5 shrink-0">
              🩻 Human
            </Link>
          </div>
          <input
            type="search"
            value={searchQ}
            onChange={e => handleSearch(e.target.value)}
            placeholder="Search — canine heart, equine hoof, feline kidney..."
            className="w-full border border-border rounded-xl px-4 py-2.5 font-serif text-sm text-ink bg-surface focus:outline-none focus:border-ink-3"
          />
          {/* Mobile species pills */}
          <div className="flex gap-2 mt-2.5 overflow-x-auto pb-1 md:hidden">
            {SPECIES_FILTERS.map(sp => (
              <button
                key={sp.key}
                onClick={() => handleSpeciesChange(sp.key)}
                className={`shrink-0 px-3 py-1 rounded-full font-syne text-xs border transition-colors ${activeSpecies === sp.key ? "bg-ink text-white border-ink" : "border-border text-ink-3 hover:border-ink-3"}`}
              >
                {sp.icon} {sp.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-light border border-red/20 text-red text-sm font-serif">{error}</div>
          )}

          {loading ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
              {Array.from({ length: 12 }).map((_, i) => (
                <div key={i} className="card overflow-hidden animate-pulse">
                  <div className="aspect-[4/3] bg-surface" />
                  <div className="p-3 space-y-2">
                    <div className="h-3 bg-surface rounded w-3/4" />
                    <div className="h-2 bg-surface rounded w-1/2" />
                  </div>
                </div>
              ))}
            </div>
          ) : images.length === 0 ? (
            <div className="text-center py-20">
              <div className="text-5xl mb-3">🐾</div>
              <div className="font-syne font-semibold text-ink">No images found</div>
              <div className="font-serif text-sm text-ink-3 mt-1">
                {searchQ ? `No results for "${searchQ}"` : "No images in this filter. Try All Species or All Modalities."}
              </div>
              <p className="font-serif text-xs text-ink-3 mt-4 max-w-sm mx-auto">
                Veterinary images come from Ruth Lawson's <em>Anatomy and Physiology of Animals</em> (CC BY-SA),
                Sisson & Grossman's <em>Anatomy of Domestic Animals</em> (1914, PD), and other open-access sources.
              </p>
            </div>
          ) : (
            <>
              {searchQ && (
                <p className="font-syne text-xs text-ink-3 mb-3">{images.length} result{images.length !== 1 ? "s" : ""} for "{searchQ}"</p>
              )}

              {/* Source info banner */}
              {!searchQ && !activeSpecies && !activeModality && (
                <div className="mb-4 p-3 rounded-xl bg-blue-light border border-blue/20 flex items-start gap-3">
                  <span className="text-xl">📚</span>
                  <div>
                    <div className="font-syne font-bold text-xs text-blue mb-0.5">Open-Access Sources</div>
                    <p className="font-serif text-xs text-ink-3">
                      Images from <strong>Ruth Lawson — Anatomy and Physiology of Animals</strong> (CC BY-SA 3.0),
                      <strong> Sisson & Grossman 1914</strong> (Public Domain), Wikimedia Commons veterinary radiology,
                      and BHL historical anatomy textbooks.
                    </p>
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
                {images.map(img => (
                  <ImageCard key={img.id} img={img} />
                ))}
              </div>

              {hasMore && !searchQ && (
                <div className="mt-6 text-center">
                  <button
                    onClick={() => loadImages(activeModality, activeSpecies, false)}
                    disabled={loadingMore}
                    className="btn-ghost text-sm px-6 py-2.5 disabled:opacity-50"
                  >
                    {loadingMore ? "Loading..." : "Load more"}
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
