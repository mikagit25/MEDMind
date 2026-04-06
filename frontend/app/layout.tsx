import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";
import { Toaster } from "react-hot-toast";

export const metadata: Metadata = {
  title: "MedMind AI — Medical Education Platform",
  description:
    "AI-powered learning for doctors, residents, students, and veterinarians. Evidence-based content with Claude AI and PubMed integration.",
  keywords: ["medical education", "AI tutor", "USMLE", "flashcards", "clinical cases"],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-bg font-serif text-ink antialiased">
        <Providers>{children}</Providers>
        <Toaster position="top-right" />
      </body>
    </html>
  );
}
