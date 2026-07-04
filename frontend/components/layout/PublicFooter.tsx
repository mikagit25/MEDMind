import Link from "next/link";
import { getTrustShared, type TrustLocale } from "@/lib/trust-i18n";

interface Props {
  locale?: string;
}

export function PublicFooter({ locale = "en" }: Props) {
  const SUPPORTED: TrustLocale[] = ["en", "ru", "ar", "tr", "de", "fr", "es"];
  const loc: TrustLocale = SUPPORTED.includes(locale as TrustLocale) ? (locale as TrustLocale) : "en";
  const t = getTrustShared(loc);

  return (
    <footer className="border-t border-border bg-surface mt-16" dir={t.dir}>
      <div className="max-w-6xl mx-auto px-6 py-10">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
          {/* Brand */}
          <div>
            <Link
              href="/"
              className="font-syne font-extrabold text-lg text-ink tracking-tight"
            >
              MedMind AI
            </Link>
            <p className="text-ink-3 text-xs mt-1">{t.footer_tagline}</p>
          </div>

          {/* Trust links */}
          <nav className="flex flex-wrap gap-4 text-sm font-syne">
            <Link href="/how-it-works" className="text-ink-2 hover:text-ink transition-colors">{t.footer_how_it_works}</Link>
            <Link href="/pricing"       className="text-ink-2 hover:text-ink transition-colors">{t.footer_pricing}</Link>
            <Link href="/about"         className="text-ink-2 hover:text-ink transition-colors">{t.footer_about}</Link>
            <Link href="/editorial-policy"   className="text-ink-2 hover:text-ink transition-colors">{t.footer_editorial}</Link>
            <Link href="/medical-disclaimer" className="text-ink-2 hover:text-ink transition-colors">{t.footer_disclaimer}</Link>
            <Link href="/contact"       className="text-ink-2 hover:text-ink transition-colors">{t.footer_contact}</Link>
          </nav>
        </div>

        {/* Disclaimer line */}
        <p className="mt-6 text-xs text-ink-3 text-center md:text-start border-t border-border pt-6">
          {t.disclaimer_short}
        </p>
      </div>
    </footer>
  );
}
