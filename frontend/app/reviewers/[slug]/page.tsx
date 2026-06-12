import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { PublicFooter } from "@/components/layout/PublicFooter";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const API_URL =
  process.env.INTERNAL_API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000/api/v1";

type ReviewerProfile = {
  slug: string;
  name: string;
  credentials: string | null;
  bio: string | null;
  institution: string | null;
  avatar_url: string | null;
  specialties: string[];
  linkedin_url: string | null;
  reviewed_articles: {
    slug: string;
    title: string;
    category: string;
    published_at: string | null;
  }[];
};

async function fetchReviewer(slug: string): Promise<ReviewerProfile | null> {
  try {
    const res = await fetch(`${API_URL}/reviewers/${slug}`, {
      next: { revalidate: 3600 },
    });
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
}: {
  params: { slug: string };
}): Promise<Metadata> {
  const reviewer = await fetchReviewer(params.slug);
  if (!reviewer) return { title: "Reviewer not found" };

  const title = `${reviewer.name}${reviewer.credentials ? `, ${reviewer.credentials}` : ""} — Medical Reviewer`;
  const description = reviewer.bio
    ? reviewer.bio.slice(0, 160)
    : `Medical reviewer profile for ${reviewer.name} at MedMind AI.`;
  const url = `${SITE_URL}/reviewers/${reviewer.slug}`;

  return {
    title,
    description,
    alternates: { canonical: url },
    openGraph: {
      title,
      description,
      url,
      siteName: "MedMind AI",
      type: "profile",
    },
  };
}

export default async function ReviewerPage({
  params,
}: {
  params: { slug: string };
}) {
  const reviewer = await fetchReviewer(params.slug);
  if (!reviewer) notFound();

  const schema = {
    "@context": "https://schema.org",
    "@type": "Person",
    name: reviewer.name,
    jobTitle: reviewer.credentials ?? undefined,
    affiliation: reviewer.institution
      ? { "@type": "Organization", name: reviewer.institution }
      : undefined,
    description: reviewer.bio ?? undefined,
    url: `${SITE_URL}/reviewers/${reviewer.slug}`,
    image: reviewer.avatar_url ?? undefined,
    sameAs: reviewer.linkedin_url ? [reviewer.linkedin_url] : undefined,
  };

  return (
    <div className="min-h-screen bg-bg">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
      />
      <ArticleNav />

      <div className="max-w-3xl mx-auto px-6 py-12">
        {/* Profile header */}
        <div className="flex gap-6 items-start mb-10">
          {reviewer.avatar_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={reviewer.avatar_url}
              alt={reviewer.name}
              width={96}
              height={96}
              className="w-24 h-24 rounded-full object-cover border-2 border-border flex-shrink-0"
            />
          ) : (
            <div className="w-24 h-24 rounded-full bg-blue-100 flex items-center justify-center text-3xl font-bold text-blue-600 flex-shrink-0">
              {reviewer.name[0]}
            </div>
          )}
          <div>
            <h1 className="font-syne font-extrabold text-2xl text-ink">{reviewer.name}</h1>
            {reviewer.credentials && (
              <p className="text-ink-2 font-medium mt-0.5">{reviewer.credentials}</p>
            )}
            {reviewer.institution && (
              <p className="text-ink-3 text-sm mt-1">{reviewer.institution}</p>
            )}
            {reviewer.specialties?.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-3">
                {reviewer.specialties.map((s) => (
                  <span
                    key={s}
                    className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full border border-blue-100"
                  >
                    {s}
                  </span>
                ))}
              </div>
            )}
            {reviewer.linkedin_url && (
              <a
                href={reviewer.linkedin_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-block mt-3 text-xs text-blue-600 hover:underline"
              >
                LinkedIn →
              </a>
            )}
          </div>
        </div>

        {/* Bio */}
        {reviewer.bio && (
          <section className="mb-10">
            <h2 className="font-syne font-bold text-lg text-ink mb-3">Biography</h2>
            <p className="text-ink-2 leading-relaxed">{reviewer.bio}</p>
          </section>
        )}

        {/* Reviewed articles */}
        {reviewer.reviewed_articles?.length > 0 && (
          <section>
            <h2 className="font-syne font-bold text-lg text-ink mb-4">
              Reviewed Articles ({reviewer.reviewed_articles.length})
            </h2>
            <ul className="space-y-3">
              {reviewer.reviewed_articles.map((a) => (
                <li key={a.slug}>
                  <Link
                    href={`/articles/${a.slug}`}
                    className="block bg-surface border border-border rounded-xl p-4 hover:border-blue-300 transition-colors"
                  >
                    <span className="font-syne font-semibold text-ink text-sm">{a.title}</span>
                    {a.published_at && (
                      <span className="block text-ink-3 text-xs mt-1">
                        {new Date(a.published_at).toLocaleDateString("en-US", {
                          year: "numeric",
                          month: "short",
                          day: "numeric",
                        })}
                      </span>
                    )}
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>

      <PublicFooter />
    </div>
  );
}
