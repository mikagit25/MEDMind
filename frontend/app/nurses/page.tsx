import type { Metadata } from "next";
import Link from "next/link";
import { cookies } from "next/headers";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { PublicFooter } from "@/components/layout/PublicFooter";

const SUPPORTED = ["en", "ru", "ar", "tr", "de", "fr", "es"];
const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";

export async function generateMetadata(): Promise<Metadata> {
  return {
    title: "Nursing Education Platform — NCLEX-Style Practice & Dose Calculations | MedMind AI",
    description:
      "Evidence-based nursing modules, NCLEX-style SATA and ordered questions, parametric dose-calculation trainer, and medication safety practice. Built for nurses, by clinicians.",
    alternates: {
      canonical: `${SITE_URL}/nurses`,
      languages: Object.fromEntries(
        SUPPORTED.map(l => [l, l === "en" ? `${SITE_URL}/nurses` : `${SITE_URL}/${l}/nurses`])
      ),
    },
    openGraph: {
      title: "Nursing Education That Fits Your Shift — MedMind AI",
      description:
        "NCLEX prep, medication safety, dose calculations, and clinical skills — in 7 languages, offline-capable on mobile.",
      url: `${SITE_URL}/nurses`,
      siteName: "MedMind AI",
      type: "website",
    },
  };
}

// ── i18n strings ─────────────────────────────────────────────────────────────

const COPY: Record<string, {
  hero_tag: string;
  hero_h1: string;
  hero_sub: string;
  cta_primary: string;
  cta_secondary: string;
  modules_h2: string;
  modules_sub: string;
  features_h2: string;
  cta_final_h2: string;
  cta_final_sub: string;
  cta_final_btn: string;
}> = {
  en: {
    hero_tag: "For Nurses & Nursing Students",
    hero_h1: "Nursing education\nthat fits your shift.",
    hero_sub: "NCLEX-style questions, parametric dose-calculation practice, medication safety, and 8 evidence-based nursing modules — in 7 languages, offline on mobile.",
    cta_primary: "Start free",
    cta_secondary: "Browse modules",
    modules_h2: "8 Core Nursing Modules",
    modules_sub: "Written from the nursing angle — not simplified medical content.",
    features_h2: "Built for how nurses actually learn",
    cta_final_h2: "Start practising today",
    cta_final_sub: "Free plan includes 5 AI questions per day and full access to nursing modules.",
    cta_final_btn: "Create free account",
  },
  ru: {
    hero_tag: "Для медсестёр и студентов сестринского дела",
    hero_h1: "Сестринское образование,\nкоторое вписывается в смену.",
    hero_sub: "Вопросы в стиле NCLEX, тренажёр расчёта доз, безопасность медикаментов и 8 доказательных модулей — на 7 языках, офлайн на мобильном.",
    cta_primary: "Начать бесплатно",
    cta_secondary: "Смотреть модули",
    modules_h2: "8 базовых сестринских модулей",
    modules_sub: "Контент написан с сестринского угла — не упрощённая медицина.",
    features_h2: "Создано под реальный режим обучения медсестры",
    cta_final_h2: "Начните практику сегодня",
    cta_final_sub: "Бесплатный план включает 5 AI-вопросов в день и полный доступ к сестринским модулям.",
    cta_final_btn: "Создать аккаунт бесплатно",
  },
};

const MODULES = [
  { code: "NURSE-001", icon: "📋", title: "Nursing Process & Documentation", sub: "ADPIE, SBAR, legal charting" },
  { code: "NURSE-002", icon: "💊", title: "Medication Safety", sub: "5 Rights, HAMs, SATA + ordered questions" },
  { code: "NURSE-003", icon: "🧮", title: "Dose Calculations & IV Therapy", sub: "Linked to the dose-calc trainer" },
  { code: "NURSE-004", icon: "🦠", title: "Infection Control & Hand Hygiene", sub: "WHO 5 Moments, precaution types" },
  { code: "NURSE-005", icon: "📊", title: "Recognising Deterioration (NEWS2)", sub: "Sepsis Six, qSOFA, ordered priorities" },
  { code: "NURSE-006", icon: "🚨", title: "Emergency Skills: Nurse's Role", sub: "BLS, anaphylaxis, hypoglycaemia" },
  { code: "NURSE-007", icon: "🛏️", title: "Patient Care: Wounds, Falls, Mobility", sub: "Braden, Morse, staging, prevention" },
  { code: "NURSE-008", icon: "💬", title: "Communication, Family & SBAR Handoff", sub: "Therapeutic techniques, teach-back" },
];

const FEATURES = [
  {
    icon: "✅",
    title: "NCLEX-style question types",
    body: "Select All That Apply (SATA), put-in-order, numeric dose calculation, and standard MCQ — the four types on real nursing licensure exams.",
  },
  {
    icon: "🧮",
    title: "Parametric dose-calculation trainer",
    body: "Unlimited practice problems generated from clinical formulas — weight-based dosing, infusion rates, dilutions, unit conversions, paediatric dosing. Step-by-step solution every time.",
  },
  {
    icon: "🌍",
    title: "7 languages",
    body: "Study in English, Russian, Arabic, Turkish, German, French, or Spanish. Interface and content — both translated.",
  },
  {
    icon: "📱",
    title: "Offline on mobile",
    body: "Download modules and practice between shifts. iOS and Android. No WiFi needed on the ward.",
  },
  {
    icon: "🏥",
    title: "Point-of-care drug database",
    body: "Full drug database access — interactions, dosing, contraindications. Nurses are specialists: you have the same access as physicians.",
  },
  {
    icon: "📚",
    title: "3 nursing clinical cases",
    body: "Branching patient scenarios built around nursing decisions — observation, escalation, prioritisation — not physician orders.",
  },
];

function getLocale(): string {
  const cookieStore = cookies();
  const raw = cookieStore.get("medmind_locale")?.value;
  return raw && SUPPORTED.includes(raw) ? raw : "en";
}

export default function NursesPage() {
  const locale = getLocale();
  const c = COPY[locale] ?? COPY.en;

  return (
    <div className="min-h-screen bg-bg">
      <ArticleNav />

      {/* Hero */}
      <section className="max-w-5xl mx-auto px-6 pt-20 pb-16 text-center">
        <span className="inline-block text-xs font-syne font-semibold bg-red/10 text-red border border-red/20 rounded-full px-4 py-1.5 mb-6">
          {c.hero_tag}
        </span>
        <h1 className="font-syne font-black text-4xl sm:text-5xl text-ink mb-5 leading-tight whitespace-pre-line">
          {c.hero_h1}
        </h1>
        <p className="text-ink-2 font-serif text-lg max-w-2xl mx-auto leading-relaxed mb-8">
          {c.hero_sub}
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <Link
            href="/register?role=nurse"
            className="font-syne font-bold text-sm bg-ink text-white px-8 py-3.5 rounded-xl hover:bg-red transition-colors"
          >
            {c.cta_primary}
          </Link>
          <Link
            href="/learn"
            className="font-syne font-semibold text-sm border border-border text-ink px-8 py-3.5 rounded-xl hover:border-ink transition-colors"
          >
            {c.cta_secondary}
          </Link>
        </div>

        {/* Social proof strip */}
        <div className="mt-12 flex flex-wrap justify-center gap-x-8 gap-y-3">
          {[
            "8 evidence-based modules",
            "SATA · Ordered · Calculation questions",
            "Dose-calc trainer",
            "7 languages",
            "Mobile offline",
          ].map(item => (
            <span key={item} className="text-xs font-syne font-semibold text-ink-3 flex items-center gap-1.5">
              <svg className="w-3.5 h-3.5 text-green flex-shrink-0" viewBox="0 0 16 16" fill="currentColor">
                <path d="M6.5 11.5l-3-3 1.06-1.06L6.5 9.38l5-5L12.56 5.44z"/>
              </svg>
              {item}
            </span>
          ))}
        </div>
      </section>

      {/* Modules grid */}
      <section className="max-w-5xl mx-auto px-6 pb-16">
        <div className="text-center mb-10">
          <h2 className="font-syne font-black text-2xl sm:text-3xl text-ink mb-3">{c.modules_h2}</h2>
          <p className="text-ink-2 font-serif text-base max-w-xl mx-auto">{c.modules_sub}</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {MODULES.map(m => (
            <div
              key={m.code}
              className="bg-surface border border-border rounded-xl p-5 hover:border-ink hover:shadow-sm transition-all"
            >
              <span className="text-2xl mb-3 block">{m.icon}</span>
              <h3 className="font-syne font-bold text-sm text-ink mb-1 leading-snug">{m.title}</h3>
              <p className="text-ink-3 font-serif text-xs leading-relaxed">{m.sub}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Dose calc highlight */}
      <section className="bg-surface border-y border-border py-16">
        <div className="max-w-5xl mx-auto px-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-10 items-center">
            <div>
              <span className="text-xs font-syne font-bold text-red uppercase tracking-wider">Killer feature</span>
              <h2 className="font-syne font-black text-2xl sm:text-3xl text-ink mt-2 mb-4">
                Dose-calculation trainer
              </h2>
              <p className="text-ink-2 font-serif leading-relaxed mb-6">
                Unlimited parametric practice problems — not AI-generated numbers, but deterministic clinical formulas. Every answer comes with a step-by-step solution. Five categories:
              </p>
              <ul className="space-y-2">
                {[
                  "Weight-based dosing (mg/kg → mL)",
                  "Infusion rate (mL/h and gtt/min)",
                  "Dilution and concentration",
                  "Unit conversion (mcg ↔ mg, mL ↔ L)",
                  "Paediatric dosing",
                ].map(item => (
                  <li key={item} className="flex items-center gap-2 text-sm font-serif text-ink">
                    <svg className="w-4 h-4 text-green flex-shrink-0" viewBox="0 0 16 16" fill="currentColor">
                      <path d="M6.5 11.5l-3-3 1.06-1.06L6.5 9.38l5-5L12.56 5.44z"/>
                    </svg>
                    {item}
                  </li>
                ))}
              </ul>
              <Link
                href="/register?role=nurse"
                className="inline-block mt-6 font-syne font-bold text-sm bg-ink text-white px-6 py-3 rounded-xl hover:bg-red transition-colors"
              >
                Try the trainer →
              </Link>
            </div>
            <div className="bg-bg border border-border rounded-2xl p-6 font-mono text-sm space-y-3">
              <div className="text-ink-3 text-xs font-syne mb-4 uppercase tracking-wider">Sample problem</div>
              <p className="text-ink font-semibold leading-relaxed">
                Patient weighs 72 kg. Order: gentamicin 5 mg/kg IV. Stock: 40 mg/mL. How many mL?
              </p>
              <div className="border-t border-border pt-3 space-y-1 text-ink-2">
                <p>Step 1: 72 kg × 5 mg/kg = <span className="text-ink font-semibold">360 mg</span></p>
                <p>Step 2: 360 mg ÷ 40 mg/mL = <span className="text-green font-semibold">9 mL</span></p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Feature grid */}
      <section className="max-w-5xl mx-auto px-6 py-16">
        <h2 className="font-syne font-black text-2xl sm:text-3xl text-ink text-center mb-10">{c.features_h2}</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {FEATURES.map(f => (
            <div key={f.title} className="bg-surface border border-border rounded-xl p-6">
              <div className="text-2xl mb-3">{f.icon}</div>
              <h3 className="font-syne font-bold text-sm text-ink mb-2">{f.title}</h3>
              <p className="text-ink-2 font-serif text-sm leading-relaxed">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="bg-ink text-white py-20">
        <div className="max-w-2xl mx-auto px-6 text-center">
          <h2 className="font-syne font-black text-3xl mb-4">{c.cta_final_h2}</h2>
          <p className="font-serif text-white/70 text-base mb-8">{c.cta_final_sub}</p>
          <Link
            href="/register?role=nurse"
            className="inline-block font-syne font-bold text-sm bg-white text-ink px-8 py-3.5 rounded-xl hover:bg-white/90 transition-colors"
          >
            {c.cta_final_btn}
          </Link>
        </div>
      </section>

      <PublicFooter />
    </div>
  );
}
