import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export const revalidate = 3600;

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

const CATEGORY_DESCRIPTIONS: Record<string, string> = {
  diseases: "Evidence-based articles on medical conditions, their pathophysiology, diagnosis, and treatment.",
  drugs: "Comprehensive drug monographs: mechanisms of action, dosing, contraindications, and interactions.",
  procedures: "Step-by-step guides to clinical procedures and techniques used in modern medicine.",
  symptoms: "Clinical approach to common and rare symptoms — differential diagnosis and workup.",
  diagnostics: "Laboratory tests, imaging, and diagnostic criteria explained for clinical practice.",
  emergency: "Rapid-reference articles on acute medical emergencies and critical care.",
  nutrition: "Evidence-based nutritional guidelines and preventive medicine recommendations.",
  pediatrics: "Medical content tailored to pediatric patients — growth, development, and disease management.",
  cardiology: "Heart diseases, arrhythmias, heart failure, and cardiovascular pharmacology.",
  neurology: "Neurological disorders, stroke, epilepsy, neurodegenerative diseases.",
  oncology: "Cancer biology, diagnosis, staging, and treatment modalities.",
  surgery: "Surgical principles, operative techniques, and perioperative care.",
  psychiatry: "Mental health conditions, psychopharmacology, and psychiatric emergencies.",
  endocrinology: "Hormonal disorders, diabetes, thyroid, adrenal, and metabolic conditions.",
  "infectious-diseases": "Bacterial, viral, fungal, and parasitic infections — diagnosis and antimicrobial therapy.",
  veterinary: "Veterinary medicine: animal diseases, pharmacology, and clinical techniques.",
};

const CATEGORY_ICONS: Record<string, string> = {
  diseases: "🫀", drugs: "💊", procedures: "🔬", symptoms: "🩺",
  diagnostics: "🧪", emergency: "🚑", nutrition: "🥗", pediatrics: "👶",
  cardiology: "❤️", neurology: "🧠", oncology: "🎗️", surgery: "🔪",
  psychiatry: "🧘", endocrinology: "⚗️", "infectious-diseases": "🦠", veterinary: "🐾",
};

type Article = {
  id: string;
  slug: string;
  title: string;
  excerpt: string;
  category: string;
  keywords: string[];
  reading_time_minutes: number;
  published_at: string | null;
};

async function fetchCategory(cat: string, page = 1): Promise<{ articles: Article[]; total: number } | null> {
  try {
    const res = await fetch(`${API_URL}/articles/category/${cat}?page=${page}&limit=24`, {
      next: { revalidate: 3600 },
    });
    if (res.status === 404) return null;
    if (!res.ok) return null;
    const data = await res.json();
    return { articles: data.articles ?? [], total: data.total ?? 0 };
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
  searchParams,
}: {
  params: { cat: string };
  searchParams?: { page?: string };
}): Promise<Metadata> {
  const label = CATEGORY_LABELS[params.cat];
  if (!label) return { title: "Category not found" };

  const page = Math.max(1, parseInt(searchParams?.page ?? "1", 10) || 1);
  const description = CATEGORY_DESCRIPTIONS[params.cat] ??
    `Evidence-based medical articles in ${label}. Comprehensive content for healthcare professionals.`;
  const baseUrl = `${SITE_URL}/articles/category/${params.cat}`;
  const canonical = page > 1 ? `${baseUrl}?page=${page}` : baseUrl;

  return {
    title: page > 1 ? `${label} — Page ${page} — Medical Articles` : `${label} — Medical Articles`,
    description,
    alternates: { canonical },
    openGraph: {
      title: `${label} — MedMind AI Articles`,
      description,
      url: canonical,
      siteName: "MedMind AI",
      type: "website",
    },
  };
}

const PAGE_SIZE = 24;

export default async function CategoryPage({
  params,
  searchParams,
}: {
  params: { cat: string };
  searchParams?: { page?: string };
}) {
  const label = CATEGORY_LABELS[params.cat];
  if (!label) notFound();

  const page = Math.max(1, parseInt(searchParams?.page ?? "1", 10) || 1);
  const result = await fetchCategory(params.cat, page);
  if (!result) notFound();

  const { articles, total } = result;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  // Breadcrumb schema
  const breadcrumbSchema = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Home", item: SITE_URL },
      { "@type": "ListItem", position: 2, name: "Articles", item: `${SITE_URL}/articles` },
      { "@type": "ListItem", position: 3, name: label, item: `${SITE_URL}/articles/category/${params.cat}` },
    ],
  };

  return (
    <div className="min-h-screen bg-bg">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbSchema) }}
      />

      {/* Nav */}
      <nav className="bg-surface border-b border-border sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center gap-6">
          <Link href="/" className="font-syne font-extrabold text-xl text-ink tracking-tight">MedMind AI</Link>
          <div className="flex gap-4 text-sm font-serif text-ink-2">
            <Link href="/articles" className="hover:text-ink transition-colors">Articles</Link>
            <Link href="/pricing" className="hover:text-ink transition-colors">Pricing</Link>
          </div>
          <div className="ml-auto">
            <Link href="/register" className="bg-ink text-white font-syne font-semibold text-sm px-4 py-1.5 rounded-lg hover:bg-ink-2 transition-colors">
              Get started free
            </Link>
          </div>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto px-6 py-12">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-1.5 text-xs font-serif text-ink-3 mb-8" aria-label="Breadcrumb">
          <Link href="/articles" className="hover:text-ink">Articles</Link>
          <span>/</span>
          <span className="text-ink-2">{label}</span>
        </nav>

        {/* Header */}
        <div className="mb-10">
          <div className="flex items-center gap-3 mb-3">
            <span className="text-3xl">{CATEGORY_ICONS[params.cat] ?? "📄"}</span>
            <h1 className="font-syne font-black text-3xl text-ink">{label}</h1>
          </div>
          <p className="text-ink-2 font-serif text-base max-w-2xl">
            {CATEGORY_DESCRIPTIONS[params.cat]}
          </p>
          <p className="text-ink-3 font-serif text-sm mt-2">{total} article{total !== 1 ? "s" : ""}</p>
        </div>

        {/* Articles */}
        {articles.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {articles.map((a) => (
              <Link
                key={a.id}
                href={`/articles/${a.slug}`}
                className="group flex flex-col bg-surface border border-border rounded-xl p-5 hover:border-ink hover:shadow-md transition-all"
              >
                <h2 className="font-syne font-bold text-base text-ink mb-2 group-hover:text-accent transition-colors line-clamp-2">
                  {a.title}
                </h2>
                <p className="text-ink-2 font-serif text-sm leading-relaxed flex-1 line-clamp-3">
                  {a.excerpt}
                </p>
                <div className="flex items-center gap-3 mt-4 pt-3 border-t border-border">
                  <span className="text-ink-3 text-xs font-serif">{a.reading_time_minutes} min read</span>
                  {a.published_at && (
                    <span className="text-ink-3 text-xs font-serif ml-auto">
                      {new Date(a.published_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                    </span>
                  )}
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="text-center py-20 text-ink-3 font-serif">
            No articles in this category yet. Check back soon.
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <nav className="mt-12 pt-8 border-t border-border flex items-center justify-between gap-3" aria-label="Pagination">
            <div>
              {page > 1 && (
                <Link
                  href={`/articles/category/${params.cat}?page=${page - 1}`}
                  className="inline-flex items-center gap-1.5 font-syne font-semibold text-sm text-ink-2 hover:text-ink border border-border rounded-lg px-4 py-2 hover:border-ink transition-all"
                >
                  ← Previous
                </Link>
              )}
            </div>
            <span className="font-serif text-xs text-ink-3">
              Page {page} of {totalPages} &mdash; {total} articles
            </span>
            <div>
              {page < totalPages && (
                <Link
                  href={`/articles/category/${params.cat}?page=${page + 1}`}
                  className="inline-flex items-center gap-1.5 font-syne font-semibold text-sm text-ink-2 hover:text-ink border border-border rounded-lg px-4 py-2 hover:border-ink transition-all"
                >
                  Next →
                </Link>
              )}
            </div>
          </nav>
        )}

        {/* Back link */}
        <div className="mt-6 pt-4">
          <Link href="/articles" className="font-syne font-semibold text-sm text-ink-2 hover:text-ink">
            ← All articles
          </Link>
        </div>
      </main>
    </div>
  );
}
