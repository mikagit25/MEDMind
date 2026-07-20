// SYNC-GROUP: gulf-landing
// This page is part of a multilingual set. When content changes here,
// update all sibling pages to stay in sync:
//   /exams/gulf (EN)   /ar/gulf  (AR)   /tr/gulf  (TR)
//   /de/gulf  (DE)     /fr/gulf  (FR)   /es/gulf  (ES)
//   /ru/gulf  (RU) ← you are here
// TODO: replace with next-intl server routing when the project migrates to SSR i18n.

import type { Metadata } from "next";
import Link from "next/link";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { PublicFooter } from "@/components/layout/PublicFooter";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";

export const metadata: Metadata = {
  title: "Подготовка к экзаменам по сестринскому делу в странах Залива — SNLE, DHA, QCHP, OMSB | MedMind AI",
  description:
    "Готовьтесь к экзаменам на медсестру в странах Персидского залива: SNLE Саудовская Аравия, DHA Дубай, QCHP Катар, OMSB Оман, NHRA Бахрейн. Вопросы в формате Prometric с объяснениями ИИ.",
  alternates: {
    canonical: `${SITE_URL}/ru/gulf`,
    languages: { "en": `${SITE_URL}/exams/gulf`, "ru": `${SITE_URL}/ru/gulf`, "ar": `${SITE_URL}/ar/gulf`, "x-default": `${SITE_URL}/exams/gulf` },
  },
  openGraph: {
    title: "Экзамены сестринского дела Персидского залива — MedMind AI",
    description: "SNLE · DHA · QCHP · OMSB · NHRA · MOH UAE · DOH — все лицензионные экзамены в одном месте",
    url: `${SITE_URL}/ru/gulf`, siteName: "MedMind AI", type: "website",
  },
};

const EXAMS = [
  { slug: "snle",     name: "SNLE — Саудовская Аравия",         body: "SCHS (Саудовская комиссия по здравоохранению)" },
  { slug: "dha",      name: "DHA — Дубай, ОАЭ",                body: "Управление здравоохранения Дубая (DHA)" },
  { slug: "qchp",    name: "QCHP — Катар",                     body: "Совет медицинских работников Катара (QCHP)" },
  { slug: "omsb",    name: "OMSB — Оман",                      body: "Оманский совет медицинских специальностей (OMSB)" },
  { slug: "nhra",    name: "NHRA — Бахрейн",                   body: "Национальный регулятор здравоохранения Бахрейна (NHRA)" },
  { slug: "moh-uae", name: "MOH UAE — Северные Эмираты",       body: "Министерство здравоохранения ОАЭ (MOHAP)" },
  { slug: "haad",    name: "DOH — Абу-Даби, ОАЭ",              body: "Департамент здравоохранения Абу-Даби (DOH)" },
];

export default function RussianGulfPage() {
  return (
    <div className="min-h-screen bg-bg font-serif text-ink">
      <ArticleNav />
      <section className="max-w-5xl mx-auto px-4 pt-16 pb-10">
        <div className="mb-2 text-xs font-syne font-bold text-ink-3 uppercase tracking-widest">Персидский Залив · Лицензирование Prometric</div>
        <h1 className="font-syne font-black text-3xl sm:text-4xl text-ink leading-tight mb-4">
          Экзамены по сестринскому делу в странах Залива
        </h1>
        <p className="text-lg text-ink-2 leading-relaxed mb-6 max-w-3xl">
          Все 7 лицензионных экзаменов по системе Prometric в одном месте. Многие медсёстры сдают несколько экзаменов одновременно — та страна, которая принимает первой, и становится местом работы. Gulf Bundle открывает доступ ко всем 7 экзаменам сразу.
        </p>
        <div className="flex flex-wrap gap-3 mb-8">
          <Link href="/register" className="font-syne font-bold text-sm bg-ink text-white px-6 py-3 rounded-xl hover:bg-red transition-colors">Начать бесплатно →</Link>
          <Link href="/exams/gulf" className="font-syne font-bold text-sm border border-border text-ink px-6 py-3 rounded-xl hover:bg-surface transition-colors">English</Link>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-10">
          {[{ num: "7", label: "экзаменов" }, { num: "608+", label: "вопросов" }, { num: "3 ч", label: "длительность" }, { num: "65%", label: "проходной балл" }].map(({ num, label }) => (
            <div key={label} className="bg-surface border border-border rounded-2xl p-4 text-center">
              <div className="font-syne font-black text-2xl text-ink">{num}</div>
              <div className="text-xs font-syne text-ink-3 mt-1">{label}</div>
            </div>
          ))}
        </div>
      </section>
      <section className="max-w-5xl mx-auto px-4 py-8">
        <h2 className="font-syne font-bold text-xl text-ink mb-5">Доступные экзамены</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {EXAMS.map(e => (
            <Link key={e.slug} href={`/exams/${e.slug}`} className="bg-surface border border-border rounded-xl p-5 hover:border-ink/30 hover:shadow-sm transition-all">
              <div className="font-syne font-bold text-sm text-ink mb-1">{e.name}</div>
              <div className="text-xs text-ink-3 mb-3">{e.body}</div>
              <div className="text-xs font-syne text-ink-2">100 вопросов · 3 часа · Проход 65%</div>
            </Link>
          ))}
        </div>
      </section>
      <section className="max-w-5xl mx-auto px-4 py-10">
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6">
          <h2 className="font-syne font-bold text-base text-ink mb-2">Для медсестёр, стремящихся работать в Заливе</h2>
          <p className="text-sm text-ink-2 leading-relaxed mb-4">
            Все экзамены Prometric в Заливе охватывают одинаковые 8 клинических категорий. Подготовка к SNLE на 80%+ готовит вас к DHA, QCHP и другим. Один план обучения — семь стран.
          </p>
          <Link href="/register" className="inline-block font-syne font-bold text-sm bg-ink text-white px-6 py-3 rounded-xl hover:bg-red transition-colors">Зарегистрироваться бесплатно →</Link>
        </div>
      </section>
      <section className="max-w-5xl mx-auto px-4 pb-10">
        <p className="text-xs font-serif text-ink-3 leading-relaxed border-t border-border pt-6">
          MedMind AI не является аффилиатом, представителем или партнёром каких-либо регулирующих органов Залива или Prometric. Параметры экзаменов взяты из общедоступных официальных источников. Проверяйте актуальные требования у соответствующего регулятора.
        </p>
      </section>
      <PublicFooter />
    </div>
  );
}
