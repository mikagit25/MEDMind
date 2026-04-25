import type { Metadata } from "next";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";

export const metadata: Metadata = {
  title: "Pricing — MedMind AI",
  description:
    "Affordable plans for medical students, residents, doctors and veterinarians. Start free, upgrade anytime. Evidence-based medical education powered by AI.",
  keywords: ["medical education pricing", "USMLE prep cost", "medical AI subscription", "student plan"],
  alternates: {
    canonical: `${SITE_URL}/pricing`,
    languages: Object.fromEntries(
      ["en", "ru", "ar", "tr", "de", "fr", "es"].map((l) => [l, `${SITE_URL}/${l}/pricing`])
    ),
  },
  openGraph: {
    title: "Pricing — MedMind AI",
    description: "Start free. Full AI-powered medical education from $15/month.",
    url: `${SITE_URL}/pricing`,
    siteName: "MedMind AI",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "MedMind AI Pricing",
    description: "Start free. Full AI-powered medical education from $15/month.",
  },
};

export default function PricingLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
