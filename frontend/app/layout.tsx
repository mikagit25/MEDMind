import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";
import { Toaster } from "react-hot-toast";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.ai";
const SUPPORTED_LOCALES = ["en", "ru", "ar", "tr", "de", "fr", "es"];

export const metadata: Metadata = {
  title: "MedMind AI — Medical Education Platform",
  description:
    "AI-powered learning for doctors, residents, students, and veterinarians. Evidence-based content with Claude AI and PubMed integration.",
  keywords: ["medical education", "AI tutor", "USMLE", "flashcards", "clinical cases"],
  // Open Graph
  openGraph: {
    title: "MedMind AI — Medical Education Platform",
    description: "AI-powered medical learning — evidence-based modules, flashcards, clinical cases and drug database.",
    url: SITE_URL,
    siteName: "MedMind AI",
    type: "website",
  },
  // Tell crawlers this page is available in 7 languages
  alternates: {
    canonical: SITE_URL,
    languages: Object.fromEntries(
      SUPPORTED_LOCALES.map((l) => [l, `${SITE_URL}/${l}`])
    ),
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
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
        {/* hreflang — tells Google which locale version to serve per country */}
        {SUPPORTED_LOCALES.map((l) => (
          <link key={l} rel="alternate" hrefLang={l} href={`${SITE_URL}/${l}`} />
        ))}
        <link rel="alternate" hrefLang="x-default" href={SITE_URL} />
      </head>
      <body className="bg-bg font-serif text-ink antialiased">
        <Providers>{children}</Providers>
        <Toaster position="top-right" />
      </body>
    </html>
  );
}
