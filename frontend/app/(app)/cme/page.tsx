"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { contentApi } from "@/lib/api";

type CMECredit = {
  id: string;
  module_title: string;
  credits_earned: number;
  completion_date: string;
  certificate_url?: string;
};

type CMEData = {
  total_credits: number;
  credits_this_year: number;
  annual_goal: number;
  credits: CMECredit[];
};

function LinkedInShareButton({ certUrl, moduleTitle }: { certUrl: string; moduleTitle: string }) {
  const shareUrl = encodeURIComponent(certUrl || window.location.href);
  const title = encodeURIComponent(`I earned a CME certificate for "${moduleTitle}" on MedMind AI!`);
  const liUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${shareUrl}&title=${title}`;
  return (
    <a
      href={liUrl}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1.5 text-xs font-syne font-semibold text-blue-700 bg-blue-50 border border-blue-200 rounded px-2 py-1 hover:bg-blue-100 transition-colors"
    >
      <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
        <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
      </svg>
      Share on LinkedIn
    </a>
  );
}

export default function CMEPage() {
  const [data, setData] = useState<CMEData | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [toast, setToast] = useState<{ msg: string; ok: boolean } | null>(null);
  const [year, setYear] = useState(new Date().getFullYear());

  const showToast = (msg: string, ok = true) => {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 4000);
  };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await contentApi.getCMECredits(year);
      setData(res);
    } catch {
      showToast("Failed to load CME credits", false);
    } finally {
      setLoading(false);
    }
  }, [year]);

  useEffect(() => { load(); }, [load]);

  const handleDownload = async (credit: CMECredit) => {
    setDownloading(credit.id);
    try {
      const blob = await contentApi.downloadCMECertificate(credit.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `CME_Certificate_${credit.module_title.replace(/\s+/g, "_")}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      showToast("Certificate downloaded");
    } catch {
      showToast("Failed to generate certificate", false);
    } finally {
      setDownloading(null);
    }
  };

  const pct = data ? Math.min(((data.credits_this_year) / (data.annual_goal || 50)) * 100, 100) : 0;

  return (
    <div className="flex-1 overflow-y-auto p-6 max-w-3xl mx-auto">
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-2 rounded shadow font-syne font-semibold text-sm text-white animate-fade-up ${
          toast.ok ? "bg-green" : "bg-red"
        }`}>{toast.msg}</div>
      )}

      <div className="mb-6 flex items-center gap-3">
        <Link href="/dashboard" className="text-ink-3 hover:text-ink font-syne text-sm transition-colors">
          ← Dashboard
        </Link>
        <span className="text-border">|</span>
        <h1 className="font-syne font-black text-2xl text-ink">CME / CPD Credits</h1>
      </div>

      {loading ? (
        <div className="text-center py-20 text-ink-3 font-serif">Loading…</div>
      ) : (
        <>
          {/* Year selector + summary */}
          <div className="card p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="text-xs font-syne text-ink-3 uppercase tracking-widest mb-1">Annual Progress</div>
                <div className="font-syne font-black text-4xl text-ink">
                  {data?.credits_this_year ?? 0}
                  <span className="text-lg text-ink-3 ml-1">/ {data?.annual_goal ?? 50} credits</span>
                </div>
                <div className="text-sm font-serif text-ink-3 mt-1">
                  {data?.total_credits ?? 0} total credits earned · all time
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => setYear(y => y - 1)} className="w-8 h-8 rounded-full border border-border hover:bg-surface-2 flex items-center justify-center font-syne font-bold text-ink-3">‹</button>
                <span className="font-syne font-semibold text-ink w-12 text-center">{year}</span>
                <button onClick={() => setYear(y => y + 1)} disabled={year >= new Date().getFullYear()} className="w-8 h-8 rounded-full border border-border hover:bg-surface-2 disabled:opacity-30 flex items-center justify-center font-syne font-bold text-ink-3">›</button>
              </div>
            </div>
            <div className="h-3 bg-surface-2 rounded-full overflow-hidden">
              <div className="h-full bg-green rounded-full transition-all" style={{ width: `${pct}%` }} />
            </div>
            <div className="text-xs font-syne text-ink-3 mt-1">{Math.round(pct)}% of annual goal</div>
          </div>

          {/* Credits list */}
          <h2 className="font-syne font-bold text-base text-ink mb-3">Completed Modules</h2>
          {!data?.credits?.length ? (
            <div className="card p-12 text-center">
              <div className="text-4xl mb-3">🩺</div>
              <div className="font-syne font-bold text-ink mb-1">No CME credits yet</div>
              <div className="font-serif text-sm text-ink-3">Complete medical modules to earn CME/CPD credits</div>
              <Link href="/modules" className="mt-4 inline-block btn-primary text-sm px-4 py-2 rounded">Browse Modules</Link>
            </div>
          ) : (
            <div className="space-y-3">
              {data.credits.map((credit) => (
                <div key={credit.id} className="card p-4 flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-green-light border border-green/20 flex items-center justify-center flex-shrink-0">
                    <span className="text-lg">🎓</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-syne font-semibold text-sm text-ink truncate">{credit.module_title}</div>
                    <div className="text-xs font-serif text-ink-3 mt-0.5">
                      {new Date(credit.completion_date).toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" })}
                      {" · "}
                      <span className="text-green font-syne font-semibold">{credit.credits_earned} CME credit{credit.credits_earned !== 1 ? "s" : ""}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    {credit.certificate_url && (
                      <LinkedInShareButton certUrl={credit.certificate_url} moduleTitle={credit.module_title} />
                    )}
                    <button
                      onClick={() => handleDownload(credit)}
                      disabled={downloading === credit.id}
                      className="inline-flex items-center gap-1.5 text-xs font-syne font-semibold text-ink bg-surface border border-border rounded px-2 py-1 hover:bg-surface-2 transition-colors disabled:opacity-50"
                    >
                      {downloading === credit.id ? "Generating…" : "📄 Certificate"}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
