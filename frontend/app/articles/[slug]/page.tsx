import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export const revalidate = 3600;

const LOCALE_LABELS: Record<string, string> = {
  en: "English",
  ru: "Русский",
  ar: "العربية",
  tr: "Türkçe",
  de: "Deutsch",
  fr: "Français",
  es: "Español",
};

const CATEGORY_LABELS: Record<string, string> = {
  diseases: "Diseases & Conditions",
  drugs: "Drugs & Medications",
  procedures: "Procedures & Techniques",
  symptoms: "Symptoms & Signs",
  diagnostics: "Diagnostics & Lab Tests",
  emergency: "Emergency Medicine",
  nutrition: "Nutrition & Prevention",
  pediatrics: "Pediatrics",
  cardiology: "Cardiology",
  neurology: "Neurology",
  oncology: "Oncology",
  surgery: "Surgery",
  psychiatry: "Psychiatry",
  endocrinology: "Endocrinology",
  "infectious-diseases": "Infectious Diseases",
  veterinary: "Veterinary Medicine",
};

type Block =
  | { type: "h2"; content: string }
  | { type: "h3"; content: string }
  | { type: "p"; content: string }
  | { type: "ul"; items: string[] }
  | { type: "callout"; variant: "warning" | "info" | "tip"; content: string }
  | { type: "table"; headers: string[]; rows: string[][] }
  | { type: "image"; url: string; caption?: string; alt?: string };

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
};

async function fetchArticle(slug: string, locale?: string): Promise<ArticleDetail | null> {
  try {
    const url = locale && locale !== "en"
      ? `${API_URL}/articles/${slug}?locale=${locale}`
      : `${API_URL}/articles/${slug}`;
    const res = await fetch(url, { next: { revalidate: 3600 } });
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
      next: { revalidate: 3600 },
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

async function fetchRelated(slug: string): Promise<RelatedArticle[]> {
  try {
    const res = await fetch(`${API_URL}/articles/${slug}/related`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

async function fetchNav(slug: string): Promise<ArticleNav> {
  try {
    const res = await fetch(`${API_URL}/articles/${slug}/nav`, {
      next: { revalidate: 3600 },
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
  searchParams: { lang?: string };
}): Promise<Metadata> {
  const locale = searchParams.lang ?? "en";
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
      section: CATEGORY_LABELS[article.category] ?? article.category,
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
function buildSchemaOrg(article: ArticleDetail, moduleInfo?: ModuleInfo): object[] {
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
        name: CATEGORY_LABELS[article.category] ?? article.category,
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

export default async function ArticlePage({
  params,
  searchParams,
}: {
  params: { slug: string };
  searchParams: { lang?: string };
}) {
  const locale = searchParams.lang ?? "en";
  const [article, availableLocales, related, nav, linkMap] = await Promise.all([
    fetchArticle(params.slug, locale),
    fetchAvailableLocales(params.slug),
    fetchRelated(params.slug),
    fetchNav(params.slug),
    fetchLinkMap(),
  ]);
  if (!article) notFound();

  // Resolve module if article has a related module code
  const moduleInfo = article.related_module_code
    ? await fetchModuleByCode(article.related_module_code)
    : null;

  const schema = buildSchemaOrg(article, moduleInfo);
  const allLocales = ["en", ...availableLocales.filter((l) => l !== "en")];

  return (
    <div className="min-h-screen bg-bg">
      {/* Structured data */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
      />

      {/* Nav */}
      <nav className="bg-surface border-b border-border sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center gap-6">
          <Link href="/" className="font-syne font-extrabold text-xl text-ink tracking-tight">
            MedMind AI
          </Link>
          <div className="flex gap-4 text-sm font-serif text-ink-2">
            <Link href="/articles" className="hover:text-ink transition-colors">Articles</Link>
            <Link href="/pricing" className="hover:text-ink transition-colors">Pricing</Link>
          </div>
          <div className="ml-auto flex gap-2">
            <Link href="/login" className="text-ink-2 font-syne font-semibold text-sm px-3 py-1.5 hover:text-ink">Sign in</Link>
            <Link href="/register" className="bg-ink text-white font-syne font-semibold text-sm px-4 py-1.5 rounded-lg hover:bg-ink-2 transition-colors">
              Start free
            </Link>
          </div>
        </div>
      </nav>

      <div className="max-w-6xl mx-auto px-6 py-10 grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-10">
        {/* Main content */}
        <main>
          {/* Breadcrumb */}
          <nav className="flex items-center gap-1.5 text-xs font-serif text-ink-3 mb-6" aria-label="Breadcrumb">
            <Link href="/articles" className="hover:text-ink">Articles</Link>
            <span>/</span>
            <Link href={`/articles/category/${article.category}`} className="hover:text-ink capitalize">
              {CATEGORY_LABELS[article.category] ?? article.category}
            </Link>
            <span>/</span>
            <span className="text-ink-2 truncate max-w-xs">{article.title}</span>
          </nav>

          {/* Header */}
          <div className="mb-8">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xs font-syne font-semibold border border-border rounded-full px-3 py-0.5 text-ink-2">
                {CATEGORY_LABELS[article.category] ?? article.category}
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
            <div className="flex items-center gap-4 mt-4 text-xs font-serif text-ink-3">
              <span>📖 {article.reading_time_minutes} min read</span>
              {article.published_at && (
                <span>
                  {new Date(article.published_at).toLocaleDateString("en-US", {
                    year: "numeric", month: "long", day: "numeric",
                  })}
                </span>
              )}
              <span>{article.author?.name ?? "MedMind AI Editorial"}</span>
            </div>
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

          {/* Sources */}
          {article.sources?.length > 0 && (
            <section className="mt-10 border-t border-border pt-6">
              <h2 className="font-syne font-bold text-sm text-ink-2 uppercase tracking-wider mb-3">References</h2>
              <ol className="space-y-2">
                {article.sources.map((src, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs font-serif text-ink-3">
                    <span className="font-syne font-semibold text-ink-3 mt-0.5">{i + 1}.</span>
                    <span>
                      {src.url ? (
                        <a href={src.url} target="_blank" rel="noopener noreferrer" className="hover:text-ink underline underline-offset-2">
                          {src.title}
                        </a>
                      ) : (
                        src.title
                      )}
                      {src.pmid && <span className="ml-1 text-ink-3">[PMID: {src.pmid}]</span>}
                    </span>
                  </li>
                ))}
              </ol>
            </section>
          )}

          {/* Medical disclaimer */}
          <div className="mt-10 bg-surface-2 border border-border rounded-lg px-5 py-4 text-xs font-serif text-ink-3">
            <strong className="font-syne font-semibold text-ink-2">Medical Disclaimer:</strong>{" "}
            This article is for educational purposes only and does not constitute medical advice.
            Always consult a qualified healthcare professional for diagnosis and treatment.
          </div>

          {/* Prev / Next in category */}
          {(nav.prev || nav.next) && (
            <nav className="mt-10 border-t border-border pt-6 grid grid-cols-2 gap-4" aria-label="Article navigation">
              <div>
                {nav.prev && (
                  <Link
                    href={`/articles/${nav.prev.slug}`}
                    className="group flex flex-col gap-1 p-4 rounded-xl border border-border hover:border-ink hover:shadow-sm transition-all"
                  >
                    <span className="text-[10px] font-syne font-semibold text-ink-3 uppercase tracking-wider">← Previous</span>
                    <span className="font-syne font-semibold text-sm text-ink group-hover:text-accent transition-colors line-clamp-2">
                      {nav.prev.title}
                    </span>
                  </Link>
                )}
              </div>
              <div>
                {nav.next && (
                  <Link
                    href={`/articles/${nav.next.slug}`}
                    className="group flex flex-col gap-1 p-4 rounded-xl border border-border hover:border-ink hover:shadow-sm transition-all text-right"
                  >
                    <span className="text-[10px] font-syne font-semibold text-ink-3 uppercase tracking-wider">Next →</span>
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
                More in {CATEGORY_LABELS[article.category] ?? article.category}
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {related.map((r) => (
                  <Link
                    key={r.slug}
                    href={`/articles/${r.slug}`}
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
              More in {CATEGORY_LABELS[article.category] ?? article.category}
            </Link>
          </div>
        </aside>
      </div>
    </div>
  );
}
