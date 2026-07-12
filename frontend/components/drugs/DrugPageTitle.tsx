"use client";

import { useEffect, useState } from "react";
import { useI18n } from "@/lib/i18n";

const SEO_TITLES: Record<string, string> = {
  en: "Drug Reference Database",
  ru: "База данных лекарственных препаратов",
  ar: "قاعدة بيانات الأدوية",
  de: "Arzneimittel-Datenbank",
  fr: "Base de données des médicaments",
  es: "Base de datos de medicamentos",
  tr: "İlaç Referans Veritabanı",
};

const SEO_SUBS: Record<string, string> = {
  en: "with mechanisms, dosing, interactions & side effects — in 7 languages",
  ru: "с механизмами, дозировками, взаимодействиями и побочными эффектами — на 7 языках",
  ar: "مع الآليات والجرعات والتفاعلات والآثار الجانبية — بـ 7 لغات",
  de: "mit Wirkmechanismen, Dosierung, Wechselwirkungen & Nebenwirkungen — in 7 Sprachen",
  fr: "avec mécanismes, posologie, interactions & effets secondaires — en 7 langues",
  es: "con mecanismos, dosificación, interacciones y efectos secundarios — en 7 idiomas",
  tr: "mekanizmalar, dozaj, etkileşimler ve yan etkilerle — 7 dilde",
};

export function DrugPageTitle({ serverLang, total }: { serverLang: string; total: number }) {
  const { locale } = useI18n();
  const [lang, setLang] = useState(serverLang);
  useEffect(() => { if (locale) setLang(locale); }, [locale]);

  return (
    <>
      <h1 className="font-syne font-black text-2xl sm:text-3xl text-ink mb-1">
        {SEO_TITLES[lang] ?? SEO_TITLES.en}
      </h1>
      <p className="font-serif text-ink-3 text-sm mb-6">
        {total > 0 ? `${total.toLocaleString()} ` : ""}
        {SEO_SUBS[lang] ?? SEO_SUBS.en}
      </p>
    </>
  );
}
