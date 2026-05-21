import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Drug Database — MedMind AI",
  description:
    "Browse 833+ drugs with mechanisms, dosing, side effects, interactions and monitoring. Available in 7 languages for medical students, residents, and physicians.",
  keywords:
    "drug database, pharmacology, medication reference, drug interactions, clinical pharmacology, dosing calculator",
  openGraph: {
    title: "Drug Database — MedMind AI",
    description: "Comprehensive pharmacology reference: 833+ drugs in 7 languages.",
    type: "website",
    url: "https://medmind.pro/drugs",
  },
  alternates: {
    canonical: "https://medmind.pro/drugs",
    languages: {
      ru: "https://medmind.pro/drugs?lang=ru",
      ar: "https://medmind.pro/drugs?lang=ar",
      de: "https://medmind.pro/drugs?lang=de",
      fr: "https://medmind.pro/drugs?lang=fr",
      es: "https://medmind.pro/drugs?lang=es",
      tr: "https://medmind.pro/drugs?lang=tr",
    },
  },
  robots: { index: true, follow: true },
};

export default function DrugsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
