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

// ── Contact cards ─────────────────────────────────────────────────────────────

function PartnershipCard({ title, email }: { title: string; email: string }) {
  return (
    <div className="bg-surface border border-border rounded-xl p-6 flex flex-col gap-3">
      <div className="text-3xl">🤝</div>
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

function FounderCard({
  title,
  phoneLabel,
}: {
  title: string;
  phoneLabel: string;
}) {
  return (
    <div className="bg-surface border border-border rounded-xl p-6 flex flex-col gap-3">
      <div className="text-3xl">👤</div>
      <h2 className="font-syne font-bold text-lg text-ink">{title}</h2>
      <p className="font-syne font-semibold text-sm text-ink">Mikalai Mikheyeu</p>
      <a
        href="https://www.linkedin.com/in/mikalai-mikheyeu/"
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-2 text-blue-600 hover:underline text-sm font-medium"
      >
        <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor">
          <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
        </svg>
        LinkedIn
      </a>
      <div className="flex items-center gap-2 text-sm text-ink-2">
        <span className="text-ink-3 text-xs font-syne uppercase tracking-wide">{phoneLabel}:</span>
        <a href="tel:+375296945071" className="hover:text-ink transition-colors">
          +375 29 694-50-71
        </a>
      </div>
    </div>
  );
}

function CompanyCard({
  title,
  emailLabel,
  phoneLabel,
}: {
  title: string;
  emailLabel: string;
  phoneLabel: string;
}) {
  return (
    <div className="bg-surface border border-border rounded-xl p-6 flex flex-col gap-3">
      <div className="text-3xl">🏢</div>
      <h2 className="font-syne font-bold text-lg text-ink">{title}</h2>
      <p className="font-syne font-semibold text-sm text-ink leading-snug">
        Частное предприятие «Первая Компания»
      </p>
      <div className="flex items-center gap-2 text-sm text-ink-2">
        <span className="text-ink-3 text-xs font-syne uppercase tracking-wide">{emailLabel}:</span>
        <a
          href="mailto:6035582@gmail.com"
          className="text-blue-600 hover:underline break-all"
        >
          6035582@gmail.com
        </a>
      </div>
      <div className="flex items-center gap-2 text-sm text-ink-2">
        <span className="text-ink-3 text-xs font-syne uppercase tracking-wide">{phoneLabel}:</span>
        <a href="tel:+375296035582" className="hover:text-ink transition-colors">
          +375 29 603-55-82
        </a>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

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
      email: t.partnership_email,
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
        {/* Contact cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-6">
          <FounderCard title={t.founder_title} phoneLabel={t.phone_label} />
          <CompanyCard title={t.company_title} emailLabel={t.email_label} phoneLabel={t.phone_label} />
        </div>
        <div className="mb-10">
          <PartnershipCard title={t.partnership_title} email={t.partnership_email} />
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
