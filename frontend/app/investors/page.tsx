import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Investors — MedMind AI",
  description:
    "MedMind AI is building the global AI-powered medical education platform. Learn about our market opportunity, traction, business model, and vision.",
};

const NAV_LINKS = [
  { href: "/how-it-works", label: "Product" },
  { href: "/articles", label: "Articles" },
  { href: "/pricing", label: "Pricing" },
];

const MARKET_STATS = [
  { val: "$6.4B", label: "Global medical e-learning market (2024)", sub: "Growing at 18% CAGR" },
  { val: "~2M", label: "Medical students worldwide", sub: "Primary target segment" },
  { val: "~10M", label: "Practicing physicians globally", sub: "Expansion market" },
  { val: "$299–$699", label: "Annual spend on medical study tools", sub: "Per student, current average" },
];

const PRODUCT_METRICS = [
  { val: "82+", label: "Clinical modules", color: "red" },
  { val: "500+", label: "Flashcards", color: "blue" },
  { val: "7", label: "Languages", color: "green" },
  { val: "5", label: "User roles", color: "amber" },
];

const REVENUE_STREAMS = [
  {
    name: "B2C Subscriptions",
    icon: "💳",
    tiers: [
      { tier: "Student", price: "$15/mo", desc: "Full module access, 50 AI Q/day" },
      { tier: "Pro", price: "$40/mo", desc: "Unlimited AI, drug database, vet content" },
      { tier: "Lifetime", price: "$299 once", desc: "All future content, one payment" },
    ],
    note: "Primary growth engine — high LTV, low CAC via SEO content strategy.",
  },
  {
    name: "B2B Institutional",
    icon: "🏫",
    tiers: [
      { tier: "Clinic", price: "$199/mo", desc: "Up to 10 seats, team analytics" },
      { tier: "Enterprise", price: "Custom", desc: "Medical schools, hospitals, residency programs" },
    ],
    note: "High-value, sticky contracts. One medical school = 200–500 seats.",
  },
  {
    name: "Content & Licensing",
    icon: "📄",
    tiers: [
      { tier: "SEO Articles", price: "Ad / affiliate revenue", desc: "Hundreds of indexed medical articles" },
      { tier: "Video Content", price: "YouTube monetization", desc: "Auto-generated multilingual medical videos" },
      { tier: "API Access", price: "Usage-based", desc: "Medical AI Q&A for EHR / health-tech integrations" },
    ],
    note: "Long-term diversification beyond subscriptions.",
  },
];

const MOAT = [
  {
    title: "Clinical-grade AI accuracy",
    desc: "Real-time PubMed integration means every AI answer is grounded in current evidence — not static training data. This is a structural advantage vs. generic AI tools.",
    icon: "🔬",
  },
  {
    title: "Curriculum depth",
    desc: "82+ structured modules with lessons, MCQs, cases, and flashcards per module — built around actual medical curricula. Years of content work that cannot be copy-pasted.",
    icon: "📚",
  },
  {
    title: "Multilingual by design",
    desc: "Full 7-language support (en, ru, de, fr, es, tr, ar) from day one. Competitors focus on English-speaking markets. We address emerging markets with large medical student populations.",
    icon: "🌍",
  },
  {
    title: "SEO content flywheel",
    desc: "Hundreds of AI-generated, SEO-optimised medical articles drive organic discovery. Each article links back to the platform — compounding traffic without paid acquisition.",
    icon: "📈",
  },
  {
    title: "Spaced repetition + AI = retention loop",
    desc: "The combination of SM-2 flashcards and AI tutoring creates daily engagement. Users return to do reviews — building a habit loop that premium tools exploit for high retention.",
    icon: "🔄",
  },
  {
    title: "Multi-role platform",
    desc: "Student, Resident, Doctor, Professor, Veterinarian, Admin. One platform serves the entire medical education ecosystem, enabling institution-level contracts.",
    icon: "👥",
  },
];

const TRACTION = [
  { label: "Platform fully built & deployed", done: true },
  { label: "82+ modules across 6 specialties", done: true },
  { label: "7-language localisation complete", done: true },
  { label: "SEO article generation engine live", done: true },
  { label: "Article-to-video pipeline ready", done: true },
  { label: "Admin panel with full content management", done: true },
  { label: "B2B Clinic tier implemented", done: true },
  { label: "Production server deployment", done: false },
  { label: "First 100 paying users", done: false },
  { label: "University partnership pilot", done: false },
];

const ROADMAP = [
  {
    phase: "Phase 1",
    period: "Q2–Q3 2026",
    title: "Launch & first revenue",
    items: [
      "Production deployment on dedicated server",
      "Launch SEO content campaign (500+ articles)",
      "First YouTube channel with medical video content",
      "Reach 100 paying subscribers",
      "App Store / Google Play listing",
    ],
    color: "red",
  },
  {
    phase: "Phase 2",
    period: "Q4 2026–Q1 2027",
    title: "B2B & institutional",
    items: [
      "First university pilot (100–300 seats)",
      "SCORM / LTI integration for LMS compatibility",
      "Custom white-label offering for medical schools",
      "Expand to 1,000+ monthly active users",
      "CME / CPD credit integration",
    ],
    color: "blue",
  },
  {
    phase: "Phase 3",
    period: "2027+",
    title: "Scale & API",
    items: [
      "Medical AI API for EHR / health-tech companies",
      "Expand to 15+ languages",
      "Partnerships with national medical boards",
      "Series A fundraise",
      "Target: 10,000 paying users across B2C + B2B",
    ],
    color: "green",
  },
];

const UNIT_ECONOMICS = [
  { label: "Student plan LTV (24 mo avg)", val: "$360", color: "green" },
  { label: "Pro plan LTV (18 mo avg)", val: "$720", color: "green" },
  { label: "Clinic contract LTV (12 mo avg)", val: "$2,388", color: "green" },
  { label: "Target CAC via SEO", val: "< $10", color: "blue" },
  { label: "Target paid CAC (social)", val: "< $30", color: "blue" },
  { label: "Gross margin (SaaS)", val: "~85%", color: "amber" },
];

export default function InvestorsPage() {
  return (
    <div className="min-h-screen bg-bg">
      {/* Nav */}
      <nav className="bg-surface border-b border-border sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
          <Link href="/" className="font-syne font-extrabold text-2xl tracking-tight text-ink">
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
              href="/register"
              className="font-syne font-semibold text-sm bg-ink text-white px-4 py-2 rounded hover:bg-red transition-colors"
            >
              Try platform
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-5xl mx-auto px-6 pt-20 pb-16 text-center">
        <div className="inline-flex items-center gap-2 bg-surface border border-border px-3 py-1.5 rounded-full font-syne font-semibold text-xs text-ink-2 mb-8">
          <span className="w-2 h-2 rounded-full bg-green-2 inline-block" />
          Investor Overview — 2026
        </div>
        <h1 className="font-syne font-extrabold text-5xl md:text-6xl text-ink leading-tight tracking-tight mb-6">
          The AI platform<br />
          <span className="text-red">medical education needs</span>
        </h1>
        <p className="text-ink-2 text-lg max-w-2xl mx-auto leading-relaxed mb-10">
          MedMind is building the world's first comprehensive AI-powered medical education platform —
          combining adaptive learning, real-time evidence, and multilingual access for the
          12 million+ clinicians who need to keep learning every day.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link
            href="#contact"
            className="inline-block font-syne font-bold text-base bg-ink text-white px-8 py-3.5 rounded hover:bg-red transition-colors"
          >
            Contact us →
          </Link>
          <Link
            href="/how-it-works"
            className="inline-block font-syne font-semibold text-base border border-border-2 text-ink-2 px-8 py-3.5 rounded hover:border-ink hover:text-ink transition-colors"
          >
            See the product
          </Link>
        </div>
      </section>

      {/* Market */}
      <section className="border-y border-border bg-surface">
        <div className="max-w-6xl mx-auto px-6 py-16">
          <h2 className="font-syne font-bold text-2xl text-ink text-center mb-10">
            A large, growing, underserved market
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {MARKET_STATS.map((s) => (
              <div key={s.label} className="text-center">
                <div className="font-syne font-extrabold text-3xl text-red mb-1">{s.val}</div>
                <div className="font-syne font-semibold text-sm text-ink mb-1">{s.label}</div>
                <div className="text-ink-3 text-xs">{s.sub}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Problem */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div>
            <h2 className="font-syne font-bold text-3xl text-ink mb-6">The problem</h2>
            <div className="space-y-4">
              {[
                {
                  icon: "📖",
                  text: "Medical students rely on static textbooks that go out of date the moment they're printed.",
                },
                {
                  icon: "🔀",
                  text: "Existing tools are fragmented — a flashcard app here, a chatbot there, a textbook PDF somewhere else.",
                },
                {
                  icon: "🌐",
                  text: "The best learning tools are English-only, excluding the majority of the world's medical students.",
                },
                {
                  icon: "💸",
                  text: "High-quality medical prep courses cost thousands of dollars — inaccessible for most students globally.",
                },
                {
                  icon: "📉",
                  text: "Generic AI chatbots lack clinical structure, cite nothing, and can't replace a curriculum.",
                },
              ].map(({ icon, text }) => (
                <div key={text} className="flex items-start gap-3">
                  <span className="text-xl flex-shrink-0">{icon}</span>
                  <p className="text-ink-2 text-sm leading-relaxed">{text}</p>
                </div>
              ))}
            </div>
          </div>
          <div>
            <h2 className="font-syne font-bold text-3xl text-ink mb-6">Our solution</h2>
            <div className="space-y-4">
              {[
                {
                  icon: "⚡",
                  text: "Real-time PubMed integration — every AI answer is backed by the latest published evidence, not static data.",
                },
                {
                  icon: "🎯",
                  text: "A complete system: structured curriculum + AI tutor + spaced repetition + clinical cases — in one platform.",
                },
                {
                  icon: "🌍",
                  text: "Seven languages at launch: English, Russian, German, French, Spanish, Turkish, Arabic.",
                },
                {
                  icon: "💡",
                  text: "Free tier with meaningful content removes the price barrier and builds top-of-funnel organically.",
                },
                {
                  icon: "🏥",
                  text: "Platform serves students, residents, doctors, and educators — enabling institutional contracts.",
                },
              ].map(({ icon, text }) => (
                <div key={text} className="flex items-start gap-3">
                  <span className="text-xl flex-shrink-0">{icon}</span>
                  <p className="text-ink-2 text-sm leading-relaxed">{text}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Product built */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-6xl mx-auto px-6 py-16">
          <h2 className="font-syne font-bold text-2xl text-ink text-center mb-4">
            Product is built and deployed
          </h2>
          <p className="text-ink-3 text-center text-sm mb-10">
            Not a pitch deck. Not a prototype. A working platform.
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-12">
            {PRODUCT_METRICS.map((m) => (
              <div key={m.label} className="bg-bg border border-border rounded-lg p-5 text-center">
                <div className="font-syne font-extrabold text-3xl text-ink mb-1">{m.val}</div>
                <div className="text-ink-3 text-xs font-syne uppercase tracking-widest">{m.label}</div>
              </div>
            ))}
          </div>
          <div className="grid md:grid-cols-2 gap-4 max-w-3xl mx-auto">
            {TRACTION.map(({ label, done }) => (
              <div key={label} className="flex items-center gap-3">
                <span className={`w-5 h-5 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold ${done ? "bg-green-2 text-white" : "bg-border text-ink-3"}`}>
                  {done ? "✓" : "○"}
                </span>
                <span className={`text-sm font-syne ${done ? "text-ink" : "text-ink-3"}`}>{label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Business model */}
      <section className="max-w-6xl mx-auto px-6 py-20">
        <h2 className="font-syne font-bold text-3xl text-ink text-center mb-3">
          Three revenue streams
        </h2>
        <p className="text-ink-3 text-center mb-12 text-sm">
          Starting with B2C subscriptions, expanding into B2B and content
        </p>
        <div className="grid md:grid-cols-3 gap-6">
          {REVENUE_STREAMS.map((rs) => (
            <div key={rs.name} className="bg-surface border border-border rounded-xl p-6">
              <div className="flex items-center gap-3 mb-5">
                <span className="text-2xl">{rs.icon}</span>
                <h3 className="font-syne font-bold text-base text-ink">{rs.name}</h3>
              </div>
              <div className="space-y-3 mb-5">
                {rs.tiers.map((t) => (
                  <div key={t.tier} className="flex justify-between items-start gap-2">
                    <div>
                      <div className="font-syne font-semibold text-sm text-ink">{t.tier}</div>
                      <div className="text-ink-3 text-xs">{t.desc}</div>
                    </div>
                    <div className="font-syne font-bold text-sm text-red flex-shrink-0">{t.price}</div>
                  </div>
                ))}
              </div>
              <p className="text-ink-3 text-xs leading-relaxed border-t border-border pt-4">{rs.note}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Unit economics */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-4xl mx-auto px-6 py-16">
          <h2 className="font-syne font-bold text-2xl text-ink text-center mb-10">
            Unit economics
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {UNIT_ECONOMICS.map(({ label, val, color }) => (
              <div key={label} className="bg-bg border border-border rounded-lg p-5">
                <div className={`font-syne font-extrabold text-2xl mb-1 ${
                  color === "green" ? "text-green-2" : color === "blue" ? "text-blue" : "text-amber-2"
                }`}>{val}</div>
                <div className="text-ink-3 text-xs font-syne leading-tight">{label}</div>
              </div>
            ))}
          </div>
          <p className="text-center text-ink-3 text-xs mt-8 max-w-lg mx-auto">
            Projections based on comparable SaaS education platforms (Brilliant, Coursera, Osmosis).
            CAC via SEO assumes organic-first strategy with minimal paid spend.
          </p>
        </div>
      </section>

      {/* Competitive moat */}
      <section className="max-w-6xl mx-auto px-6 py-20">
        <h2 className="font-syne font-bold text-3xl text-ink text-center mb-3">
          Why MedMind wins
        </h2>
        <p className="text-ink-3 text-center mb-12 text-sm">
          Structural advantages that compound over time
        </p>
        <div className="grid md:grid-cols-3 gap-6">
          {MOAT.map((m) => (
            <div key={m.title} className="bg-surface border border-border rounded-lg p-6 hover:border-border-2 transition-colors">
              <div className="text-2xl mb-3">{m.icon}</div>
              <h3 className="font-syne font-bold text-base text-ink mb-2">{m.title}</h3>
              <p className="text-ink-3 text-sm leading-relaxed">{m.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Roadmap */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-5xl mx-auto px-6 py-20">
          <h2 className="font-syne font-bold text-3xl text-ink text-center mb-3">
            Roadmap to scale
          </h2>
          <p className="text-ink-3 text-center mb-12 text-sm">
            Platform-ready today. Revenue-focused tomorrow.
          </p>
          <div className="grid md:grid-cols-3 gap-6">
            {ROADMAP.map((r) => (
              <div key={r.phase} className="bg-bg border border-border rounded-xl p-6">
                <div className={`inline-block font-syne font-bold text-xs px-2 py-1 rounded mb-3 ${
                  r.color === "red" ? "bg-red-light text-red" :
                  r.color === "blue" ? "bg-blue/10 text-blue" : "bg-green-2/10 text-green-2"
                }`}>
                  {r.phase} · {r.period}
                </div>
                <h3 className="font-syne font-bold text-base text-ink mb-4">{r.title}</h3>
                <ul className="space-y-2">
                  {r.items.map((item) => (
                    <li key={item} className="flex items-start gap-2 text-sm text-ink-3">
                      <span className="flex-shrink-0 mt-0.5">→</span>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Team / Ask */}
      <section className="max-w-4xl mx-auto px-6 py-20">
        <div className="grid md:grid-cols-2 gap-12">
          <div>
            <h2 className="font-syne font-bold text-2xl text-ink mb-6">Why now?</h2>
            <div className="space-y-4 text-ink-2 text-sm leading-relaxed">
              <p>
                The convergence of three trends makes 2026 the right moment: <strong className="text-ink">LLMs reaching clinical-grade accuracy</strong>, global demand for affordable medical education post-COVID, and medical students increasingly comfortable using AI tools for learning.
              </p>
              <p>
                Competitors like Osmosis (acquired by Elsevier) are large and slow. Generic AI tools like ChatGPT lack clinical structure. <strong className="text-ink">The window for a focused, AI-native medical education platform is open now.</strong>
              </p>
              <p>
                MedMind has already built what most EdTech startups spend Series A money on: a complete, multilingual, production-ready platform with differentiated content strategy.
              </p>
            </div>
          </div>
          <div id="contact">
            <h2 className="font-syne font-bold text-2xl text-ink mb-6">Get in touch</h2>
            <div className="space-y-4">
              <div className="bg-surface border border-border rounded-lg p-5">
                <div className="font-syne font-bold text-sm text-ink mb-1">Investment enquiries</div>
                <p className="text-ink-3 text-sm mb-3">
                  We are raising a pre-seed round to fund server infrastructure, marketing launch, and first institutional partnerships.
                </p>
                <a
                  href="mailto:invest@medmind.pro"
                  className="inline-block font-syne font-semibold text-sm text-red hover:underline"
                >
                  invest@medmind.pro →
                </a>
              </div>
              <div className="bg-surface border border-border rounded-lg p-5">
                <div className="font-syne font-bold text-sm text-ink mb-1">Partnership & institutional</div>
                <p className="text-ink-3 text-sm mb-3">
                  Medical schools, hospitals, and residency programs — let's discuss a pilot program.
                </p>
                <a
                  href="mailto:partners@medmind.pro"
                  className="inline-block font-syne font-semibold text-sm text-red hover:underline"
                >
                  partners@medmind.pro →
                </a>
              </div>
              <div className="bg-surface border border-border rounded-lg p-5">
                <div className="font-syne font-bold text-sm text-ink mb-1">Try the platform</div>
                <p className="text-ink-3 text-sm mb-3">
                  The best way to evaluate MedMind is to use it. Free account, no credit card.
                </p>
                <Link
                  href="/register"
                  className="inline-block font-syne font-semibold text-sm text-red hover:underline"
                >
                  Create free account →
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Disclaimer */}
      <section className="max-w-4xl mx-auto px-6 pb-12">
        <p className="text-ink-3 text-xs leading-relaxed text-center border border-border rounded-lg p-4 bg-surface">
          This page contains forward-looking statements and projections based on current market data and platform metrics.
          Financial projections are estimates only and not guarantees of future performance.
          MedMind is a private company; this page does not constitute a securities offering.
        </p>
      </section>

      {/* Footer */}
      <footer className="border-t border-border bg-surface">
        <div className="max-w-6xl mx-auto px-6 py-8 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="font-syne font-extrabold text-lg text-ink">
            Med<span className="text-red">Mind</span>
            <span className="font-normal text-ink-3 text-xs ml-2">AI Education Platform</span>
          </div>
          <div className="flex gap-6 flex-wrap justify-center">
            <Link href="/articles" className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">Articles</Link>
            <Link href="/how-it-works" className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">How it works</Link>
            <Link href="/pricing" className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">Pricing</Link>
            <Link href="/investors" className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">Investors</Link>
          </div>
          <div className="text-ink-3 text-xs font-syne">© 2026 MedMind AI.</div>
        </div>
      </footer>
    </div>
  );
}
