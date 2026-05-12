import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { cookies } from "next/headers";
import { getCategoryLabel, getMoreIn, CATEGORY_ICONS } from "@/lib/categories";
import { ArticleViewTracker } from "./ArticleViewTracker";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { ArticleAudioPlayer } from "@/components/ui/ArticleAudioPlayer";
import { BookmarkButton } from "@/components/ui/BookmarkButton";
import { ArticleReadTracker } from "@/components/ui/ArticleReadTracker";
import { ArticleQuiz } from "@/components/ui/ArticleQuiz";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const API_URL = process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

// Force dynamic rendering so searchParams (locale) are always respected
export const dynamic = "force-dynamic";

const LOCALE_LABELS: Record<string, string> = {
  en: "English",
  ru: "Русский",
  ar: "العربية",
  tr: "Türkçe",
  de: "Deutsch",
  fr: "Français",
  es: "Español",
};


type Block =
  | { type: "h2"; content: string }
  | { type: "h3"; content: string }
  | { type: "p"; content: string }
  | { type: "ul"; items: string[] }
  | { type: "callout"; variant: "warning" | "info" | "tip"; content: string }
  | { type: "table"; headers: string[]; rows: string[][] }
  | { type: "image"; url: string; caption?: string; alt?: string };

type VerifiedSource = {
  pmid: string;
  title: string;
  authors: string;
  journal: string;
  year: string;
  url: string;
};

type ArticleDetail = {
  id: string;
  slug: string;
  title: string;
  excerpt: string;
  og_title: string | null;
  og_description: string | null;
  category: string;
  subcategory: string | null;
  keywords: string[];
  reading_time_minutes: number;
  schema_type: string;
  published_at: string | null;
  body: Block[];
  faq: { question: string; answer: string }[];
  sources: { title: string; url: string; pmid: string | null }[];
  related_module_code: string | null;
  author: { name: string; bio: string | null; is_ai: boolean } | null;
  // Verification
  verification_status: "unverified" | "ai_verified" | "expert_verified";
  verified_sources: VerifiedSource[];
  last_verified_at: string | null;
  generated_by: string | null;
};

async function fetchArticle(slug: string, locale?: string): Promise<ArticleDetail | null> {
  try {
    const url = locale && locale !== "en"
      ? `${API_URL}/articles/${slug}?locale=${locale}`
      : `${API_URL}/articles/${slug}`;
    // no-store: article content is locale-dependent (dynamic) and translates over time
    const res = await fetch(url, { cache: "no-store" });
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch {
    return null;
  }
}

async function fetchAvailableLocales(slug: string): Promise<string[]> {
  try {
    const res = await fetch(`${API_URL}/articles/${slug}/available-locales`, {
      next: { revalidate: 300 },
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.locales ?? [];
  } catch {
    return [];
  }
}

type RelatedArticle = {
  slug: string;
  title: string;
  excerpt: string;
  reading_time_minutes: number;
};

type ArticleNav = {
  prev: { slug: string; title: string } | null;
  next: { slug: string; title: string } | null;
};

async function fetchRelated(slug: string, locale?: string): Promise<RelatedArticle[]> {
  try {
    const localeParam = locale && locale !== "en" ? `?locale=${locale}` : "";
    const res = await fetch(`${API_URL}/articles/${slug}/related${localeParam}`, {
      cache: "no-store",
    });
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

async function fetchNav(slug: string, locale?: string): Promise<ArticleNav> {
  try {
    const localeParam = locale && locale !== "en" ? `?locale=${locale}` : "";
    const res = await fetch(`${API_URL}/articles/${slug}/nav${localeParam}`, {
      cache: "no-store",
    });
    if (!res.ok) return { prev: null, next: null };
    return await res.json();
  } catch {
    return { prev: null, next: null };
  }
}

type LinkMapEntry = { term: string; slug: string };

async function fetchLinkMap(): Promise<LinkMapEntry[]> {
  try {
    const res = await fetch(`${API_URL}/articles/link-map`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

type ModuleInfo = { id: string; title: string; code: string } | null;

async function fetchModuleByCode(code: string): Promise<ModuleInfo> {
  try {
    const res = await fetch(`${API_URL}/articles/module-by-code/${encodeURIComponent(code)}`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
  searchParams,
}: {
  params: { slug: string };
  searchParams?: { lang?: string; locale?: string };
}): Promise<Metadata> {
  const SUPPORTED = ["en", "ru", "ar", "tr", "de", "fr", "es"];
  const rawLocale = searchParams?.lang || searchParams?.locale;
  const locale = rawLocale && SUPPORTED.includes(rawLocale) ? rawLocale : "en";
  const article = await fetchArticle(params.slug, locale);
  if (!article) return { title: "Article not found" };

  const availableLocales = await fetchAvailableLocales(params.slug);
  const title = article.og_title ?? article.title;
  const description = article.og_description ?? article.excerpt;
  const canonicalUrl = `${SITE_URL}/articles/${article.slug}`;
  const currentUrl = locale !== "en"
    ? `${SITE_URL}/articles/${article.slug}?lang=${locale}`
    : canonicalUrl;

  // Build hreflang alternates for all available translations
  const hreflangAlternates: Record<string, string> = {
    "x-default": canonicalUrl,
    en: canonicalUrl,
  };
  for (const loc of availableLocales) {
    hreflangAlternates[loc] = `${SITE_URL}/articles/${article.slug}?lang=${loc}`;
  }

  return {
    title,
    description,
    keywords: article.keywords,
    alternates: {
      canonical: currentUrl,
      languages: hreflangAlternates,
    },
    openGraph: {
      title,
      description,
      url: currentUrl,
      siteName: "MedMind AI",
      type: "article",
      publishedTime: article.published_at ?? undefined,
      section: getCategoryLabel(article.category, locale),
      tags: article.keywords,
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
    },
  };
}

// schema.org structured data
function buildSchemaOrg(article: ArticleDetail, moduleInfo?: ModuleInfo, locale = "en"): object[] {
  const url = `${SITE_URL}/articles/${article.slug}`;
  const base = {
    "@context": "https://schema.org",
    "@type": article.schema_type === "Drug"
      ? "Drug"
      : article.schema_type === "MedicalCondition"
      ? "MedicalCondition"
      : article.schema_type === "MedicalProcedure"
      ? "MedicalProcedure"
      : "MedicalWebPage",
    name: article.title,
    description: article.excerpt,
    url,
    datePublished: article.published_at,
    publisher: {
      "@type": "Organization",
      name: "MedMind AI",
      url: SITE_URL,
    },
    mainEntityOfPage: { "@type": "WebPage", "@id": url },
  };

  // Breadcrumb
  const breadcrumb = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Home", item: SITE_URL },
      { "@type": "ListItem", position: 2, name: "Articles", item: `${SITE_URL}/articles` },
      {
        "@type": "ListItem",
        position: 3,
        name: getCategoryLabel(article.category, locale),
        item: `${SITE_URL}/articles/category/${article.category}`,
      },
      { "@type": "ListItem", position: 4, name: article.title, item: url },
    ],
  };

  // FAQ schema
  const faqSchema = article.faq?.length
    ? {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        mainEntity: article.faq.map((f) => ({
          "@type": "Question",
          name: f.question,
          acceptedAnswer: { "@type": "Answer", text: f.answer },
        })),
      }
    : null;

  // Course schema — link this article to the related MedMind learning module
  const courseSchema = moduleInfo
    ? {
        "@context": "https://schema.org",
        "@type": "Course",
        name: moduleInfo.title,
        description: article.excerpt,
        url: `${SITE_URL}/modules/${moduleInfo.id}`,
        provider: {
          "@type": "Organization",
          name: "MedMind AI",
          url: SITE_URL,
        },
        hasCourseInstance: {
          "@type": "CourseInstance",
          courseMode: "online",
          url: `${SITE_URL}/modules/${moduleInfo.id}`,
        },
      }
    : null;

  const schemas: object[] = [base, breadcrumb];
  if (faqSchema) schemas.push(faqSchema);
  if (courseSchema) schemas.push(courseSchema);
  return schemas;
}

// ── Internal linking ──────────────────────────────────────────────────────────

/**
 * Replace medical term occurrences in a paragraph with internal article links.
 * Terms are matched case-insensitively. Each term is linked at most once per
 * paragraph to avoid noise. Returns an array of React nodes.
 */
function linkifyText(
  text: string,
  linkMap: LinkMapEntry[],
  currentSlug: string
): React.ReactNode[] {
  if (!linkMap.length || !text) return [text];

  // Only link terms that are different from the current article
  const candidates = linkMap.filter((e) => e.slug !== currentSlug);
  if (!candidates.length) return [text];

  // Build one regex that matches any candidate term (longest first)
  const escaped = candidates.map((e) =>
    e.term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
  );
  const pattern = new RegExp(`\\b(${escaped.join("|")})\\b`, "gi");

  const parts: React.ReactNode[] = [];
  let last = 0;
  let match: RegExpExecArray | null;
  const linked = new Set<string>(); // link each term once per paragraph

  while ((match = pattern.exec(text)) !== null) {
    const matched = match[0];
    const key = matched.toLowerCase();
    if (linked.has(key)) continue;
    linked.add(key);

    const entry = candidates.find((e) => e.term.toLowerCase() === key);
    if (!entry) continue;

    if (match.index > last) {
      parts.push(text.slice(last, match.index));
    }
    parts.push(
      <a
        key={`${key}-${match.index}`}
        href={`/articles/${entry.slug}`}
        className="text-accent underline underline-offset-2 hover:text-accent-2 transition-colors"
      >
        {matched}
      </a>
    );
    last = match.index + matched.length;
    // Advance to avoid re-matching same position
    pattern.lastIndex = last;
  }

  if (last < text.length) parts.push(text.slice(last));
  return parts.length ? parts : [text];
}

const CALLOUT_STYLES: Record<string, string> = {
  warning: "bg-amber-light border-amber/30 text-amber-900",
  info: "bg-blue-light border-blue/30 text-blue-900",
  tip: "bg-green-light border-green/30 text-green-900",
};
const CALLOUT_ICONS: Record<string, string> = {
  warning: "⚠️", info: "ℹ️", tip: "💡",
};

function renderBlock(
  block: Block,
  i: number,
  linkMap: LinkMapEntry[] = [],
  currentSlug = ""
) {
  switch (block.type) {
    case "h2":
      return <h2 key={i} className="font-syne font-bold text-xl text-ink mt-8 mb-3">{block.content}</h2>;
    case "h3":
      return <h3 key={i} className="font-syne font-semibold text-base text-ink mt-6 mb-2">{block.content}</h3>;
    case "p":
      return (
        <p key={i} className="font-serif text-ink-2 text-base leading-relaxed mb-4">
          {linkifyText(block.content, linkMap, currentSlug)}
        </p>
      );
    case "ul":
      return (
        <ul key={i} className="list-disc list-inside space-y-1.5 mb-4 ml-2">
          {block.items.map((item, j) => (
            <li key={j} className="font-serif text-ink-2 text-base">{item}</li>
          ))}
        </ul>
      );
    case "callout":
      return (
        <div key={i} className={`border rounded-lg px-5 py-4 mb-4 ${CALLOUT_STYLES[block.variant] ?? CALLOUT_STYLES.info}`}>
          <span className="mr-2">{CALLOUT_ICONS[block.variant] ?? "ℹ️"}</span>
          <span className="font-serif text-sm">{block.content}</span>
        </div>
      );
    case "table":
      return (
        <div key={i} className="overflow-x-auto mb-6 rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead className="bg-surface-2">
              <tr>
                {block.headers.map((h, j) => (
                  <th key={j} className="text-left px-4 py-2.5 font-syne font-semibold text-ink-2 text-xs uppercase border-b border-border">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {block.rows.map((row, j) => (
                <tr key={j} className="border-t border-border hover:bg-surface-2">
                  {row.map((cell, k) => (
                    <td key={k} className="px-4 py-2.5 font-serif text-ink-2">{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    case "image":
      return (
        <figure key={i} className="mb-6">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={block.url}
            alt={block.alt ?? block.caption ?? ""}
            className="w-full rounded-lg border border-border object-contain max-h-[500px]"
            loading="lazy"
          />
          {block.caption && (
            <figcaption className="text-center text-xs font-serif text-ink-3 mt-2 px-2">
              {block.caption}
            </figcaption>
          )}
        </figure>
      );
    default:
      return null;
  }
}

// Simple server-side labels (SSR can't use useT hook)
const SERVER_LABELS: Record<string, Record<string, string>> = {
  en: { faq: "{ui.faq}", refs: "References", disclaimer: "Medical Disclaimer", related: "Related Articles", read_in: "Read in", module: "Study this topic in-depth", open_module: "Open module →" },
  ru: { faq: "Часто задаваемые вопросы", refs: "Источники", disclaimer: "Медицинский дисклеймер", related: "Похожие статьи", read_in: "Читать на", module: "Изучить тему подробнее", open_module: "Открыть модуль →" },
  de: { faq: "Häufig gestellte Fragen", refs: "Referenzen", disclaimer: "Medizinischer Haftungsausschluss", related: "Verwandte Artikel", read_in: "Lesen auf", module: "Dieses Thema vertiefen", open_module: "Modul öffnen →" },
  fr: { faq: "Questions fréquemment posées", refs: "Références", disclaimer: "Avertissement médical", related: "Articles connexes", read_in: "Lire en", module: "Approfondir ce sujet", open_module: "Ouvrir le module →" },
  ar: { faq: "الأسئلة الشائعة", refs: "المراجع", disclaimer: "إخلاء المسؤولية الطبية", related: "مقالات ذات صلة", read_in: "اقرأ بـ", module: "ادرس هذا الموضوع بعمق", open_module: "→ فتح الوحدة" },
  tr: { faq: "Sık Sorulan Sorular", refs: "Kaynaklar", disclaimer: "Tıbbi Sorumluluk Reddi", related: "İlgili Makaleler", read_in: "Oku:", module: "Bu konuyu derinlemesine incele", open_module: "Modülü aç →" },
  es: { faq: "Preguntas frecuentes", refs: "Referencias", disclaimer: "Aviso médico", related: "Artículos relacionados", read_in: "Leer en", module: "Estudiar este tema en profundidad", open_module: "Abrir módulo →" },
};

export default async function ArticlePage({
  params,
  searchParams,
}: {
  params: { slug: string };
  searchParams?: { lang?: string; locale?: string };
}) {
  // 1. Explicit lang param wins; 2. fall back to user's cookie locale
  const SUPPORTED = ["en", "ru", "ar", "tr", "de", "fr", "es"];
  const cookieLocale = cookies().get("medmind_locale")?.value;
  const rawLocale = searchParams?.lang || searchParams?.locale || cookieLocale;
  const locale = rawLocale && SUPPORTED.includes(rawLocale) ? rawLocale : "en";
  const ui = SERVER_LABELS[locale] ?? SERVER_LABELS.en;
  const [article, availableLocales, related, nav, linkMap] = await Promise.all([
    fetchArticle(params.slug, locale),
    fetchAvailableLocales(params.slug),
    fetchRelated(params.slug, locale),
    fetchNav(params.slug, locale),
    fetchLinkMap(),
  ]);
  if (!article) notFound();

  // Resolve module if article has a related module code
  const moduleInfo = article.related_module_code
    ? await fetchModuleByCode(article.related_module_code)
    : null;

  const schema = buildSchemaOrg(article, moduleInfo, locale);
  const allLocales = ["en", ...availableLocales.filter((l) => l !== "en")];

  return (
    <div className="min-h-screen bg-bg">
      {/* Structured data */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
      />

      {/* View tracking + reading progress (client-side) */}
      <ArticleViewTracker slug={article.slug} />
      <ArticleReadTracker slug={article.slug} />

      <ArticleNav />

      <div
        className="max-w-6xl mx-auto px-6 py-10 grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-10"
        dir={locale === "ar" ? "rtl" : "ltr"}
      >
        {/* Main content */}
        <main>
          {/* Breadcrumb */}
          <nav className="flex items-center gap-1.5 text-xs font-serif text-ink-3 mb-6" aria-label="Breadcrumb">
            <Link href="/articles" className="hover:text-ink">Articles</Link>
            <span>/</span>
            <Link href={`/articles/category/${article.category}`} className="hover:text-ink capitalize">
              {getCategoryLabel(article.category, locale)}
            </Link>
            <span>/</span>
            <span className="text-ink-2 truncate max-w-xs">{article.title}</span>
          </nav>

          {/* Header */}
          <div className="mb-8">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xs font-syne font-semibold border border-border rounded-full px-3 py-0.5 text-ink-2">
                {getCategoryLabel(article.category, locale)}
              </span>
              {article.subcategory && (
                <span className="text-xs font-syne font-semibold border border-border rounded-full px-3 py-0.5 text-ink-3">
                  {article.subcategory}
                </span>
              )}
            </div>
            <h1 className="font-syne font-black text-3xl md:text-4xl text-ink leading-tight mb-4">
              {article.title}
            </h1>
            <p className="font-serif text-ink-2 text-lg leading-relaxed">
              {article.excerpt}
            </p>
            <div className="flex items-center gap-4 mt-4 text-xs font-serif text-ink-3 flex-wrap">
              <span>📖 {article.reading_time_minutes} min read</span>
              {article.published_at && (
                <span>
                  {new Date(article.published_at).toLocaleDateString(
                    locale === "ar" ? "ar-SA" : locale === "ru" ? "ru-RU" : "en-US",
                    { year: "numeric", month: "long", day: "numeric" }
                  )}
                </span>
              )}
              <span>{article.author?.name ?? "MedMind AI Editorial"}</span>
              <BookmarkButton articleId={article.id} />
            </div>

            {/* Audio player */}
            <ArticleAudioPlayer articleId={article.id} locale={locale} title={article.title} />

            {/* Verification badge */}
            {article.verification_status === "expert_verified" ? (
              <div className="mt-4 inline-flex items-center gap-2 bg-green-light border border-green/30 rounded-lg px-3 py-2">
                <span className="text-green text-base">✅</span>
                <div>
                  <div className="font-syne font-bold text-xs text-green">Expert Verified</div>
                  <div className="font-serif text-[11px] text-ink-2">Reviewed by a licensed healthcare professional</div>
                </div>
              </div>
            ) : article.verification_status === "ai_verified" ? (
              <div className="mt-4 inline-flex items-center gap-2 bg-blue-50 border border-blue-200 rounded-lg px-3 py-2">
                <span className="text-blue-500 text-base">🔬</span>
                <div>
                  <div className="font-syne font-bold text-xs text-blue-700">AI Cross-Referenced</div>
                  <div className="font-serif text-[11px] text-ink-2">
                    Topic validated against {article.verified_sources?.length ?? 0} PubMed-indexed publications
                    {article.last_verified_at && ` · ${new Date(article.last_verified_at).toLocaleDateString("en-US", {month:"short", year:"numeric"})}`}
                  </div>
                </div>
              </div>
            ) : (
              <div className="mt-4 inline-flex items-center gap-2 bg-amber-50 border border-amber/30 rounded-lg px-3 py-2">
                <span className="text-amber text-base">⚠️</span>
                <div>
                  <div className="font-syne font-bold text-xs text-amber-800">AI-Generated · Not Verified</div>
                  <div className="font-serif text-[11px] text-ink-2">Content has not been cross-referenced with medical literature</div>
                </div>
              </div>
            )}
          </div>

          {/* Body */}
          <article className="prose-custom">
            {article.body.map((block, i) => renderBlock(block, i, linkMap, article.slug))}
          </article>

          {/* Author bio — only for human authors */}
          {article.author && !article.author.is_ai && (
            <div className="mt-10 border-t border-border pt-6 flex items-start gap-4">
              <div className="w-10 h-10 rounded-full bg-surface-2 border border-border flex items-center justify-center flex-shrink-0 font-syne font-bold text-ink-2 text-sm">
                {article.author.name.charAt(0).toUpperCase()}
              </div>
              <div>
                <div className="font-syne font-semibold text-sm text-ink">
                  {article.author.name}
                </div>
                {article.author.bio && (
                  <p className="font-serif text-xs text-ink-3 mt-1 leading-relaxed">{article.author.bio}</p>
                )}
              </div>
            </div>
          )}

          {/* Quiz */}
          <ArticleQuiz slug={article.slug} />

          {/* FAQ */}
          {article.faq?.length > 0 && (
            <section className="mt-12 border-t border-border pt-8">
              <h2 className="font-syne font-bold text-xl text-ink mb-5">Frequently Asked Questions</h2>
              <div className="space-y-4">
                {article.faq.map((faq, i) => (
                  <details key={i} className="group border border-border rounded-lg">
                    <summary className="px-5 py-3.5 font-syne font-semibold text-sm text-ink cursor-pointer hover:bg-surface-2 rounded-lg list-none flex items-center justify-between">
                      {faq.question}
                      <span className="text-ink-3 text-xs group-open:rotate-180 transition-transform">▼</span>
                    </summary>
                    <div className="px-5 py-3.5 border-t border-border font-serif text-sm text-ink-2 leading-relaxed">
                      {faq.answer}
                    </div>
                  </details>
                ))}
              </div>
            </section>
          )}

          {/* Sources — PubMed verified (preferred) or LLM-provided */}
          {(() => {
            const hasPubMed = article.verified_sources?.length > 0;
            const sources = hasPubMed
              ? article.verified_sources
              : article.sources || [];
            if (!sources.length) return null;
            return (
              <section className="mt-10 border-t border-border pt-6">
                <div className="flex items-center gap-2 mb-3">
                  <h2 className="font-syne font-bold text-sm text-ink-2 uppercase tracking-wider">{ui.refs}</h2>
                  {hasPubMed && (
                    <span className="text-[10px] font-syne font-bold text-blue-600 bg-blue-50 border border-blue-200 rounded-full px-2 py-0.5">
                      PubMed indexed
                    </span>
                  )}
                  {!hasPubMed && (
                    <span className="text-[10px] font-syne font-bold text-amber-700 bg-amber-50 border border-amber/20 rounded-full px-2 py-0.5">
                      AI-cited · not validated
                    </span>
                  )}
                </div>
                <ol className="space-y-2.5">
                  {sources.map((src: any, i: number) => (
                    <li key={i} className="flex items-start gap-2 text-xs font-serif text-ink-3">
                      <span className="font-syne font-semibold text-ink-3 mt-0.5 flex-shrink-0">{i + 1}.</span>
                      <span className="leading-relaxed">
                        {src.url ? (
                          <a href={src.url} target="_blank" rel="noopener noreferrer" className="hover:text-ink underline underline-offset-2 text-ink-2">
                            {src.title}
                          </a>
                        ) : (
                          <span className="text-ink-2">{src.title}</span>
                        )}
                        {src.authors && <span className="ml-1 text-ink-3"> — {src.authors}</span>}
                        {src.journal && <span className="ml-1 italic text-ink-3">{src.journal}</span>}
                        {src.year && <span className="ml-1 text-ink-3">({src.year})</span>}
                        {src.pmid && (
                          <a
                            href={`https://pubmed.ncbi.nlm.nih.gov/${src.pmid}/`}
                            target="_blank" rel="noopener noreferrer"
                            className="ml-1.5 text-blue-600 hover:underline text-[10px] font-syne font-semibold"
                          >
                            PMID:{src.pmid}
                          </a>
                        )}
                      </span>
                    </li>
                  ))}
                </ol>
              </section>
            );
          })()}

          {/* Medical disclaimer — full, depends on verification status */}
          <div className={`mt-10 rounded-xl px-5 py-5 border text-xs font-serif leading-relaxed ${
            article.verification_status === "expert_verified"
              ? "bg-green-light/30 border-green/20"
              : article.verification_status === "ai_verified"
              ? "bg-blue-50 border-blue-200"
              : "bg-amber-50 border-amber/20"
          }`}>
            <div className="flex items-start gap-3">
              <span className="text-lg flex-shrink-0 mt-0.5">
                {article.verification_status === "expert_verified" ? "✅" :
                 article.verification_status === "ai_verified" ? "🔬" : "⚕️"}
              </span>
              <div>
                <div className="font-syne font-bold text-sm text-ink mb-2">{ui.disclaimer}</div>
                <p className="text-ink-2 mb-2">
                  <strong>This article is intended for educational and informational purposes only.</strong>{" "}
                  It does not constitute medical advice, professional diagnosis, or a treatment plan.
                  Never disregard professional medical advice or delay seeking it because of information in this article.
                  Always consult a qualified, licensed healthcare professional before making clinical decisions.
                </p>
                {article.verification_status === "expert_verified" && (
                  <p className="text-green-800 font-semibold">
                    ✅ This article has been reviewed by a licensed healthcare professional on the MedMind editorial team.
                  </p>
                )}
                {article.verification_status === "ai_verified" && (
                  <p className="text-blue-700">
                    🔬 The topic and references in this article have been cross-referenced with{" "}
                    <strong>{article.verified_sources?.length ?? 0} peer-reviewed publications</strong> indexed in PubMed/MEDLINE.
                    The content was generated by AI and has not been verified by a human clinician.
                  </p>
                )}
                {article.verification_status === "unverified" && (
                  <p className="text-amber-800">
                    ⚠️ This article was generated by AI ({article.generated_by ?? "AI"}) and has{" "}
                    <strong>not yet been cross-referenced with medical databases</strong>.
                    Treat all information with appropriate clinical judgement.
                  </p>
                )}
                <p className="mt-2 text-ink-3">
                  MedMind AI is an educational platform. Drug dosages, contraindications, and clinical protocols
                  should always be verified against current official guidelines and prescribing information.
                </p>
              </div>
            </div>
          </div>

          {/* Prev / Next in category */}
          {(nav.prev || nav.next) && (
            <nav className="mt-10 border-t border-border pt-6 grid grid-cols-2 gap-4" aria-label="Article navigation">
              <div>
                {nav.prev && (
                  <Link
                    href={locale && locale !== "en" ? `/articles/${nav.prev.slug}?lang=${locale}` : `/articles/${nav.prev.slug}`}
                    className="group flex flex-col gap-1 p-4 rounded-xl border border-border hover:border-ink hover:shadow-sm transition-all"
                  >
                    <span className="text-[10px] font-syne font-semibold text-ink-3 uppercase tracking-wider">←</span>
                    <span className="font-syne font-semibold text-sm text-ink group-hover:text-accent transition-colors line-clamp-2">
                      {nav.prev.title}
                    </span>
                  </Link>
                )}
              </div>
              <div>
                {nav.next && (
                  <Link
                    href={locale && locale !== "en" ? `/articles/${nav.next.slug}?lang=${locale}` : `/articles/${nav.next.slug}`}
                    className="group flex flex-col gap-1 p-4 rounded-xl border border-border hover:border-ink hover:shadow-sm transition-all text-right"
                  >
                    <span className="text-[10px] font-syne font-semibold text-ink-3 uppercase tracking-wider">→</span>
                    <span className="font-syne font-semibold text-sm text-ink group-hover:text-accent transition-colors line-clamp-2">
                      {nav.next.title}
                    </span>
                  </Link>
                )}
              </div>
            </nav>
          )}

          {/* Related articles */}
          {related.length > 0 && (
            <section className="mt-12 border-t border-border pt-8">
              <h2 className="font-syne font-bold text-base text-ink mb-5 uppercase tracking-wide text-sm text-ink-2">
                {getMoreIn(locale)} {getCategoryLabel(article.category, locale)}
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {related.map((r) => (
                  <Link
                    key={r.slug}
                    href={locale && locale !== "en" ? `/articles/${r.slug}?lang=${locale}` : `/articles/${r.slug}`}
                    className="group flex flex-col gap-2 p-4 rounded-xl border border-border hover:border-ink hover:shadow-sm transition-all"
                  >
                    <h3 className="font-syne font-semibold text-sm text-ink group-hover:text-accent transition-colors line-clamp-2">
                      {r.title}
                    </h3>
                    <p className="font-serif text-xs text-ink-3 line-clamp-2 leading-relaxed">{r.excerpt}</p>
                    <span className="text-[10px] font-syne text-ink-3 mt-auto">{r.reading_time_minutes} min read →</span>
                  </Link>
                ))}
              </div>
            </section>
          )}
        </main>

        {/* Sidebar */}
        <aside className="space-y-6">
          {/* CTA — study deeper */}
          <div className="bg-ink text-white rounded-xl p-6 sticky top-20">
            <div className="font-syne font-black text-lg mb-2">Study deeper with AI</div>
            <p className="text-white/70 font-serif text-sm mb-4 leading-relaxed">
              MedMind AI offers interactive modules, flashcards, clinical cases and AI tutor — all evidence-based.
            </p>
            <Link
              href="/register"
              className="block w-full bg-white text-ink font-syne font-bold text-sm text-center px-4 py-2.5 rounded-lg hover:bg-white/90 transition-colors"
            >
              Start learning free →
            </Link>
            {moduleInfo ? (
              <Link
                href={`/modules/${moduleInfo.id}`}
                className="block w-full mt-2 border border-white/20 text-white/80 font-syne text-xs text-center px-4 py-2 rounded-lg hover:border-white/40 transition-colors"
              >
                Open module: {moduleInfo.title} →
              </Link>
            ) : article.related_module_code && (
              <Link
                href={`/register?ref=article&module=${article.related_module_code}`}
                className="block w-full mt-2 border border-white/20 text-white/80 font-syne text-xs text-center px-4 py-2 rounded-lg hover:border-white/40 transition-colors"
              >
                Open related module
              </Link>
            )}
          </div>

          {/* Keywords */}
          {article.keywords?.length > 0 && (
            <div className="bg-surface border border-border rounded-xl p-5">
              <div className="font-syne font-semibold text-xs text-ink-2 uppercase tracking-wider mb-3">Topics</div>
              <div className="flex flex-wrap gap-1.5">
                {article.keywords.map((kw) => (
                  <Link
                    key={kw}
                    href={`/articles?search=${encodeURIComponent(kw)}`}
                    className="text-xs font-serif bg-surface-2 border border-border rounded-full px-2.5 py-0.5 text-ink-2 hover:border-ink hover:text-ink transition-colors"
                  >
                    {kw}
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* Language switcher */}
          {allLocales.length > 1 && (
            <div className="bg-surface border border-border rounded-xl p-5">
              <div className="font-syne font-semibold text-xs text-ink-2 uppercase tracking-wider mb-3">
                Read in another language
              </div>
              <div className="flex flex-col gap-1">
                {allLocales.map((loc) => {
                  const isCurrent = loc === locale;
                  const href = loc === "en"
                    ? `/articles/${article.slug}`
                    : `/articles/${article.slug}?lang=${loc}`;
                  return (
                    <Link
                      key={loc}
                      href={href}
                      className={`text-sm font-serif flex items-center gap-2 rounded-lg px-3 py-1.5 transition-colors ${
                        isCurrent
                          ? "bg-ink text-white"
                          : "text-ink-2 hover:text-ink hover:bg-surface-2"
                      }`}
                    >
                      {LOCALE_LABELS[loc] ?? loc}
                    </Link>
                  );
                })}
              </div>
            </div>
          )}

          {/* Browse more */}
          <div className="bg-surface border border-border rounded-xl p-5">
            <div className="font-syne font-semibold text-xs text-ink-2 uppercase tracking-wider mb-3">More Articles</div>
            <Link href="/articles" className="text-sm font-serif text-ink-2 hover:text-ink flex items-center gap-1">
              ← All articles
            </Link>
            <Link href={`/articles/category/${article.category}`} className="mt-2 text-sm font-serif text-ink-2 hover:text-ink flex items-center gap-1">
              {getMoreIn(locale)} {getCategoryLabel(article.category, locale)}
            </Link>
          </div>
        </aside>
      </div>
    </div>
  );
}
