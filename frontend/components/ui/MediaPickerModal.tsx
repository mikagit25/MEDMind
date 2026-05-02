"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { imagingApi } from "@/lib/api";

type LibraryImage = {
  id: string;
  title: string;
  modality: string;
  anatomy_region: string | null;
  image_url: string;
  thumbnail_url: string | null;
  source_name: string;
  license: string | null;
  attribution: string | null;
  tags: string[];
};

type Modality = { modality: string; count: number };

interface Props {
  onSelect: (imageUrl: string, caption: string, imageId?: string) => void;
  onClose: () => void;
}

const MODALITY_LABELS: Record<string, string> = {
  xray: "X-Ray", ct: "CT", mri: "MRI", ultrasound: "Ultrasound",
  anatomy: "Anatomy", histology: "Histology", "3d": "3D", other: "Other",
};
const MODALITY_ICONS: Record<string, string> = {
  xray: "🩻", ct: "🔬", mri: "🧲", ultrasound: "〰️",
  anatomy: "🫀", histology: "🔭", "3d": "🧊", other: "📷",
};

export function MediaPickerModal({ onSelect, onClose }: Props) {
  const [images, setImages] = useState<LibraryImage[]>([]);
  const [modalities, setModalities] = useState<Modality[]>([]);
  const [activeModality, setActiveModality] = useState("");
  const [searchQ, setSearchQ] = useState("");
  const [loading, setLoading] = useState(true);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(async (modality: string, q?: string) => {
    setLoading(true);
    try {
      let data: LibraryImage[];
      if (q && q.trim().length >= 2) {
        data = await imagingApi.search(q.trim(), modality || undefined);
      } else {
        data = await imagingApi.browse({ modality: modality || undefined, limit: 48 });
      }
      setImages(data);
    } catch {
      setImages([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    Promise.all([
      imagingApi.modalities().then(setModalities),
      load(""),
    ]);
  }, [load]);

  function handleSearch(q: string) {
    setSearchQ(q);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => load(activeModality, q), 350);
  }

  function handleModalityChange(mod: string) {
    setActiveModality(mod);
    load(mod, searchQ);
  }

  function handleSelect(img: LibraryImage) {
    const caption = img.attribution
      ? `${img.title} — ${img.attribution}`
      : `${img.title} — ${img.source_name}`;
    onSelect(img.image_url, caption, img.id);
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="bg-white dark:bg-surface rounded-2xl shadow-2xl w-full max-w-3xl max-h-[85vh] flex flex-col overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
          <div>
            <h2 className="font-syne font-black text-base text-ink">Medical Image Library</h2>
            <p className="font-serif text-xs text-ink-3">Select an image to insert into your lesson</p>
          </div>
          <button onClick={onClose} className="text-ink-3 hover:text-ink text-lg leading-none px-2">✕</button>
        </div>

        {/* Search + filters */}
        <div className="px-4 py-2.5 border-b border-border shrink-0 space-y-2">
          <input
            type="search"
            value={searchQ}
            onChange={e => handleSearch(e.target.value)}
            placeholder="Search — pneumonia, brain MRI, anatomy..."
            autoFocus
            className="w-full border border-border rounded-lg px-3 py-2 font-serif text-sm text-ink bg-surface focus:outline-none focus:border-ink-3"
          />
          <div className="flex gap-1.5 overflow-x-auto pb-0.5">
            <button
              onClick={() => handleModalityChange("")}
              className={`shrink-0 px-3 py-1 rounded-full font-syne text-xs border transition-colors ${!activeModality ? "bg-ink text-white border-ink" : "border-border text-ink-3 hover:border-ink-3"}`}
            >
              All
            </button>
            {modalities.map(m => (
              <button
                key={m.modality}
                onClick={() => handleModalityChange(m.modality)}
                className={`shrink-0 flex items-center gap-1 px-3 py-1 rounded-full font-syne text-xs border transition-colors ${activeModality === m.modality ? "bg-ink text-white border-ink" : "border-border text-ink-3 hover:border-ink-3"}`}
              >
                <span>{MODALITY_ICONS[m.modality] ?? "📷"}</span>
                {MODALITY_LABELS[m.modality] ?? m.modality}
              </button>
            ))}
          </div>
        </div>

        {/* Grid */}
        <div className="flex-1 overflow-y-auto p-4">
          {loading ? (
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
              {Array.from({ length: 12 }).map((_, i) => (
                <div key={i} className="rounded-lg overflow-hidden animate-pulse">
                  <div className="aspect-[4/3] bg-surface" />
                  <div className="p-1.5 space-y-1">
                    <div className="h-2 bg-surface rounded w-3/4" />
                  </div>
                </div>
              ))}
            </div>
          ) : images.length === 0 ? (
            <div className="text-center py-12">
              <div className="text-4xl mb-2">🩻</div>
              <div className="font-syne font-semibold text-ink text-sm">No images found</div>
              <div className="font-serif text-xs text-ink-3 mt-1">
                Try a different search or modality filter
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
              {images.map(img => (
                <button
                  key={img.id}
                  onClick={() => handleSelect(img)}
                  className="rounded-xl overflow-hidden border border-border hover:border-ink hover:shadow-md transition-all text-left group"
                  title={img.title}
                >
                  <div className="aspect-[4/3] bg-surface overflow-hidden relative">
                    <img
                      src={img.thumbnail_url || img.image_url}
                      alt={img.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                      onError={e => {
                        (e.target as HTMLImageElement).style.display = "none";
                      }}
                    />
                    <div className="absolute inset-0 bg-ink/0 group-hover:bg-ink/5 transition-colors flex items-center justify-center">
                      <span className="opacity-0 group-hover:opacity-100 transition-opacity bg-ink text-white font-syne text-[10px] px-2 py-0.5 rounded-full">
                        Insert
                      </span>
                    </div>
                  </div>
                  <div className="p-1.5">
                    <div className="font-syne text-[10px] font-semibold text-ink line-clamp-1">{img.title}</div>
                    <div className="flex items-center justify-between mt-0.5">
                      <span className="font-serif text-[9px] text-ink-3">{img.source_name}</span>
                      {img.license && (
                        <span className="font-syne text-[9px] text-green">{img.license.replace("Public Domain", "PD")}</span>
                      )}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-2.5 border-t border-border bg-surface shrink-0">
          <p className="font-serif text-xs text-ink-3">
            All images are open-access with proper attribution. Attribution is automatically added to the caption.
          </p>
        </div>
      </div>
    </div>
  );
}
