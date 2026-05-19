import LandingPage from "./LandingPage";

export const dynamic = "force-dynamic";

const API_URL =
  process.env.INTERNAL_API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000/api/v1";

type ArticlePreview = {
  id: string;
  slug: string;
  title: string;
  excerpt: string;
  category: string;
  reading_time_minutes: number;
  cover_image: string | null;
  published_at: string | null;
};

async function fetchFeaturedArticles(): Promise<ArticlePreview[]> {
  try {
    // Fetch latest articles — mix of categories for variety on homepage
    const res = await fetch(
      `${API_URL}/articles?limit=24`,
      { next: { revalidate: 1800 } } // refresh every 30 min
    );
    if (!res.ok) return [];
    const data = await res.json();
    const articles: ArticlePreview[] = data.articles ?? [];

    // Deduplicate by category — pick at most 2-3 per category for variety
    const seen: Record<string, number> = {};
    return articles.filter(a => {
      seen[a.category] = (seen[a.category] ?? 0) + 1;
      return seen[a.category] <= 3;
    }).slice(0, 10);
  } catch {
    return [];
  }
}

export default async function Page() {
  const articles = await fetchFeaturedArticles();
  return <LandingPage articles={articles} />;
}
