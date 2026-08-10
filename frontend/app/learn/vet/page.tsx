import type { Metadata } from "next";
import Link from "next/link";
import { getLearnT } from "@/lib/learn-i18n";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const API_URL =
  process.env.INTERNAL_API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000/api/v1";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Veterinary Medicine — Clinical Modules | MedMind",
  description:
    "Clinical modules for veterinary students and practitioners. Small animals, large animals, exotic species, pharmacology, surgery — with species-adjusted drug dosing and clinical cases.",
  alternates: { canonical: `${SITE_URL}/learn/vet` },
  openGraph: {
    title: "Veterinary Medicine — MedMind",
    description: "Clinical modules for vet students & professionals.",
    url: `${SITE_URL}/learn/vet`,
    type: "website",
  },
};

// Map Russian specialty names → display data
// (API returns specialty names in Russian, we map to localized display info)
const VET_SPEC_MAP: Record<string, { icon: string; en: string; modulePrefix: string }> = {
  "Ветеринария":              { icon: "🐾", en: "General Veterinary",      modulePrefix: "VET" },
  "Мелкие животные":          { icon: "🐕", en: "Small Animals",            modulePrefix: "VET" },
  "Крупные животные / Лошади":{ icon: "🐎", en: "Large Animals & Equine",   modulePrefix: "VET" },
  "Зоопарковая медицина":     { icon: "🦁", en: "Zoo Medicine",             modulePrefix: "VET" },
  "Птицы":                    { icon: "🦜", en: "Avian Medicine",           modulePrefix: "VET" },
  "Экзотические животные":    { icon: "🦎", en: "Exotic Animals",           modulePrefix: "VET" },
};

const SPEC_DISPLAY_NAMES: Record<string, Record<string, string>> = {
  "Ветеринария":               { en: "General Veterinary", ru: "Общая ветеринария", ar: "الطب البيطري العام", tr: "Genel Veterinerlik", de: "Allgemeine Veterinärmedizin", fr: "Médecine vétérinaire générale", es: "Medicina Veterinaria General" },
  "Мелкие животные":           { en: "Small Animals",      ru: "Мелкие животные",   ar: "الحيوانات الصغيرة",   tr: "Küçük Hayvanlar",    de: "Kleintiere",           fr: "Petits animaux",   es: "Animales pequeños" },
  "Крупные животные / Лошади": { en: "Large Animals & Equine", ru: "Крупные животные / Лошади", ar: "الحيوانات الكبيرة والخيول", tr: "Büyük Hayvanlar / Atlar", de: "Großtiere & Pferde", fr: "Grands animaux & Équins", es: "Animales grandes y Équidos" },
  "Зоопарковая медицина":      { en: "Zoo Medicine",       ru: "Зоопарковая медицина", ar: "طب حديقة الحيوان", tr: "Hayvanat Bahçesi Tıbbı", de: "Zootierkunde",     fr: "Médecine zoo",     es: "Medicina de Zoológico" },
  "Птицы":                     { en: "Avian Medicine",     ru: "Птицы",             ar: "طب الطيور",          tr: "Kanatlı Tıbbı",      de: "Vogelmedizin",         fr: "Médecine aviaire", es: "Medicina Aviar" },
  "Экзотические животные":     { en: "Exotic Animals",     ru: "Экзотические животные", ar: "الحيوانات الغريبة", tr: "Egzotik Hayvanlar", de: "Exoten",              fr: "Animaux exotiques",es: "Animales exóticos" },
};

type PublicTopic = {
  module_code: string;
  slug: string;
  title: string;
  title_en?: string | null;
  specialty: string | null;
  specialty_en?: string | null;
  lesson_count: number;
  lay_summary: string | null;
};

async function fetchVetTopics(): Promise<PublicTopic[]> {
  try {
    const res = await fetch(`${API_URL}/public/topics?limit=200`, {
      next: { revalidate: 86400 },
    });
    if (!res.ok) return [];
    const all: PublicTopic[] = await res.json();
    return all.filter(
      (t) =>
        t.specialty !== null &&
        t.specialty in VET_SPEC_MAP &&
        t.module_code.startsWith("VET")
    );
  } catch {
    return [];
  }
}

export default async function VetPage({
  searchParams,
}: {
  searchParams?: { lang?: string };
}) {
  const lang = searchParams?.lang ?? "en";
  const [topics, t] = await Promise.all([
    fetchVetTopics(),
    Promise.resolve(getLearnT(lang)),
  ]);

  // Group by specialty, same order as VET_SPEC_MAP
  const specOrder = Object.keys(VET_SPEC_MAP);
  const grouped: Record<string, PublicTopic[]> = {};
  for (const topic of topics) {
    const key = topic.specialty!;
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(topic);
  }
  const specs = specOrder.filter((s) => grouped[s]?.length > 0);

  const totalModules = topics.length;

  return (
    <>
      <script
        type="application/ld+json"
        suppressHydrationWarning
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "MedicalWebPage",
            name: "Veterinary Medicine Modules",
            description: "Clinical modules for veterinary students and practitioners",
            url: `${SITE_URL}/learn/vet`,
            audience: { "@type": "MedicalAudience", audienceType: "Veterinarian" },
          }),
        }}
      />

      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10">
        {/* Hero */}
        <div className="text-center mb-12">
          <div className="inline-block px-3 py-1 rounded-full bg-green-50 border border-green-200 font-syne font-semibold text-xs text-green-700 mb-4">
            🩺 {t.vet_badge}
          </div>
          <h1 className="font-syne font-black text-4xl sm:text-5xl text-ink mb-4 leading-tight">
            {t.vet_h1}
          </h1>
          <p className="font-serif text-ink-3 text-lg max-w-2xl mx-auto mb-6 leading-relaxed">
            {t.vet_subtitle}
          </p>
          {totalModules > 0 && (
            <div className="inline-flex items-center gap-2 font-syne font-black text-3xl text-ink mb-6">
              {totalModules}+
              <span className="font-serif font-normal text-base text-ink-3">{t.vet_modules_label}</span>
            </div>
          )}
        </div>

        {/* Disclaimer */}
        <div className="bg-amber-light border border-amber/30 rounded-lg p-4 mb-10 flex gap-3 max-w-2xl mx-auto">
          <span className="flex-shrink-0">🔬</span>
          <p className="font-serif text-sm text-amber-dark">{t.vet_disclaimer}</p>
        </div>

        {/* Specialties */}
        {specs.length > 0 && (
          <div className="mb-14">
            <h2 className="font-syne font-black text-xl text-ink mb-6 text-center">{t.vet_specs_title}</h2>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {specs.map((spec) => {
                const meta = VET_SPEC_MAP[spec];
                const displayName =
                  SPEC_DISPLAY_NAMES[spec]?.[lang] ??
                  SPEC_DISPLAY_NAMES[spec]?.en ??
                  spec;
                const mods = grouped[spec];
                return (
                  <div
                    key={spec}
                    className="bg-surface border border-border rounded-2xl p-5 hover:border-ink hover:shadow-sm transition-all"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <span className="text-3xl">{meta.icon}</span>
                      <span className="font-serif text-xs text-ink-3/60 bg-bg-2 px-2 py-0.5 rounded border border-border">
                        {mods.length} {t.vet_modules_label}
                      </span>
                    </div>
                    <h3 className="font-syne font-bold text-base text-ink mb-3">{displayName}</h3>
                    <ul className="space-y-1.5">
                      {mods.slice(0, 4).map((m) => (
                        <li key={m.slug} className="font-serif text-xs text-ink-3 flex items-start gap-1.5">
                          <span className="flex-shrink-0 mt-0.5">›</span>
                          <span className="line-clamp-1">{m.title}</span>
                        </li>
                      ))}
                      {mods.length > 4 && (
                        <li className="font-serif text-xs text-ink-3/60">+{mods.length - 4} more…</li>
                      )}
                    </ul>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* CTA block */}
        <div className="bg-ink rounded-2xl p-8 text-center mb-8">
          <div className="font-syne font-black text-2xl text-white mb-2">{t.vet_cta_h2}</div>
          <p className="font-serif text-sm text-white/70 mb-6 max-w-xl mx-auto">{t.vet_cta_desc}</p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link
              href="/register"
              className="px-7 py-3 rounded-xl bg-white text-ink font-syne font-bold text-sm hover:bg-gray-100 transition-colors"
            >
              {t.vet_cta_signup}
            </Link>
            <Link
              href="/login"
              className="px-7 py-3 rounded-xl border border-white/20 text-white font-syne font-bold text-sm hover:border-white/60 transition-colors"
            >
              {t.vet_cta_login}
            </Link>
          </div>
        </div>

        {/* Link back to pet owners */}
        <div className="text-center">
          <span className="font-serif text-sm text-ink-3">{t.vet_pet_owners} </span>
          <Link href="/learn/pets" className="font-syne font-semibold text-sm text-ink hover:text-accent transition-colors">
            {t.vet_pet_owners_link}
          </Link>
        </div>
      </div>
    </>
  );
}
