"use client";
import Link from "next/link";
import { useState } from "react";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { useRouter } from "next/navigation";

const PLANS = [
  {
    tier: "free",
    name: "Free",
    price: "$0",
    period: "forever",
    description: "Start learning with core modules",
    features: [
      "8 fundamental modules",
      "5 AI questions / day",
      "Basic flashcards",
      "Progress tracking",
    ],
    cta: "Start free",
    ctaHref: "/register",
    highlight: false,
  },
  {
    tier: "student",
    name: "Student",
    price: "$15",
    period: "/month",
    description: "Full access for medical students",
    features: [
      "All 82+ medical modules",
      "50 AI questions / day",
      "Spaced repetition flashcards",
      "Clinical case simulations",
      "PubMed search integration",
      "Progress analytics",
    ],
    cta: "Get Student",
    highlight: false,
  },
  {
    tier: "pro",
    name: "Pro",
    price: "$40",
    period: "/month",
    description: "For practicing physicians",
    features: [
      "Everything in Student",
      "Unlimited AI questions",
      "Drug database access",
      "Veterinary modules",
      "Advanced AI modes (Socratic, Exam)",
      "Priority support",
    ],
    cta: "Get Pro",
    highlight: true,
  },
  {
    tier: "clinic",
    name: "Clinic",
    price: "$199",
    period: "/month",
    description: "For teams & institutions",
    features: [
      "Up to 10 users",
      "Everything in Pro",
      "Team analytics dashboard",
      "Custom module upload",
      "Dedicated support",
      "SCORM export",
    ],
    cta: "Get Clinic",
    highlight: false,
  },
  {
    tier: "lifetime",
    name: "Lifetime",
    price: "$299",
    period: "one-time",
    description: "Unlimited access forever",
    features: [
      "Everything in Pro",
      "Lifetime updates",
      "Early access to new features",
      "Unlimited AI forever",
      "All future specialties",
    ],
    cta: "Buy Lifetime",
    highlight: false,
  },
];

export default function PricingPage() {
  const { isAuthenticated } = useAuthStore();
  const router = useRouter();
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

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
      {/* Nav */}
      <nav className="bg-surface border-b border-border sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
          <Link href="/" className="font-syne font-extrabold text-2xl tracking-tight text-ink">
            Med<span className="text-red">Mind</span>
          </Link>
          <div className="flex items-center gap-3">
            <Link href="/articles" className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-4 py-2">
              Articles
            </Link>
            {isAuthenticated ? (
              <Link href="/dashboard" className="font-syne font-semibold text-sm bg-ink text-white px-4 py-2 rounded hover:bg-red transition-colors">
                Dashboard →
              </Link>
            ) : (
              <>
                <Link href="/login" className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-4 py-2">
                  Sign in
                </Link>
                <Link href="/register" className="font-syne font-semibold text-sm bg-ink text-white px-4 py-2 rounded hover:bg-red transition-colors">
                  Start free
                </Link>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* Header */}
      <section className="max-w-6xl mx-auto px-6 pt-16 pb-10 text-center">
        <h1 className="font-syne font-extrabold text-4xl md:text-5xl text-ink tracking-tight mb-4">
          Simple, transparent pricing
        </h1>
        <p className="text-ink-2 text-lg max-w-xl mx-auto">
          Start free. Upgrade when you need more.
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
                Most popular
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
              {loading === plan.tier ? "Redirecting…" : plan.cta}
            </button>
          </div>
        ))}
      </section>

      {/* FAQ */}
      <section className="max-w-3xl mx-auto px-6 pb-20">
        <h2 className="font-syne font-extrabold text-2xl text-ink text-center mb-8">FAQ</h2>
        <div className="space-y-4">
          {[
            {
              q: "Can I cancel anytime?",
              a: "Yes. Cancel anytime from your settings. You keep access until the end of your billing period.",
            },
            {
              q: "What payment methods do you accept?",
              a: "All major credit/debit cards via Stripe. Apple Pay and Google Pay available on supported browsers.",
            },
            {
              q: "Is there a student discount?",
              a: "The Student plan at $15/mo is already our discounted tier. Contact us with your .edu email for additional discounts.",
            },
            {
              q: "What's included in veterinary modules?",
              a: "Pro and above includes species-specific pharmacology, physiology, and clinical cases for companion animals and livestock.",
            },
          ].map(({ q, a }) => (
            <div key={q} className="bg-surface border border-border rounded-lg p-5">
              <div className="font-syne font-bold text-sm text-ink mb-2">{q}</div>
              <div className="text-ink-2 text-sm">{a}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
