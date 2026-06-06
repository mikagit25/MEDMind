"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useI18n } from "@/lib/i18n";

type Lang = "en" | "ru" | "ar" | "es" | "de" | "fr" | "tr";

interface NewsItem {
  id: string;
  slug: string;
  source_name: string;
  source_url: string;
  title: string;
  summary_excerpt: string;
  category: string;
  original_published_at: string | null;
  fetched_at: string;
}

interface CategoryStat {
  category: string;
  count: number;
}

const LANGS: { value: Lang; flag: string }[] = [
  { value: "en", flag: "🇬🇧" }, { value: "ru", flag: "🇷🇺" }, { value: "de", flag: "🇩🇪" },
  { value: "fr", flag: "🇫🇷" }, { value: "ar", flag: "🇸🇦" }, { value: "tr", flag: "🇹🇷" },
  { value: "es", flag: "🇪🇸" },
];

const CATEGORY_LABELS: Record<string, Record<Lang, string>> = {
  "cardiology":          { en: "Cardiology", ru: "Кардиология", ar: "أمراض القلب", es: "Cardiología", de: "Kardiologie", fr: "Cardiologie", tr: "Kardiyoloji" },
  "oncology":            { en: "Oncology", ru: "Онкология", ar: "علم الأورام", es: "Oncología", de: "Onkologie", fr: "Oncologie", tr: "Onkoloji" },
  "neurology":           { en: "Neurology", ru: "Неврология", ar: "طب الأعصاب", es: "Neurología", de: "Neurologie", fr: "Neurologie", tr: "Nöroloji" },
  "infectious-disease":  { en: "Infectious Disease", ru: "Инфекционные болезни", ar: "الأمراض المعدية", es: "Enfermedades infecciosas", de: "Infektionskrankheiten", fr: "Maladies infectieuses", tr: "Enfeksiyon hastalıkları" },
  "endocrinology":       { en: "Endocrinology", ru: "Эндокринология", ar: "أمراض الغدد الصماء", es: "Endocrinología", de: "Endokrinologie", fr: "Endocrinologie", tr: "Endokrinoloji" },
  "pulmonology":         { en: "Pulmonology", ru: "Пульмонология", ar: "أمراض الرئة", es: "Neumología", de: "Pneumologie", fr: "Pneumologie", tr: "Pulmonoloji" },
  "nephrology":          { en: "Nephrology", ru: "Нефрология", ar: "أمراض الكلى", es: "Nefrología", de: "Nephrologie", fr: "Néphrologie", tr: "Nefroloji" },
  "gastroenterology":    { en: "Gastroenterology", ru: "Гастроэнтерология", ar: "أمراض الجهاز الهضمي", es: "Gastroenterología", de: "Gastroenterologie", fr: "Gastro-entérologie", tr: "Gastroenteroloji" },
  "psychiatry":          { en: "Psychiatry", ru: "Психиатрия", ar: "الطب النفسي", es: "Psiquiatría", de: "Psychiatrie", fr: "Psychiatrie", tr: "Psikiyatri" },
  "pediatrics":          { en: "Pediatrics", ru: "Педиатрия", ar: "طب الأطفال", es: "Pediatría", de: "Pädiatrie", fr: "Pédiatrie", tr: "Pediatri" },
  "surgery":             { en: "Surgery", ru: "Хирургия", ar: "الجراحة", es: "Cirugía", de: "Chirurgie", fr: "Chirurgie", tr: "Cerrahi" },
  "obstetrics":          { en: "Obstetrics", ru: "Акушерство", ar: "التوليد", es: "Obstetricia", de: "Geburtshilfe", fr: "Obstétrique", tr: "Obstetrik" },
  "public-health":       { en: "Public Health", ru: "Общественное здравоохранение", ar: "الصحة العامة", es: "Salud pública", de: "Öffentliche Gesundheit", fr: "Santé publique", tr: "Halk sağlığı" },
  "general-medicine":    { en: "General Medicine", ru: "Общая медицина", ar: "الطب العام", es: "Medicina general", de: "Allgemeinmedizin", fr: "Médecine générale", tr: "Genel tıp" },
};

const SOURCE_COLORS: Record<string, string> = {
  "WHO": "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  "medRxiv": "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300",
};

const T: Record<Lang, {
  title: string; sub: string; all: string; loading: string; empty: string;
  read_more: string; source: string; updated: string; categories: string;
  nav_articles: string; nav_calcs: string; nav_symptoms: string;
}> = {
  en: { title: "Medical News", sub: "Latest research from PubMed, WHO, and medRxiv — AI-summarised in 7 languages", all: "All", loading: "Loading news…", empty: "No articles yet. Check back soon — we update every 6 hours.", read_more: "Read more", source: "Source", updated: "Updated", categories: "Categories", nav_articles: "Articles", nav_calcs: "Calculators", nav_symptoms: "Symptoms" },
  ru: { title: "Медицинские новости", sub: "Последние исследования из PubMed, ВОЗ и medRxiv — AI-рефераты на 7 языках", all: "Все", loading: "Загрузка…", empty: "Статей пока нет. Мы обновляемся каждые 6 часов.", read_more: "Читать далее", source: "Источник", updated: "Обновлено", categories: "Категории", nav_articles: "Статьи", nav_calcs: "Калькуляторы", nav_symptoms: "Чекер симптомов" },
  ar: { title: "الأخبار الطبية", sub: "أحدث الأبحاث من PubMed وWHO وmedRxiv — ملخصات بالذكاء الاصطناعي بـ7 لغات", all: "الكل", loading: "جارٍ التحميل…", empty: "لا توجد مقالات بعد. نحدّث كل 6 ساعات.", read_more: "اقرأ المزيد", source: "المصدر", updated: "تحديث", categories: "التصنيفات", nav_articles: "مقالات", nav_calcs: "آلات حاسبة", nav_symptoms: "فاحص الأعراض" },
  es: { title: "Noticias médicas", sub: "Últimas investigaciones de PubMed, OMS y medRxiv — resúmenes por IA en 7 idiomas", all: "Todo", loading: "Cargando…", empty: "Aún no hay artículos. Actualizamos cada 6 horas.", read_more: "Leer más", source: "Fuente", updated: "Actualizado", categories: "Categorías", nav_articles: "Artículos", nav_calcs: "Calculadoras", nav_symptoms: "Síntomas" },
  de: { title: "Medizinische Neuigkeiten", sub: "Aktuelle Forschung aus PubMed, WHO und medRxiv — KI-Zusammenfassungen in 7 Sprachen", all: "Alle", loading: "Lädt…", empty: "Noch keine Artikel. Wir aktualisieren alle 6 Stunden.", read_more: "Mehr lesen", source: "Quelle", updated: "Aktualisiert", categories: "Kategorien", nav_articles: "Artikel", nav_calcs: "Rechner", nav_symptoms: "Symptom-Checker" },
  fr: { title: "Actualités médicales", sub: "Dernières recherches de PubMed, OMS et medRxiv — résumés par IA en 7 langues", all: "Tout", loading: "Chargement…", empty: "Aucun article pour l'instant. Nous mettons à jour toutes les 6 heures.", read_more: "Lire la suite", source: "Source", updated: "Mis à jour", categories: "Catégories", nav_articles: "Articles", nav_calcs: "Calculateurs", nav_symptoms: "Symptômes" },
  tr: { title: "Tıp Haberleri", sub: "PubMed, DSÖ ve medRxiv'den son araştırmalar — 7 dilde YZ özetleri", all: "Tümü", loading: "Yükleniyor…", empty: "Henüz makale yok. Her 6 saatte güncelliyoruz.", read_more: "Devamını oku", source: "Kaynak", updated: "Güncellendi", categories: "Kategoriler", nav_articles: "Makaleler", nav_calcs: "Hesap makineleri", nav_symptoms: "Semptomlar" },
};

function getCatLabel(cat: string, lang: Lang): string {
  return CATEGORY_LABELS[cat]?.[lang] ?? cat.replace(/-/g, " ");
}

function formatDate(dateStr: string | null, lang: Lang): string {
  if (!dateStr) return "";
  try {
    return new Intl.DateTimeFormat(lang === "ar" ? "ar-SA" : lang, {
      year: "numeric", month: "short", day: "numeric"
    }).format(new Date(dateStr));
  } catch {
    return dateStr.split("T")[0];
  }
}

const API = process.env.NEXT_PUBLIC_API_URL ?? "/api/v1";

export default function NewsPage() {
  const { locale, setLocale } = useI18n();
  const lang = (LANGS.some(l => l.value === locale) ? locale : "en") as Lang;
  const t = T[lang];

  const [news, setNews] = useState<NewsItem[]>([]);
  const [categories, setCategories] = useState<CategoryStat[]>([]);
  const [activeCat, setActiveCat] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchNews = useCallback(async (cat: string | null) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ locale: lang, limit: "24" });
      if (cat) params.set("category", cat);
      const res = await fetch(`${API}/news?${params}`);
      if (res.ok) setNews(await res.json());
    } catch { /* silent */ } finally {
      setLoading(false);
    }
  }, [lang]);

  useEffect(() => {
    fetch(`${API}/news/categories`).then(r => r.json()).then(setCategories).catch(() => {});
  }, []);

  useEffect(() => { fetchNews(activeCat); }, [activeCat, fetchNews]);

  return (
    <div className="min-h-screen bg-bg" dir={lang === "ar" ? "rtl" : "ltr"}>
      {/* Nav */}
      <nav className="bg-surface border-b border-border sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-3">
          <Link href="/" className="font-syne font-extrabold text-xl sm:text-2xl tracking-tight text-ink flex-shrink-0">
            Med<span className="text-red">Mind</span>
          </Link>
          <div className="hidden md:flex items-center gap-1">
            <Link href="/articles" className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2">{t.nav_articles}</Link>
            <Link href="/news" className="font-syne font-semibold text-sm text-ink hover:text-red transition-colors px-3 py-2">{t.title}</Link>
            <Link href="/calculators" className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2">{t.nav_calcs}</Link>
            <Link href="/symptoms" className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2">{t.nav_symptoms}</Link>
          </div>
          <div className="flex items-center gap-2">
            <select value={lang} onChange={e => setLocale(e.target.value)}
              className="text-xs font-syne border border-border rounded px-1.5 py-1 bg-bg text-ink focus:outline-none">
              {LANGS.map(l => <option key={l.value} value={l.value}>{l.flag}</option>)}
            </select>
            <Link href="/register" className="btn-primary text-xs sm:text-sm px-3 py-1.5 hidden sm:block">
              {lang === "ru" ? "Регистрация" : lang === "ar" ? "التسجيل" : lang === "de" ? "Registrieren" : lang === "fr" ? "S'inscrire" : lang === "es" ? "Registrarse" : lang === "tr" ? "Kayıt ol" : "Sign up"}
            </Link>
          </div>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
        {/* Header */}
        <div className="mb-8">
          <div className="inline-flex items-center gap-2 bg-surface border border-border rounded-full px-4 py-1.5 mb-4">
            <span className="inline-block w-2 h-2 bg-green-500 rounded-full animate-pulse"/>
            <span className="font-syne font-semibold text-xs text-ink-2">
              {lang === "ru" ? "Обновляется каждые 6 часов" : lang === "ar" ? "يتحدث كل 6 ساعات" : lang === "de" ? "Alle 6 Stunden aktualisiert" : lang === "fr" ? "Mis à jour toutes les 6h" : lang === "es" ? "Actualizado cada 6h" : lang === "tr" ? "Her 6 saatte güncellendi" : "Updated every 6 hours"}
            </span>
          </div>
          <h1 className="font-syne font-extrabold text-3xl sm:text-4xl text-ink mb-2">{t.title}</h1>
          <p className="text-ink-2 text-sm sm:text-base">{t.sub}</p>
        </div>

        <div className="flex flex-col lg:flex-row gap-8">
          {/* Sidebar: categories */}
          <aside className="lg:w-52 flex-shrink-0">
            <p className="font-syne font-bold text-xs text-ink-3 uppercase tracking-widest mb-3">{t.categories}</p>
            <div className="flex flex-row lg:flex-col gap-1.5 flex-wrap">
              <button
                onClick={() => setActiveCat(null)}
                className={`text-left font-syne font-semibold text-sm px-3 py-2 rounded-lg transition-colors ${!activeCat ? "bg-ink text-[#f0ede8]" : "text-ink-2 hover:bg-surface-2"}`}
              >
                {t.all}
              </button>
              {categories.map(c => (
                <button
                  key={c.category}
                  onClick={() => setActiveCat(c.category)}
                  className={`text-left font-syne font-semibold text-sm px-3 py-2 rounded-lg transition-colors flex items-center justify-between gap-2 ${activeCat === c.category ? "bg-ink text-[#f0ede8]" : "text-ink-2 hover:bg-surface-2"}`}
                >
                  <span className="truncate">{getCatLabel(c.category, lang)}</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded-full ${activeCat === c.category ? "bg-white/20 text-white" : "bg-border text-ink-3"}`}>{c.count}</span>
                </button>
              ))}
            </div>
          </aside>

          {/* News grid */}
          <div className="flex-1 min-w-0">
            {loading ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
                {[...Array(6)].map((_, i) => (
                  <div key={i} className="bg-surface border border-border rounded-2xl p-5 animate-pulse">
                    <div className="h-3 bg-border rounded w-1/3 mb-3"/>
                    <div className="h-5 bg-border rounded w-full mb-2"/>
                    <div className="h-5 bg-border rounded w-4/5 mb-4"/>
                    <div className="h-3 bg-border rounded w-full mb-1.5"/>
                    <div className="h-3 bg-border rounded w-full mb-1.5"/>
                    <div className="h-3 bg-border rounded w-2/3"/>
                  </div>
                ))}
              </div>
            ) : news.length === 0 ? (
              <div className="text-center py-20 text-ink-3 font-syne">
                <div className="text-4xl mb-4">📰</div>
                <p>{t.empty}</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
                {news.map(item => (
                  <Link
                    key={item.id}
                    href={`/news/${item.slug}?locale=${lang}`}
                    className="group bg-surface border border-border rounded-2xl p-5 hover:border-red/40 hover:shadow-sm transition-all flex flex-col"
                  >
                    {/* Top row: source badge + date */}
                    <div className="flex items-center justify-between gap-2 mb-3">
                      <span className={`text-xs font-syne font-bold px-2 py-0.5 rounded-full ${SOURCE_COLORS[item.source_name] ?? "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300"}`}>
                        {item.source_name}
                      </span>
                      <span className="text-xs text-ink-3 font-syne flex-shrink-0">
                        {formatDate(item.original_published_at || item.fetched_at, lang)}
                      </span>
                    </div>

                    {/* Category */}
                    <span className="text-xs font-syne font-semibold text-red mb-2 uppercase tracking-wide">
                      {getCatLabel(item.category, lang)}
                    </span>

                    {/* Title */}
                    <h2 className="font-syne font-bold text-sm sm:text-base text-ink group-hover:text-red transition-colors mb-2 leading-snug line-clamp-3">
                      {item.title}
                    </h2>

                    {/* Excerpt */}
                    <p className="text-xs sm:text-sm text-ink-2 leading-relaxed line-clamp-4 flex-1">
                      {item.summary_excerpt}
                    </p>

                    {/* Read more */}
                    <div className="mt-4 flex items-center gap-1 text-xs font-syne font-semibold text-red">
                      {t.read_more}
                      <svg className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <path d="M5 12h14M12 5l7 7-7 7"/>
                      </svg>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
