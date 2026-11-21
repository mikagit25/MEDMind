import type { ReactNode } from "react";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { PublicFooter } from "@/components/layout/PublicFooter";

export interface LegalSection {
  id: string;
  title: string;
  body: ReactNode;
}

interface Props {
  title: string;
  updated: string;
  intro: ReactNode;
  sections: LegalSection[];
}

/** Shared layout for /privacy and /terms (English-only legal pages). */
export function LegalPage({ title, updated, intro, sections }: Props) {
  return (
    <div className="min-h-screen bg-bg" dir="ltr" lang="en">
      <ArticleNav />

      <section className="bg-gradient-to-b from-surface to-bg py-14 px-6">
        <div className="max-w-3xl mx-auto">
          <h1 className="font-syne font-extrabold text-4xl text-ink mb-3">{title}</h1>
          <p className="text-ink-3 text-sm">Last updated: {updated}</p>
          <div className="text-ink-2 text-base leading-relaxed mt-6">{intro}</div>
        </div>
      </section>

      <div className="max-w-3xl mx-auto px-6 pb-12 space-y-8">
        <nav aria-label="Contents" className="rounded-xl border border-border bg-surface p-5">
          <ol className="list-decimal list-inside space-y-1 text-sm text-ink-2">
            {sections.map((s) => (
              <li key={s.id}>
                <a href={`#${s.id}`} className="hover:text-ink underline-offset-2 hover:underline">
                  {s.title}
                </a>
              </li>
            ))}
          </ol>
        </nav>

        {sections.map((s, i) => (
          <section key={s.id} id={s.id} className="scroll-mt-24">
            <h2 className="font-syne font-bold text-xl text-ink mb-3">
              {i + 1}. {s.title}
            </h2>
            <div className="text-ink-2 text-sm leading-relaxed space-y-3 [&_ul]:list-disc [&_ul]:pl-5 [&_ul]:space-y-1 [&_a]:underline [&_a]:text-ink">
              {s.body}
            </div>
          </section>
        ))}
      </div>

      <PublicFooter locale="en" />
    </div>
  );
}
