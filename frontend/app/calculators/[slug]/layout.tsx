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
  "gcs": {
    title: "Glasgow Coma Scale (GCS) Calculator — Consciousness Assessment — MedMind AI",
    description: "GCS calculator with eye, verbal, and motor response components. Assess level of consciousness and severity of traumatic brain injury. Free, 7 languages.",
    keywords: ["Glasgow Coma Scale", "GCS calculator", "consciousness assessment", "traumatic brain injury", "TBI score", "neurology calculator"],
  },
  "qsofa": {
    title: "qSOFA Score Calculator — Sepsis Risk Screening — MedMind AI",
    description: "Quick SOFA (qSOFA) score for early sepsis identification outside ICU. Three criteria: altered mentation, tachypnoea, hypotension. Based on Sepsis-3 definition. Free.",
    keywords: ["qSOFA", "sepsis screening", "quick SOFA", "Sepsis-3", "sepsis calculator", "critical care"],
  },
  "has-bled": {
    title: "HAS-BLED Score Calculator — Bleeding Risk in AFib — MedMind AI",
    description: "HAS-BLED score for major bleeding risk in atrial fibrillation patients on anticoagulation. ESC guideline recommended. Identify modifiable risk factors. Free, 7 languages.",
    keywords: ["HAS-BLED", "bleeding risk calculator", "anticoagulation bleeding", "atrial fibrillation", "ESC guidelines", "cardiology"],
  },
  "abcd2": {
    title: "ABCD² Score Calculator — TIA Stroke Risk — MedMind AI",
    description: "ABCD² score for early stroke risk after transient ischaemic attack (TIA). Predicts 2-day and 7-day stroke risk. Guides hospital admission and investigation urgency. Free.",
    keywords: ["ABCD2 score", "TIA stroke risk", "transient ischaemic attack", "stroke prediction", "neurology calculator", "stroke risk"],
  },
  "child-pugh": {
    title: "Child-Pugh Score Calculator — Liver Cirrhosis Severity — MedMind AI",
    description: "Child-Pugh score for hepatic reserve assessment in liver cirrhosis. Classifies into Child-Pugh A/B/C with 1-year and 2-year survival estimates. Free, 7 languages.",
    keywords: ["Child-Pugh score", "liver cirrhosis", "hepatic reserve", "cirrhosis severity", "hepatology calculator", "MELD alternative"],
  },
  "bmi": {
    title: "BMI Calculator — Body Mass Index (WHO Classification) — MedMind AI",
    description: "Free BMI calculator using WHO classification. Calculate body mass index, determine obesity grade, and get evidence-based management recommendations. Available in 7 languages.",
    keywords: ["BMI calculator", "body mass index", "obesity classification", "WHO BMI", "overweight calculator", "weight calculator"],
  },
  "corrected-calcium": {
    title: "Corrected Calcium Calculator — Hypoalbuminaemia Adjustment — MedMind AI",
    description: "Calculate albumin-corrected calcium to interpret serum calcium accurately in hypoalbuminaemic patients. Detects true hypo- and hypercalcaemia. Free, multilingual.",
    keywords: ["corrected calcium calculator", "albumin corrected calcium", "hypercalcemia", "hypocalcemia", "calcium correction", "biochemistry calculator"],
  },
  "anion-gap": {
    title: "Anion Gap Calculator — Metabolic Acidosis Classification — MedMind AI",
    description: "Calculate anion gap and albumin-corrected anion gap for metabolic acidosis diagnosis. Differentiates high-AG from normal-AG acidosis. Free, 7 languages.",
    keywords: ["anion gap calculator", "metabolic acidosis", "albumin corrected anion gap", "HAGMA", "acid-base calculator", "biochemistry"],
  },
  "meld": {
    title: "MELD / MELD-Na Score Calculator — Liver Disease Severity — MedMind AI",
    description: "MELD and MELD-Na score for liver disease severity and transplant priority (UNOS). Predicts 90-day mortality in cirrhosis. Evidence-based, free, 7 languages.",
    keywords: ["MELD score calculator", "MELD-Na", "liver transplant", "cirrhosis prognosis", "UNOS scoring", "hepatology calculator"],
  },
  "cockcroft-gault": {
    title: "Cockcroft-Gault Calculator — Creatinine Clearance & Drug Dosing — MedMind AI",
    description: "Cockcroft-Gault formula for creatinine clearance estimation and drug dose adjustment in renal impairment. Essential for pharmacokinetics. Free, 7 languages.",
    keywords: ["Cockcroft-Gault", "creatinine clearance", "drug dosing renal", "CrCl calculator", "nephrology", "renal dosing"],
  },
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
