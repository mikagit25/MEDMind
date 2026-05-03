"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/store";
import Link from "next/link";
import { useT } from "@/lib/i18n";

export default function RootPage() {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const t = useT();

  useEffect(() => {
    if (isAuthenticated) {
      router.replace("/dashboard");
    }
  }, [isAuthenticated, router]);

  if (isAuthenticated) {
    return (
      <div className="min-h-screen bg-bg flex items-center justify-center">
        <div className="font-syne text-ink-3 text-sm animate-pulse">Loading…</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bg">
      {/* Navigation */}
      <nav className="bg-surface border-b border-border sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="font-syne font-extrabold text-2xl tracking-tight text-ink">
            Med<span className="text-red">Mind</span>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/how-it-works"
              className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-4 py-2"
            >
              How it works
            </Link>
            <Link
              href="/articles"
              className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-4 py-2"
            >
              Articles
            </Link>
            <Link
              href="/pricing"
              className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-4 py-2"
            >
              Pricing
            </Link>
            <Link
              href="/login"
              className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-4 py-2"
            >
              Sign in
            </Link>
            <Link
              href="/register"
              className="font-syne font-semibold text-sm bg-ink text-white px-4 py-2 rounded hover:bg-red transition-colors"
            >
              Start free
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-6 pt-20 pb-16 text-center">
        <div className="inline-flex items-center gap-2 bg-surface border border-border px-3 py-1.5 rounded-full font-syne font-semibold text-xs text-ink-2 mb-8">
          <span className="w-2 h-2 rounded-full bg-green-2 animate-pulse inline-block"></span>
          {t("landing.hero_badge")}
        </div>
        <h1 className="font-syne font-extrabold text-5xl md:text-6xl text-ink leading-tight tracking-tight mb-6">
          Medical education<br />
          <span className="text-red">reimagined with AI</span>
        </h1>
        <p className="text-ink-2 text-lg md:text-xl max-w-2xl mx-auto leading-relaxed mb-10">
          Evidence-based AI tutor with real-time PubMed integration. Spaced repetition flashcards, 
          clinical case simulations, and adaptive learning — for doctors, residents, and students.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link
            href="/register"
            className="font-syne font-bold text-base bg-ink text-white px-8 py-3.5 rounded hover:bg-red transition-colors"
          >
            Start learning free →
          </Link>
          <Link
            href="/login"
            className="font-syne font-semibold text-base border border-border-2 text-ink-2 px-8 py-3.5 rounded hover:border-ink hover:text-ink transition-colors"
          >
            Sign in
          </Link>
        </div>
        <p className="text-ink-3 text-xs mt-4 font-syne">
          {t("landing.hero_note")}
        </p>
      </section>

      {/* Stats Bar */}
      <section className="border-y border-border bg-surface">
        <div className="max-w-6xl mx-auto px-6 py-6 grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
          {[
            { val: "82+", label: "Clinical modules" },
            { val: "6", label: "Specialties" },
            { val: "500+", label: "Flashcards" },
            { val: "Real-time", label: "PubMed search" },
          ].map((s) => (
            <div key={s.label}>
              <div className="font-syne font-extrabold text-2xl text-ink">{s.val}</div>
              <div className="text-ink-3 text-xs font-syne uppercase tracking-widest mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-6 py-20">
        <h2 className="font-syne font-bold text-3xl text-ink text-center mb-3">
          Everything you need to excel
        </h2>
        <p className="text-ink-3 text-center mb-12 text-sm">{t("landing.features_subtitle")}</p>
        <div className="grid md:grid-cols-3 gap-6">
          {[
            {
              icon: "🧠",
              title: "AI Medical Tutor",
              desc: "Four learning modes: Tutor, Socratic, Case-based, and Exam Prep. Each answer backed by real PubMed citations.",
              color: "red",
            },
            {
              icon: "📇",
              title: "Spaced Repetition",
              desc: "SM-2 algorithm schedules flashcard reviews at optimal intervals. Study smarter, retain longer.",
              color: "blue",
            },
            {
              icon: "🩺",
              title: "Clinical Cases",
              desc: "Interactive patient simulations with vitals, labs, and decision trees. Present cases like a pro.",
              color: "green",
            },
            {
              icon: "📚",
              title: "82 Expert Modules",
              desc: "Cardiology, Neurology, Surgery, Pediatrics, OB/GYN, Therapy — all with lessons, MCQs, and cases.",
              color: "amber",
            },
            {
              icon: "🔬",
              title: "PubMed Live Search",
              desc: "Every AI answer searches PubMed in real-time and cites the latest evidence. Always up-to-date.",
              color: "blue",
            },
            {
              icon: "🐾",
              title: "Veterinary Mode",
              desc: "Dedicated veterinary content with species-specific dosing and protocols. Coming in Pro tier.",
              color: "green",
            },
          ].map((f) => (
            <div
              key={f.title}
              className="bg-surface border border-border rounded-lg p-6 hover:border-border-2 transition-colors"
            >
              <div className="text-3xl mb-4">{f.icon}</div>
              <h3 className="font-syne font-bold text-base text-ink mb-2">{f.title}</h3>
              <p className="text-ink-3 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <h2 className="font-syne font-bold text-3xl text-ink text-center mb-3">
            Simple, transparent pricing
          </h2>
          <p className="text-ink-3 text-center mb-12 text-sm">Start free, upgrade when you need more</p>
          <div className="grid md:grid-cols-4 gap-5">
            {[
              {
                name: "Free",
                price: "$0",
                period: "forever",
                features: ["8 base modules", "5 AI questions/day", "Basic flashcards", "Community support"],
                cta: "Get started",
                highlight: false,
              },
              {
                name: "Student",
                price: "$15",
                period: "/month",
                features: ["All 82+ modules", "50 AI questions/day", "Full flashcards + SM-2", "PubMed citations"],
                cta: "Start Student",
                highlight: false,
              },
              {
                name: "Pro",
                price: "$40",
                period: "/month",
                features: ["Everything in Student", "Unlimited AI questions", "Veterinary content", "Drug database", "Priority support"],
                cta: "Start Pro",
                highlight: true,
              },
              {
                name: "Lifetime",
                price: "$299",
                period: "one-time",
                features: ["Everything in Pro", "All future modules", "Lifetime updates", "No recurring fee"],
                cta: "Get Lifetime",
                highlight: false,
              },
            ].map((p) => (
              <div
                key={p.name}
                className={`rounded-lg p-6 border ${
                  p.highlight
                    ? "border-red bg-red-light"
                    : "border-border bg-bg"
                }`}
              >
                {p.highlight && (
                  <div className="font-syne font-bold text-xs text-red uppercase tracking-widest mb-3">
                    Most Popular
                  </div>
                )}
                <div className="font-syne font-extrabold text-xl text-ink mb-1">{p.name}</div>
                <div className="flex items-baseline gap-1 mb-4">
                  <span className="font-syne font-bold text-3xl text-ink">{p.price}</span>
                  <span className="text-ink-3 text-sm">{p.period}</span>
                </div>
                <ul className="space-y-2 mb-6">
                  {p.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-ink-2">
                      <span className="text-green-2 mt-0.5">✓</span>
                      {f}
                    </li>
                  ))}
                </ul>
                <Link
                  href="/register"
                  className={`block text-center font-syne font-semibold text-sm py-2.5 rounded transition-colors ${
                    p.highlight
                      ? "bg-ink text-white hover:bg-red"
                      : "border border-border-2 text-ink-2 hover:border-ink hover:text-ink"
                  }`}
                >
                  {p.cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Specialties */}
      <section className="max-w-6xl mx-auto px-6 py-20">
        <h2 className="font-syne font-bold text-3xl text-ink text-center mb-3">
          Six core specialties
        </h2>
        <p className="text-ink-3 text-center mb-12 text-sm">82+ modules covering the full medical curriculum</p>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {[
            { icon: "❤️", name: "Cardiology", count: 10, article: "cardiology" },
            { icon: "🧠", name: "Neurology", count: 10, article: "neurology" },
            { icon: "🔪", name: "Surgery", count: 10, article: "surgery" },
            { icon: "👶", name: "Pediatrics", count: 11, article: "pediatrics" },
            { icon: "🤰", name: "OB/GYN", count: 9, article: null },
            { icon: "💊", name: "Therapy", count: 12, article: null },
          ].map((s) => (
            <Link
              key={s.name}
              href={s.article ? `/articles/category/${s.article}` : "/register"}
              className="bg-surface border border-border rounded-lg p-4 text-center hover:border-border-2 hover:shadow-sm transition-all"
            >
              <div className="text-2xl mb-2">{s.icon}</div>
              <div className="font-syne font-bold text-sm text-ink">{s.name}</div>
              <div className="text-ink-3 text-xs mt-1">{s.count} modules</div>
            </Link>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="bg-ink text-white">
        <div className="max-w-3xl mx-auto px-6 py-20 text-center">
          <h2 className="font-syne font-extrabold text-4xl mb-4">
            Ready to learn smarter?
          </h2>
          <p className="text-white/60 mb-8 text-base leading-relaxed">
            Join thousands of medical students and residents using MedMind AI to prepare for exams, 
            master clinical skills, and stay current with evidence-based medicine.
          </p>
          <Link
            href="/register"
            className="inline-block font-syne font-bold text-base bg-white text-ink px-10 py-4 rounded hover:bg-red hover:text-white transition-colors"
          >
            Create free account →
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border bg-surface">
        <div className="max-w-6xl mx-auto px-6 py-8 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="font-syne font-extrabold text-lg text-ink">
            Med<span className="text-red">Mind</span>
            <span className="font-normal text-ink-3 text-xs ml-2">AI Education Platform</span>
          </div>
          <div className="flex gap-6 flex-wrap justify-center">
            <Link href="/how-it-works" className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">{t("landing.how_it_works")}</Link>
            <Link href="/articles" className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">Articles</Link>
            <Link href="/pricing" className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">Pricing</Link>
            <Link href="/investors" className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">Investors</Link>
            <Link href="/register" className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">Register</Link>
            <Link href="/login" className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">Login</Link>
          </div>
          <div className="text-ink-3 text-xs font-syne">
            © 2026 MedMind AI. Evidence-based learning.
          </div>
        </div>
      </footer>
    </div>
  );
}

