"use client";
import Link from "next/link";
import { useT } from "@/lib/i18n";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const t = useT();
  return (
    <div className="min-h-screen bg-bg flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Brand — links back to homepage */}
        <div className="text-center mb-8">
          <Link href="/" className="inline-block hover:opacity-80 transition-opacity">
            <div className="font-syne font-black text-4xl text-ink tracking-tight">
              Med<span className="text-red">Mind</span>
            </div>
          </Link>
          <div className="text-ink-3 font-serif text-sm mt-1">{t("landing.footer_tagline")}</div>
        </div>
        {children}
      </div>
    </div>
  );
}
