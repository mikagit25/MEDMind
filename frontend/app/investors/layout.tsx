import type { Metadata } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";

export const metadata: Metadata = {
  title: { absolute: "Investors — MedMind AI" },
  description:
    "MedMind AI is building the future of medical education. AI-powered platform serving doctors, medical students and veterinarians in 7 languages with evidence-based content.",
  keywords: ["medmind investors", "medical education startup", "AI healthtech", "medical edtech investment"],
  alternates: {
    canonical: `${SITE_URL}/investors`,
  },
  openGraph: {
    title: "Investors — MedMind AI",
    description: "MedMind AI — AI-powered medical education platform. Evidence-based content in 7 languages powered by Claude AI and PubMed.",
    url: `${SITE_URL}/investors`,
    siteName: "MedMind AI",
    type: "website",
  },
  robots: { index: true, follow: true },
};

export default function InvestorsLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
