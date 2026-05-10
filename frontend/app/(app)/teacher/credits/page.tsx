"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { creditsApi } from "@/lib/api";

type BalanceData = {
  balance: number;
  total_purchased: number;
  total_spent: number;
};

type Package = {
  id: string;
  credits: number;
  usd: number;
  label: string;
  bonus: string;
};

type PricingRow = {
  model: string;
  display_name: string;
  description: string;
  credits_per_article: number;
  usd_per_article: number;
};

type Transaction = {
  id: string;
  type: string;
  credits: number;
  usd_amount: number | null;
  model: string | null;
  description: string | null;
  created_at: string | null;
};

const TYPE_STYLE: Record<string, string> = {
  purchase: "text-green font-semibold",
  bonus:    "text-green font-semibold",
  spend:    "text-red",
  refund:   "text-green font-semibold",
};

const TYPE_SIGN: Record<string, string> = {
  purchase: "+",
  bonus:    "+",
  spend:    "-",
  refund:   "+",
};

export default function CreditsPage() {
  const [balance, setBalance] = useState<BalanceData | null>(null);
  const [packages, setPackages] = useState<Package[]>([]);
  const [pricing, setPricing] = useState<PricingRow[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [buying, setBuying] = useState<string | null>(null);
  const [toast, setToast] = useState<{ msg: string; type: "ok" | "err" } | null>(null);

  const showToast = (msg: string, type: "ok" | "err" = "ok") => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 4000);
  };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [bal, pkgs, price, txs] = await Promise.all([
        creditsApi.getBalance(),
        creditsApi.getPackages(),
        creditsApi.getPricing(),
        creditsApi.getTransactions(),
      ]);
      setBalance(bal);
      setPackages(pkgs);
      setPricing(price);
      setTransactions(txs);
    } catch {
      showToast("Failed to load credits data.", "err");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleBuy = async (pkgId: string) => {
    setBuying(pkgId);
    try {
      const result = await creditsApi.createCheckout(pkgId);
      if (result.coming_soon) {
        showToast("Payment processing coming soon! Stay tuned.", "ok");
      } else if (result.checkout_url) {
        window.location.href = result.checkout_url;
      }
    } catch {
      showToast("Failed to create checkout session.", "err");
    } finally {
      setBuying(null);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 max-w-4xl mx-auto">
      {/* Toast */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-2 rounded shadow font-syne font-semibold text-sm text-white animate-fade-up ${
          toast.type === "ok" ? "bg-green" : "bg-red"
        }`}>
          {toast.msg}
        </div>
      )}

      {/* Header */}
      <div className="mb-6 flex items-center gap-3">
        <Link href="/teacher/articles" className="text-ink-3 hover:text-ink font-syne text-sm transition-colors">
          ← My Articles
        </Link>
        <span className="text-border">|</span>
        <h1 className="font-syne font-black text-2xl text-ink">AI Credits</h1>
      </div>

      {loading ? (
        <div className="text-center py-20 text-ink-3 font-serif">Loading…</div>
      ) : (
        <>
          {/* Balance card */}
          <div className="card p-6 mb-8 flex items-center justify-between gap-6 flex-wrap">
            <div>
              <div className="text-xs font-syne text-ink-3 uppercase tracking-widest mb-1">Your Balance</div>
              <div className="text-5xl font-syne font-black text-ink">
                {balance?.balance ?? 0}
                <span className="text-xl font-semibold text-ink-3 ml-2">credits</span>
              </div>
              <div className="text-sm font-serif text-ink-3 mt-1">
                Purchased: {balance?.total_purchased ?? 0} &nbsp;·&nbsp; Spent: {balance?.total_spent ?? 0}
              </div>
            </div>
            <div className="text-right">
              <div className="text-xs font-syne text-ink-3 mb-1">1 credit = $0.01 USD</div>
              <div className="text-sm font-serif text-ink-2">Use credits to generate articles with AI</div>
            </div>
          </div>

          {/* AI Pricing */}
          <div className="mb-8">
            <h2 className="font-syne font-bold text-lg text-ink mb-3">Generation Costs</h2>
            <div className="card overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-surface-2">
                    <th className="text-left px-5 py-3 font-syne font-semibold text-xs text-ink-3 uppercase tracking-wider">Model</th>
                    <th className="text-left px-4 py-3 font-syne font-semibold text-xs text-ink-3 uppercase tracking-wider">Description</th>
                    <th className="text-right px-4 py-3 font-syne font-semibold text-xs text-ink-3 uppercase tracking-wider">Credits</th>
                    <th className="text-right px-5 py-3 font-syne font-semibold text-xs text-ink-3 uppercase tracking-wider">Cost (USD)</th>
                  </tr>
                </thead>
                <tbody>
                  {pricing.map((p) => (
                    <tr key={p.model} className={`border-t border-border hover:bg-surface-2 transition-colors ${p.credits_per_article === 0 ? "bg-green-light/20" : ""}`}>
                      <td className="px-5 py-3 font-syne font-bold text-ink">{p.display_name}</td>
                      <td className="px-4 py-3 font-serif text-ink-3 text-xs">{p.description}</td>
                      <td className="px-4 py-3 text-right font-syne font-bold">
                        {p.credits_per_article === 0
                          ? <span className="text-green">FREE</span>
                          : <span className="text-amber-700">{p.credits_per_article} cr</span>
                        }
                      </td>
                      <td className="px-5 py-3 text-right font-syne text-ink-3">
                        {p.credits_per_article === 0 ? "—" : `$${p.usd_per_article.toFixed(2)}`}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Purchase packages */}
          <div className="mb-8">
            <h2 className="font-syne font-bold text-lg text-ink mb-3">Buy Credits</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {packages.map((pkg) => (
                <div key={pkg.id} className={`card p-5 flex flex-col gap-3 border-2 transition-colors ${
                  pkg.id === "popular" ? "border-gold/60 bg-amber-50/40" : "border-border"
                }`}>
                  {pkg.id === "popular" && (
                    <div className="text-[10px] font-syne font-bold uppercase tracking-widest text-amber-700 bg-gold/20 rounded-full px-2 py-0.5 w-fit">
                      Most Popular
                    </div>
                  )}
                  <div>
                    <div className="font-syne font-black text-xl text-ink">{pkg.credits.toLocaleString()}</div>
                    <div className="text-xs font-syne text-ink-3">credits</div>
                  </div>
                  <div className="font-syne font-bold text-2xl text-ink">${pkg.usd.toFixed(2)}</div>
                  <div className="text-xs font-serif text-ink-3 flex-1">{pkg.bonus}</div>
                  <button
                    onClick={() => handleBuy(pkg.id)}
                    disabled={buying === pkg.id}
                    className={`w-full font-syne font-semibold text-sm py-2 rounded-lg transition-colors ${
                      pkg.id === "popular"
                        ? "bg-gold/80 hover:bg-gold text-ink"
                        : "bg-ink text-white hover:bg-ink-2"
                    } disabled:opacity-50`}
                  >
                    {buying === pkg.id ? "…" : "Buy"}
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* How it works */}
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200/50 rounded-xl p-5 mb-8">
            <h2 className="font-syne font-bold text-base text-ink mb-3">How Credits Work</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div className="bg-green-light border border-green/20 rounded-xl p-4">
                <div className="font-syne font-bold text-sm text-green mb-1">🆓 Ollama — Always Free</div>
                <div className="text-xs font-serif text-ink-2">Generate unlimited articles using our local AI server. No credits needed. Article is ready in ~2–3 minutes and automatically translated to 7 languages.</div>
              </div>
              <div className="bg-amber-light/40 border border-amber/20 rounded-xl p-4">
                <div className="font-syne font-bold text-sm text-amber-800 mb-1">⚡ Claude — Paid (Better Quality)</div>
                <div className="text-xs font-serif text-ink-2">When you buy credits, we transfer your payment directly to the Anthropic API. Your credits = actual Claude API budget. Haiku: 1 credit, Sonnet: 5 credits.</div>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[
                { step: "1", title: "Buy Credits (optional)", desc: "Purchase only if you want Claude quality. 1 credit = $0.01, paid directly to Anthropic API on your behalf." },
                { step: "2", title: "Generate Article", desc: "Choose Ollama (free) or Claude (credits). Article auto-published after admin review, translated to 7 languages." },
                { step: "3", title: "Earn Revenue", desc: "Published articles earn 40% of ad revenue — RPM ~$2.00 per 1,000 views. Payouts monthly, min $10." },
              ].map((s) => (
                <div key={s.step} className="flex gap-3">
                  <div className="w-7 h-7 rounded-full bg-ink text-white font-syne font-bold text-xs flex items-center justify-center flex-shrink-0">
                    {s.step}
                  </div>
                  <div>
                    <div className="font-syne font-semibold text-sm text-ink">{s.title}</div>
                    <div className="text-xs font-serif text-ink-3 mt-0.5">{s.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Transaction history */}
          <div>
            <h2 className="font-syne font-bold text-lg text-ink mb-3">Transaction History</h2>
            {transactions.length === 0 ? (
              <div className="card p-8 text-center text-ink-3 font-serif text-sm">No transactions yet.</div>
            ) : (
              <div className="card overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border bg-surface-2">
                        <th className="text-left px-5 py-3 font-syne font-semibold text-xs text-ink-3 uppercase tracking-wider">Date</th>
                        <th className="text-left px-4 py-3 font-syne font-semibold text-xs text-ink-3 uppercase tracking-wider">Description</th>
                        <th className="text-left px-4 py-3 font-syne font-semibold text-xs text-ink-3 uppercase tracking-wider">Type</th>
                        <th className="text-right px-5 py-3 font-syne font-semibold text-xs text-ink-3 uppercase tracking-wider">Credits</th>
                      </tr>
                    </thead>
                    <tbody>
                      {transactions.map((tx) => (
                        <tr key={tx.id} className="border-t border-border hover:bg-surface-2 transition-colors">
                          <td className="px-5 py-3 text-xs font-serif text-ink-3 whitespace-nowrap">
                            {tx.created_at ? new Date(tx.created_at).toLocaleDateString("en-US", {
                              month: "short", day: "numeric", year: "numeric"
                            }) : "—"}
                          </td>
                          <td className="px-4 py-3 font-serif text-ink-2 text-xs max-w-[280px] truncate">
                            {tx.description ?? tx.type}
                            {tx.model && <span className="ml-1 text-ink-3">({tx.model})</span>}
                          </td>
                          <td className="px-4 py-3">
                            <span className={`text-xs font-syne font-semibold capitalize ${TYPE_STYLE[tx.type] ?? ""}`}>
                              {tx.type}
                            </span>
                          </td>
                          <td className={`px-5 py-3 text-right font-syne font-bold ${TYPE_STYLE[tx.type] ?? "text-ink"}`}>
                            {TYPE_SIGN[tx.type] ?? ""}{tx.credits}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
