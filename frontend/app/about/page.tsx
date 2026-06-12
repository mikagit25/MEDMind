import type { Metadata } from "next";
import Link from "next/link";
import { cookies } from "next/headers";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { getAboutT } from "@/lib/trust-i18n";

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
  const t = getAboutT(locale);
  const canonical = locale !== "en" ? `${SITE_URL}/${locale}/about` : `${SITE_URL}/about`;
  return {
    title: t.meta_title,
    description: t.meta_desc,
    alternates: {
      canonical,
      languages: Object.fromEntries(
        SUPPORTED.map((l) => [l, l === "en" ? `${SITE_URL}/about` : `${SITE_URL}/${l}/about`])
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

export default async function AboutPage({
  searchParams,
}: {
  searchParams?: { lang?: string };
}) {
  const cookieStore = cookies();
  const cookieLocale = cookieStore.get("locale")?.value;
  const rawLocale = searchParams?.lang ?? cookieLocale;
  const locale = rawLocale && SUPPORTED.includes(rawLocale) ? rawLocale : "en";
  const t = getAboutT(locale);

  const schema = {
    "@context": "https://schema.org",
    "@type": "AboutPage",
    name: t.meta_title,
    description: t.meta_desc,
    url: `${SITE_URL}/about`,
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
      <section className="bg-gradient-to-b from-blue-50 to-bg py-16 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <h1 className="font-syne font-extrabold text-4xl text-ink mb-4">{t.hero_title}</h1>
          <p className="text-ink-2 text-lg">{t.hero_sub}</p>
        </div>
      </section>

      <div className="max-w-3xl mx-auto px-6 py-12 space-y-12">
        {/* Mission */}
        <section>
          <h2 className="font-syne font-bold text-2xl text-ink mb-3">{t.mission_title}</h2>
          <p className="text-ink-2 leading-relaxed">{t.mission_body}</p>
        </section>

        {/* Who we serve */}
        <section>
          <h2 className="font-syne font-bold text-2xl text-ink mb-4">{t.for_whom_title}</h2>
          <ul className="space-y-3">
            {[t.for_whom_doctors, t.for_whom_students, t.for_whom_patients, t.for_whom_vet].map((item) => (
              <li key={item} className="flex gap-3 text-ink-2">
                <span className="text-blue-500 mt-0.5 flex-shrink-0">✓</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </section>

        {/* How content is created */}
        <section>
          <h2 className="font-syne font-bold text-2xl text-ink mb-6">{t.how_title}</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            {[
              { title: t.how_1_title, body: t.how_1_body },
              { title: t.how_2_title, body: t.how_2_body },
              { title: t.how_3_title, body: t.how_3_body },
              { title: t.how_4_title, body: t.how_4_body },
            ].map((step) => (
              <div key={step.title} className="bg-surface border border-border rounded-xl p-5">
                <h3 className="font-syne font-semibold text-sm text-ink mb-2">{step.title}</h3>
                <p className="text-ink-2 text-sm leading-relaxed">{step.body}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Team */}
        <section>
          <h2 className="font-syne font-bold text-2xl text-ink mb-3">{t.team_title}</h2>
          <p className="text-ink-2 leading-relaxed">{t.team_body}</p>
        </section>

        {/* CTA */}
        <section className="bg-blue-50 rounded-2xl p-8 text-center">
          <h2 className="font-syne font-bold text-xl text-ink mb-4">{t.cta_title}</h2>
          <Link
            href="/register"
            className="inline-block bg-ink text-white font-syne font-semibold px-6 py-3 rounded-xl hover:bg-ink/80 transition-colors"
          >
            {t.cta_btn}
          </Link>
        </section>
      </div>

      <PublicFooter locale={locale} />
    </div>
  );
}
