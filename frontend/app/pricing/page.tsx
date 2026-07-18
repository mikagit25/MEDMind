"use client";
import Link from "next/link";
import { useState } from "react";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { useRouter } from "next/navigation";
import { useT } from "@/lib/i18n";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { Gift, CheckCircle2, XCircle, ChevronDown, Loader2 } from "lucide-react";

type PlanData = {
  name: string; price: string; period: string; description: string;
  features: string[]; cta: string; highlight: boolean; tier: string;
};
type FaqItem = { q: string; a: string };

export default function PricingPage() {
  const t = useT();
  const { isAuthenticated } = useAuthStore();
  const router = useRouter();
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Promo code widget state
  const [promoOpen, setPromoOpen] = useState(false);
  const [promoCode, setPromoCode] = useState("");
  const [promoLoading, setPromoLoading] = useState(false);
  const [promoResult, setPromoResult] = useState<{ type: string; tier?: string; expires_at?: string; message: string } | null>(null);
  const [promoError, setPromoError] = useState<string | null>(null);

  async function handlePromoApply(e: React.FormEvent) {
    e.preventDefault();
    if (!promoCode.trim()) return;
    if (!isAuthenticated) { router.push("/login"); return; }
    setPromoLoading(true);
    setPromoError(null);
    setPromoResult(null);
    try {
      const res = await api.post("/promo/apply", { code: promoCode.trim() });
      setPromoResult(res.data);
      // subscription tier will refresh on next /auth/me call (navigation)
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setPromoError(msg || "Invalid or expired code.");
    } finally {
      setPromoLoading(false);
    }
  }

  const PLANS = t("pricing_page.plans") as unknown as PlanData[];
  const FAQ = t("pricing_page.faq") as unknown as FaqItem[];

  async function handleBuy(tier: string) {
    if (tier === "free") {
      router.push("/register");
      return;
    }
    if (!isAuthenticated) {
      router.push("/register");
      return;
    }
    setLoading(tier);
    setError(null);
    try {
      const res = await api.post("/payments/checkout", {
        tier,
        success_url: `${window.location.origin}/settings?payment=success`,
        cancel_url: `${window.location.origin}/pricing`,
      });
      window.location.href = res.data.url;
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg || "Payment unavailable. Add STRIPE_SECRET_KEY to backend .env");
      setLoading(null);
    }
  }

  return (
    <div className="min-h-screen bg-bg">
      <ArticleNav />

      {/* Header */}
      <section className="max-w-6xl mx-auto px-6 pt-16 pb-10 text-center">
        <h1 className="font-syne font-extrabold text-4xl md:text-5xl text-ink tracking-tight mb-4">
          {t("pricing_page.title")}
        </h1>
        <p className="text-ink-2 text-lg max-w-xl mx-auto">
          {t("pricing_page.subtitle")}
        </p>
      </section>

      {/* Error banner */}
      {error && (
        <div className="max-w-6xl mx-auto px-6 mb-6">
          <div className="bg-red/10 border border-red/30 text-red rounded-lg px-4 py-3 text-sm font-syne">
            {error}
          </div>
        </div>
      )}

      {/* Plans grid */}
      <section className="max-w-6xl mx-auto px-6 pb-20 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
        {PLANS.map((plan) => (
          <div
            key={plan.tier}
            className={`bg-surface rounded-xl border p-6 flex flex-col relative ${
              plan.highlight
                ? "border-ink shadow-lg ring-2 ring-ink/10"
                : "border-border"
            }`}
          >
            {plan.highlight && (
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-ink text-white font-syne font-bold text-xs px-3 py-1 rounded-full">
                {t("pricing_page.most_popular")}
              </div>
            )}
            <div className="mb-4">
              <div className="font-syne font-extrabold text-lg text-ink">{plan.name}</div>
              <div className="flex items-baseline gap-1 mt-1">
                <span className="font-syne font-black text-3xl text-ink">{plan.price}</span>
                <span className="text-ink-3 text-sm font-syne">{plan.period}</span>
              </div>
              <p className="text-ink-3 text-xs mt-1 font-syne">{plan.description}</p>
            </div>

            <ul className="flex-1 space-y-2 mb-6">
              {plan.features.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm text-ink-2">
                  <span className="text-green-2 mt-0.5 flex-shrink-0">✓</span>
                  <span>{f}</span>
                </li>
              ))}
            </ul>

            <button
              onClick={() => handleBuy(plan.tier)}
              disabled={loading === plan.tier}
              className={`w-full font-syne font-bold text-sm py-2.5 rounded transition-colors ${
                plan.highlight
                  ? "bg-ink text-white hover:bg-red"
                  : "border border-border-2 text-ink-2 hover:border-ink hover:text-ink bg-transparent"
              } disabled:opacity-50 disabled:cursor-wait`}
            >
              {loading === plan.tier ? t("pricing_page.redirecting") : plan.cta}
            </button>
          </div>
        ))}
      </section>

      {/* FAQ */}
      <section className="max-w-3xl mx-auto px-6 pb-16">
        <h2 className="font-syne font-extrabold text-2xl text-ink text-center mb-8">{t("pricing_page.faq_title")}</h2>
        <div className="space-y-4">
          {FAQ.map(({ q, a }) => (
            <div key={q} className="bg-surface border border-border rounded-lg p-5">
              <div className="font-syne font-bold text-sm text-ink mb-2">{q}</div>
              <div className="text-ink-2 text-sm">{a}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Promo code widget */}
      <section className="max-w-md mx-auto px-6 pb-12">
        <button
          onClick={() => setPromoOpen(o => !o)}
          className="w-full flex items-center justify-center gap-2 text-sm font-syne text-ink-3 hover:text-ink transition-colors"
        >
          <Gift className="w-4 h-4" />
          Have a promo code?
          <ChevronDown className={`w-4 h-4 transition-transform ${promoOpen ? "rotate-180" : ""}`} />
        </button>
        {promoOpen && (
          <div className="mt-4 bg-surface border border-border rounded-xl p-5">
            {promoResult ? (
              <div className="flex items-center gap-3">
                <CheckCircle2 className="w-5 h-5 text-green flex-shrink-0" />
                <div>
                  <div className="font-syne font-bold text-sm text-ink">
                    {promoResult.type === "trial" && promoResult.tier
                      ? `${promoResult.tier.charAt(0).toUpperCase() + promoResult.tier.slice(1)} access activated!`
                      : promoResult.message}
                  </div>
                  {promoResult.expires_at && (
                    <div className="text-xs font-serif text-ink-3 mt-0.5">
                      Valid until {new Date(promoResult.expires_at).toLocaleDateString()}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <form onSubmit={handlePromoApply} className="flex gap-2">
                <input
                  value={promoCode}
                  onChange={e => setPromoCode(e.target.value.toUpperCase())}
                  placeholder="ENTER CODE"
                  className="flex-1 bg-bg border border-border rounded-lg px-3 py-2 font-mono text-sm text-ink tracking-widest focus:outline-none focus:border-ink transition-colors uppercase"
                  disabled={promoLoading}
                />
                <button
                  type="submit"
                  disabled={promoLoading || !promoCode.trim()}
                  className="font-syne font-bold text-xs bg-ink text-white px-4 py-2 rounded-lg hover:bg-red transition-colors disabled:opacity-40 flex items-center gap-1.5"
                >
                  {promoLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
                  Apply
                </button>
              </form>
            )}
            {promoError && (
              <div className="mt-2 flex items-center gap-2 text-red text-xs font-serif">
                <XCircle className="w-3.5 h-3.5" /> {promoError}
              </div>
            )}
          </div>
        )}
      </section>

      {/* Enterprise / Teams callout */}
      <section className="max-w-6xl mx-auto px-6 pb-20">
        <div className="bg-ink text-white rounded-2xl p-8 md:p-12 flex flex-col md:flex-row items-center gap-10">
          <div className="flex-1 min-w-0">
            <div className="font-syne font-bold text-xs uppercase tracking-widest text-white/50 mb-3">
              For organisations
            </div>
            <h2 className="font-syne font-extrabold text-2xl md:text-3xl text-white mb-3 leading-tight">
              Need a plan for your whole team?
            </h2>
            <p className="text-white/70 text-sm leading-relaxed mb-5">
              MedMind Enterprise is built for veterinary companies, clinics, universities, and medical associations. Team dashboard, admin controls, progress reporting, and dedicated onboarding — from&nbsp;$149/month.
            </p>
            <div className="flex flex-col sm:flex-row gap-2.5 text-xs text-white/60 mb-7">
              <span className="flex items-center gap-1.5"><span className="text-green-2 font-bold">✓</span> Starter — up to 25 users · $149/mo</span>
              <span className="hidden sm:block text-white/20">·</span>
              <span className="flex items-center gap-1.5"><span className="text-green-2 font-bold">✓</span> Business — up to 100 users · $349/mo</span>
              <span className="hidden sm:block text-white/20">·</span>
              <span className="flex items-center gap-1.5"><span className="text-green-2 font-bold">✓</span> Enterprise — 100+ · Custom pricing</span>
            </div>
            <div className="flex flex-col sm:flex-row gap-3">
              <Link
                href="/enterprise#demo-form"
                className="bg-white text-ink font-syne font-bold text-sm px-6 py-3 rounded-lg hover:bg-red hover:text-white transition-colors whitespace-nowrap text-center"
              >
                Request a demo →
              </Link>
              <Link
                href="/enterprise"
                className="border border-white/30 text-white/80 font-syne font-semibold text-sm px-6 py-3 rounded-lg hover:border-white hover:text-white transition-colors whitespace-nowrap text-center"
              >
                See team plans
              </Link>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3 shrink-0 w-full md:w-64">
            {([
              ["🐾", "Vet companies"],
              ["🏥", "Clinics & hospitals"],
              ["🎓", "Universities"],
              ["🤝", "Associations"],
            ] as [string, string][]).map(([icon, label]) => (
              <div key={label} className="bg-white/10 rounded-xl px-4 py-4 text-center">
                <div className="text-2xl mb-1.5">{icon}</div>
                <div className="font-syne font-semibold text-xs text-white/80 leading-tight">{label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
