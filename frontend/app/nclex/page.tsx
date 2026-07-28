import type { Metadata } from "next";
import Link from "next/link";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { PublicFooter } from "@/components/layout/PublicFooter";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";

export const metadata: Metadata = {
  title: "NCLEX-RN Prep 2025 — Adaptive CAT Simulations & AI Explanations | MedMind AI",
  description:
    "Practice NCLEX-RN with adaptive CAT simulations (75–145 questions), SATA, NGN, and AI-powered explanations. Track your performance across all 7 NCLEX Client Needs categories and 6 CJMM clinical judgment skills. Free demo included.",
  alternates: {
    canonical: `${SITE_URL}/nclex`,
  },
  openGraph: {
    title: "NCLEX-RN Prep — Adaptive Simulations & AI Explanations | MedMind AI",
    description:
      "600+ NCLEX-style questions, adaptive CAT mode, AI explanations, and personal analytics across Client Needs categories and CJMM skills.",
    url: `${SITE_URL}/nclex`,
    siteName: "MedMind AI",
    type: "website",
  },
};

const FEATURES = [
  {
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
    title: "Adaptive CAT Simulation",
    desc: "Real NCLEX-RN logic: the exam adjusts difficulty based on each answer. Choose 75, 85, or 145 questions — same format as Pearson VUE.",
  },
  {
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
    ),
    title: "AI Explanation for Every Question",
    desc: "After answering, get a full clinical reasoning breakdown: why the correct answer is right, why each distractor is wrong, and the key nursing concept to remember.",
  },
  {
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M11 3.055A9.001 9.001 0 1020.945 13H11V3.055z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M20.488 9H15V3.512A9.025 9.025 0 0120.488 9z" />
      </svg>
    ),
    title: "7 Client Needs Categories",
    desc: "Every question is tagged to one of 7 NCLEX Client Needs domains. After the exam, see your exact score per category — Safe & Effective Care, Pharmacological Therapies, Physiological Adaptation, and more.",
  },
  {
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
      </svg>
    ),
    title: "CJMM Clinical Judgment Tracking",
    desc: "Track your mastery of all 6 NCSBN Clinical Judgment Measurement Model skills: Recognize Cues, Analyze Cues, Prioritize Hypotheses, Generate Solutions, Take Actions, and Evaluate Outcomes.",
  },
  {
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
      </svg>
    ),
    title: "Retry Wrong Questions",
    desc: "After each session, launch a targeted retry session with only the questions you got wrong — focused practice on your actual weak spots.",
  },
  {
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
      </svg>
    ),
    title: "SATA, Calculations & NGN Format",
    desc: "Not just standard MCQ. Practice Select-All-That-Apply, IV drip calculations, ordered response, and Next Generation NCLEX (NGN) item types — the formats that trip up most test-takers.",
  },
];

const MODES = [
  { id: "Demo", questions: 10, tag: "Free, no login", desc: "Try before you commit. 10 questions across all categories, full AI explanations included.", free: true },
  { id: "NCLEX-RN 75", questions: 75, tag: "Minimum passing length", desc: "Standard adaptive simulation. The exam ends here if performance is clearly passing or failing.", free: false },
  { id: "NCLEX-RN 85", questions: 85, tag: "Extended simulation", desc: "Push through the borderline zone. Tougher questions, more accurate assessment of readiness.", free: false },
  { id: "NCLEX-RN 145", questions: 145, tag: "Maximum length", desc: "Full-length simulation. Every category covered in depth. Best for final prep week.", free: false },
  { id: "By Category", questions: "10–30", tag: "Targeted practice", desc: "Choose one of the 7 Client Needs categories and drill it specifically.", free: false },
];

const FAQ = [
  {
    q: "Is the demo really free?",
    a: "Yes. The 10-question demo requires no account. You get full AI explanations and see your score breakdown — no credit card, no email needed.",
  },
  {
    q: "How is this different from other NCLEX prep apps?",
    a: "Most apps test recall. MedMind tracks your clinical judgment using the NCSBN's CJMM framework — so you learn to think like a nurse, not just memorize answers. Every wrong answer comes with an AI-generated clinical reasoning breakdown.",
  },
  {
    q: "Are the questions up to date with NCLEX-RN 2024/2025 changes?",
    a: "Yes. The question bank includes Next Generation NCLEX (NGN) item types introduced in the 2023 update — SATA, ordered response, and calculation questions. The adaptive algorithm mirrors Pearson VUE's CAT logic.",
  },
  {
    q: "Can I use MedMind alongside other prep materials?",
    a: "Absolutely. MedMind is designed to supplement — not replace — your core prep materials (Saunders, ATI, UWorld). Use it to reinforce weak areas, practice clinical judgment, and simulate exam conditions.",
  },
];

export default function NclexLandingPage() {
  return (
    <>
      <ArticleNav />

      {/* ── Hero ─────────────────────────────────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 pt-16 sm:pt-24 pb-12 sm:pb-16">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div>
            <div className="inline-flex items-center gap-2 bg-red/10 border border-red/20 px-3 py-1 rounded-full font-syne font-semibold text-xs text-red mb-5">
              <span className="w-1.5 h-1.5 rounded-full bg-red inline-block" />
              NCLEX-RN 2025 Prep
            </div>
            <h1 className="font-syne font-extrabold text-3xl sm:text-4xl lg:text-5xl text-ink mb-4 leading-tight">
              Pass NCLEX-RN<br />on your first attempt.
            </h1>
            <p className="text-ink-2 text-base sm:text-lg leading-relaxed mb-8 max-w-lg">
              Adaptive CAT simulations, AI-powered clinical reasoning breakdowns, and analytics across every NCLEX Client Needs category — built for how nurses actually learn.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link
                href="/register"
                className="inline-block font-syne font-bold text-base bg-red text-white px-8 py-4 rounded-xl hover:bg-ink transition-colors"
              >
                Start free →
              </Link>
              <Link
                href="/login"
                className="inline-block font-syne font-semibold text-base border border-border text-ink-2 px-8 py-4 rounded-xl hover:border-ink hover:text-ink transition-colors"
              >
                Sign in
              </Link>
            </div>
            <p className="text-xs text-ink-3 mt-4 font-syne">Free account · 5 AI questions/day · No credit card required</p>
          </div>

          {/* Stats grid */}
          <div className="grid grid-cols-2 gap-3">
            {[
              { value: "600+", label: "NCLEX questions", sub: "SATA · CAT · NGN · Calc" },
              { value: "12", label: "Nursing modules", sub: "Evidence-based content" },
              { value: "7", label: "Client Needs", sub: "Full category coverage" },
              { value: "6", label: "CJMM skills", sub: "Clinical judgment tracking" },
            ].map((s) => (
              <div key={s.label} className="bg-surface border border-border rounded-xl p-5 flex flex-col gap-1">
                <span className="font-syne font-extrabold text-3xl sm:text-4xl text-ink">{s.value}</span>
                <span className="font-syne font-semibold text-sm text-ink leading-tight">{s.label}</span>
                <span className="text-xs text-ink-3">{s.sub}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Exam modes ───────────────────────────────────────────────────────── */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-12 sm:py-16">
          <div className="mb-8">
            <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink mb-2">Five exam modes</h2>
            <p className="text-ink-3 text-sm">From a quick 10-question demo to a full 145-question simulation.</p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {MODES.map((m) => (
              <div key={m.id} className={`rounded-xl border p-5 flex flex-col gap-3 ${m.free ? "border-red/30 bg-red/5" : "border-border bg-bg"}`}>
                <div className="flex items-start justify-between gap-2">
                  <span className="font-syne font-extrabold text-xl text-ink">{m.questions}</span>
                  <span className={`text-xs font-syne font-semibold px-2 py-0.5 rounded-full border ${m.free ? "bg-red/10 border-red/20 text-red" : "bg-surface border-border text-ink-3"}`}>
                    {m.tag}
                  </span>
                </div>
                <div>
                  <h3 className="font-syne font-bold text-base text-ink mb-1">{m.id}</h3>
                  <p className="text-ink-3 text-sm leading-snug">{m.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Features grid ────────────────────────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
        <div className="mb-10">
          <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink mb-2">Everything you need to pass</h2>
          <p className="text-ink-3 text-sm max-w-xl">Every feature is built around one goal: pass NCLEX-RN with confidence, not luck.</p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {FEATURES.map((f) => (
            <div key={f.title} className="flex flex-col gap-3">
              <div className="w-9 h-9 rounded-xl bg-surface border border-border flex items-center justify-center text-ink-2 flex-shrink-0">
                {f.icon}
              </div>
              <div>
                <h3 className="font-syne font-bold text-base text-ink mb-1">{f.title}</h3>
                <p className="text-ink-3 text-sm leading-relaxed">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── How it works ─────────────────────────────────────────────────────── */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
          <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink mb-10 text-center">How it works</h2>
          <div className="grid sm:grid-cols-3 gap-8">
            {[
              { step: "01", title: "Choose a mode", desc: "Start with the free 10-question demo, or pick a full CAT simulation (75 / 85 / 145 questions) or a category-specific drill." },
              { step: "02", title: "Answer & review", desc: "After each question, tap 'Explain with AI' for a full clinical reasoning breakdown — why your answer was right or wrong, and what concept to remember." },
              { step: "03", title: "Track & improve", desc: "The Analytics tab shows your pass rate by Client Needs category and CJMM skill. Retry wrong questions with one click." },
            ].map((s) => (
              <div key={s.step} className="flex flex-col gap-3">
                <span className="font-syne font-extrabold text-5xl text-ink/10 leading-none">{s.step}</span>
                <h3 className="font-syne font-bold text-base text-ink">{s.title}</h3>
                <p className="text-ink-3 text-sm leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── NCLEX content coverage ───────────────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
        <div className="grid md:grid-cols-2 gap-12">
          <div>
            <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink mb-6">7 Client Needs categories</h2>
            <div className="space-y-2">
              {[
                { key: "Safe & Effective Care Environment", pct: 26 },
                { key: "Health Promotion & Maintenance", pct: 6 },
                { key: "Psychosocial Integrity", pct: 9 },
                { key: "Basic Care & Comfort", pct: 6 },
                { key: "Pharmacological & Parenteral Therapies", pct: 15 },
                { key: "Reduction of Risk Potential", pct: 9 },
                { key: "Physiological Adaptation", pct: 11 },
              ].map((c) => (
                <div key={c.key} className="flex items-center gap-3">
                  <span className="text-xs font-syne text-ink-3 w-5 text-right flex-shrink-0">{c.pct}%</span>
                  <div className="flex-1 bg-surface rounded-full h-1.5 border border-border overflow-hidden">
                    <div className="bg-red h-full rounded-full" style={{ width: `${(c.pct / 26) * 100}%` }} />
                  </div>
                  <span className="text-sm text-ink-2 font-syne leading-tight">{c.key}</span>
                </div>
              ))}
            </div>
            <p className="text-xs text-ink-3 mt-3">Percentages reflect NCSBN 2023 NCLEX-RN test plan distribution.</p>
          </div>
          <div>
            <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink mb-6">6 CJMM clinical judgment skills</h2>
            <div className="space-y-3">
              {[
                { skill: "Recognize Cues", desc: "Identify relevant assessment data from the clinical situation" },
                { skill: "Analyze Cues", desc: "Interpret the meaning and significance of recognized cues" },
                { skill: "Prioritize Hypotheses", desc: "Rank possible client problems by urgency and likelihood" },
                { skill: "Generate Solutions", desc: "Identify evidence-based interventions for each hypothesis" },
                { skill: "Take Actions", desc: "Implement the plan and communicate findings accurately" },
                { skill: "Evaluate Outcomes", desc: "Assess whether actions achieved the expected outcomes" },
              ].map((s) => (
                <div key={s.skill} className="flex gap-3">
                  <span className="w-1.5 h-1.5 rounded-full bg-red mt-2 flex-shrink-0" />
                  <div>
                    <span className="font-syne font-semibold text-sm text-ink">{s.skill}</span>
                    <p className="text-xs text-ink-3 leading-snug mt-0.5">{s.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── FAQ ──────────────────────────────────────────────────────────────── */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
          <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink mb-8 text-center">Frequently asked questions</h2>
          <div className="space-y-6">
            {FAQ.map((item) => (
              <div key={item.q} className="border-b border-border pb-6 last:border-0 last:pb-0">
                <h3 className="font-syne font-bold text-base text-ink mb-2">{item.q}</h3>
                <p className="text-ink-3 text-sm leading-relaxed">{item.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Final CTA ────────────────────────────────────────────────────────── */}
      <section className="bg-ink text-white">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 py-16 sm:py-20 text-center">
          <h2 className="font-syne font-extrabold text-3xl sm:text-4xl mb-4">Ready to start?</h2>
          <p className="text-white/60 mb-8 text-base leading-relaxed">
            Try the free demo now — 10 questions, full AI explanations, no account needed. Create an account to unlock full CAT simulations and personal analytics.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link
              href="/register"
              className="inline-block font-syne font-bold text-base bg-white text-ink px-8 py-4 rounded-xl hover:bg-red hover:text-white transition-colors"
            >
              Start free →
            </Link>
            <Link
              href="/register"
              className="inline-block font-syne font-semibold text-base border border-white/30 text-white/80 px-8 py-4 rounded-xl hover:border-white hover:text-white transition-colors"
            >
              Create free account
            </Link>
          </div>
          <p className="text-white/30 text-xs mt-5 font-syne">No credit card required · Free plan includes 5 AI questions/day</p>
        </div>
      </section>

      <PublicFooter />
    </>
  );
}
