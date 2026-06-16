import type { Metadata } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const LOCALES = ["en", "ru", "ar", "tr", "de", "fr", "es"];

export const metadata: Metadata = {
  title: { absolute: "Medical News — MedMind AI" },
  description:
    "Latest medical research news from PubMed, WHO, and medRxiv. AI-summarised and translated into 7 languages. Updated every 6 hours.",
  keywords: [
    "medical news", "healthcare news", "medical research", "PubMed news",
    "WHO news", "clinical research updates", "медицинские новости", "actualités médicales",
  ],
  // canonical for /news index only; no languages — layout alternates merge with
  // child page alternates in Next.js and would create conflicting hreflang.
  alternates: { canonical: `${SITE_URL}/news` },
  openGraph: {
    title: "Medical News — MedMind AI",
    description: "Latest medical research summarised by AI. PubMed, WHO, medRxiv — in 7 languages.",
    url: `${SITE_URL}/news`,
    siteName: "MedMind AI",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "Medical News — MedMind AI",
    description: "AI-summarised medical research news in 7 languages. Updated every 6 hours.",
  },
  robots: { index: true, follow: true },
};

export default function NewsLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
