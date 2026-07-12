"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { API_URL } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────
type DauPoint  = { date: string; dau: number };
type WauPoint  = { week: string; wau: number };
type Cohort    = { week: string; size: number; d1_pct: number; d7_pct: number; d30_pct: number };
type Funnel    = { step: string; count: number };
type Abandoned = { module_id: string; title: string; started: number; completed: number; abandoned_pct: number };

type Overview = {
  dau_series: DauPoint[];
  wau_series: WauPoint[];
  mau_series: { month: string; mau: number }[];
  cohorts: Cohort[];
  funnel: Funnel[];
  abandoned_modules: Abandoned[];
};

// ── Helpers ───────────────────────────────────────────────────────────────────
function pctColor(pct: number): string {
  if (pct >= 40) return "bg-green text-white";
  if (pct >= 20) return "bg-amber-400 text-black";
  if (pct >= 10) return "bg-orange-400 text-white";
  return "bg-red text-white";
}

function Skeleton({ h = "h-4", w = "w-full" }: { h?: string; w?: string }) {
  return <div className={`${h} ${w} rounded animate-pulse bg-surface-2`} />;
}

// ── Sparkline (inline SVG, no deps) ──────────────────────────────────────────
function Sparkline({ data, color = "#1a1814" }: { data: number[]; color?: string }) {
  if (data.length < 2) return null;
  const max = Math.max(...data) || 1;
  const w = 120, h = 36, pad = 2;
  const pts = data.map((v, i) => {
    const x = pad + (i / (data.length - 1)) * (w - 2 * pad);
    const y = pad + (1 - v / max) * (h - 2 * pad);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="block">
      <polyline points={pts} fill="none" stroke={color} strokeWidth={1.5} strokeLinejoin="round" />
    </svg>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function AdminAnalyticsPage() {
  const [data, setData] = useState<Overview | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    fetch(`${API_URL}/admin/analytics/overview`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => r.ok ? r.json() : Promise.reject(r.status))
      .then(setData)
      .catch(() => setError(true));
  }, []);

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center flex-col gap-3 p-8 text-center">
        <div className="text-3xl">⚠️</div>
        <p className="font-serif text-ink-3">Failed to load analytics. Admin access required.</p>
        <Link href="/admin" className="btn-secondary text-sm px-4 py-1.5">← Back to Admin</Link>
      </div>
    );
  }

  const dau = data?.dau_series ?? [];
  const dauValues = dau.map((d) => d.dau);
  const latestDau = dauValues[dauValues.length - 1] ?? 0;
  const latestWau = (data?.wau_series ?? []).at(-1)?.wau ?? 0;
  const latestMau = (data?.mau_series ?? []).at(-1)?.mau ?? 0;

  const funnel = data?.funnel ?? [];
  const funnelMax = Math.max(...funnel.map((f) => f.count), 1);

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 space-y-8">

        {/* Header */}
        <div className="flex items-center gap-3">
          <Link href="/admin" className="text-ink-3 hover:text-ink text-sm">← Admin</Link>
          <h1 className="font-syne font-black text-2xl text-ink">Product Analytics</h1>
          <span className="text-xs font-syne text-ink-3 bg-surface-2 border border-border px-2 py-0.5 rounded-full">
            self-hosted · GDPR-safe
          </span>
        </div>

        {/* ── DAU/WAU/MAU ── */}
        <section>
          <h2 className="font-syne font-bold text-base text-ink mb-4">Active Users (last 90 days)</h2>
          <div className="grid grid-cols-3 gap-4">
            {[
              { label: "DAU", val: latestDau, series: dauValues, color: "#1a1814" },
              { label: "WAU", val: latestWau, series: (data?.wau_series ?? []).map(d => d.wau), color: "#2563eb" },
              { label: "MAU", val: latestMau, series: (data?.mau_series ?? []).map(d => d.mau), color: "#16a34a" },
            ].map(({ label, val, series, color }) => (
              <div key={label} className="card p-4">
                {!data ? (
                  <div className="space-y-2"><Skeleton h="h-8" w="w-16" /><Skeleton h="h-9" /></div>
                ) : (
                  <>
                    <div className="font-syne font-black text-3xl text-ink">{val.toLocaleString()}</div>
                    <div className="text-ink-3 text-xs font-syne mb-2">{label} (latest period)</div>
                    <Sparkline data={series} color={color} />
                  </>
                )}
              </div>
            ))}
          </div>
        </section>

        {/* ── Cohort retention heatmap ── */}
        <section>
          <h2 className="font-syne font-bold text-base text-ink mb-4">Cohort Retention (D1 / D7 / D30)</h2>
          <div className="card overflow-x-auto">
            <table className="w-full text-sm font-syne">
              <thead>
                <tr className="border-b border-border text-ink-3 text-xs uppercase tracking-wide">
                  <th className="text-left p-3">Cohort week</th>
                  <th className="p-3">Size</th>
                  <th className="p-3">D1</th>
                  <th className="p-3">D7</th>
                  <th className="p-3">D30</th>
                </tr>
              </thead>
              <tbody>
                {!data ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i} className="border-b border-border">
                      {Array.from({ length: 5 }).map((_, j) => (
                        <td key={j} className="p-3"><Skeleton /></td>
                      ))}
                    </tr>
                  ))
                ) : data.cohorts.length === 0 ? (
                  <tr><td colSpan={5} className="p-6 text-center text-ink-3 font-serif text-sm">No cohort data yet — events will appear here within 24h of first signups.</td></tr>
                ) : (
                  data.cohorts.map((c) => (
                    <tr key={c.week} className="border-b border-border hover:bg-surface-2 transition-colors">
                      <td className="p-3 font-mono text-xs">{c.week}</td>
                      <td className="p-3 text-center text-ink-2">{c.size.toLocaleString()}</td>
                      <td className="p-3 text-center">
                        <span className={`inline-block px-2 py-0.5 rounded text-xs font-bold ${pctColor(c.d1_pct)}`}>{c.d1_pct}%</span>
                      </td>
                      <td className="p-3 text-center">
                        <span className={`inline-block px-2 py-0.5 rounded text-xs font-bold ${pctColor(c.d7_pct)}`}>{c.d7_pct}%</span>
                      </td>
                      <td className="p-3 text-center">
                        <span className={`inline-block px-2 py-0.5 rounded text-xs font-bold ${pctColor(c.d30_pct)}`}>{c.d30_pct}%</span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

        {/* ── Onboarding funnel ── */}
        <section>
          <h2 className="font-syne font-bold text-base text-ink mb-4">Onboarding Funnel (last 30 days)</h2>
          <div className="card p-4 space-y-3">
            {!data ? (
              Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} h="h-8" />)
            ) : funnel.map((f, i) => {
              const pct = funnelMax > 0 ? Math.round((f.count / funnelMax) * 100) : 0;
              const prev = i > 0 ? funnel[i - 1].count : f.count;
              const cvr = prev > 0 ? Math.round((f.count / prev) * 100) : 100;
              return (
                <div key={f.step}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-syne text-xs text-ink-2">{f.step}</span>
                    <div className="flex gap-3 text-xs font-syne">
                      <span className="text-ink font-bold">{f.count.toLocaleString()}</span>
                      {i > 0 && <span className="text-ink-3">→ {cvr}% from prev</span>}
                    </div>
                  </div>
                  <div className="h-2 bg-surface-2 rounded-full overflow-hidden">
                    <div className="h-full bg-ink rounded-full transition-all" style={{ width: `${pct}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* ── Abandoned modules ── */}
        <section>
          <h2 className="font-syne font-bold text-base text-ink mb-4">Top Abandoned Modules (last 30 days)</h2>
          <div className="card overflow-x-auto">
            <table className="w-full text-sm font-syne">
              <thead>
                <tr className="border-b border-border text-ink-3 text-xs uppercase tracking-wide">
                  <th className="text-left p-3">Module</th>
                  <th className="p-3">Started</th>
                  <th className="p-3">Completed</th>
                  <th className="p-3">Abandoned</th>
                </tr>
              </thead>
              <tbody>
                {!data ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i} className="border-b border-border">
                      {Array.from({ length: 4 }).map((_, j) => (
                        <td key={j} className="p-3"><Skeleton /></td>
                      ))}
                    </tr>
                  ))
                ) : data.abandoned_modules.length === 0 ? (
                  <tr><td colSpan={4} className="p-6 text-center text-ink-3 font-serif text-sm">No data yet — track module_started events for 30 days to see this report.</td></tr>
                ) : (
                  data.abandoned_modules.map((m) => (
                    <tr key={m.module_id} className="border-b border-border hover:bg-surface-2 transition-colors">
                      <td className="p-3 max-w-xs truncate text-ink-2">{m.title}</td>
                      <td className="p-3 text-center">{m.started}</td>
                      <td className="p-3 text-center text-green font-semibold">{m.completed}</td>
                      <td className="p-3 text-center">
                        <span className={`inline-block px-2 py-0.5 rounded text-xs font-bold ${m.abandoned_pct > 60 ? "bg-red text-white" : m.abandoned_pct > 30 ? "bg-amber-400 text-black" : "bg-surface-2 text-ink-2"}`}>
                          {m.abandoned_pct}%
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>

      </div>
    </div>
  );
}
