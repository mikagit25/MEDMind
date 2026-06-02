import type { Metadata } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const LOCALES = ["en", "ru", "ar", "tr", "de", "fr", "es"];

export const metadata: Metadata = {
  title: { absolute: "Clinical Calculators — MedMind AI" },
  description:
    "Free evidence-based clinical calculators: CHA₂DS₂-VASc, CURB-65, Wells DVT, HEART Score, eGFR. Used by physicians daily. Available in 7 languages.",
  keywords: [
    "clinical calculators", "medical calculators", "CHA2DS2-VASc", "CURB-65", "Wells criteria DVT",
    "HEART score", "eGFR calculator", "CKD-EPI", "medical scoring tools", "stroke risk calculator",
  ],
  alternates: {
    canonical: `${SITE_URL}/calculators`,
    languages: Object.fromEntries(
      LOCALES.map(l => [l, l === "en" ? `${SITE_URL}/calculators` : `${SITE_URL}/${l}/calculators`])
    ),
  },
  openGraph: {
    title: "Clinical Calculators — MedMind AI",
    description: "Free multilingual clinical calculators: CHA₂DS₂-VASc, CURB-65, Wells DVT, HEART Score, eGFR.",
    url: `${SITE_URL}/calculators`,
    siteName: "MedMind AI",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "Clinical Calculators — MedMind AI",
    description: "Free evidence-based calculators in 7 languages. CHA₂DS₂-VASc, CURB-65, Wells DVT, HEART, eGFR.",
  },
  robots: { index: true, follow: true },
};

export default function CalculatorsLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
