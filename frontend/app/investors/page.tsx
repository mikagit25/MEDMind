import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: { absolute: "Investors — MedMind AI" },
  description:
    "MedMind AI is building the global AI-powered medical education platform. 8,000+ articles, 3 YouTube channels, 16 clinical calculators, 7 languages. Pre-seed round open.",
};

const NAV_LINKS = [
  { href: "/how-it-works", label: "Product" },
  { href: "/articles",     label: "Articles" },
  { href: "/calculators",  label: "Calculators" },
  { href: "/pricing",      label: "Pricing" },
];

const MARKET_STATS = [
  { val: "$6.4B",     label: "Global medical e-learning market (2024)", sub: "Growing at 18% CAGR" },
  { val: "~12M",      label: "Clinicians & students worldwide",          sub: "Primary addressable market" },
  { val: "$299–$699", label: "Annual spend per student on study tools",  sub: "Willingness to pay validated" },
  { val: "80%+",      label: "Medical students outside English-first tools", sub: "Our underserved opportunity" },
];

const PRODUCT_METRICS = [
  { val: "8,000+", label: "Medical articles published", color: "red" },
  { val: "82+",    label: "Clinical modules",           color: "blue" },
  { val: "16",     label: "Clinical calculators",       color: "green" },
  { val: "7",      label: "Languages",                  color: "amber" },
];

const CONTENT_METRICS = [
  { val: "3",    label: "YouTube channels (EN · ES · AR)" },
  { val: "200+", label: "Videos & Shorts uploaded" },
  { val: "7K+",  label: "Estimated monthly YouTube views" },
  { val: "5",    label: "User roles (B2C + B2B ready)" },
];

const REVENUE_STREAMS = [
  {
    name: "B2C Subscriptions",
    icon: "💳",
    tiers: [
      { tier: "Student",  price: "$15/mo",   desc: "Full module access, 50 AI queries/day" },
      { tier: "Pro",      price: "$40/mo",   desc: "Unlimited AI, drug database, vet content" },
      { tier: "Lifetime", price: "$299 once", desc: "All future content, one payment" },
    ],
    note: "Primary growth engine — high LTV, near-zero CAC via SEO and YouTube content flywheel.",
  },
  {
    name: "B2B Institutional",
    icon: "🏫",
    tiers: [
      { tier: "Clinic",     price: "$199/mo", desc: "Up to 10 seats, team analytics" },
      { tier: "Enterprise", price: "Custom",  desc: "Medical schools, hospitals, residency programs" },
    ],
    note: "High-value, sticky contracts. One medical school = 200–500 seats and multi-year renewal.",
  },
  {
    name: "Content & API",
    icon: "📄",
    tiers: [
      { tier: "YouTube",   price: "Ad revenue",   desc: "3 auto-generated channels, daily uploads" },
      { tier: "SEO",       price: "Affiliate",     desc: "8,000+ indexed medical articles driving traffic" },
      { tier: "API Access", price: "Usage-based", desc: "Medical AI Q&A for EHR / health-tech integrations" },
    ],
    note: "Long-term diversification. Video pipeline and SEO flywheel already operational.",
  },
];

const MOAT = [
  {
    title: "7 Languages — a structural advantage",
    desc: "Full multilingual support (EN, RU, DE, FR, ES, TR, AR) from day one including Arabic. Every major competitor is English-only. We directly address the 80%+ of medical students outside English-first markets.",
    icon: "🌍",
  },
  {
    title: "Complete product, not a feature",
    desc: "Structured curriculum + AI tutor + spaced-repetition flashcards + 16 clinical calculators + automated video content — all under one roof. Not a chatbot. Not a flashcard app. A platform.",
    icon: "🏗️",
  },
  {
    title: "Evidence-based AI (not ChatGPT)",
    desc: "Real-time PubMed integration means every AI answer is grounded in current evidence. Clinically accurate responses with citations — the structural advantage over generic AI tools.",
    icon: "🔬",
  },
  {
    title: "SEO + YouTube content flywheel",
    desc: "8,000+ AI-generated, SEO-optimised articles and 200+ YouTube videos across 3 channels create compounding organic discovery. Near-zero paid acquisition cost while growing every day.",
    icon: "📈",
  },
  {
    title: "Spaced repetition + AI = daily habit",
    desc: "SM-2 flashcard scheduling combined with AI tutoring creates a daily return loop. Users come back for their due cards — this is the habit engine that drives retention and justifies premium pricing.",
    icon: "🔄",
  },
  {
    title: "Multi-role = institutional sales",
    desc: "Student → Resident → Doctor → Professor → Admin. One platform serves the entire medical education ecosystem, enabling institution-wide contracts rather than individual seats.",
    icon: "👥",
  },
];

const TRACTION = [
  { label: "Platform live at medmind.pro (production)", done: true },
  { label: "8,000+ multilingual medical articles, Google-indexed", done: true },
  { label: "82+ clinical modules across 7 specialties", done: true },
  { label: "16 multilingual clinical calculators deployed", done: true },
  { label: "3 YouTube channels (EN, ES, AR) — 200+ videos uploaded", done: true },
  { label: "Daily automated Shorts pipeline across all 3 channels", done: true },
  { label: "7-language localisation complete (incl. Arabic, Turkish)", done: true },
  { label: "Admin panel + B2B Clinic tier fully implemented", done: true },
  { label: "First 100 paying users", done: false },
  { label: "University partnership pilot", done: false },
];

const ROADMAP = [
  {
    phase: "Phase 1",
    period: "Q2–Q3 2026",
    title: "Launch & first revenue",
    items: [
      "Marketing launch — SEO & YouTube content push",
      "Reach 100 paying subscribers",
      "App Store / Google Play listing",
      "First paid B2B clinic pilot",
    ],
    color: "red",
  },
  {
    phase: "Phase 2",
    period: "Q4 2026–Q1 2027",
    title: "B2B & institutional",
    items: [
      "First university pilot — 100–300 seats",
      "SCORM / LTI integration for LMS compatibility",
      "CME / CPD credit integration",
      "1,000+ monthly active users",
    ],
    color: "blue",
  },
  {
    phase: "Phase 3",
    period: "2027+",
    title: "Scale & API",
    items: [
      "Medical AI API for EHR / health-tech",
      "Expand to 15+ languages",
      "Partnerships with national medical boards",
      "Series A · target 10,000 paying users",
    ],
    color: "green",
  },
];

const UNIT_ECONOMICS = [
  { label: "Student plan LTV (24 mo avg)",  val: "$360",   color: "green" },
  { label: "Pro plan LTV (18 mo avg)",      val: "$720",   color: "green" },
  { label: "Clinic contract LTV (12 mo)",   val: "$2,400+", color: "green" },
  { label: "Target CAC via SEO / YouTube",  val: "< $10",  color: "blue" },
  { label: "Target paid CAC (social ads)",  val: "< $30",  color: "blue" },
  { label: "Gross margin (SaaS)",           val: "~85%",   color: "amber" },
];

export default function InvestorsPage() {
  return (
    <div className="min-h-screen bg-bg">

      {/* ── Nav ── */}
      <nav className="bg-surface border-b border-border sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center justify-between">
          <Link href="/" className="font-syne font-extrabold text-2xl tracking-tight text-ink">
            Med<span className="text-red">Mind</span>
          </Link>
          <div className="flex items-center gap-1">
            {NAV_LINKS.map((l) => (
              <Link key={l.href} href={l.href}
                className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2 hidden sm:block">
                {l.label}
              </Link>
            ))}
            <a
              href="/medmind-pitch-deck.pdf"
              download="MedMind-Pitch-Deck-2026.pdf"
              className="font-syne font-semibold text-sm border border-border text-ink-2 px-4 py-2 rounded hover:border-ink hover:text-ink transition-colors flex items-center gap-2"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
              </svg>
              Pitch Deck
            </a>
            <Link href="/register"
              className="font-syne font-semibold text-sm bg-ink text-white px-4 py-2 rounded hover:bg-red transition-colors ml-1">
              Try platform
            </Link>
          </div>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section className="max-w-5xl mx-auto px-6 pt-20 pb-14 text-center">
        <div className="inline-flex items-center gap-2 bg-surface border border-border px-3 py-1.5 rounded-full font-syne font-semibold text-xs text-ink-2 mb-8">
          <span className="w-2 h-2 rounded-full bg-green-2 inline-block animate-pulse" />
          Investor Overview — 2026 · Pre-Seed Round Open
        </div>
        <h1 className="font-syne font-extrabold text-5xl md:text-6xl text-ink leading-tight tracking-tight mb-6">
          The AI platform<br />
          <span className="text-red">medical education needs</span>
        </h1>
        <p className="text-ink-2 text-lg max-w-2xl mx-auto leading-relaxed mb-10">
          MedMind is building the world's first comprehensive AI-powered medical education platform —
          combining adaptive learning, real-time evidence, multilingual access, and automated content
          generation for the 12M+ clinicians who need to keep learning every day.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link href="#contact"
            className="inline-block font-syne font-bold text-base bg-ink text-white px-8 py-3.5 rounded hover:bg-red transition-colors">
            Contact us →
          </Link>
          <a
            href="/medmind-pitch-deck.pdf"
            download="MedMind-Pitch-Deck-2026.pdf"
            className="inline-flex items-center gap-2 font-syne font-semibold text-base border border-border-2 text-ink-2 px-8 py-3.5 rounded hover:border-ink hover:text-ink transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            Download Pitch Deck
          </a>
          <Link href="/how-it-works"
            className="inline-block font-syne font-semibold text-base border border-border text-ink-3 px-8 py-3.5 rounded hover:border-ink-2 hover:text-ink-2 transition-colors">
            See the product
          </Link>
        </div>
      </section>

      {/* ── Market ── */}
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

      {/* ── Problem / Solution ── */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <div className="grid md:grid-cols-2 gap-12 items-start">
          <div>
            <h2 className="font-syne font-bold text-3xl text-ink mb-6">The problem</h2>
            <div className="space-y-4">
              {[
                { icon: "📖", text: "Medical students rely on static textbooks and fragmented tools — a flashcard app here, a chatbot there, a PDF somewhere else." },
                { icon: "🌐", text: "The best learning tools are English-only, excluding the majority of the world's 12M+ medical students and clinicians." },
                { icon: "💸", text: "Quality medical prep costs $1,000–$5,000/year — completely inaccessible for students in emerging markets." },
                { icon: "📉", text: "Generic AI chatbots (ChatGPT, etc.) lack clinical structure, cite nothing, and cannot replace a curriculum." },
                { icon: "📺", text: "Medical video content (Osmosis, Lecturio) is static, expensive to produce, and English-only." },
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
                { icon: "⚡", text: "Real-time PubMed integration — every AI answer is backed by the latest published evidence, not static training data." },
                { icon: "🎯", text: "A complete system: structured curriculum + AI tutor + spaced repetition + 16 clinical calculators + video — in one platform." },
                { icon: "🌍", text: "Seven languages at launch including Arabic and Turkish. The only multilingual medical AI platform in the world." },
                { icon: "📺", text: "Automated video pipeline: 3 YouTube channels (EN/ES/AR) updated daily with AI-generated medical Shorts and full videos." },
                { icon: "💡", text: "Free tier with meaningful content removes the price barrier; premium converts via AI depth and advanced features." },
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

      {/* ── Platform built ── */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-6xl mx-auto px-6 py-16">
          <h2 className="font-syne font-bold text-2xl text-ink text-center mb-2">
            Platform is built, deployed, and generating content daily
          </h2>
          <p className="text-ink-3 text-center text-sm mb-10">
            Not a pitch deck. Not a prototype. A working platform at medmind.pro.
          </p>

          {/* Core metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            {PRODUCT_METRICS.map((m) => (
              <div key={m.label} className="bg-bg border border-border rounded-xl p-5 text-center">
                <div className="font-syne font-extrabold text-3xl text-ink mb-1">{m.val}</div>
                <div className="text-ink-3 text-xs font-syne uppercase tracking-widest leading-tight">{m.label}</div>
              </div>
            ))}
          </div>

          {/* Content / growth metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
            {CONTENT_METRICS.map((m) => (
              <div key={m.label} className="bg-red-light border border-red/20 rounded-xl p-5 text-center">
                <div className="font-syne font-extrabold text-3xl text-red mb-1">{m.val}</div>
                <div className="text-red/70 text-xs font-syne uppercase tracking-widest leading-tight">{m.label}</div>
              </div>
            ))}
          </div>

          {/* Traction checklist */}
          <div className="grid md:grid-cols-2 gap-3 max-w-3xl mx-auto">
            {TRACTION.map(({ label, done }) => (
              <div key={label} className="flex items-center gap-3">
                <span className={`w-5 h-5 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold ${
                  done ? "bg-green-2 text-white" : "bg-border text-ink-3"
                }`}>
                  {done ? "✓" : "○"}
                </span>
                <span className={`text-sm font-syne ${done ? "text-ink" : "text-ink-3"}`}>{label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Business model ── */}
      <section className="max-w-6xl mx-auto px-6 py-20">
        <h2 className="font-syne font-bold text-3xl text-ink text-center mb-3">
          Three revenue streams
        </h2>
        <p className="text-ink-3 text-center mb-12 text-sm">
          B2C subscriptions generating now — B2B and content diversifying from Q3 2026
        </p>
        <div className="grid md:grid-cols-3 gap-6">
          {REVENUE_STREAMS.map((rs) => (
            <div key={rs.name} className="bg-surface border border-border rounded-xl p-6">
              <div className="flex items-center gap-3 mb-5">
                <span className="text-2xl">{rs.icon}</span>
                <h3 className="font-syne font-bold text-base text-ink">{rs.name}</h3>
              </div>
              <div className="space-y-3 mb-5">
                {rs.tiers.map((tier) => (
                  <div key={tier.tier} className="flex justify-between items-start gap-2">
                    <div>
                      <div className="font-syne font-semibold text-sm text-ink">{tier.tier}</div>
                      <div className="text-ink-3 text-xs">{tier.desc}</div>
                    </div>
                    <div className="font-syne font-bold text-sm text-red flex-shrink-0">{tier.price}</div>
                  </div>
                ))}
              </div>
              <p className="text-ink-3 text-xs leading-relaxed border-t border-border pt-4">{rs.note}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Unit economics ── */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-4xl mx-auto px-6 py-16">
          <h2 className="font-syne font-bold text-2xl text-ink text-center mb-10">Unit economics</h2>
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
            Projections based on comparable SaaS education platforms (Brilliant, Coursera, Osmosis, MDCalc).
            CAC via SEO/YouTube assumes organic-first strategy — content flywheel already operational.
          </p>
        </div>
      </section>

      {/* ── Competitive moat ── */}
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

      {/* ── Roadmap ── */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-5xl mx-auto px-6 py-20">
          <h2 className="font-syne font-bold text-3xl text-ink text-center mb-3">
            Roadmap to scale
          </h2>
          <p className="text-ink-3 text-center mb-12 text-sm">
            Production-ready today. Revenue-focused from Q3 2026.
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

      {/* ── Why now + Contact ── */}
      <section className="max-w-4xl mx-auto px-6 py-20">
        <div className="grid md:grid-cols-2 gap-12">
          <div>
            <h2 className="font-syne font-bold text-2xl text-ink mb-6">Why now?</h2>
            <div className="space-y-4 text-ink-2 text-sm leading-relaxed">
              <p>
                Three converging trends make 2026 the inflection point: <strong className="text-ink">LLMs reaching clinical-grade accuracy</strong>, global demand for affordable medical education,
                and the explosion of multilingual AI content at near-zero marginal cost.
              </p>
              <p>
                Competitors like Osmosis (acquired by Elsevier for ~$100M) are large and slow.
                MDCalc dominates calculators but is English-only and has no AI.
                Generic AI tools like ChatGPT lack clinical structure.{" "}
                <strong className="text-ink">The window for a focused, AI-native, multilingual medical education platform is open now.</strong>
              </p>
              <p>
                MedMind has already built what most EdTech startups spend Series A money on:
                a production-deployed platform with 8,000+ articles, 3 YouTube channels,
                16 clinical calculators, and a complete multilingual AI curriculum.
              </p>
              <div className="mt-6">
                <a
                  href="/medmind-pitch-deck.pdf"
                  download="MedMind-Pitch-Deck-2026.pdf"
                  className="inline-flex items-center gap-2 font-syne font-semibold text-sm border border-border text-ink-2 px-5 py-2.5 rounded hover:border-ink hover:text-ink transition-colors"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none"
                    stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="7 10 12 15 17 10"/>
                    <line x1="12" y1="15" x2="12" y2="3"/>
                  </svg>
                  Download one-page pitch deck (PDF)
                </a>
              </div>
            </div>
          </div>

          <div id="contact">
            <h2 className="font-syne font-bold text-2xl text-ink mb-6">Get in touch</h2>
            <div className="space-y-4">
              <div className="bg-surface border border-border rounded-lg p-5">
                <div className="font-syne font-bold text-sm text-ink mb-1">Investment enquiries</div>
                <p className="text-ink-3 text-sm mb-3">
                  We are raising a pre-seed round to fund marketing launch, infrastructure scaling,
                  and first institutional partnerships.
                </p>
                <a href="mailto:invest@medmind.pro"
                  className="inline-block font-syne font-semibold text-sm text-red hover:underline">
                  invest@medmind.pro →
                </a>
              </div>
              <div className="bg-surface border border-border rounded-lg p-5">
                <div className="font-syne font-bold text-sm text-ink mb-1">Partnership & institutional</div>
                <p className="text-ink-3 text-sm mb-3">
                  Medical schools, hospitals, and residency programs — let's discuss a pilot program.
                </p>
                <a href="mailto:partners@medmind.pro"
                  className="inline-block font-syne font-semibold text-sm text-red hover:underline">
                  partners@medmind.pro →
                </a>
              </div>
              <div className="bg-surface border border-border rounded-lg p-5">
                <div className="font-syne font-bold text-sm text-ink mb-1">Try the platform</div>
                <p className="text-ink-3 text-sm mb-3">
                  The best way to evaluate MedMind is to use it. Free account, no credit card required.
                </p>
                <Link href="/register"
                  className="inline-block font-syne font-semibold text-sm text-red hover:underline">
                  Create free account →
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Disclaimer ── */}
      <section className="max-w-4xl mx-auto px-6 pb-12">
        <p className="text-ink-3 text-xs leading-relaxed text-center border border-border rounded-lg p-4 bg-surface">
          This page contains forward-looking statements and projections based on current market data and platform metrics.
          Financial projections are estimates only and not guarantees of future performance.
          MedMind is a private company; this page does not constitute a securities offering.
        </p>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-border bg-surface">
        <div className="max-w-6xl mx-auto px-6 py-8 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="font-syne font-extrabold text-lg text-ink">
            Med<span className="text-red">Mind</span>
            <span className="font-normal text-ink-3 text-xs ml-2">AI Education Platform</span>
          </div>
          <div className="flex gap-6 flex-wrap justify-center">
            <Link href="/articles"    className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">Articles</Link>
            <Link href="/calculators" className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">Calculators</Link>
            <Link href="/how-it-works" className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">How it works</Link>
            <Link href="/pricing"     className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">Pricing</Link>
            <Link href="/investors"   className="text-ink-3 text-sm hover:text-ink transition-colors font-syne">Investors</Link>
          </div>
          <div className="text-ink-3 text-xs font-syne">© 2026 MedMind AI.</div>
        </div>
      </footer>
    </div>
  );
}
