import type { Metadata } from "next";
import { headers } from "next/headers";
import Link from "next/link";
import { getLearnT } from "@/lib/learn-i18n";

export const metadata: Metadata = {
  title: {
    template: "%s — MedMind Learn",
    default: "MedMind Learn — Medical Knowledge for Everyone",
  },
};

export default function LearnLayout({ children }: { children: React.ReactNode }) {
  const locale = headers().get("x-locale") ?? "en";
  const t = getLearnT(locale);

  return (
    <div className="min-h-screen bg-bg">
      {/* Top nav */}
      <header className="border-b border-border bg-surface sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link href="/" className="font-syne font-black text-lg text-ink">
              MedMind
            </Link>
            <nav className="hidden sm:flex items-center gap-4">
              <Link href="/learn/glossary" className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors">
                {t.nav_glossary}
              </Link>
              <Link href="/learn/topics" className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors">
                {t.nav_topics}
              </Link>
              <Link href="/learn/drugs" className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors">
                {t.nav_drugs}
              </Link>
            </nav>
          </div>
          <Link
            href="/register"
            className="px-4 py-1.5 rounded-lg bg-ink text-white font-syne font-bold text-sm hover:bg-ink-2 transition-colors"
          >
            {t.nav_get_started}
          </Link>
        </div>
      </header>

      {/* Medical disclaimer banner */}
      <div className="bg-amber-light border-b border-amber/20 px-4 py-2">
        <p className="max-w-5xl mx-auto font-serif text-xs text-amber text-center">
          ⚕️ <strong>Educational content only.</strong> {t.disclaimer}
        </p>
      </div>

      <main>{children}</main>

      {/* Footer */}
      <footer className="border-t border-border mt-16 py-8 px-4">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="font-serif text-xs text-ink-3 text-center sm:text-left">
            © {new Date().getFullYear()} MedMind AI · {t.footer_tagline}
          </div>
          <div className="flex items-center gap-4">
            <Link href="/learn/glossary" className="font-serif text-xs text-ink-3 hover:text-ink">{t.nav_glossary}</Link>
            <Link href="/learn/topics" className="font-serif text-xs text-ink-3 hover:text-ink">{t.nav_topics}</Link>
            <Link href="/drugs" className="font-serif text-xs text-ink-3 hover:text-ink">Drug DB</Link>
            <Link href="/login" className="font-serif text-xs text-ink-3 hover:text-ink">Login</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
