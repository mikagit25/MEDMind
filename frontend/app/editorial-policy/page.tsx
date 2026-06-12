import type { Metadata } from "next";
import { cookies } from "next/headers";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { getEditorialT } from "@/lib/trust-i18n";

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
  const t = getEditorialT(locale);
  const canonical =
    locale !== "en" ? `${SITE_URL}/${locale}/editorial-policy` : `${SITE_URL}/editorial-policy`;
  return {
    title: t.meta_title,
    description: t.meta_desc,
    alternates: {
      canonical,
      languages: Object.fromEntries(
        SUPPORTED.map((l) => [
          l,
          l === "en" ? `${SITE_URL}/editorial-policy` : `${SITE_URL}/${l}/editorial-policy`,
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

export default async function EditorialPolicyPage({
  searchParams,
}: {
  searchParams?: { lang?: string };
}) {
  const cookieStore = cookies();
  const cookieLocale = cookieStore.get("locale")?.value;
  const rawLocale = searchParams?.lang ?? cookieLocale;
  const locale = rawLocale && SUPPORTED.includes(rawLocale) ? rawLocale : "en";
  const t = getEditorialT(locale);

  const schema = {
    "@context": "https://schema.org",
    "@type": "WebPage",
    name: t.meta_title,
    description: t.meta_desc,
    url: `${SITE_URL}/editorial-policy`,
    publisher: {
      "@type": "Organization",
      name: "MedMind AI",
      url: SITE_URL,
    },
  };

  return (
    <div className="min-h-screen bg-bg" dir={t.dir}>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
      />
      <ArticleNav />

      {/* Hero */}
      <section className="bg-gradient-to-b from-emerald-50 to-bg py-16 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <h1 className="font-syne font-extrabold text-4xl text-ink mb-4">{t.hero_title}</h1>
          <p className="text-ink-2 text-lg">{t.hero_sub}</p>
        </div>
      </section>

      <div className="max-w-3xl mx-auto px-6 py-12 space-y-10">
        {/* Sources */}
        <section>
          <h2 className="font-syne font-bold text-2xl text-ink mb-3">{t.sources_title}</h2>
          <p className="text-ink-2 mb-4">{t.sources_body}</p>
          <ul className="space-y-2 text-ink-2 text-sm">
            <li className="flex gap-2">
              <span className="font-semibold text-emerald-600 flex-shrink-0">Tier 1:</span>
              <span>{t.sources_tier1}</span>
            </li>
            <li className="flex gap-2">
              <span className="font-semibold text-emerald-500 flex-shrink-0">Tier 2:</span>
              <span>{t.sources_tier2}</span>
            </li>
            <li className="flex gap-2">
              <span className="font-semibold text-emerald-400 flex-shrink-0">Tier 3:</span>
              <span>{t.sources_tier3}</span>
            </li>
          </ul>
        </section>

        {/* AI Generation */}
        <section>
          <h2 className="font-syne font-bold text-2xl text-ink mb-3">{t.generation_title}</h2>
          <p className="text-ink-2 leading-relaxed">{t.generation_body}</p>
        </section>

        {/* Automated Verification */}
        <section>
          <h2 className="font-syne font-bold text-2xl text-ink mb-3">{t.verification_title}</h2>
          <p className="text-ink-2 mb-4">{t.verification_body}</p>
          <ol className="space-y-2 list-decimal list-inside text-ink-2 text-sm">
            {t.verification_steps.map((step, i) => (
              <li key={i}>{step}</li>
            ))}
          </ol>
        </section>

        {/* Human Review */}
        <section>
          <h2 className="font-syne font-bold text-2xl text-ink mb-3">{t.human_review_title}</h2>
          <p className="text-ink-2 leading-relaxed">{t.human_review_body}</p>
        </section>

        {/* Updates */}
        <section>
          <h2 className="font-syne font-bold text-2xl text-ink mb-3">{t.updates_title}</h2>
          <p className="text-ink-2 leading-relaxed">{t.updates_body}</p>
        </section>

        {/* Feedback */}
        <section className="bg-emerald-50 rounded-2xl p-6">
          <h2 className="font-syne font-bold text-xl text-ink mb-2">{t.feedback_title}</h2>
          <p className="text-ink-2 text-sm">{t.feedback_body}</p>
        </section>
      </div>

      <PublicFooter locale={locale} />
    </div>
  );
}
