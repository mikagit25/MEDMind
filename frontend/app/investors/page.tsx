import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: { absolute: "Investors — MedMind AI" },
  description:
    "MedMind AI — global AI-powered medical education platform. 11,600+ articles, 8 Gulf Prometric exam banks, 2,600+ verified MCQ, 9 languages. Pre-seed round open.",
};

// ── Data ──────────────────────────────────────────────────────────────────────

const MARKET = [
  { val: "$6.4B",  label: "Medical e-learning market (2024)", sub: "18% CAGR through 2030" },
  { val: "~23M",   label: "Medical students & clinicians", sub: "Global primary audience" },
  { val: "$350+",  label: "Avg annual spend on study tools", sub: "Validated willingness to pay" },
  { val: "80%+",   label: "Non-English-first medical students", sub: "Underserved by competitors" },
];

const METRICS = [
  { val: "11,600+", label: "Published medical articles",       icon: "📄", color: "text-red" },
  { val: "125+",    label: "Structured clinical modules",       icon: "📚", color: "text-blue-500" },
  { val: "2,600+",  label: "Verified MCQ questions",           icon: "✅", color: "text-green-2" },
  { val: "8",       label: "Gulf Prometric exam banks",        icon: "🏆", color: "text-amber-500" },
  { val: "307",     label: "Drugs in database",                icon: "💊", color: "text-purple-500" },
  { val: "9",       label: "Languages (incl. Arabic, Turkish)", icon: "🌍", color: "text-amber-500" },
];

const PRODUCTS = [
  {
    name: "Web Platform",
    icon: "💻",
    desc: "Full-stack SaaS at medmind.pro — AI tutor, modules, flashcards, calculators, drug DB, imaging, clinical cases, Gulf Prometric exam simulations, progress analytics.",
    status: "Live",
    statusColor: "bg-green-2/10 text-green-2 border-green-2/30",
  },
  {
    name: "Gulf Prometric Prep",
    icon: "🏆",
    desc: "8 exam banks: SNLE (Saudi), DHA (Dubai), HAAD (Abu Dhabi), QCHP (Qatar), OMSB (Oman), NHRA (Bahrain), MOH UAE, MOH Kuwait. 2,600+ AI-verified MCQs with full 100Q timed simulations.",
    status: "Live",
    statusColor: "bg-green-2/10 text-green-2 border-green-2/30",
  },
  {
    name: "Telegram Bot",
    icon: "✈️",
    desc: "@Medmindpro_bot — AI medical education in Telegram. 5 AI modes, 9 languages, free tier (Llama 3.3) + paid (Claude Sonnet). No signup to start.",
    status: "Live",
    statusColor: "bg-green-2/10 text-green-2 border-green-2/30",
  },
  {
    name: "YouTube Channels",
    icon: "📹",
    desc: "3 auto-generated channels (EN, ES, AR) with daily Shorts and long-form videos. Organic content flywheel driving discovery at zero CAC.",
    status: "Live",
    statusColor: "bg-green-2/10 text-green-2 border-green-2/30",
  },
  {
    name: "Mobile App",
    icon: "📱",
    desc: "React Native Expo app with offline-first WatermelonDB sync. Study anywhere — modules, flashcards, AI tutor on iOS & Android.",
    status: "In development",
    statusColor: "bg-amber-500/10 text-amber-600 border-amber-500/30",
  },
  {
    name: "WhatsApp Bot",
    icon: "💬",
    desc: "Same MedMind AI experience for WhatsApp users — 2B+ addressable users, especially in LATAM, Middle East, Africa.",
    status: "Planned",
    statusColor: "bg-ink-3/10 text-ink-3 border-ink-3/30",
  },
  {
    name: "Medical AI API",
    icon: "🔌",
    desc: "Evidence-based medical Q&A API for EHR systems, health-tech platforms, and hospital education portals.",
    status: "Planned",
    statusColor: "bg-ink-3/10 text-ink-3 border-ink-3/30",
  },
];

const REVENUE_STREAMS = [
  {
    name: "B2C Subscriptions",
    icon: "👤",
    tiers: [
      { tier: "Student",  price: "$15/mo",    desc: "Full module access, 50 AI queries/day" },
      { tier: "Pro",      price: "$40/mo",    desc: "Unlimited AI, all features, Claude Sonnet" },
      { tier: "Lifetime", price: "$299 once", desc: "All future content, permanent access" },
    ],
    note: "Primary growth engine. Near-zero CAC via SEO & YouTube flywheel.",
    color: "border-red/30 bg-red/5",
  },
  {
    name: "B2B Institutional",
    icon: "🏫",
    tiers: [
      { tier: "Clinic",     price: "$199/mo",  desc: "Up to 10 seats, team analytics" },
      { tier: "Enterprise", price: "Custom",   desc: "Medical schools, hospitals, residency programs" },
    ],
    note: "High-LTV sticky contracts. One university = 300–2,000 seats, multi-year.",
    color: "border-blue-500/30 bg-blue-500/5",
  },
  {
    name: "Messenger Bots",
    icon: "📲",
    tiers: [
      { tier: "Free Bot",     price: "10 msg/day", desc: "Groq/Llama — top-of-funnel conversion" },
      { tier: "Pro Bot",      price: "Included",   desc: "Claude Sonnet via linked account" },
    ],
    note: "Bot is a low-friction acquisition channel. Users link to paid plans.",
    color: "border-[#229ED9]/30 bg-[#229ED9]/5",
  },
  {
    name: "Content & Licensing",
    icon: "📄",
    tiers: [
      { tier: "YouTube",    price: "Ad revenue",   desc: "3 channels (EN/ES/AR), daily upload pipeline" },
      { tier: "SEO Affiliate", price: "Passive",   desc: "11,600+ indexed articles + Gulf exam prep pages" },
      { tier: "API Access", price: "Usage-based",  desc: "Medical AI for EHR / health-tech" },
    ],
    note: "Long-term diversification. SEO flywheel already generating organic traffic. Gulf exam pages target high-intent search traffic.",
    color: "border-green-2/30 bg-green-2/5",
  },
];

const MOAT = [
  {
    icon: "🌍",
    title: "9 Languages — structural advantage",
    desc: "Full multilingual support from day one including Arabic, Turkish, Indonesian. Every major competitor (Osmosis, Amboss, Anki) is English-first. We own the 80% of medical students outside English markets.",
  },
  {
    icon: "🏆",
    title: "Gulf Prometric — a vertical no one owns",
    desc: "8 Gulf licensing exam banks (SNLE, DHA, HAAD, QCHP, OMSB, NHRA, MOH UAE, MOH Kuwait) with 2,600+ AI-verified MCQs and full timed simulations. 500,000+ nurses and doctors in GCC must pass these exams annually. No competitor covers all 8.",
  },
  {
    icon: "📱",
    title: "Omnichannel presence",
    desc: "Web + Telegram + YouTube + Mobile (soon WhatsApp). Users can learn on any surface. Competitors are locked to a single app. Our Telegram bot alone covers 950M+ users with no signup friction.",
  },
  {
    icon: "🔬",
    title: "Evidence-grounded AI (not ChatGPT)",
    desc: "Real-time PubMed integration on every AI answer. Citations, not hallucinations. This is clinically critical and our structural moat vs generic AI tools that physicians don't trust.",
  },
  {
    icon: "📈",
    title: "SEO + YouTube content flywheel",
    desc: "11,600 SEO-optimised articles and 3 YouTube channels publishing daily. Every piece of content compounds — more traffic → more trials → more subscriptions → funds more content.",
  },
  {
    icon: "🔄",
    title: "Spaced repetition creates daily habit",
    desc: "SM-2 flashcard scheduling means users return every day for their due cards. Daily habit = high retention = justifiable premium pricing = high LTV. Competitors without this lose users after exam season.",
  },
  {
    icon: "🏗️",
    title: "Complete platform, not a feature",
    desc: "AI tutor + structured curriculum + flashcards + Gulf exam prep + drug DB + calculators + imaging viewer + cases + analytics. Competitors offer one of these. We offer all. Switching cost is high.",
  },
];

const UNIT_ECONOMICS = [
  { label: "Student plan LTV (24 mo avg)",  val: "$360",    note: "$15/mo × 24" },
  { label: "Pro plan LTV (18 mo avg)",      val: "$720",    note: "$40/mo × 18" },
  { label: "Clinic LTV (12 mo contract)",   val: "$2,400+", note: "$199/mo × 12" },
  { label: "Organic CAC (SEO / YouTube)",   val: "< $5",    note: "Near-zero — content flywheel" },
  { label: "Paid CAC target (social)",      val: "< $30",   note: "LTV/CAC ratio > 20×" },
  { label: "Gross margin (SaaS)",           val: "~85%",    note: "AI API costs declining" },
];

const TRACTION = [
  { done: true,  text: "Platform live in production — medmind.pro" },
  { done: true,  text: "11,600+ multilingual medical articles, Google-indexed" },
  { done: true,  text: "125+ clinical modules across 39 specialties" },
  { done: true,  text: "307-drug database with interactions & dosing" },
  { done: true,  text: "8 Gulf Prometric exam banks — SNLE, DHA, HAAD, QCHP, OMSB, NHRA, MOH UAE, MOH Kuwait" },
  { done: true,  text: "2,600+ AI-verified MCQ questions with full 100Q timed simulations" },
  { done: true,  text: "Patient AI mode — plain-language explanations for non-specialists" },
  { done: true,  text: "3 YouTube channels (EN, ES, AR) — daily automated pipeline" },
  { done: true,  text: "Telegram bot launched — @Medmindpro_bot, 9 languages, live" },
  { done: true,  text: "9-language localisation (incl. Arabic, Turkish, Indonesian)" },
  { done: true,  text: "Stripe subscriptions — Student, Pro, Clinic, Lifetime tiers" },
  { done: true,  text: "B2B admin panel + team management fully implemented" },
  { done: true,  text: "Clinical calculators, imaging viewer, symptom checker deployed" },
  { done: true,  text: "Public SEO module pages — /learn/modules/[code] indexed by Google" },
  { done: false, text: "Product Hunt launch — Q3 2026" },
  { done: false, text: "First 100 paying subscribers" },
  { done: false, text: "Mobile app (iOS + Android) — App Store listing" },
  { done: false, text: "First university / hospital pilot — B2B Clinic tier" },
];

const ROADMAP = [
  {
    phase: "Now",
    period: "Q3 2026",
    title: "Launch & first revenue",
    color: "bg-red text-white",
    borderColor: "border-red",
    items: [
      "Product Hunt launch",
      "100 paying subscribers",
      "WhatsApp bot launch",
      "Mobile app (iOS/Android)",
    ],
  },
  {
    phase: "Phase 2",
    period: "Q4 2026 – Q1 2027",
    title: "B2B & institutional",
    color: "bg-blue-500 text-white",
    borderColor: "border-blue-500",
    items: [
      "First university pilot (100–500 seats)",
      "SCORM/LTI for LMS integration",
      "CME/CPD credit integration",
      "1,000+ monthly active users",
    ],
  },
  {
    phase: "Phase 3",
    period: "2027+",
    title: "Scale & API",
    color: "bg-green-2 text-white",
    borderColor: "border-green-2",
    items: [
      "Medical AI API for EHR systems",
      "15+ languages",
      "National medical board partnerships",
      "Series A · 10,000+ paying users",
    ],
  },
];

const COMPETITORS = [
  { name: "Osmosis",    model: "Video-first", lang: "EN only", ai: "Basic",   price: "$$$", moat: "Video library" },
  { name: "Amboss",     model: "Question bank", lang: "EN + DE", ai: "None",   price: "$$$", moat: "Q-bank depth" },
  { name: "Anki",       model: "Flashcards",  lang: "Any",    ai: "None",   price: "Free", moat: "User-generated" },
  { name: "ChatGPT",    model: "General AI",  lang: "Many",   ai: "Yes",    price: "$$",  moat: "Brand" },
  { name: "MedMind AI", model: "Full platform", lang: "9 langs", ai: "Evidence-based", price: "$$", moat: "Multilingual + Gulf exam prep + omnichannel + flywheel" },
];

// ── Page ──────────────────────────────────────────────────────────────────────

export default function InvestorsPage() {
  return (
    <div className="min-h-screen bg-bg text-ink">

      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-surface/95 backdrop-blur border-b border-border">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <Link href="/" className="font-syne font-extrabold text-xl text-ink">
            Med<span className="text-red">Mind</span>
          </Link>
          <div className="flex items-center gap-3">
            {[
              { href: "/how-it-works", label: "Product" },
              { href: "/pricing",      label: "Pricing" },
              { href: "/bots",         label: "Telegram Bot" },
            ].map(l => (
              <Link key={l.href} href={l.href} className="hidden sm:block text-ink-3 hover:text-ink text-sm font-syne transition-colors">
                {l.label}
              </Link>
            ))}
            <a href="mailto:partners@medmind.pro"
              className="bg-ink hover:bg-red text-white font-syne font-bold text-sm px-4 py-2 rounded-lg transition-colors">
              Contact us →
            </a>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-5xl mx-auto px-4 sm:px-6 pt-20 pb-16 text-center">
        <div className="inline-flex items-center gap-2 bg-red/10 border border-red/30 px-3 py-1 rounded-full font-syne font-semibold text-xs text-red mb-6">
          <span className="w-1.5 h-1.5 rounded-full bg-red animate-pulse" />
          Pre-seed round open · August 2026
        </div>
        <h1 className="font-syne font-extrabold text-4xl sm:text-6xl text-ink leading-tight tracking-tight mb-6">
          The global AI platform<br className="hidden sm:block" />
          <span className="text-red"> for medical education</span>
        </h1>
        <p className="text-ink-2 text-lg sm:text-xl max-w-3xl mx-auto mb-4 leading-relaxed">
          MedMind AI is building what Duolingo is for languages — but for medicine.
          A complete, multilingual, AI-powered education platform for the world's 23 million medical students and clinicians.
        </p>
        <p className="text-ink-3 text-sm font-syne mb-10">
          11,600+ articles · 8 Gulf exam banks · 2,600+ verified MCQ · 9 languages · Telegram bot · 3 YouTube channels
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <a
            href="/medmind-pitch-deck.pdf"
            download="MedMind_AI_Pitch_Deck_2026.pdf"
            className="inline-flex items-center justify-center gap-2 bg-ink hover:bg-red text-white font-syne font-bold px-8 py-4 rounded-xl text-base transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3M3 17V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
            </svg>
            Download pitch deck (PDF)
          </a>
          <a
            href="mailto:33mikalai@gmail.com"
            className="inline-flex items-center justify-center gap-2 border border-border hover:border-ink text-ink-2 hover:text-ink font-syne font-semibold px-8 py-4 rounded-xl text-base transition-colors"
          >
            Contact founder →
          </a>
        </div>
      </section>

      {/* Market */}
      <section className="border-y border-border bg-surface">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10 sm:py-14">
          <p className="text-center font-syne font-semibold text-xs text-ink-3 uppercase tracking-widest mb-8">Market opportunity</p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 sm:gap-10">
            {MARKET.map(m => (
              <div key={m.label} className="text-center">
                <div className="font-syne font-extrabold text-3xl sm:text-4xl text-ink mb-1">{m.val}</div>
                <div className="font-syne font-semibold text-xs text-ink-2 mb-0.5">{m.label}</div>
                <div className="font-serif text-xs text-ink-3">{m.sub}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Problem / Solution */}
      <section className="max-w-5xl mx-auto px-4 sm:px-6 py-16 sm:py-20">
        <div className="grid md:grid-cols-2 gap-12">
          <div>
            <div className="inline-block bg-red/10 text-red font-syne font-bold text-xs px-3 py-1 rounded-full mb-4">The Problem</div>
            <h2 className="font-syne font-bold text-2xl sm:text-3xl text-ink mb-4">Medical education is broken for most of the world</h2>
            <ul className="space-y-3">
              {[
                "Top tools (Osmosis, Amboss) are English-only — irrelevant to 80% of students",
                "Fragmented ecosystem: flashcards here, AI there, videos elsewhere",
                "No single platform covers all stages: student → resident → doctor",
                "Existing AI tools (ChatGPT) have no clinical evidence grounding — dangerous for medicine",
                "$350+/year per student with still no comprehensive solution",
              ].map(p => (
                <li key={p} className="flex gap-3 items-start text-sm text-ink-2 font-serif">
                  <span className="text-red font-bold mt-0.5 flex-shrink-0">✕</span>
                  {p}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <div className="inline-block bg-green-2/10 text-green-2 font-syne font-bold text-xs px-3 py-1 rounded-full mb-4">Our Solution</div>
            <h2 className="font-syne font-bold text-2xl sm:text-3xl text-ink mb-4">One platform. Every surface. Every language.</h2>
            <ul className="space-y-3">
              {[
                "9 languages including Arabic, Turkish, Indonesian — from day one",
                "AI tutor + modules + flashcards + drug DB + calculators in one platform",
                "8 Gulf Prometric exam banks — 2,600+ verified MCQs, the only platform covering all GCC licensing exams",
                "PubMed-grounded AI — every answer has clinical evidence citations",
                "Patient AI mode — plain-language explanations for non-specialists",
                "Omnichannel: web + Telegram bot + mobile + YouTube (WhatsApp coming)",
                "Content flywheel: 11,600+ SEO articles growing daily, near-zero CAC",
              ].map(p => (
                <li key={p} className="flex gap-3 items-start text-sm text-ink-2 font-serif">
                  <span className="text-green-2 font-bold mt-0.5 flex-shrink-0">✓</span>
                  {p}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* Product metrics */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-12 sm:py-16">
          <p className="text-center font-syne font-semibold text-xs text-ink-3 uppercase tracking-widest mb-8">What we've built</p>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 sm:gap-6 mb-10">
            {METRICS.map(m => (
              <div key={m.label} className="bg-bg border border-border rounded-2xl p-5 text-center">
                <div className="text-2xl mb-2">{m.icon}</div>
                <div className={`font-syne font-extrabold text-2xl sm:text-3xl ${m.color} mb-1`}>{m.val}</div>
                <div className="font-syne text-xs text-ink-3">{m.label}</div>
              </div>
            ))}
          </div>

          {/* Product suite */}
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {PRODUCTS.map(p => (
              <div key={p.name} className="bg-bg border border-border rounded-xl p-5">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{p.icon}</span>
                    <span className="font-syne font-bold text-sm text-ink">{p.name}</span>
                  </div>
                  <span className={`text-[10px] font-syne font-semibold px-2 py-0.5 rounded-full border ${p.statusColor}`}>
                    {p.status}
                  </span>
                </div>
                <p className="font-serif text-xs text-ink-3 leading-relaxed">{p.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Competitive landscape */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 py-16 sm:py-20">
        <div className="text-center mb-10">
          <h2 className="font-syne font-bold text-2xl sm:text-3xl text-ink mb-2">Competitive landscape</h2>
          <p className="text-ink-3 text-sm">We're not competing with one player — we're replacing the entire fragmented stack.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-border">
                {["Platform", "Model", "Languages", "AI", "Price", "Moat"].map(h => (
                  <th key={h} className="text-left font-syne font-semibold text-xs text-ink-3 uppercase tracking-wider py-3 px-4 whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {COMPETITORS.map((c, i) => {
                const isUs = c.name === "MedMind AI";
                return (
                  <tr key={c.name} className={`border-b border-border transition-colors ${isUs ? "bg-red/5" : "hover:bg-surface"}`}>
                    <td className={`py-3 px-4 font-syne font-bold text-sm ${isUs ? "text-red" : "text-ink"}`}>
                      {isUs ? "★ " : ""}{c.name}
                    </td>
                    <td className="py-3 px-4 font-serif text-ink-2 text-xs">{c.model}</td>
                    <td className={`py-3 px-4 font-syne text-xs font-semibold ${isUs ? "text-green-2" : c.lang === "EN only" ? "text-red" : "text-ink-2"}`}>{c.lang}</td>
                    <td className={`py-3 px-4 font-syne text-xs font-semibold ${isUs ? "text-green-2" : c.ai === "None" ? "text-ink-3" : "text-ink-2"}`}>{c.ai}</td>
                    <td className="py-3 px-4 font-serif text-ink-2 text-xs">{c.price}</td>
                    <td className={`py-3 px-4 font-serif text-xs ${isUs ? "text-ink font-semibold" : "text-ink-3"}`}>{c.moat}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      {/* Revenue streams */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
          <div className="text-center mb-12">
            <h2 className="font-syne font-bold text-2xl sm:text-3xl text-ink mb-2">4 revenue streams, 1 platform</h2>
            <p className="text-ink-3 text-sm">Diversified from day one — not dependent on a single growth channel.</p>
          </div>
          <div className="grid sm:grid-cols-2 gap-6">
            {REVENUE_STREAMS.map(rs => (
              <div key={rs.name} className={`rounded-2xl border p-6 ${rs.color}`}>
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-2xl">{rs.icon}</span>
                  <h3 className="font-syne font-bold text-base text-ink">{rs.name}</h3>
                </div>
                <div className="space-y-2.5 mb-4">
                  {rs.tiers.map(t => (
                    <div key={t.tier} className="flex items-start gap-3">
                      <div className="flex-shrink-0 mt-0.5">
                        <span className="inline-block w-2 h-2 rounded-full bg-ink/30" />
                      </div>
                      <div>
                        <span className="font-syne font-semibold text-xs text-ink">{t.tier} · {t.price}</span>
                        <span className="font-serif text-xs text-ink-3 ml-2">{t.desc}</span>
                      </div>
                    </div>
                  ))}
                </div>
                <p className="font-serif text-xs text-ink-3 border-t border-border pt-3">{rs.note}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Unit economics */}
      <section className="max-w-5xl mx-auto px-4 sm:px-6 py-16 sm:py-20">
        <div className="text-center mb-10">
          <h2 className="font-syne font-bold text-2xl sm:text-3xl text-ink mb-2">Unit economics</h2>
          <p className="text-ink-3 text-sm">High LTV, near-zero organic CAC — a classic SaaS flywheel.</p>
        </div>
        <div className="grid sm:grid-cols-3 gap-4">
          {UNIT_ECONOMICS.map(u => (
            <div key={u.label} className="bg-surface border border-border rounded-2xl p-5 text-center">
              <div className="font-syne font-extrabold text-2xl text-ink mb-1">{u.val}</div>
              <div className="font-syne font-semibold text-xs text-ink-2 mb-0.5">{u.label}</div>
              <div className="font-serif text-xs text-ink-3">{u.note}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Moat */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
          <div className="text-center mb-12">
            <h2 className="font-syne font-bold text-2xl sm:text-3xl text-ink mb-2">Why MedMind wins</h2>
            <p className="text-ink-3 text-sm">Seven structural advantages that compound over time.</p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {MOAT.map(m => (
              <div key={m.title} className="bg-bg border border-border rounded-xl p-5">
                <div className="text-2xl mb-3">{m.icon}</div>
                <h3 className="font-syne font-bold text-sm text-ink mb-2">{m.title}</h3>
                <p className="font-serif text-xs text-ink-3 leading-relaxed">{m.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Traction */}
      <section className="max-w-5xl mx-auto px-4 sm:px-6 py-16 sm:py-20">
        <div className="text-center mb-10">
          <h2 className="font-syne font-bold text-2xl sm:text-3xl text-ink mb-2">Traction & milestones</h2>
          <p className="text-ink-3 text-sm">Built in public — what's shipped and what's next.</p>
        </div>
        <div className="space-y-3">
          {TRACTION.map(t => (
            <div key={t.text} className={`flex items-start gap-3 p-4 rounded-xl border ${t.done ? "border-green-2/30 bg-green-2/5" : "border-border bg-surface"}`}>
              <div className={`flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center mt-0.5 ${t.done ? "bg-green-2" : "bg-border"}`}>
                {t.done
                  ? <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7"/></svg>
                  : <svg className="w-3 h-3 text-ink-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><circle cx="12" cy="12" r="3"/></svg>
                }
              </div>
              <span className={`font-syne text-sm ${t.done ? "text-ink" : "text-ink-3"}`}>{t.text}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Roadmap */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
          <div className="text-center mb-12">
            <h2 className="font-syne font-bold text-2xl sm:text-3xl text-ink mb-2">Roadmap</h2>
            <p className="text-ink-3 text-sm">From launch to Series A.</p>
          </div>
          <div className="grid sm:grid-cols-3 gap-6">
            {ROADMAP.map((r, i) => (
              <div key={r.phase} className={`relative rounded-2xl border-2 ${r.borderColor} p-6`}>
                <div className={`inline-flex items-center gap-2 font-syne font-bold text-xs px-3 py-1 rounded-full mb-3 ${r.color}`}>
                  {r.phase}
                </div>
                <div className="font-syne font-semibold text-xs text-ink-3 mb-1">{r.period}</div>
                <h3 className="font-syne font-bold text-base text-ink mb-4">{r.title}</h3>
                <ul className="space-y-2">
                  {r.items.map(item => (
                    <li key={item} className="flex gap-2 items-start text-xs font-serif text-ink-2">
                      <span className="text-ink-3 flex-shrink-0 mt-0.5">→</span>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Why now + CTA */}
      <section className="max-w-5xl mx-auto px-4 sm:px-6 py-16 sm:py-20">
        <div className="grid md:grid-cols-2 gap-12">
          <div>
            <h2 className="font-syne font-bold text-2xl text-ink mb-4">Why now?</h2>
            <ul className="space-y-4">
              {[
                ["🤖", "LLMs finally good enough for clinical use", "Claude 3.5 / GPT-4 level AI is genuinely safe for medical education. 2 years ago this wasn't true."],
                ["📉", "AI API costs dropped 90% in 18 months", "What cost $1/query in 2023 now costs $0.05. Unit economics work at scale."],
                ["📱", "Messenger-first learning exploding", "WhatsApp/Telegram AI bots are the fastest-growing category. We're already there."],
                ["🌍", "Emerging markets go online for education", "Middle East, SEA, LATAM are the fastest-growing medical student populations — all underserved by English tools."],
              ].map(([icon, title, desc]) => (
                <li key={title as string} className="flex gap-3">
                  <span className="text-xl flex-shrink-0">{icon}</span>
                  <div>
                    <div className="font-syne font-semibold text-sm text-ink mb-0.5">{title}</div>
                    <div className="font-serif text-xs text-ink-3">{desc}</div>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-ink text-white rounded-2xl p-8">
            <div className="font-syne font-semibold text-xs text-white/50 uppercase tracking-widest mb-4">Get in touch</div>
            <h2 className="font-syne font-extrabold text-2xl mb-3">Interested in investing?</h2>
            <p className="text-white/70 font-serif text-sm mb-6 leading-relaxed">
              We're raising a pre-seed round to fund our go-to-market push, mobile app launch, and first B2B contracts. We'd love to talk.
            </p>
            <div className="space-y-3">
              <a href="mailto:33mikalai@gmail.com"
                className="flex items-center gap-3 bg-white/10 hover:bg-white/20 rounded-xl px-4 py-3 transition-colors">
                <span className="text-lg">✉️</span>
                <div>
                  <div className="font-syne font-semibold text-sm">Founder — Mikalai Mikheyeu</div>
                  <div className="text-white/50 text-xs font-syne">33mikalai@gmail.com</div>
                </div>
              </a>
              <a href="mailto:partners@medmind.pro"
                className="flex items-center gap-3 bg-white/10 hover:bg-white/20 rounded-xl px-4 py-3 transition-colors">
                <span className="text-lg">🏢</span>
                <div>
                  <div className="font-syne font-semibold text-sm">Business inquiries</div>
                  <div className="text-white/50 text-xs font-syne">partners@medmind.pro</div>
                </div>
              </a>
              <Link href="/"
                className="flex items-center gap-3 bg-white/10 hover:bg-white/20 rounded-xl px-4 py-3 transition-colors">
                <span className="text-lg">🌐</span>
                <div>
                  <div className="font-syne font-semibold text-sm">Try the product</div>
                  <div className="text-white/50 text-xs font-syne">medmind.pro — live in production</div>
                </div>
              </Link>
              <a href="https://t.me/Medmindpro_bot" target="_blank" rel="noopener noreferrer"
                className="flex items-center gap-3 bg-white/10 hover:bg-white/20 rounded-xl px-4 py-3 transition-colors">
                <span className="text-lg">✈️</span>
                <div>
                  <div className="font-syne font-semibold text-sm">Try Telegram bot</div>
                  <div className="text-white/50 text-xs font-syne">@Medmindpro_bot — no signup needed</div>
                </div>
              </a>
            </div>
            <a
              href="/medmind-pitch-deck.pdf"
              download="MedMind_AI_Pitch_Deck_2026.pdf"
              className="inline-flex items-center gap-2 text-white/50 hover:text-white text-xs font-syne mt-5 transition-colors"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3M3 17V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
              </svg>
              Download pitch deck PDF
            </a>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border bg-surface">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <Link href="/" className="font-syne font-extrabold text-lg text-ink">
            Med<span className="text-red">Mind</span>
          </Link>
          <div className="flex gap-5">
            {["/", "/pricing", "/bots", "/articles"].map(href => (
              <Link key={href} href={href} className="text-ink-3 text-sm hover:text-ink transition-colors font-syne capitalize">
                {href === "/" ? "Home" : href.replace("/", "")}
              </Link>
            ))}
          </div>
          <p className="text-ink-3 text-xs font-syne">⚕️ For educational purposes only</p>
        </div>
      </footer>
    </div>
  );
}
