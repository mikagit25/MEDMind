import { NextResponse } from "next/server";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const BACKEND_URL =
  process.env.BACKEND_URL ??
  `${SITE_URL}/api/v1`;

async function fetchArticles() {
  try {
    const res = await fetch(`${BACKEND_URL}/articles/sitemap-data`, {
      next: { revalidate: 3600 },
    });
    if (!res.ok) return [];
    return await res.json() as { slug: string; category: string }[];
  } catch {
    return [];
  }
}

export async function GET() {
  const articles = await fetchArticles();

  // Group by category
  const byCategory: Record<string, { slug: string; category: string }[]> = {};
  for (const a of articles) {
    (byCategory[a.category] ??= []).push(a);
  }

  const lines: string[] = [
    `# MedMind AI`,
    ``,
    `> MedMind AI is an evidence-based medical education platform powered by Anthropic's Claude AI and real-time PubMed integration. It serves doctors, medical students, residents, nurses, and veterinarians across 7 languages.`,
    ``,
    `## Platform`,
    ``,
    `- [Home](${SITE_URL}/) — Overview of MedMind AI medical education platform`,
    `- [How It Works](${SITE_URL}/how-it-works) — Step-by-step guide to the AI learning system`,
    `- [Pricing](${SITE_URL}/pricing) — Free and paid plans for individuals and institutions`,
    `- [Articles](${SITE_URL}/articles) — Evidence-based medical articles with PubMed citations`,
    ``,
    `## About`,
    ``,
    `MedMind AI provides:`,
    `- AI Medical Tutor (Claude AI) with 4 learning modes: Tutor, Socratic, Case-based, Exam Prep`,
    `- 97+ medical modules covering Cardiology, Neurology, Surgery, Pediatrics, OB/GYN, Internal Medicine, and Veterinary Medicine`,
    `- Spaced repetition flashcards (SM-2 algorithm) — 500+ cards`,
    `- Interactive clinical case simulations with FSM branching and AI debrief`,
    `- Real-time PubMed search integration — every AI answer cites current literature`,
    `- Drug database with dosing, interactions, and contraindications`,
    `- 7 languages: English, Russian, German, French, Spanish, Turkish, Arabic`,
    ``,
    `## Medical Knowledge Base`,
    ``,
    `All articles are AI-generated and evidence-based with PubMed citations. Updated monthly.`,
    ``,
  ];

  // Add articles grouped by category (up to 50 per category to keep file manageable)
  const CATEGORY_LABELS: Record<string, string> = {
    cardiology:       "Cardiology",
    neurology:        "Neurology",
    surgery:          "Surgery",
    pediatrics:       "Pediatrics",
    "internal-medicine": "Internal Medicine",
    "ob-gyn":         "Obstetrics & Gynecology",
    pharmacology:     "Pharmacology & Drugs",
    emergency:        "Emergency Medicine",
    psychiatry:       "Psychiatry",
    dermatology:      "Dermatology",
    oncology:         "Oncology",
    infectious:       "Infectious Diseases",
    veterinary:       "Veterinary Medicine",
    anatomy:          "Anatomy & Physiology",
    radiology:        "Radiology & Imaging",
  };

  for (const [cat, arts] of Object.entries(byCategory)) {
    const label = CATEGORY_LABELS[cat] ?? cat;
    lines.push(`### ${label}`, ``);
    for (const a of arts.slice(0, 50)) {
      const title = a.slug
        .replace(/-/g, " ")
        .replace(/\b\w/g, (c) => c.toUpperCase());
      lines.push(`- [${title}](${SITE_URL}/articles/${a.slug})`);
    }
    lines.push(``);
  }

  lines.push(
    `## Licensing`,
    ``,
    `Content on MedMind AI is for educational purposes. Articles may be cited with attribution to MedMind AI (${SITE_URL}).`,
    `AI-generated content is grounded in PubMed-indexed literature.`,
    ``,
    `## Contact`,
    ``,
    `- Website: ${SITE_URL}`,
    `- For AI training partnerships or data licensing: contact via ${SITE_URL}`,
    ``,
  );

  return new NextResponse(lines.join("\n"), {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
    },
  });
}
