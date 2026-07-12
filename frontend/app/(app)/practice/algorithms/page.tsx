"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { API_URL } from "@/lib/api";
import { GitBranch, ChevronRight } from "lucide-react";

type Algorithm = {
  id: string;
  slug: string;
  title: string;
  specialty: string;
  description: string;
  tags: string[];
  is_veterinary: boolean;
};

const SPECIALTY_COLORS: Record<string, string> = {
  emergency:     "bg-red/10 text-red",
  cardiology:    "bg-blue-100 text-blue-700",
  neurology:     "bg-purple-100 text-purple-700",
  respiratory:   "bg-cyan-100 text-cyan-700",
  endocrinology: "bg-amber-100 text-amber-700",
  veterinary:    "bg-green/10 text-green",
};

function colorFor(specialty: string) {
  return SPECIALTY_COLORS[specialty] ?? "bg-surface-2 text-ink-3";
}

export default function AlgorithmsListPage() {
  const [algorithms, setAlgorithms] = useState<Algorithm[]>([]);
  const [loading, setLoading] = useState(true);
  const [vetOnly, setVetOnly] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    const url = `${API_URL}/practice/algorithms${vetOnly ? "?vet_only=true" : ""}`;
    fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((r) => r.ok ? r.json() : [])
      .then(setAlgorithms)
      .catch(() => setAlgorithms([]))
      .finally(() => setLoading(false));
  }, [vetOnly]);

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 space-y-5">

        <div className="flex items-center gap-3">
          <Link href="/practice" className="text-ink-3 hover:text-ink text-sm">← Practice</Link>
          <h1 className="font-syne font-black text-2xl text-ink flex items-center gap-2">
            <GitBranch size={20} /> Clinical Algorithms
          </h1>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => setVetOnly(false)}
            className={`px-3 py-1 rounded-full text-xs font-syne font-semibold border transition-all ${!vetOnly ? "bg-ink text-white border-ink" : "border-border text-ink-2 hover:border-ink-3"}`}
          >
            Human
          </button>
          <button
            onClick={() => setVetOnly(true)}
            className={`px-3 py-1 rounded-full text-xs font-syne font-semibold border transition-all ${vetOnly ? "bg-ink text-white border-ink" : "border-border text-ink-2 hover:border-ink-3"}`}
          >
            🐾 Veterinary
          </button>
        </div>

        {loading ? (
          <div className="space-y-3">
            {[1,2,3,4,5].map(i => (
              <div key={i} className="h-16 rounded-lg bg-surface-2 animate-pulse" />
            ))}
          </div>
        ) : algorithms.length === 0 ? (
          <div className="text-center py-12 font-serif text-ink-3 text-sm">
            No algorithms found.
          </div>
        ) : (
          <div className="card divide-y divide-border overflow-hidden">
            {algorithms.map((a) => (
              <Link
                key={a.slug}
                href={`/practice/algorithms/${a.slug}`}
                className="flex items-center gap-4 px-4 py-3.5 hover:bg-surface-2 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <div className="font-syne font-semibold text-sm text-ink">{a.title}</div>
                  {a.description && (
                    <p className="font-serif text-xs text-ink-3 truncate mt-0.5">{a.description}</p>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {a.specialty && (
                    <span className={`text-xs font-syne font-semibold px-2 py-0.5 rounded-full ${colorFor(a.specialty)}`}>
                      {a.specialty}
                    </span>
                  )}
                  <ChevronRight size={14} className="text-ink-3" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
