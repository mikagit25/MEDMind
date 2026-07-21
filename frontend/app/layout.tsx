import type { Metadata } from "next";
import { headers } from "next/headers";
import "./globals.css";
import { Providers } from "./providers";
import { Toaster } from "react-hot-toast";
import GoogleAnalytics from "@/components/GoogleAnalytics";
import { PWAInstallPrompt } from "@/components/ui/PWAInstallPrompt";
import { Suspense } from "react";
import AffiliateRefTracker from "@/components/AffiliateRefTracker";

const RTL_LOCALES = ["ar"];

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const SUPPORTED_LOCALES = ["en", "ru", "ar", "tr", "de", "fr", "es"];

export const metadata: Metadata = {
  title: {
    default: "MedMind AI — Medical Education Platform",
    template: "%s | MedMind AI",
  },
  description:
    "AI-powered learning for doctors, residents, students, and veterinarians. Evidence-based content with Claude AI and PubMed integration.",
  keywords: ["medical education", "AI tutor", "USMLE prep", "medical flashcards", "clinical cases", "drug database", "medical quiz"],
  metadataBase: new URL(SITE_URL),
  // Open Graph
  openGraph: {
    title: "MedMind AI — Medical Education Platform",
    description: "AI-powered medical learning — evidence-based modules, flashcards, clinical cases and drug database.",
    url: SITE_URL,
    siteName: "MedMind AI",
    type: "website",
    locale: "en_US",
    alternateLocale: ["ru_RU", "ar_SA", "tr_TR", "de_DE", "fr_FR", "es_ES"],
    images: [
      {
        url: `${SITE_URL}/opengraph-image`,
        width: 1200,
        height: 630,
        alt: "MedMind AI — Medical Education Platform",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "MedMind AI — Medical Education Platform",
    description: "AI-powered medical learning for doctors, students, and veterinarians.",
    site: "@medmindai",
    images: [`${SITE_URL}/opengraph-image`],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true, "max-snippet": -1 },
  },
  // No alternates in root layout — Next.js merges layout+page alternates,
  // so any canonical/languages here would appear on EVERY page. Each page's
  // generateMetadata sets its own alternates independently.
};

const JSON_LD_ORGANIZATION = {
  "@context": "https://schema.org",
  "@type": ["Organization", "EducationalOrganization"],
  name: "MedMind AI",
  legalName: "MedMind AI",
  alternateName: "MedMind Pro",
  url: "https://medmind.pro",
  logo: "https://medmind.pro/icon-512.png",
  description:
    "AI-powered medical education platform for doctors, residents, medical students, and veterinarians. Evidence-based learning with Claude AI and real-time PubMed integration.",
  disambiguatingDescription:
    "MedMind AI (medmind.pro) is a medical education and AI tutoring platform for healthcare professionals and students — not affiliated with medmind.com, which provides remote patient monitoring services.",
  foundingDate: "2025",
  founder: {
    "@type": "Person",
    name: "Mikalai",
    email: "33mikalai@gmail.com",
  },
  sameAs: [
    "https://medmind.pro",
    "https://t.me/Medmindpro_bot",
    "https://twitter.com/medmindai",
    "https://x.com/medmindai",
    "https://www.linkedin.com/company/medmind-pro",
  ],
  knowsAbout: [
    "Medical Education", "Clinical Cases", "Pharmacology",
    "Cardiology", "Neurology", "Surgery", "Pediatrics",
    "Veterinary Medicine", "Spaced Repetition", "AI Tutoring",
    "USMLE Preparation", "Medical Flashcards", "Drug Database",
  ],
};

const JSON_LD_WEBSITE = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: "MedMind AI",
  url: "https://medmind.pro",
  potentialAction: {
    "@type": "SearchAction",
    target: {
      "@type": "EntryPoint",
      urlTemplate: "https://medmind.pro/articles?q={search_term_string}",
    },
    "query-input": "required name=search_term_string",
  },
};

const JSON_LD_SOFTWARE = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "MedMind AI",
  applicationCategory: "EducationApplication",
  applicationSubCategory: "Medical Education",
  operatingSystem: "Web, iOS, Android",
  url: "https://medmind.pro",
  description:
    "AI-powered medical education app for doctors, residents, students, and veterinarians. Study with AI tutor, clinical cases, drug database and spaced repetition flashcards.",
  offers: {
    "@type": "Offer",
    price: "0",
    priceCurrency: "USD",
    description: "Free plan available — no credit card required",
  },
  featureList: [
    "AI Medical Tutor (Claude Sonnet)",
    "97+ Evidence-based Learning Modules",
    "Spaced Repetition Flashcards",
    "Clinical Case Simulations",
    "Drug Database",
    "Differential Diagnosis AI",
    "USMLE Preparation",
    "Available in 9 languages",
    "Telegram Bot Integration",
  ],
  publisher: {
    "@type": "Organization",
    name: "MedMind AI",
    url: "https://medmind.pro",
  },
};

const JSON_LD_EDUCATIONAL = {
  "@context": "https://schema.org",
  "@type": "EducationalOrganization",
  name: "MedMind AI",
  url: "https://medmind.pro",
  description: "Evidence-based AI medical education — 97+ modules, clinical cases, drug database, spaced repetition flashcards in 9 languages.",
  hasOfferCatalog: {
    "@type": "OfferCatalog",
    name: "Medical Learning Plans",
    itemListElement: [
      {
        "@type": "Offer",
        name: "Free Plan",
        price: "0",
        priceCurrency: "USD",
        description: "8 core modules, 5 AI questions/day, basic flashcards",
      },
      {
        "@type": "Offer",
        name: "Student Plan",
        price: "15",
        priceCurrency: "USD",
        description: "All 82+ modules, 50 AI questions/day, full SM-2 flashcards",
      },
      {
        "@type": "Offer",
        name: "Pro Plan",
        price: "20",
        priceCurrency: "USD",
        description: "Unlimited AI, veterinary content, drug database, priority support",
      },
    ],
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  // Read locale injected by middleware (x-locale header) for bypass paths like /ar/gulf.
  // Falls back to "en" for all other routes.
  const locale = headers().get("x-locale") ?? "en";
  const dir = RTL_LOCALES.includes(locale) ? "rtl" : "ltr";
  return (
    <html lang={locale} dir={dir}>
      <head>
        {/* Anti-FOUC: apply dark class before first paint from localStorage */}
        <script dangerouslySetInnerHTML={{ __html: `
          try {
            var ui = JSON.parse(localStorage.getItem('medmind-ui') || '{}');
            if (ui.state && ui.state.darkMode) {
              document.documentElement.classList.add('dark');
            }
          } catch(e) {}
        `}} />
        {/* hreflang is set per-page via generateMetadata alternates.languages,
            NOT here — layout-level hreflang would appear on every page and
            create duplicate/conflicting tags on article and drug pages. */}
        {/* PWA — manifest injected automatically by app/manifest.ts as /manifest.webmanifest */}
        <meta name="theme-color" content="#1a1814" media="(prefers-color-scheme: dark)" />
        <meta name="theme-color" content="#1a1814" media="(prefers-color-scheme: light)" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="apple-mobile-web-app-title" content="MedMind" />
        <link rel="apple-touch-icon" href="/icon-192.png" />
        {/* Bing Webmaster Tools verification */}
        <meta name="msvalidate.01" content="EE9494199B77315D3C02B51990B776E4" />
        {/* Viewport — prevents zoom on input focus on iOS */}
        <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
        {/* JSON-LD structured data for Google, Perplexity, ChatGPT, Bing */}
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(JSON_LD_ORGANIZATION) }} />
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(JSON_LD_WEBSITE) }} />
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(JSON_LD_EDUCATIONAL) }} />
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(JSON_LD_SOFTWARE) }} />
      </head>
      <body className="bg-bg font-serif text-ink antialiased">
        <GoogleAnalytics />
        <Suspense fallback={null}>
          <AffiliateRefTracker />
        </Suspense>
        <Providers>{children}</Providers>
        <Toaster position="top-right" />
        <PWAInstallPrompt />
      </body>
    </html>
  );
}
