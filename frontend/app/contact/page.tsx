import type { Metadata } from "next";
import { cookies } from "next/headers";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { PublicFooter } from "@/components/layout/PublicFooter";
import { getContactT } from "@/lib/trust-i18n";

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
  const t = getContactT(locale);
  const canonical = locale !== "en" ? `${SITE_URL}/${locale}/contact` : `${SITE_URL}/contact`;
  return {
    title: t.meta_title,
    description: t.meta_desc,
    alternates: {
      canonical,
      languages: Object.fromEntries(
        SUPPORTED.map((l) => [
          l,
          l === "en" ? `${SITE_URL}/contact` : `${SITE_URL}/${l}/contact`,
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

function ContactCard({
  title,
  email,
  icon,
}: {
  title: string;
  email: string;
  icon: string;
}) {
  return (
    <div className="bg-surface border border-border rounded-xl p-6 flex flex-col gap-3">
      <div className="text-3xl">{icon}</div>
      <h2 className="font-syne font-bold text-lg text-ink">{title}</h2>
      <a
        href={`mailto:${email}`}
        className="text-blue-600 hover:underline text-sm font-medium break-all"
      >
        {email}
      </a>
    </div>
  );
}

export default async function ContactPage({
  searchParams,
}: {
  searchParams?: { lang?: string };
}) {
  const cookieStore = cookies();
  const cookieLocale = cookieStore.get("locale")?.value;
  const rawLocale = searchParams?.lang ?? cookieLocale;
  const locale = rawLocale && SUPPORTED.includes(rawLocale) ? rawLocale : "en";
  const t = getContactT(locale);

  const schema = {
    "@context": "https://schema.org",
    "@type": "ContactPage",
    name: t.meta_title,
    description: t.meta_desc,
    url: `${SITE_URL}/contact`,
    publisher: {
      "@type": "Organization",
      name: "MedMind AI",
      url: SITE_URL,
      email: t.general_email,
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
      <section className="bg-gradient-to-b from-violet-50 to-bg py-16 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <h1 className="font-syne font-extrabold text-4xl text-ink mb-4">{t.hero_title}</h1>
          <p className="text-ink-2 text-lg">{t.hero_sub}</p>
        </div>
      </section>

      <div className="max-w-3xl mx-auto px-6 py-12">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-10">
          <ContactCard title={t.general_title} email={t.general_email} icon="✉️" />
          <ContactCard title={t.press_title} email={t.press_email} icon="📰" />
          <ContactCard title={t.partnership_title} email={t.partnership_email} icon="🤝" />
        </div>

        {/* Feedback / Errors */}
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-6">
          <h2 className="font-syne font-bold text-lg text-ink mb-2">{t.feedback_title}</h2>
          <p className="text-ink-2 text-sm leading-relaxed">{t.feedback_body}</p>
        </div>

        <p className="mt-8 text-xs text-ink-3 text-center">{t.response_note}</p>
      </div>

      <PublicFooter locale={locale} />
    </div>
  );
}
