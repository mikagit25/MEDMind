"use client";

import { useState } from "react";
import Link from "next/link";
import { useI18n } from "@/lib/i18n";

// ── Types ─────────────────────────────────────────────────────────────────────

type Lang = "en" | "ru" | "ar" | "es" | "de" | "fr" | "tr";

interface ConditionItem {
  name: string;
  likelihood: "high" | "moderate" | "low";
  description: string;
}

interface SymptomResult {
  urgency: "emergency" | "urgent" | "routine" | "self-care";
  urgency_reason: string;
  possible_conditions: ConditionItem[];
  red_flags: string[];
  recommended_action: string;
  disclaimer: string;
}

// ── Static translations ───────────────────────────────────────────────────────

const T: Record<Lang, {
  title: string; sub: string; label_symptoms: string; placeholder: string;
  label_age: string; label_sex: string; sex_m: string; sex_f: string; sex_o: string;
  btn: string; btn_loading: string; urgency_title: string; conditions_title: string;
  flags_title: string; action_title: string; likelihood_high: string;
  likelihood_moderate: string; likelihood_low: string; error_empty: string;
  error_api: string; disclaimer_label: string; badge_emergency: string;
  badge_urgent: string; badge_routine: string; badge_self: string;
  hint: string; new_check: string; examples: string[];
}> = {
  en: {
    title: "Symptom Checker",
    sub: "Describe your symptoms in plain language — our AI will provide a structured differential to guide your next step.",
    label_symptoms: "Describe your symptoms",
    placeholder: "e.g. I have a sharp chest pain that started 2 hours ago, I feel short of breath and my left arm feels numb...",
    label_age: "Age (optional)",
    label_sex: "Sex (optional)",
    sex_m: "Male", sex_f: "Female", sex_o: "Other",
    btn: "Check symptoms",
    btn_loading: "Analysing…",
    urgency_title: "Urgency level",
    conditions_title: "Possible conditions",
    flags_title: "Red flags to watch for",
    action_title: "Recommended action",
    likelihood_high: "High", likelihood_moderate: "Moderate", likelihood_low: "Low",
    error_empty: "Please describe your symptoms before submitting.",
    error_api: "Service temporarily unavailable. Please try again in a moment.",
    disclaimer_label: "Important",
    badge_emergency: "Emergency — Call 112 / 911 now",
    badge_urgent: "Urgent — See a doctor today",
    badge_routine: "Routine — Schedule an appointment",
    badge_self: "Self-care may be appropriate",
    hint: "This tool does not store any personal data.",
    new_check: "New check",
    examples: ["Headache and fever for 3 days", "Knee pain after running", "Dry cough and fatigue for a week"],
  },
  ru: {
    title: "Чекер симптомов",
    sub: "Опишите симптомы на русском языке — ИИ составит дифференциальный диагноз и подскажет, что делать дальше.",
    label_symptoms: "Опишите симптомы",
    placeholder: "например: острая боль в груди, появилась 2 часа назад, трудно дышать, немеет левая рука...",
    label_age: "Возраст (необязательно)",
    label_sex: "Пол (необязательно)",
    sex_m: "Мужской", sex_f: "Женский", sex_o: "Другой",
    btn: "Проверить симптомы",
    btn_loading: "Анализ…",
    urgency_title: "Уровень срочности",
    conditions_title: "Возможные состояния",
    flags_title: "Тревожные симптомы",
    action_title: "Рекомендуемые действия",
    likelihood_high: "Высокая", likelihood_moderate: "Средняя", likelihood_low: "Низкая",
    error_empty: "Пожалуйста, опишите симптомы перед отправкой.",
    error_api: "Сервис временно недоступен. Попробуйте через минуту.",
    disclaimer_label: "Важно",
    badge_emergency: "Экстренно — Вызовите скорую (103)",
    badge_urgent: "Срочно — Обратитесь к врачу сегодня",
    badge_routine: "Не срочно — Запишитесь к врачу",
    badge_self: "Возможно самолечение",
    hint: "Сервис не сохраняет личные данные.",
    new_check: "Новая проверка",
    examples: ["Головная боль и температура 3 дня", "Боль в колене после пробежки", "Сухой кашель и усталость неделю"],
  },
  ar: {
    title: "فاحص الأعراض",
    sub: "صف أعراضك بلغة بسيطة — سيقدم الذكاء الاصطناعي تشخيصاً تفاضلياً منظماً لتوجيهك.",
    label_symptoms: "صف أعراضك",
    placeholder: "مثال: ألم حاد في الصدر بدأ منذ ساعتين، أشعر بضيق في التنفس وخدر في ذراعي اليسرى...",
    label_age: "العمر (اختياري)",
    label_sex: "الجنس (اختياري)",
    sex_m: "ذكر", sex_f: "أنثى", sex_o: "آخر",
    btn: "فحص الأعراض",
    btn_loading: "جارٍ التحليل…",
    urgency_title: "مستوى الإلحاح",
    conditions_title: "الحالات المحتملة",
    flags_title: "العلامات التحذيرية",
    action_title: "الإجراء الموصى به",
    likelihood_high: "عالية", likelihood_moderate: "متوسطة", likelihood_low: "منخفضة",
    error_empty: "يرجى وصف أعراضك قبل الإرسال.",
    error_api: "الخدمة غير متاحة مؤقتاً. يرجى المحاولة مرة أخرى.",
    disclaimer_label: "مهم",
    badge_emergency: "طارئ — اتصل بـ 911 / 112 الآن",
    badge_urgent: "عاجل — راجع الطبيب اليوم",
    badge_routine: "روتيني — حدد موعداً",
    badge_self: "قد تكون الرعاية الذاتية مناسبة",
    hint: "لا تحفظ هذه الأداة أي بيانات شخصية.",
    new_check: "فحص جديد",
    examples: ["صداع وحمى منذ 3 أيام", "ألم في الركبة بعد الجري", "سعال جاف وتعب لمدة أسبوع"],
  },
  es: {
    title: "Verificador de síntomas",
    sub: "Describe tus síntomas en lenguaje sencillo — nuestra IA elaborará un diagnóstico diferencial estructurado.",
    label_symptoms: "Describe tus síntomas",
    placeholder: "p. ej. Tengo un dolor agudo en el pecho desde hace 2 horas, me cuesta respirar y siento el brazo izquierdo adormecido...",
    label_age: "Edad (opcional)",
    label_sex: "Sexo (opcional)",
    sex_m: "Masculino", sex_f: "Femenino", sex_o: "Otro",
    btn: "Verificar síntomas",
    btn_loading: "Analizando…",
    urgency_title: "Nivel de urgencia",
    conditions_title: "Posibles condiciones",
    flags_title: "Señales de alarma",
    action_title: "Acción recomendada",
    likelihood_high: "Alta", likelihood_moderate: "Moderada", likelihood_low: "Baja",
    error_empty: "Por favor describe tus síntomas antes de enviar.",
    error_api: "Servicio temporalmente no disponible. Inténtalo de nuevo en un momento.",
    disclaimer_label: "Importante",
    badge_emergency: "Emergencia — Llama al 112 / 911 ahora",
    badge_urgent: "Urgente — Ve al médico hoy",
    badge_routine: "Rutinario — Pide una cita",
    badge_self: "La automedicación puede ser apropiada",
    hint: "Esta herramienta no almacena datos personales.",
    new_check: "Nueva consulta",
    examples: ["Dolor de cabeza y fiebre 3 días", "Dolor de rodilla tras correr", "Tos seca y cansancio una semana"],
  },
  de: {
    title: "Symptom-Checker",
    sub: "Beschreiben Sie Ihre Symptome in einfacher Sprache — unsere KI erstellt eine strukturierte Differenzialdiagnose.",
    label_symptoms: "Symptome beschreiben",
    placeholder: "z. B. Ich habe seit 2 Stunden stechende Brustschmerzen, Kurzatmigkeit und Taubheitsgefühl im linken Arm...",
    label_age: "Alter (optional)",
    label_sex: "Geschlecht (optional)",
    sex_m: "Männlich", sex_f: "Weiblich", sex_o: "Divers",
    btn: "Symptome prüfen",
    btn_loading: "Analysiere…",
    urgency_title: "Dringlichkeitsstufe",
    conditions_title: "Mögliche Erkrankungen",
    flags_title: "Warnsignale",
    action_title: "Empfohlene Maßnahme",
    likelihood_high: "Hoch", likelihood_moderate: "Mittel", likelihood_low: "Niedrig",
    error_empty: "Bitte beschreiben Sie Ihre Symptome vor dem Absenden.",
    error_api: "Dienst vorübergehend nicht verfügbar. Bitte versuchen Sie es erneut.",
    disclaimer_label: "Wichtig",
    badge_emergency: "Notfall — Rufen Sie jetzt 112 / 911 an",
    badge_urgent: "Dringend — Heute zum Arzt",
    badge_routine: "Routinemäßig — Termin vereinbaren",
    badge_self: "Selbstbehandlung kann angemessen sein",
    hint: "Dieses Tool speichert keine persönlichen Daten.",
    new_check: "Neue Prüfung",
    examples: ["Kopfschmerzen und Fieber seit 3 Tagen", "Knieschmerzen nach dem Laufen", "Trockener Husten und Müdigkeit eine Woche"],
  },
  fr: {
    title: "Vérificateur de symptômes",
    sub: "Décrivez vos symptômes en langage courant — notre IA produira un diagnostic différentiel structuré.",
    label_symptoms: "Décrivez vos symptômes",
    placeholder: "ex. J'ai une douleur thoracique aiguë depuis 2 heures, j'ai du mal à respirer et mon bras gauche est engourdi...",
    label_age: "Âge (optionnel)",
    label_sex: "Sexe (optionnel)",
    sex_m: "Masculin", sex_f: "Féminin", sex_o: "Autre",
    btn: "Vérifier les symptômes",
    btn_loading: "Analyse en cours…",
    urgency_title: "Niveau d'urgence",
    conditions_title: "Conditions possibles",
    flags_title: "Signaux d'alarme",
    action_title: "Action recommandée",
    likelihood_high: "Élevée", likelihood_moderate: "Modérée", likelihood_low: "Faible",
    error_empty: "Veuillez décrire vos symptômes avant d'envoyer.",
    error_api: "Service temporairement indisponible. Réessayez dans un moment.",
    disclaimer_label: "Important",
    badge_emergency: "Urgence — Appelez le 15 / 112 maintenant",
    badge_urgent: "Urgent — Consultez un médecin aujourd'hui",
    badge_routine: "Routine — Prenez rendez-vous",
    badge_self: "L'automédication peut être appropriée",
    hint: "Cet outil ne stocke aucune donnée personnelle.",
    new_check: "Nouvelle vérification",
    examples: ["Maux de tête et fièvre 3 jours", "Douleur au genou après la course", "Toux sèche et fatigue une semaine"],
  },
  tr: {
    title: "Semptom Denetleyici",
    sub: "Semptomlarınızı sade bir dille açıklayın — yapay zekamız yapılandırılmış bir ayırıcı tanı sunacak.",
    label_symptoms: "Semptomlarınızı açıklayın",
    placeholder: "örn. 2 saattir keskin göğüs ağrısı var, nefes almakta güçlük çekiyorum ve sol kolum uyuşuyor...",
    label_age: "Yaş (isteğe bağlı)",
    label_sex: "Cinsiyet (isteğe bağlı)",
    sex_m: "Erkek", sex_f: "Kadın", sex_o: "Diğer",
    btn: "Semptomları kontrol et",
    btn_loading: "Analiz ediliyor…",
    urgency_title: "Aciliyet düzeyi",
    conditions_title: "Olası durumlar",
    flags_title: "İzlenmesi gereken uyarı işaretleri",
    action_title: "Önerilen eylem",
    likelihood_high: "Yüksek", likelihood_moderate: "Orta", likelihood_low: "Düşük",
    error_empty: "Lütfen göndermeden önce semptomlarınızı açıklayın.",
    error_api: "Hizmet geçici olarak kullanılamıyor. Lütfen bir süre sonra tekrar deneyin.",
    disclaimer_label: "Önemli",
    badge_emergency: "Acil — Şimdi 112'yi arayın",
    badge_urgent: "Acele — Bugün doktora gidin",
    badge_routine: "Rutin — Randevu alın",
    badge_self: "Kendi kendine bakım uygun olabilir",
    hint: "Bu araç kişisel veri saklamaz.",
    new_check: "Yeni kontrol",
    examples: ["3 gündür baş ağrısı ve ateş", "Koşu sonrası diz ağrısı", "Bir haftadır kuru öksürük ve yorgunluk"],
  },
};

const LANGS: { value: Lang; flag: string }[] = [
  { value: "en", flag: "🇬🇧" }, { value: "ru", flag: "🇷🇺" }, { value: "de", flag: "🇩🇪" },
  { value: "fr", flag: "🇫🇷" }, { value: "ar", flag: "🇸🇦" }, { value: "tr", flag: "🇹🇷" },
  { value: "es", flag: "🇪🇸" },
];

// ── Urgency config ────────────────────────────────────────────────────────────

const URGENCY_CONFIG = {
  emergency: { bg: "bg-red-600", text: "text-white", icon: "🚨" },
  urgent:    { bg: "bg-orange-500", text: "text-white", icon: "⚠️" },
  routine:   { bg: "bg-blue-500", text: "text-white", icon: "📅" },
  "self-care": { bg: "bg-green-600", text: "text-white", icon: "✅" },
} as const;

const LIKELIHOOD_COLOR: Record<string, string> = {
  high: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300",
  moderate: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300",
  low: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
};

// ── Main component ────────────────────────────────────────────────────────────

export default function SymptomsPage() {
  const { locale, setLocale } = useI18n();
  const lang = (LANGS.some(l => l.value === locale) ? locale : "en") as Lang;
  const t = T[lang];

  const [symptoms, setSymptoms] = useState("");
  const [age, setAge] = useState("");
  const [sex, setSex] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SymptomResult | null>(null);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = symptoms.trim();
    if (!trimmed) { setError(t.error_empty); return; }
    setError("");
    setLoading(true);
    setResult(null);

    try {
      const res = await fetch("/api/v1/symptoms/check", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symptoms: trimmed,
          age: age ? parseInt(age) : undefined,
          sex: sex || undefined,
          lang,
        }),
      });
      if (!res.ok) {
        if (res.status === 429) {
          const d = await res.json();
          setError(d.detail ?? t.error_api);
        } else {
          setError(t.error_api);
        }
        return;
      }
      const data: SymptomResult = await res.json();
      setResult(data);
    } catch {
      setError(t.error_api);
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    setResult(null);
    setSymptoms("");
    setAge("");
    setSex("");
    setError("");
  }

  const urg = result ? URGENCY_CONFIG[result.urgency] ?? URGENCY_CONFIG.routine : null;
  const urgBadge = result
    ? lang === "en" ? (
        result.urgency === "emergency" ? t.badge_emergency :
        result.urgency === "urgent" ? t.badge_urgent :
        result.urgency === "routine" ? t.badge_routine : t.badge_self
      ) : (
        result.urgency === "emergency" ? t.badge_emergency :
        result.urgency === "urgent" ? t.badge_urgent :
        result.urgency === "routine" ? t.badge_routine : t.badge_self
      )
    : "";

  return (
    <div className="min-h-screen bg-bg" dir={lang === "ar" ? "rtl" : "ltr"}>
      {/* Nav */}
      <nav className="bg-surface border-b border-border sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-3">
          <Link href="/" className="font-syne font-extrabold text-xl sm:text-2xl tracking-tight text-ink flex-shrink-0">
            Med<span className="text-red">Mind</span>
          </Link>
          <div className="hidden md:flex items-center gap-1">
            <Link href="/articles" className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2">
              {lang === "ru" ? "Статьи" : lang === "ar" ? "مقالات" : lang === "de" ? "Artikel" : lang === "fr" ? "Articles" : lang === "es" ? "Artículos" : lang === "tr" ? "Makaleler" : "Articles"}
            </Link>
            <Link href="/calculators" className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2">
              {lang === "ru" ? "Калькуляторы" : lang === "ar" ? "آلات حاسبة" : lang === "de" ? "Rechner" : lang === "fr" ? "Calculateurs" : lang === "es" ? "Calculadoras" : lang === "tr" ? "Hesap makineleri" : "Calculators"}
            </Link>
            <Link href="/symptoms" className="font-syne font-semibold text-sm text-ink hover:text-red transition-colors px-3 py-2">
              {lang === "ru" ? "Чекер симптомов" : lang === "ar" ? "فاحص الأعراض" : lang === "de" ? "Symptom-Checker" : lang === "fr" ? "Symptômes" : lang === "es" ? "Síntomas" : lang === "tr" ? "Semptomlar" : "Symptoms"}
            </Link>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={lang}
              onChange={e => setLocale(e.target.value)}
              className="text-xs font-syne border border-border rounded px-1.5 py-1 bg-bg text-ink focus:outline-none"
            >
              {LANGS.map(l => <option key={l.value} value={l.value}>{l.flag}</option>)}
            </select>
            <Link href="/login" className="hidden sm:block font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2">
              {lang === "ru" ? "Войти" : lang === "ar" ? "تسجيل الدخول" : lang === "de" ? "Anmelden" : lang === "fr" ? "Connexion" : lang === "es" ? "Iniciar sesión" : lang === "tr" ? "Giriş yap" : "Sign in"}
            </Link>
            <Link href="/register" className="btn-primary text-xs sm:text-sm px-3 py-1.5 hidden sm:block">
              {lang === "ru" ? "Регистрация" : lang === "ar" ? "التسجيل" : lang === "de" ? "Registrieren" : lang === "fr" ? "S'inscrire" : lang === "es" ? "Registrarse" : lang === "tr" ? "Kayıt ol" : "Sign up"}
            </Link>
          </div>
        </div>
      </nav>

      {/* Main */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-10 sm:py-16">

        {/* Header */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center gap-2 bg-surface border border-border rounded-full px-4 py-1.5 mb-4">
            <span className="text-base">🩺</span>
            <span className="font-syne font-semibold text-xs text-ink-2">AI-Powered · 7 Languages · Free</span>
          </div>
          <h1 className="font-syne font-extrabold text-3xl sm:text-4xl text-ink mb-3">{t.title}</h1>
          <p className="text-ink-2 text-sm sm:text-base max-w-xl mx-auto leading-relaxed">{t.sub}</p>
        </div>

        {!result ? (
          /* ── Input form ───────────────────────────────────────────────── */
          <div className="bg-surface border border-border rounded-2xl shadow-sm p-6 sm:p-8">
            <form onSubmit={handleSubmit} className="space-y-5">

              {/* Symptoms textarea */}
              <div>
                <label className="block font-syne font-semibold text-sm text-ink mb-2">
                  {t.label_symptoms}
                </label>
                <textarea
                  value={symptoms}
                  onChange={e => setSymptoms(e.target.value)}
                  placeholder={t.placeholder}
                  rows={5}
                  maxLength={2000}
                  className="w-full border border-border rounded-lg px-4 py-3 bg-bg text-ink text-sm placeholder:text-ink-3 focus:outline-none focus:ring-2 focus:ring-red/30 focus:border-red/50 resize-none font-mono"
                />
                <div className="flex justify-between items-center mt-1">
                  <span className="text-xs text-ink-3">{symptoms.length}/2000</span>
                  {error && <span className="text-xs text-red-600 font-syne">{error}</span>}
                </div>
              </div>

              {/* Example chips */}
              <div className="flex flex-wrap gap-2">
                {t.examples.map(ex => (
                  <button
                    key={ex}
                    type="button"
                    onClick={() => setSymptoms(ex)}
                    className="text-xs font-syne border border-border rounded-full px-3 py-1 text-ink-2 hover:border-red hover:text-ink transition-colors bg-bg"
                  >
                    {ex}
                  </button>
                ))}
              </div>

              {/* Age + Sex row */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block font-syne font-semibold text-xs text-ink-2 mb-1.5">{t.label_age}</label>
                  <input
                    type="number"
                    value={age}
                    onChange={e => setAge(e.target.value)}
                    min={0} max={120} placeholder="—"
                    className="w-full border border-border rounded-lg px-3 py-2 bg-bg text-ink text-sm focus:outline-none focus:ring-2 focus:ring-red/30"
                  />
                </div>
                <div>
                  <label className="block font-syne font-semibold text-xs text-ink-2 mb-1.5">{t.label_sex}</label>
                  <select
                    value={sex}
                    onChange={e => setSex(e.target.value)}
                    className="w-full border border-border rounded-lg px-3 py-2 bg-bg text-ink text-sm focus:outline-none focus:ring-2 focus:ring-red/30"
                  >
                    <option value="">—</option>
                    <option value="male">{t.sex_m}</option>
                    <option value="female">{t.sex_f}</option>
                    <option value="other">{t.sex_o}</option>
                  </select>
                </div>
              </div>

              {/* Submit */}
              <button
                type="submit"
                disabled={loading}
                className="w-full font-syne font-bold text-sm sm:text-base py-3 rounded-xl bg-ink text-[#f0ede8] hover:bg-red transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                    </svg>
                    {t.btn_loading}
                  </span>
                ) : t.btn}
              </button>
            </form>

            {/* Privacy note */}
            <p className="text-center text-xs text-ink-3 mt-4 font-syne">🔒 {t.hint}</p>
          </div>

        ) : (
          /* ── Results ─────────────────────────────────────────────────── */
          <div className="space-y-5">

            {/* Urgency banner */}
            <div className={`rounded-2xl p-5 sm:p-6 ${urg?.bg} ${urg?.text}`}>
              <div className="flex items-start gap-3">
                <span className="text-2xl">{urg?.icon}</span>
                <div>
                  <div className="font-syne font-bold text-base sm:text-lg mb-1">{urgBadge}</div>
                  <p className="text-sm opacity-90">{result.urgency_reason}</p>
                </div>
              </div>
            </div>

            {/* Possible conditions */}
            <div className="bg-surface border border-border rounded-2xl p-5 sm:p-6">
              <h2 className="font-syne font-bold text-base text-ink mb-4 flex items-center gap-2">
                <span>📋</span> {t.conditions_title}
              </h2>
              <div className="space-y-3">
                {result.possible_conditions.map((cond, i) => (
                  <div key={i} className="border border-border rounded-xl p-4 bg-bg">
                    <div className="flex items-center justify-between gap-3 mb-1.5">
                      <span className="font-syne font-semibold text-sm text-ink">{cond.name}</span>
                      <span className={`text-xs font-syne font-semibold px-2 py-0.5 rounded-full ${LIKELIHOOD_COLOR[cond.likelihood] ?? LIKELIHOOD_COLOR.low}`}>
                        {lang === "en" ? (cond.likelihood === "high" ? t.likelihood_high : cond.likelihood === "moderate" ? t.likelihood_moderate : t.likelihood_low)
                          : (cond.likelihood === "high" ? t.likelihood_high : cond.likelihood === "moderate" ? t.likelihood_moderate : t.likelihood_low)}
                      </span>
                    </div>
                    <p className="text-sm text-ink-2 leading-relaxed">{cond.description}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Red flags */}
            {result.red_flags.length > 0 && (
              <div className="bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800 rounded-2xl p-5 sm:p-6">
                <h2 className="font-syne font-bold text-base text-red-700 dark:text-red-400 mb-3 flex items-center gap-2">
                  <span>🚩</span> {t.flags_title}
                </h2>
                <ul className="space-y-1.5">
                  {result.red_flags.map((flag, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-red-700 dark:text-red-300">
                      <span className="mt-0.5 flex-shrink-0">•</span>
                      <span>{flag}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Recommended action */}
            <div className="bg-surface border border-border rounded-2xl p-5 sm:p-6">
              <h2 className="font-syne font-bold text-base text-ink mb-3 flex items-center gap-2">
                <span>💡</span> {t.action_title}
              </h2>
              <p className="text-sm text-ink-2 leading-relaxed">{result.recommended_action}</p>
            </div>

            {/* Disclaimer */}
            <div className="bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800 rounded-xl p-4">
              <p className="text-xs text-amber-800 dark:text-amber-300 font-syne">
                <span className="font-bold">{t.disclaimer_label}: </span>{result.disclaimer}
              </p>
            </div>

            {/* New check button */}
            <button
              onClick={reset}
              className="w-full font-syne font-semibold text-sm py-3 rounded-xl border-2 border-ink text-ink hover:bg-ink hover:text-[#f0ede8] transition-colors"
            >
              ← {t.new_check}
            </button>
          </div>
        )}

        {/* Footer links */}
        <div className="mt-12 pt-8 border-t border-border flex flex-wrap justify-center gap-4 text-xs text-ink-3 font-syne">
          <Link href="/calculators" className="hover:text-ink transition-colors">
            {lang === "ru" ? "Клинические калькуляторы" : lang === "ar" ? "آلات حاسبة سريرية" : lang === "de" ? "Klinische Rechner" : lang === "fr" ? "Calculateurs cliniques" : lang === "es" ? "Calculadoras clínicas" : lang === "tr" ? "Klinik hesap makineleri" : "Clinical Calculators"}
          </Link>
          <span className="text-border">·</span>
          <Link href="/articles" className="hover:text-ink transition-colors">
            {lang === "ru" ? "Медицинские статьи" : lang === "ar" ? "مقالات طبية" : lang === "de" ? "Medizinartikel" : lang === "fr" ? "Articles médicaux" : lang === "es" ? "Artículos médicos" : lang === "tr" ? "Tıp makaleleri" : "Medical Articles"}
          </Link>
          <span className="text-border">·</span>
          <Link href="/drugs" className="hover:text-ink transition-colors">
            {lang === "ru" ? "Препараты" : lang === "ar" ? "الأدوية" : lang === "de" ? "Arzneimittel" : lang === "fr" ? "Médicaments" : lang === "es" ? "Medicamentos" : lang === "tr" ? "İlaçlar" : "Drug Database"}
          </Link>
        </div>
      </main>
    </div>
  );
}
