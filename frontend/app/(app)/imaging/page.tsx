"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import Link from "next/link";
import { imagingApi } from "@/lib/api";
import { useT } from "@/lib/i18n";

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
  license: string | null;
  tags: string[];
  view_count: number;
};

type Modality = { modality: string; count: number };

const MODALITY_LABELS: Record<string, string> = {
  xray: "X-Ray",
  ct: "CT",
  mri: "MRI",
  ultrasound: "Ultrasound",
  anatomy: "Anatomy",
  histology: "Histology",
  "3d": "3D Model",
  other: "Other",
};

const MODALITY_ICONS: Record<string, string> = {
  xray: "🩻",
  ct: "🔬",
  mri: "🧲",
  ultrasound: "〰️",
  anatomy: "🫀",
  histology: "🔭",
  "3d": "🧊",
  other: "📷",
};

function ModalityBadge({ modality }: { modality: string }) {
  return (
    <span className="inline-flex items-center gap-1 text-xs font-syne px-1.5 py-0.5 rounded bg-surface border border-border text-ink-3">
      <span>{MODALITY_ICONS[modality] ?? "📷"}</span>
      {MODALITY_LABELS[modality] ?? modality}
    </span>
  );
}

function ImageCard({ img }: { img: Image }) {
  const [imgError, setImgError] = useState(false);
  const thumb = img.thumbnail_url || img.image_url;

  return (
    <Link
      href={`/imaging/${img.id}`}
      className="card overflow-hidden hover:shadow-md transition-shadow group block"
    >
      <div className="aspect-[4/3] bg-surface overflow-hidden relative">
        {imgError ? (
          <div className="w-full h-full flex items-center justify-center text-ink-3">
            <span className="text-3xl">{MODALITY_ICONS[img.modality] ?? "📷"}</span>
          </div>
        ) : (
          <img
            src={thumb}
            alt={img.title}
            onError={() => setImgError(true)}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />
        )}
        <div className="absolute top-2 left-2">
          <ModalityBadge modality={img.modality} />
        </div>
      </div>
      <div className="p-3">
        <h3 className="font-syne font-semibold text-sm text-ink line-clamp-2 mb-1 group-hover:underline">
          {img.title}
        </h3>
        <div className="flex items-center justify-between">
          <span className="font-serif text-xs text-ink-3">{img.source_name}</span>
          {img.anatomy_region && (
            <span className="font-serif text-xs text-ink-3 capitalize">{img.anatomy_region}</span>
          )}
        </div>
      </div>
    </Link>
  );
}

export default function ImagingPage() {
  const t = useT();
  const [images, setImages] = useState<Image[]>([]);
  const [modalities, setModalities] = useState<Modality[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [searchQ, setSearchQ] = useState("");
  const [activeModality, setActiveModality] = useState<string>("");
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [error, setError] = useState("");
  const [openIResults, setOpenIResults] = useState<{ uid: string; title: string; image_url: string; thumbnail_url: string; source_url: string; modality: string }[]>([]);
  const [openILoading, setOpenILoading] = useState(false);
  const searchRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const LIMIT = 36;

  const loadImages = useCallback(async (modality: string, reset = true) => {
    if (reset) {
      setLoading(true);
      setImages([]);
      setOffset(0);
    } else {
      setLoadingMore(true);
    }
    try {
      const currentOffset = reset ? 0 : offset;
      const data = await imagingApi.browse({
        modality: modality || undefined,
        limit: LIMIT,
        offset: currentOffset,
      });
      if (reset) {
        setImages(data);
      } else {
        setImages(prev => [...prev, ...data]);
      }
      setHasMore(data.length === LIMIT);
      if (!reset) setOffset(currentOffset + LIMIT);
    } catch {
      setError("Failed to load images");
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  }, [offset]);

  useEffect(() => {
    Promise.all([
      imagingApi.modalities().then(setModalities),
      loadImages("", true),
    ]).catch(() => setError("Failed to initialize"));
  }, []);

  function handleModalityChange(mod: string) {
    setActiveModality(mod);
    setSearchQ("");
    setOpenIResults([]);
    loadImages(mod, true);
  }

  function handleSearch(q: string) {
    setSearchQ(q);
    if (searchRef.current) clearTimeout(searchRef.current);
    if (!q.trim()) {
      setOpenIResults([]);
      loadImages(activeModality, true);
      return;
    }
    // Local search
    searchRef.current = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await imagingApi.search(q, activeModality || undefined);
        setImages(data);
        setHasMore(false);
      } catch {
        setError("Search failed");
      } finally {
        setLoading(false);
      }
    }, 400);
    // Live NIH OpenI proxy search (runs in parallel)
    if (q.length >= 3) {
      setOpenILoading(true);
      imagingApi.searchOpenI(q, 1, 8)
        .then(r => setOpenIResults(r.list || []))
        .catch(() => {})
        .finally(() => setOpenILoading(false));
    } else {
      setOpenIResults([]);
    }
  }

  return (
    <div className="flex h-full">
      {/* ── Sidebar filters ──────────────────────────────────── */}
      <aside className="w-48 shrink-0 border-r border-border p-4 hidden md:block">
        <h2 className="font-syne font-bold text-xs text-ink-3 uppercase tracking-widest mb-3">{t("modalities")}</h2>
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

        <div className="mt-6 pt-4 border-t border-border">
          <Link
            href="/anatomy"
            className="flex items-center gap-2 px-2 py-1.5 rounded-lg font-syne text-xs text-ink hover:bg-surface transition-colors"
          >
            <span>🧊</span>
            3D Anatomy
          </Link>
        </div>
      </aside>

      {/* ── Main content ─────────────────────────────────────── */}
      <div className="flex-1 min-w-0 flex flex-col">
        {/* Header */}
        <div className="px-4 pt-4 pb-3 border-b border-border">
          <div className="flex items-center gap-3 mb-3">
            <div>
              <h1 className="font-syne font-black text-xl text-ink">{t("imaging.title")}</h1>
              <p className="font-serif text-xs text-ink-3">X-Ray · CT · MRI · Ultrasound · Anatomy · Histology — open-access with attribution</p>
            </div>
            <Link href="/anatomy" className="ml-auto btn-ghost text-xs px-3 py-1.5 flex items-center gap-1.5 shrink-0">
              <span>🧊</span> 3D Anatomy
            </Link>
          </div>
          <input
            type="search"
            value={searchQ}
            onChange={e => handleSearch(e.target.value)}
            placeholder="Search images — pneumonia, brain MRI, femur fracture..."
            className="w-full border border-border rounded-xl px-4 py-2.5 font-serif text-sm text-ink bg-surface focus:outline-none focus:border-ink-3"
          />
          {/* Mobile modality pills */}
          <div className="flex gap-2 mt-2.5 overflow-x-auto pb-1 md:hidden">
            {[{ modality: "", count: 0 }, ...modalities].map(m => (
              <button
                key={m.modality}
                onClick={() => handleModalityChange(m.modality)}
                className={`shrink-0 px-3 py-1 rounded-full font-syne text-xs border transition-colors ${activeModality === m.modality ? "bg-ink text-white border-ink" : "border-border text-ink-3 hover:border-ink-3"}`}
              >
                {m.modality ? (MODALITY_ICONS[m.modality] + " " + (MODALITY_LABELS[m.modality] ?? m.modality)) : "All"}
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-light border border-red/20 text-red text-sm font-serif">{error}</div>
          )}

          {/* NIH OpenI live results */}
          {(openILoading || openIResults.length > 0) && (
            <div className="mb-6">
              <h2 className="font-syne font-bold text-xs text-ink-3 uppercase tracking-widest mb-3 flex items-center gap-2">
                <span>🔬</span> Live results from NIH OpenI
                {openILoading && <span className="font-serif text-xs normal-case tracking-normal text-ink-3">Loading...</span>}
              </h2>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 mb-2">
                {openIResults.map(r => (
                  <a
                    key={r.uid}
                    href={r.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="card overflow-hidden hover:shadow-md transition-shadow group block"
                  >
                    <div className="aspect-[4/3] bg-surface overflow-hidden">
                      <img
                        src={r.thumbnail_url}
                        alt={r.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                        onError={e => { (e.target as HTMLImageElement).style.display = "none"; }}
                      />
                    </div>
                    <div className="p-2">
                      <p className="font-serif text-xs text-ink line-clamp-2">{r.title}</p>
                      <div className="flex items-center justify-between mt-1">
                        <span className="text-[10px] font-syne text-ink-3">NIH OpenI</span>
                        <span className="text-[10px] font-syne text-blue">↗ Open</span>
                      </div>
                    </div>
                  </a>
                ))}
              </div>
              <p className="font-serif text-xs text-ink-3">
                NIH OpenI images open in their source page. <span className="italic">Public Domain — National Library of Medicine.</span>
              </p>
              <div className="border-b border-border mt-4 mb-4" />
            </div>
          )}

          {/* Library grid */}
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
            <div className="text-center py-16">
              <div className="text-5xl mb-3">🩻</div>
              <div className="font-syne font-semibold text-ink">{t("no_images")}</div>
              <div className="font-serif text-sm text-ink-3 mt-1">
                {searchQ ? `No local results for "${searchQ}" — try the NIH OpenI results above.` : "No images in this category yet."}
              </div>
            </div>
          ) : (
            <>
              {searchQ && (
                <p className="font-syne text-xs text-ink-3 mb-3">{images.length} result{images.length !== 1 ? "s" : ""} for "{searchQ}"</p>
              )}
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
                {images.map(img => (
                  <ImageCard key={img.id} img={img} />
                ))}
              </div>
              {hasMore && !searchQ && (
                <div className="mt-6 text-center">
                  <button
                    onClick={() => loadImages(activeModality, false)}
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
