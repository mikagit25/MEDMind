import type { Metadata } from "next";
import { getCalc, CALC_SLUGS } from "@/components/calculators/data";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const LOCALES = ["en", "ru", "ar", "tr", "de", "fr", "es"];

const EGFR_META = {
  title: "eGFR Calculator (CKD-EPI 2021) — MedMind AI",
  description: "Free eGFR calculator using the CKD-EPI 2021 race-free equation. Estimates kidney function and determines CKD stage (G1–G5). Available in 7 languages.",
  keywords: ["eGFR calculator", "CKD-EPI 2021", "kidney function", "creatinine clearance", "CKD staging", "nephrology calculator"],
};

const CALC_SEO: Record<string, { title: string; description: string; keywords: string[] }> = {
  "cha2ds2-vasc": {
    title: "CHA₂DS₂-VASc Calculator — Stroke Risk in AFib — MedMind AI",
    description: "CHA₂DS₂-VASc score calculator for stroke risk in non-valvular atrial fibrillation. ACC/AHA/ESC guideline-based anticoagulation recommendations. Free, 7 languages.",
    keywords: ["CHA2DS2-VASc", "stroke risk calculator", "atrial fibrillation", "anticoagulation", "AFib score", "cardiology calculator"],
  },
  "curb-65": {
    title: "CURB-65 Calculator — Pneumonia Severity — MedMind AI",
    description: "CURB-65 score for community-acquired pneumonia severity. Determine outpatient vs inpatient vs ICU management. Based on BTS guidelines. Free, 7 languages.",
    keywords: ["CURB-65", "pneumonia severity", "CAP score", "pulmonology calculator", "hospital admission pneumonia", "BTS guidelines"],
  },
  "wells-dvt": {
    title: "Wells Criteria DVT Calculator — Pre-test Probability — MedMind AI",
    description: "Wells criteria calculator for pre-test probability of deep vein thrombosis. Guide D-dimer testing and compression ultrasound ordering. Free, 7 languages.",
    keywords: ["Wells criteria DVT", "DVT probability", "deep vein thrombosis", "D-dimer", "Wells score", "thrombosis calculator"],
  },
  "heart-score": {
    title: "HEART Score Calculator — Chest Pain Risk — MedMind AI",
    description: "HEART Score for risk stratification of chest pain in the emergency department. Predicts 30-day MACE risk. Guides disposition and invasive testing decisions. Free, 7 languages.",
    keywords: ["HEART score", "chest pain", "MACE risk", "emergency cardiology", "ACS risk", "ED chest pain calculator"],
  },
  "egfr-ckd-epi": EGFR_META,
};

export async function generateMetadata({ params }: { params: { slug: string } }): Promise<Metadata> {
  const { slug } = params;
  const seo = CALC_SEO[slug] ?? {
    title: "Clinical Calculator — MedMind AI",
    description: "Evidence-based clinical calculator. Free, multilingual.",
    keywords: ["clinical calculator", "medical scoring", "medmind"],
  };

  return {
    title: { absolute: seo.title },
    description: seo.description,
    keywords: seo.keywords,
    alternates: {
      canonical: `${SITE_URL}/calculators/${slug}`,
      languages: Object.fromEntries(
        LOCALES.map(l => [l, l === "en" ? `${SITE_URL}/calculators/${slug}` : `${SITE_URL}/${l}/calculators/${slug}`])
      ),
    },
    openGraph: {
      title: seo.title,
      description: seo.description,
      url: `${SITE_URL}/calculators/${slug}`,
      siteName: "MedMind AI",
      type: "website",
    },
    twitter: {
      card: "summary",
      title: seo.title,
      description: seo.description,
    },
    robots: { index: true, follow: true },
  };
}

export default function CalcSlugLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
