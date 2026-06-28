"use client";
import Link from "next/link";
import { useT } from "@/lib/i18n";

export default function NotFound() {
  const t = useT();
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-bg px-4">
      <div className="text-center space-y-6 max-w-md w-full">
        <Link href="/" className="inline-block font-syne font-extrabold text-3xl tracking-tight">
          Med<span className="text-red">Mind</span>
        </Link>

        <div className="font-syne font-black text-[8rem] leading-none text-border select-none">
          404
        </div>

        <h1 className="font-syne font-bold text-xl text-ink">
          {t("how_it_works_page.page_not_found")}
        </h1>
        <p className="font-serif text-ink-3 text-sm">
          {t("how_it_works_page.page_not_found_desc")}
        </p>

        <div className="flex flex-col sm:flex-row gap-3 justify-center pt-2">
          <Link
            href="/dashboard"
            className="px-6 py-3 bg-ink text-white rounded-lg font-syne font-semibold text-sm hover:bg-red transition-colors"
          >
            {t("landing.go_to_dashboard")}
          </Link>
          <Link
            href="/modules"
            className="px-6 py-3 border border-border rounded-lg font-syne font-semibold text-sm hover:bg-bg-2 transition-colors text-ink"
          >
            {t("nav.items.my_courses")}
          </Link>
          <Link
            href="/articles"
            className="px-6 py-3 border border-border rounded-lg font-syne font-semibold text-sm hover:bg-bg-2 transition-colors text-ink"
          >
            {t("landing.nav_articles")}
          </Link>
        </div>
      </div>
    </div>
  );
}
