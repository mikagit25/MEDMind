import type { Metadata } from "next";
import { cookies } from "next/headers";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { getDisclaimerT } from "@/lib/trust-i18n";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const SUPPORTED = ["en", "ru", "ar", "tr", "de", "fr", "es"];

export const dynamic = "force-dynamic";

export async function generateMetadata({
  searchParams,
}: {
  searchParams?: { lang?: string };
}): Promise<Metadata> {
  const rawLocale = searchParams?.lang;
  const locale = rawLocale && SUPPORTED.includes(rawLocale) ? rawLocale : "en";
  const t = getDisclaimerT(locale);
  const canonical =
    locale !== "en"
      ? `${SITE_URL}/${locale}/medical-disclaimer`
      : `${SITE_URL}/medical-disclaimer`;
  return {
    title: t.meta_title,
    description: t.meta_desc,
    alternates: {
      canonical,
      languages: Object.fromEntries(
        SUPPORTED.map((l) => [
          l,
          l === "en" ? `${SITE_URL}/medical-disclaimer` : `${SITE_URL}/${l}/medical-disclaimer`,
        ])
      ),
    },
    openGraph: {
      title: t.meta_title,
      description: t.meta_desc,
      url: canonical,
      siteName: "MedMind AI",
      type: "website",
    },
  };
}

const SECTION_COLORS: Record<string, string> = {
  emergency: "border-red-400 bg-red-50",
  dosing: "border-orange-400 bg-orange-50",
};

export default async function MedicalDisclaimerPage({
  searchParams,
}: {
  searchParams?: { lang?: string };
}) {
  const cookieStore = cookies();
  const cookieLocale = cookieStore.get("locale")?.value;
  const rawLocale = searchParams?.lang ?? cookieLocale;
  const locale = rawLocale && SUPPORTED.includes(rawLocale) ? rawLocale : "en";
  const t = getDisclaimerT(locale);

  const schema = {
    "@context": "https://schema.org",
    "@type": "WebPage",
    name: t.meta_title,
    description: t.meta_desc,
    url: `${SITE_URL}/medical-disclaimer`,
    publisher: {
      "@type": "Organization",
      name: "MedMind AI",
      url: SITE_URL,
    },
  };

  const sections = [
    { key: "not_advice", title: t.not_advice_title, body: t.not_advice_body },
    { key: "emergency", title: t.emergency_title, body: t.emergency_body },
    { key: "accuracy", title: t.accuracy_title, body: t.accuracy_body },
    { key: "professional", title: t.professional_title, body: t.professional_body },
    { key: "dosing", title: t.dosing_title, body: t.dosing_body },
    { key: "liability", title: t.liability_title, body: t.liability_body },
  ];

  return (
    <div className="min-h-screen bg-bg" dir={t.dir}>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
      />
      <ArticleNav />

      {/* Hero */}
      <section className="bg-gradient-to-b from-amber-50 to-bg py-16 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <h1 className="font-syne font-extrabold text-4xl text-ink mb-4">{t.hero_title}</h1>
          <p className="text-ink-2 text-lg">{t.hero_sub}</p>
        </div>
      </section>

      <div className="max-w-3xl mx-auto px-6 py-12 space-y-8">
        {sections.map((s) => (
          <section
            key={s.key}
            className={`rounded-xl border-l-4 p-6 ${SECTION_COLORS[s.key] ?? "border-border bg-surface"}`}
          >
            <h2 className="font-syne font-bold text-lg text-ink mb-2">{s.title}</h2>
            <p className="text-ink-2 text-sm leading-relaxed">{s.body}</p>
          </section>
        ))}

        <p className="text-ink-3 text-xs text-center">{t.contact_note}</p>
      </div>

      <PublicFooter locale={locale} />
    </div>
  );
}
