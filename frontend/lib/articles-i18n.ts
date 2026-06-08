/**
 * Server-safe translations for the public articles listing pages.
 * Used by server components that cannot access useI18n() hooks.
 */

export type ArticlesLocale = "en" | "ru" | "ar" | "tr" | "de" | "fr" | "es";

export interface ArticlesPageT {
  // Page header
  heading: string;
  page_desc: string;
  // Search
  search_placeholder: string;
  search_btn: string;
  // Sections
  browse_by_cat: string;
  latest: string;
  results_for: string;   // use: results_for.replace("{q}", search)
  clear: string;
  // Article card
  read_time: string;     // use: read_time.replace("{n}", mins)
  n_articles: string;    // use: n_articles.replace("{n}", count) — plural handled per lang
  // Empty states
  no_results: string;
  no_results_cat: string;
  // Pagination
  prev: string;
  next: string;
  page_of: string;       // use: page_of.replace("{page}", p).replace("{total}", t)
  // Breadcrumb / back
  all_articles: string;
  // Category page
  articles_count: string; // "{n} article(s)" sentence form
  // Footer / CTA
  footer_tagline: string;
  start_free: string;
  view_pricing: string;
  get_started_free: string;
  // Nav
  nav_articles: string;
  nav_pricing: string;
  // RTL marker
  dir: "ltr" | "rtl";
}

const T: Record<ArticlesLocale, ArticlesPageT> = {
  en: {
    heading: "Medical Articles",
    page_desc: "Evidence-based medical content written for healthcare professionals and students. All articles are grounded in clinical guidelines and peer-reviewed research.",
    search_placeholder: "Search articles by title or topic…",
    search_btn: "Search",
    browse_by_cat: "Browse by Category",
    latest: "Latest Articles",
    results_for: 'Results for "{q}"',
    clear: "Clear",
    read_time: "{n} min read",
    n_articles: "{n} articles",
    no_results: "No articles published yet. Check back soon.",
    no_results_cat: "No articles in this category yet. Check back soon.",
    prev: "← Previous",
    next: "Next →",
    page_of: "Page {page} of {total}",
    all_articles: "← All articles",
    articles_count: "{n} article(s)",
    footer_tagline: "AI-powered medical education platform",
    start_free: "Start learning free",
    view_pricing: "View pricing",
    get_started_free: "Get started free",
    nav_articles: "Articles",
    nav_pricing: "Pricing",
    dir: "ltr",
  },

  ru: {
    heading: "Медицинские статьи",
    page_desc: "Доказательные медицинские материалы для врачей, студентов и специалистов здравоохранения. Все статьи основаны на клинических руководствах и рецензируемых исследованиях.",
    search_placeholder: "Поиск статей по названию или теме…",
    search_btn: "Найти",
    browse_by_cat: "Просмотр по категориям",
    latest: "Последние статьи",
    results_for: 'Результаты для «{q}»',
    clear: "Сбросить",
    read_time: "{n} мин",
    n_articles: "{n} статей",
    no_results: "Статьи пока не опубликованы. Загляните позже.",
    no_results_cat: "В этой категории статей пока нет. Загляните позже.",
    prev: "← Назад",
    next: "Далее →",
    page_of: "Страница {page} из {total}",
    all_articles: "← Все статьи",
    articles_count: "{n} статей",
    footer_tagline: "Платформа медицинского образования на базе ИИ",
    start_free: "Начать бесплатно",
    view_pricing: "Тарифы",
    get_started_free: "Начать бесплатно",
    nav_articles: "Статьи",
    nav_pricing: "Цены",
    dir: "ltr",
  },

  ar: {
    heading: "المقالات الطبية",
    page_desc: "محتوى طبي مبني على الأدلة، مكتوب للمختصين في الرعاية الصحية والطلاب. جميع المقالات مستندة إلى الإرشادات السريرية والأبحاث المحكّمة.",
    search_placeholder: "ابحث في المقالات بالعنوان أو الموضوع…",
    search_btn: "بحث",
    browse_by_cat: "تصفح حسب الفئة",
    latest: "أحدث المقالات",
    results_for: 'نتائج البحث عن «{q}»',
    clear: "مسح",
    read_time: "{n} د قراءة",
    n_articles: "{n} مقالة",
    no_results: "لم يتم نشر أي مقالات بعد. تفقد لاحقًا.",
    no_results_cat: "لا توجد مقالات في هذه الفئة بعد. تفقد لاحقًا.",
    prev: "→ السابق",
    next: "← التالي",
    page_of: "صفحة {page} من {total}",
    all_articles: "جميع المقالات →",
    articles_count: "{n} مقالة",
    footer_tagline: "منصة التعليم الطبي بالذكاء الاصطناعي",
    start_free: "ابدأ التعلم مجانًا",
    view_pricing: "عرض الأسعار",
    get_started_free: "ابدأ مجانًا",
    nav_articles: "المقالات",
    nav_pricing: "الأسعار",
    dir: "rtl",
  },

  de: {
    heading: "Medizinische Artikel",
    page_desc: "Evidenzbasierte medizinische Inhalte für Ärzte, Studierende und Gesundheitsfachkräfte. Alle Artikel basieren auf klinischen Leitlinien und peer-reviewed Forschung.",
    search_placeholder: "Artikel nach Titel oder Thema suchen…",
    search_btn: "Suchen",
    browse_by_cat: "Nach Kategorie durchsuchen",
    latest: "Neueste Artikel",
    results_for: 'Ergebnisse für „{q}"',
    clear: "Löschen",
    read_time: "{n} Min.",
    n_articles: "{n} Artikel",
    no_results: "Noch keine Artikel veröffentlicht. Schauen Sie bald wieder vorbei.",
    no_results_cat: "In dieser Kategorie gibt es noch keine Artikel. Schauen Sie bald wieder vorbei.",
    prev: "← Zurück",
    next: "Weiter →",
    page_of: "Seite {page} von {total}",
    all_articles: "← Alle Artikel",
    articles_count: "{n} Artikel",
    footer_tagline: "KI-gestützte Medizinbildungsplattform",
    start_free: "Kostenlos lernen",
    view_pricing: "Preise ansehen",
    get_started_free: "Kostenlos starten",
    nav_articles: "Artikel",
    nav_pricing: "Preise",
    dir: "ltr",
  },

  fr: {
    heading: "Articles médicaux",
    page_desc: "Contenu médical fondé sur des preuves, rédigé pour les professionnels de santé et les étudiants. Tous les articles s'appuient sur des directives cliniques et des recherches à comité de lecture.",
    search_placeholder: "Rechercher des articles par titre ou sujet…",
    search_btn: "Rechercher",
    browse_by_cat: "Parcourir par catégorie",
    latest: "Derniers articles",
    results_for: 'Résultats pour « {q} »',
    clear: "Effacer",
    read_time: "{n} min",
    n_articles: "{n} articles",
    no_results: "Aucun article publié pour l'instant. Revenez bientôt.",
    no_results_cat: "Aucun article dans cette catégorie pour l'instant. Revenez bientôt.",
    prev: "← Précédent",
    next: "Suivant →",
    page_of: "Page {page} sur {total}",
    all_articles: "← Tous les articles",
    articles_count: "{n} article(s)",
    footer_tagline: "Plateforme d'éducation médicale propulsée par l'IA",
    start_free: "Commencer gratuitement",
    view_pricing: "Voir les tarifs",
    get_started_free: "Démarrer gratuitement",
    nav_articles: "Articles",
    nav_pricing: "Tarifs",
    dir: "ltr",
  },

  es: {
    heading: "Artículos médicos",
    page_desc: "Contenido médico basado en evidencia, escrito para profesionales de la salud y estudiantes. Todos los artículos se fundamentan en guías clínicas e investigaciones revisadas por pares.",
    search_placeholder: "Buscar artículos por título o tema…",
    search_btn: "Buscar",
    browse_by_cat: "Explorar por categoría",
    latest: "Últimos artículos",
    results_for: 'Resultados para «{q}»',
    clear: "Borrar",
    read_time: "{n} min",
    n_articles: "{n} artículos",
    no_results: "Aún no hay artículos publicados. Vuelve pronto.",
    no_results_cat: "Aún no hay artículos en esta categoría. Vuelve pronto.",
    prev: "← Anterior",
    next: "Siguiente →",
    page_of: "Página {page} de {total}",
    all_articles: "← Todos los artículos",
    articles_count: "{n} artículo(s)",
    footer_tagline: "Plataforma de educación médica con IA",
    start_free: "Empezar gratis",
    view_pricing: "Ver precios",
    get_started_free: "Empieza gratis",
    nav_articles: "Artículos",
    nav_pricing: "Precios",
    dir: "ltr",
  },

  tr: {
    heading: "Tıbbi Makaleler",
    page_desc: "Sağlık profesyonelleri ve öğrenciler için kanıta dayalı tıbbi içerik. Tüm makaleler klinik kılavuzlar ve hakemli araştırmalara dayanmaktadır.",
    search_placeholder: "Makale başlığı veya konuya göre ara…",
    search_btn: "Ara",
    browse_by_cat: "Kategoriye Göre Gözat",
    latest: "Son Makaleler",
    results_for: '"{q}" için sonuçlar',
    clear: "Temizle",
    read_time: "{n} dk okuma",
    n_articles: "{n} makale",
    no_results: "Henüz makale yayınlanmadı. Yakında tekrar kontrol edin.",
    no_results_cat: "Bu kategoride henüz makale yok. Yakında tekrar kontrol edin.",
    prev: "← Önceki",
    next: "Sonraki →",
    page_of: "Sayfa {page} / {total}",
    all_articles: "← Tüm makaleler",
    articles_count: "{n} makale",
    footer_tagline: "Yapay zeka destekli tıp eğitimi platformu",
    start_free: "Ücretsiz öğrenmeye başla",
    view_pricing: "Fiyatları gör",
    get_started_free: "Ücretsiz başla",
    nav_articles: "Makaleler",
    nav_pricing: "Fiyatlar",
    dir: "ltr",
  },
};

export function getArticlesT(locale: string): ArticlesPageT {
  return T[(locale as ArticlesLocale)] ?? T.en;
}
