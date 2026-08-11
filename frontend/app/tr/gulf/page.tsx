// SYNC-GROUP: gulf-landing
// This page is part of a multilingual set. When content changes here,
// update all sibling pages to stay in sync:
//   /exams/gulf (EN)   /ar/gulf  (AR)   /ru/gulf  (RU)
//   /de/gulf  (DE)     /fr/gulf  (FR)   /es/gulf  (ES)
//   /tr/gulf  (TR) ← you are here
// TODO: replace with next-intl server routing when the project migrates to SSR i18n.

import type { Metadata } from "next";
import Link from "next/link";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { PublicFooter } from "@/components/layout/PublicFooter";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";

export const metadata: Metadata = {
  title: "Körfez Hemşirelik Sınavları 2025 — SNLE, DHA, QCHP, OMSB, NHRA | MedMind AI",
  description:
    "Körfez Prometric hemşirelik lisans sınavlarına hazırlanın: SNLE Suudi Arabistan, DHA Dubai, QCHP Katar, OMSB Umman, NHRA Bahreyn. Yapay zeka açıklamalı Prometric formatlı sorular.",
  alternates: {
    canonical: `${SITE_URL}/tr/gulf`,
    languages: {
      en: `${SITE_URL}/exams/gulf`,
      ru: `${SITE_URL}/ru/gulf`,
      ar: `${SITE_URL}/ar/gulf`,
      tr: `${SITE_URL}/tr/gulf`,
      "x-default": `${SITE_URL}/exams/gulf`,
    },
  },
  openGraph: {
    title: "Körfez Hemşirelik Sınavları — MedMind AI",
    description: "SNLE · DHA · QCHP · OMSB · NHRA · MOH UAE · DOH — tümü tek yerde",
    url: `${SITE_URL}/tr/gulf`,
    siteName: "MedMind AI",
    type: "website",
  },
};

const EXAMS = [
  { slug: "snle",    name: "SNLE — Suudi Arabistan",      body: "Suudi Sağlık Komisyonu (SCHS)" },
  { slug: "dha",     name: "DHA — Dubai, BAE",            body: "Dubai Sağlık Otoritesi (DHA)" },
  { slug: "qchp",   name: "QCHP — Katar",                body: "Katar Sağlık Meslekleri Konseyi (QCHP)" },
  { slug: "omsb",   name: "OMSB — Umman",                body: "Umman Tıbbi Uzmanlıklar Kurulu (OMSB)" },
  { slug: "nhra",   name: "NHRA — Bahreyn",              body: "Bahreyn Ulusal Sağlık Düzenleyici Kurumu (NHRA)" },
  { slug: "moh-uae", name: "MOH UAE — Kuzey Emirlikler", body: "BAE Sağlık Bakanlığı (MOHAP)" },
  { slug: "haad",   name: "DOH — Abu Dabi, BAE",         body: "Abu Dabi Sağlık Departmanı (DOH)" },
];

const CATEGORIES = [
  "Hemşirelik Temelleri",
  "Dahili-Cerrahi Hemşirelik",
  "Farmakoloji ve İlaç Yönetimi",
  "Maternal-Neonatal Hemşirelik",
  "Pediatrik Hemşirelik",
  "Ruh Sağlığı Hemşireliği",
  "Toplum ve Halk Sağlığı",
  "Liderlik ve Yönetim",
];

export default function TurkishGulfPage() {
  return (
    <div className="min-h-screen bg-bg font-serif text-ink">
      <ArticleNav />
      <section className="max-w-5xl mx-auto px-4 pt-16 pb-10">
        <div className="mb-2 text-xs font-syne font-bold text-ink-3 uppercase tracking-widest">
          Körfez Bölgesi · Prometric Lisansı
        </div>
        <h1 className="font-syne font-black text-3xl sm:text-4xl text-ink leading-tight mb-4">
          Körfez Hemşirelik Sınavları — Tam Karşılaştırma
        </h1>
        <p className="text-lg text-ink-2 leading-relaxed mb-6 max-w-3xl">
          7 Körfez Prometric hemşirelik lisans sınavının tamamı tek bir yerde. Pek çok hemşire birden fazla sınava aynı anda hazırlanır — önce kabul eden ülke çalışma yeri olur. Gulf Bundle ile tüm 8 sınava aynı anda erişim sağlayabilirsiniz.
        </p>
        <div className="flex flex-wrap gap-3 mb-8">
          <Link href="/register" className="font-syne font-bold text-sm bg-ink text-white px-6 py-3 rounded-xl hover:bg-red transition-colors">
            Ücretsiz Başla →
          </Link>
          <Link href="/exams/gulf" className="font-syne font-bold text-sm border border-border text-ink px-6 py-3 rounded-xl hover:bg-surface transition-colors">
            English
          </Link>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-10">
          {[
            { num: "7",    label: "sınav" },
            { num: "608+", label: "soru" },
            { num: "3 sa", label: "süre" },
            { num: "65%",  label: "geçme notu" },
          ].map(({ num, label }) => (
            <div key={label} className="bg-surface border border-border rounded-2xl p-4 text-center">
              <div className="font-syne font-black text-2xl text-ink">{num}</div>
              <div className="text-xs font-syne text-ink-3 mt-1">{label}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-4 py-8">
        <h2 className="font-syne font-bold text-xl text-ink mb-5">Mevcut Sınavlar</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {EXAMS.map(e => (
            <Link key={e.slug} href={`/exams/${e.slug}`}
              className="bg-surface border border-border rounded-xl p-5 hover:border-ink/30 hover:shadow-sm transition-all">
              <div className="font-syne font-bold text-sm text-ink mb-1">{e.name}</div>
              <div className="text-xs text-ink-3 mb-3">{e.body}</div>
              <div className="text-xs font-syne text-ink-2">100 soru · 3 saat · Geçme %65</div>
            </Link>
          ))}
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-4 py-8">
        <h2 className="font-syne font-bold text-xl text-ink mb-4">Sekiz Sınav Kategorisi</h2>
        <p className="text-sm text-ink-2 mb-5">
          Tüm Körfez Prometric sınavları aynı 8 klinik kategoriyi kapsar. SNLE için hazırlanmak, DHA, QCHP ve diğerleri için %80+ hazır olmanızı sağlar.
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {CATEGORIES.map(cat => (
            <div key={cat} className="bg-surface border border-border rounded-xl p-3 text-center">
              <div className="font-syne font-semibold text-xs text-ink">{cat}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-4 py-10">
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-6">
          <h2 className="font-syne font-bold text-base text-ink mb-2">
            Körfez'de Çalışmak İsteyen Hemşireler İçin
          </h2>
          <p className="text-sm text-ink-2 leading-relaxed mb-4">
            Tüm Körfez Prometric sınavları aynı 8 klinik kategoriyi kapsar: temeller, dahili-cerrahi, farmakoloji, maternal sağlık, pediatri, ruh sağlığı, toplum sağlığı ve liderlik. Tek çalışma planı — yedi ülke.
          </p>
          <Link href="/register" className="inline-block font-syne font-bold text-sm bg-ink text-white px-6 py-3 rounded-xl hover:bg-red transition-colors">
            Ücretsiz Kayıt Ol →
          </Link>
        </div>
      </section>

      <section className="max-w-5xl mx-auto px-4 pb-10">
        <p className="text-xs font-serif text-ink-3 leading-relaxed border-t border-border pt-6">
          MedMind AI, herhangi bir Körfez düzenleyici kuruluşu veya Prometric ile bağlantılı, onaylı veya ortak değildir. Sınav parametreleri kamuya açık resmi kaynaklardan alınmıştır. Başvurmadan önce güncel gereksinimleri ilgili otoriteden doğrulayın.
        </p>
      </section>
      <PublicFooter />
    </div>
  );
}
