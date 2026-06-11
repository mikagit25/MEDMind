import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: {
    template: "%s — MedMind Learn",
    default: "MedMind Learn — Medical Knowledge for Everyone",
  },
};

export default function LearnLayout({ children }: { children: React.ReactNode }) {
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
                Glossary
              </Link>
              <Link href="/learn/topics" className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors">
                Topics
              </Link>
              <Link href="/learn/drugs" className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors">
                Drugs
              </Link>
            </nav>
          </div>
          <Link
            href="/register"
            className="px-4 py-1.5 rounded-lg bg-ink text-white font-syne font-bold text-sm hover:bg-ink-2 transition-colors"
          >
            Get Started Free
          </Link>
        </div>
      </header>

      {/* Medical disclaimer banner */}
      <div className="bg-amber-light border-b border-amber/20 px-4 py-2">
        <p className="max-w-5xl mx-auto font-serif text-xs text-amber text-center">
          ⚕️ <strong>Educational content only.</strong> This information does not replace professional medical advice.
          Always consult a qualified healthcare provider for diagnosis and treatment.
        </p>
      </div>

      <main>{children}</main>

      {/* Footer */}
      <footer className="border-t border-border mt-16 py-8 px-4">
        <div className="max-w-5xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="font-serif text-xs text-ink-3 text-center sm:text-left">
            © {new Date().getFullYear()} MedMind AI · Educational platform for medical students, physicians &amp; everyone curious about medicine
          </div>
          <div className="flex items-center gap-4">
            <Link href="/learn/glossary" className="font-serif text-xs text-ink-3 hover:text-ink">Glossary</Link>
            <Link href="/learn/topics" className="font-serif text-xs text-ink-3 hover:text-ink">Topics</Link>
            <Link href="/drugs" className="font-serif text-xs text-ink-3 hover:text-ink">Drug DB</Link>
            <Link href="/login" className="font-serif text-xs text-ink-3 hover:text-ink">Login</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
