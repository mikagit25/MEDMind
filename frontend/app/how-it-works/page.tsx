"use client";
import { useT } from "@/lib/i18n";
import Link from "next/link";

const NAV_LINKS = [
  { href: "/articles", label: "Articles" },
  { href: "/pricing", label: "Pricing" },
  { href: "/how-it-works", label: "How it works" },
];

const STEPS = [
  {
    number: "01",
    title: "Choose your specialty",
    description:
      "Pick from 6 core specialties — Cardiology, Neurology, Surgery, Pediatrics, OB/GYN, and Internal Medicine. Each specialty has 10–15 curated modules built around real clinical curricula.",
    detail: "No guesswork. Start exactly where you need to grow.",
    icon: "🎯",
    color: "red",
  },
  {
    number: "02",
    title: "Learn with AI — your way",
    description:
      "Every module gives you four distinct AI modes. In Tutor mode the AI explains concepts step by step. Socratic mode forces you to reason aloud. Case-based mode drops you into a real patient encounter. Exam mode simulates board-style MCQs.",
    detail: "All answers are grounded in live PubMed citations — never hallucinated.",
    icon: "🧠",
    color: "blue",
  },
  {
    number: "03",
    title: "Reinforce with flashcards",
    description:
      "After every lesson, spaced-repetition flashcards schedule your reviews using the SM-2 algorithm — the same science behind Anki. Cards appear right before you're about to forget.",
    detail: "500+ cards across all modules, auto-generated and community-verified.",
    icon: "📇",
    color: "amber",
  },
  {
    number: "04",
    title: "Simulate clinical cases",
    description:
      "Interactive patient cases present vital signs, lab values, imaging, and ask you to make decisions. The AI acts as an attending, guiding you through differentials and management plans.",
    detail: "Cases are based on USMLE, MRCP, and equivalent board exam formats.",
    icon: "🩺",
    color: "green",
  },
  {
    number: "05",
    title: "Track progress & streaks",
    description:
      "Your dashboard shows completion rate per module, flashcard retention scores, AI question history, and a streak calendar. See exactly where you're strong — and where to focus next.",
    detail: "Daily goals and reminders keep momentum going.",
    icon: "📈",
    color: "blue",
  },
  {
    number: "06",
    title: "Stay current with articles",
    description:
      "MedMind publishes AI-generated, evidence-based articles on hundreds of conditions, drugs, and procedures. Search by keyword or browse by specialty for quick clinical references.",
    detail: "Every article includes an FAQ and source list with PMIDs.",
    icon: "📄",
    color: "red",
  },
];

const ROLES = [
  {
    role: "Medical Student",
    icon: "📚",
    description:
      "From first year to finals — structure your preclinical knowledge, ace your OSCE, and prepare for board exams with adaptive AI practice.",
    features: [
      "Full curriculum coverage across 82+ modules",
      "Spaced repetition that adapts to your schedule",
      "Exam simulation mode for USMLE / MRCP / local boards",
    ],
  },
  {
    role: "Resident / Junior Doctor",
    icon: "🏥",
    description:
      "Keep up with evidence-based medicine while managing heavy rotations. Quick AI lookups, drug references, and clinical case practice — all in one place.",
    features: [
      "AI tutor available 24/7 for ward-side questions",
      "Drug database with dosing, interactions, contraindications",
      "Case simulations covering common emergency presentations",
    ],
  },
  {
    role: "Attending Physician",
    icon: "👨‍⚕️",
    description:
      "CME-ready learning that fits around a full practice. Refresh subspecialty knowledge, stay updated on guidelines, and upskill in areas outside your core training.",
    features: [
      "Unlimited AI questions with PubMed-backed answers",
      "Latest clinical guidelines integrated into content",
      "Veterinary modules for mixed or exotic practices",
    ],
  },
  {
    role: "Educator / Professor",
    icon: "🎓",
    description:
      "Build and manage your own course content. Assign modules to students, track their progress, and supplement lectures with AI-powered case discussions.",
    features: [
      "Custom module and lesson upload",
      "Student progress dashboard and analytics",
      "Exportable progress reports (SCORM compatible)",
    ],
  },
];

const TECH_FEATURES = [
  {
    title: "Claude AI Engine",
    desc: "Powered by Anthropic's Claude — one of the most accurate AI models for medical reasoning. Every response is calibrated for clinical precision, not generic text generation.",
    icon: "⚡",
  },
  {
    title: "Live PubMed Search",
    desc: "Before answering, MedMind queries PubMed in real-time and surfaces the most relevant, recent studies. Your learning is always evidence-based.",
    icon: "🔬",
  },
  {
    title: "SM-2 Spaced Repetition",
    desc: "The proven algorithm behind Anki and SuperMemo. Cards are scheduled at the exact interval needed to maximize long-term retention.",
    icon: "📊",
  },
  {
    title: "Multilingual Platform",
    desc: "Full support for English, Russian, German, French, Spanish, Turkish, and Arabic. All interfaces, lessons, and AI responses available in your language.",
    icon: "🌍",
  },
  {
    title: "Dark & Light Mode",
    desc: "Designed for long study sessions. Switch between light and dark mode — easy on the eyes during night shifts or late-night reviews.",
    icon: "🌙",
  },
  {
    title: "Works on Any Device",
    desc: "Fully responsive — desktop, tablet, or mobile. Study during a commute, between cases, or at your desk. Sync is automatic.",
    icon: "📱",
  },
];

export default function HowItWorksPage() {
  const t = useT();
  return (
    <div className="min-h-screen bg-bg">
      {/* Nav */}
      <nav className="bg-surface border-b border-border sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
          <Link
            href="/"
            className="font-syne font-extrabold text-2xl tracking-tight text-ink"
          >
            Med<span className="text-red">Mind</span>
          </Link>
          <div className="flex items-center gap-3">
            {NAV_LINKS.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-4 py-2"
              >
                {l.label}
              </Link>
            ))}
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
      <section className="max-w-5xl mx-auto px-6 pt-20 pb-16 text-center">
        <div className="inline-flex items-center gap-2 bg-surface border border-border px-3 py-1.5 rounded-full font-syne font-semibold text-xs text-ink-2 mb-8">
          <span className="w-2 h-2 rounded-full bg-blue animate-pulse inline-block" />
          {t("how_it_works_page.title")}
        </div>
        <h1 className="font-syne font-extrabold text-5xl md:text-6xl text-ink leading-tight tracking-tight mb-6">
          How MedMind<br />
          <span className="text-red">works for you</span>
        </h1>
        <p className="text-ink-2 text-lg max-w-2xl mx-auto leading-relaxed mb-10">
          MedMind is not a textbook, not a flashcard app, and not a chatbot. It is a complete
          adaptive learning system that combines AI tutoring, spaced repetition, and real evidence —
          structured around the way clinicians think.
        </p>
        <Link
          href="/register"
          className="inline-block font-syne font-bold text-base bg-ink text-white px-8 py-3.5 rounded hover:bg-red transition-colors"
        >
          Try it free — no card needed →
        </Link>
      </section>

      {/* How it works — step by step */}
      <section className="max-w-5xl mx-auto px-6 py-16">
        <h2 className="font-syne font-bold text-3xl text-ink text-center mb-3">
          {t("how_it_works_page.subtitle")}
        </h2>
        <p className="text-ink-3 text-center mb-16 text-sm">
          {t("how_it_works_page.note")}
        </p>

        <div className="space-y-12">
          {STEPS.map((step, i) => (
            <div
              key={step.number}
              className={`flex flex-col md:flex-row gap-8 items-start ${
                i % 2 === 1 ? "md:flex-row-reverse" : ""
              }`}
            >
              {/* Visual */}
              <div className="flex-shrink-0 w-full md:w-64 bg-surface border border-border rounded-xl p-8 text-center">
                <div className="text-5xl mb-4">{step.icon}</div>
                <div className="font-syne font-extrabold text-4xl text-border-2 mb-1">
                  {step.number}
                </div>
              </div>
              {/* Text */}
              <div className="flex-1 pt-4">
                <h3 className="font-syne font-bold text-2xl text-ink mb-3">
                  {step.title}
                </h3>
                <p className="text-ink-2 text-base leading-relaxed mb-4">
                  {step.description}
                </p>
                <div className="inline-flex items-center gap-2 bg-surface border border-border rounded-lg px-4 py-2">
                  <span className="text-green-2 text-sm">→</span>
                  <span className="text-ink-3 text-sm font-syne">{step.detail}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Who it's for */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-6xl mx-auto px-6 py-20">
          <h2 className="font-syne font-bold text-3xl text-ink text-center mb-3">
            {t("how_it_works_page.roles_title")}
          </h2>
          <p className="text-ink-3 text-center mb-12 text-sm">
            From first lecture to consultant rounds
          </p>
          <div className="grid md:grid-cols-2 gap-6">
            {ROLES.map((r) => (
              <div
                key={r.role}
                className="bg-bg border border-border rounded-xl p-6 hover:border-border-2 transition-colors"
              >
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-3xl">{r.icon}</span>
                  <h3 className="font-syne font-bold text-lg text-ink">{r.role}</h3>
                </div>
                <p className="text-ink-2 text-sm leading-relaxed mb-4">{r.description}</p>
                <ul className="space-y-2">
                  {r.features.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-ink-3">
                      <span className="text-green-2 mt-0.5 flex-shrink-0">✓</span>
                      {f}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Technology */}
      <section className="max-w-6xl mx-auto px-6 py-20">
        <h2 className="font-syne font-bold text-3xl text-ink text-center mb-3">
          The technology behind it
        </h2>
        <p className="text-ink-3 text-center mb-12 text-sm">
          Best-in-class tools, assembled into a seamless experience
        </p>
        <div className="grid md:grid-cols-3 gap-6">
          {TECH_FEATURES.map((f) => (
            <div
              key={f.title}
              className="bg-surface border border-border rounded-lg p-6 hover:border-border-2 transition-colors"
            >
              <div className="text-2xl mb-3">{f.icon}</div>
              <h3 className="font-syne font-bold text-base text-ink mb-2">{f.title}</h3>
              <p className="text-ink-3 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Comparison */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-4xl mx-auto px-6 py-20">
          <h2 className="font-syne font-bold text-3xl text-ink text-center mb-3">
            MedMind vs. the alternatives
          </h2>
          <p className="text-ink-3 text-center mb-12 text-sm">
            Why a purpose-built medical AI platform beats a collection of tools
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 pr-6 font-syne font-bold text-ink-2 w-48">Feature</th>
                  <th className="py-3 px-4 font-syne font-bold text-red text-center">MedMind</th>
                  <th className="py-3 px-4 font-syne font-bold text-ink-3 text-center">Generic chatbot</th>
                  <th className="py-3 px-4 font-syne font-bold text-ink-3 text-center">Anki alone</th>
                  <th className="py-3 px-4 font-syne font-bold text-ink-3 text-center">Textbook</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {[
                  ["PubMed-backed answers", "✅", "⚠️ sometimes", "❌", "⚠️ outdated"],
                  ["Spaced repetition", "✅", "❌", "✅", "❌"],
                  ["Clinical case simulation", "✅", "⚠️ generic", "❌", "❌"],
                  ["Structured curriculum", "✅", "❌", "❌", "✅"],
                  ["Multilingual", "✅ 7 languages", "⚠️", "⚠️", "⚠️"],
                  ["Progress tracking", "✅", "❌", "✅ basic", "❌"],
                  ["Drug database", "✅", "⚠️", "❌", "✅ static"],
                  ["Always up-to-date", "✅", "⚠️", "❌", "❌"],
                ].map(([feat, ...vals]) => (
                  <tr key={feat}>
                    <td className="py-3 pr-6 font-syne text-ink-2">{feat}</td>
                    {vals.map((v, i) => (
                      <td key={i} className="py-3 px-4 text-center text-ink-3">{v}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="max-w-3xl mx-auto px-6 py-20">
        <h2 className="font-syne font-bold text-3xl text-ink text-center mb-12">
          Common questions
        </h2>
        <div className="space-y-6">
          {[
            {
              q: "Do I need any prior AI experience?",
              a: "None at all. MedMind is designed for clinicians, not engineers. You ask questions the same way you would ask a colleague — and get structured, cited answers.",
            },
            {
              q: "How accurate is the medical content?",
              a: "Every AI response searches PubMed in real-time and includes citations. The platform uses Claude, one of the highest-accuracy LLMs for medical reasoning. All module content is reviewed against current guidelines.",
            },
            {
              q: "Can I use MedMind offline?",
              a: "The AI tutor requires an internet connection. Flashcards downloaded to your device work offline in a future update. Articles are accessible from any browser.",
            },
            {
              q: "Is this a replacement for textbooks or my university?",
              a: "MedMind complements your existing study — it does not replace clinical training or your institution. Think of it as a 24/7 AI study partner that adapts to your exact knowledge gaps.",
            },
            {
              q: "What languages are supported?",
              a: "English, Russian, German, French, Spanish, Turkish, and Arabic. More languages are on the roadmap. All AI responses can be requested in your chosen language.",
            },
            {
              q: "Is there a free plan?",
              a: "Yes — the Free tier includes 8 core modules, 5 AI questions per day, and basic flashcards. No credit card required to sign up.",
            },
          ].map(({ q, a }) => (
            <div key={q} className="bg-surface border border-border rounded-lg p-6">
              <h3 className="font-syne font-bold text-base text-ink mb-2">{q}</h3>
              <p className="text-ink-2 text-sm leading-relaxed">{a}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="bg-ink text-white">
        <div className="max-w-3xl mx-auto px-6 py-20 text-center">
          <h2 className="font-syne font-extrabold text-4xl mb-4">
            Start learning in under 2 minutes
          </h2>
          <p className="text-white/60 mb-8 text-base leading-relaxed">
            Create a free account, choose your specialty, and ask your first AI question.
            No setup, no credit card, no commitment.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link
              href="/register"
              className="inline-block font-syne font-bold text-base bg-white text-ink px-10 py-4 rounded hover:bg-red hover:text-white transition-colors"
            >
              Create free account →
            </Link>
            <Link
              href="/pricing"
              className="inline-block font-syne font-semibold text-base border border-white/30 text-white/80 px-10 py-4 rounded hover:border-white hover:text-white transition-colors"
            >
              See pricing
            </Link>
          </div>
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
            <Link href="/articles" className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">{t("nav.items.articles")}</Link>
            <Link href="/how-it-works" className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">{t("landing.how_it_works")}</Link>
            <Link href="/pricing" className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">Pricing</Link>
            <Link href="/investors" className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">Investors</Link>
            <Link href="/register" className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">Register</Link>
          </div>
          <div className="text-ink-3 text-xs font-syne">© 2026 MedMind AI.</div>
        </div>
      </footer>
    </div>
  );
}
