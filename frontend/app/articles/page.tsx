import type { Metadata } from "next";
import Link from "next/link";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const API_URL = process.env.INTERNAL_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export const revalidate = 3600; // ISR: re-generate every hour

export const metadata: Metadata = {
  title: "Medical Articles — Evidence-Based Health Information",
  description:
    "Comprehensive evidence-based medical articles on diseases, drugs, procedures, and clinical guidelines. Written for doctors, students, and healthcare professionals.",
  alternates: {
    canonical: `${SITE_URL}/articles`,
    languages: Object.fromEntries(
      ["en", "ru", "ar", "tr", "de", "fr", "es"].map((l) => [l, `${SITE_URL}/${l}/articles`])
    ),
  },
  openGraph: {
    title: "Medical Articles — MedMind AI",
    description: "Evidence-based medical content: diseases, drugs, procedures, diagnostics.",
    url: `${SITE_URL}/articles`,
    siteName: "MedMind AI",
    type: "website",
  },
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

const CATEGORY_ICONS: Record<string, string> = {
  diseases: "🫀",
  drugs: "💊",
  procedures: "🔬",
  symptoms: "🩺",
  diagnostics: "🧪",
  emergency: "🚑",
  nutrition: "🥗",
  pediatrics: "👶",
  cardiology: "❤️",
  neurology: "🧠",
  oncology: "🎗️",
  surgery: "🔪",
  psychiatry: "🧘",
  endocrinology: "⚗️",
  "infectious-diseases": "🦠",
  veterinary: "🐾",
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

type CategoryStat = { category: string; count: number };

async function fetchArticles(search?: string): Promise<Article[]> {
  try {
    const params = new URLSearchParams({ limit: "24" });
    if (search) params.set("search", search);
    const res = await fetch(`${API_URL}/articles?${params}`, {
      next: { revalidate: search ? 60 : 3600 },
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.articles ?? [];
  } catch {
    return [];
  }
}

async function fetchCategories(): Promise<CategoryStat[]> {
  try {
    const res = await fetch(`${API_URL}/articles/categories`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

export default async function ArticlesPage({
  searchParams,
}: {
  searchParams?: { search?: string };
}) {
  const search = searchParams?.search;
  const [articles, categories] = await Promise.all([fetchArticles(search), fetchCategories()]);

  return (
    <div className="min-h-screen bg-bg">
      {/* Nav */}
      <nav className="bg-surface border-b border-border sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 py-3 flex items-center gap-6">
          <Link href="/" className="font-syne font-extrabold text-xl text-ink tracking-tight">
            MedMind AI
          </Link>
          <div className="flex gap-4 text-sm font-serif text-ink-2">
            <Link href="/articles" className="text-ink font-semibold">Articles</Link>
            <Link href="/pricing" className="hover:text-ink transition-colors">Pricing</Link>
            <Link href="/login" className="hover:text-ink transition-colors">Sign in</Link>
          </div>
          <div className="ml-auto">
            <Link href="/register" className="bg-ink text-white font-syne font-semibold text-sm px-4 py-1.5 rounded-lg hover:bg-ink-2 transition-colors">
              Get started free
            </Link>
          </div>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="mb-10">
          <h1 className="font-syne font-black text-4xl text-ink mb-3">Medical Articles</h1>
          <p className="text-ink-2 font-serif text-lg max-w-2xl">
            Evidence-based medical content written for healthcare professionals and students.
            All articles are grounded in clinical guidelines and peer-reviewed research.
          </p>
          {/* Search bar */}
          <form method="GET" action="/articles" className="mt-6 flex gap-2 max-w-lg">
            <div className="relative flex-1">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-3 pointer-events-none">🔍</span>
              <input
                name="search"
                defaultValue={search ?? ""}
                placeholder="Search articles by title or topic…"
                className="w-full bg-surface border border-border rounded-xl pl-9 pr-4 py-2.5 text-ink text-sm font-serif focus:outline-none focus:border-ink transition-colors"
              />
            </div>
            <button
              type="submit"
              className="bg-ink text-white font-syne font-semibold text-sm px-5 py-2.5 rounded-xl hover:bg-ink-2 transition-colors shrink-0"
            >
              Search
            </button>
            {search && (
              <Link href="/articles" className="flex items-center px-3 py-2.5 border border-border rounded-xl text-ink-3 text-sm hover:border-ink-3 transition-colors font-serif shrink-0">
                ✕
              </Link>
            )}
          </form>
        </div>

        {/* Category grid */}
        {categories.length > 0 && (
          <section className="mb-12">
            <h2 className="font-syne font-bold text-sm text-ink-3 uppercase tracking-wider mb-4">Browse by Category</h2>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
              {categories.map(({ category, count }) => (
                <Link
                  key={category}
                  href={`/articles/category/${category}`}
                  className="flex flex-col items-center gap-1 p-4 bg-surface border border-border rounded-xl hover:border-ink hover:shadow-sm transition-all text-center"
                >
                  <span className="text-2xl">{CATEGORY_ICONS[category] ?? "📄"}</span>
                  <span className="font-syne font-semibold text-xs text-ink">
                    {CATEGORY_LABELS[category] ?? category}
                  </span>
                  <span className="text-ink-3 text-[10px] font-serif">{count} articles</span>
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* Article grid */}
        {articles.length > 0 ? (
          <section>
            <h2 className="font-syne font-bold text-sm text-ink-3 uppercase tracking-wider mb-4">
              {search ? (
                <>
                  Results for &ldquo;{search}&rdquo;
                  <Link href="/articles" className="ml-3 text-ink-2 font-normal normal-case text-xs hover:text-ink underline">
                    Clear
                  </Link>
                </>
              ) : "Latest Articles"}
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {articles.map((a) => (
                <ArticleCard key={a.id} article={a} />
              ))}
            </div>
          </section>
        ) : (
          <div className="text-center py-20 text-ink-3 font-serif">
            No articles published yet. Check back soon.
          </div>
        )}
      </main>

      {/* Footer CTA */}
      <footer className="border-t border-border mt-20 py-12">
        <div className="max-w-6xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6">
          <div>
            <div className="font-syne font-extrabold text-xl text-ink mb-1">MedMind AI</div>
            <p className="text-ink-3 font-serif text-sm">AI-powered medical education platform</p>
          </div>
          <div className="flex gap-3">
            <Link href="/register" className="bg-ink text-white font-syne font-semibold text-sm px-5 py-2 rounded-lg hover:bg-ink-2 transition-colors">
              Start learning free
            </Link>
            <Link href="/pricing" className="border border-border text-ink font-syne font-semibold text-sm px-5 py-2 rounded-lg hover:border-ink transition-colors">
              View pricing
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}

function ArticleCard({ article }: { article: Article }) {
  return (
    <Link
      href={`/articles/${article.slug}`}
      className="group flex flex-col bg-surface border border-border rounded-xl p-5 hover:border-ink hover:shadow-md transition-all"
    >
      <div className="flex items-center gap-2 mb-3">
        <span className="text-base">{CATEGORY_ICONS[article.category] ?? "📄"}</span>
        <span className="text-[11px] font-syne font-semibold text-ink-3 uppercase tracking-wider">
          {CATEGORY_LABELS[article.category] ?? article.category}
        </span>
      </div>
      <h3 className="font-syne font-bold text-base text-ink mb-2 group-hover:text-accent transition-colors line-clamp-2">
        {article.title}
      </h3>
      <p className="text-ink-2 font-serif text-sm leading-relaxed flex-1 line-clamp-3">
        {article.excerpt}
      </p>
      <div className="flex items-center gap-3 mt-4 pt-3 border-t border-border">
        <span className="text-ink-3 text-xs font-serif">{article.reading_time_minutes} min read</span>
        {article.published_at && (
          <span className="text-ink-3 text-xs font-serif ml-auto">
            {new Date(article.published_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
          </span>
        )}
      </div>
    </Link>
  );
}
