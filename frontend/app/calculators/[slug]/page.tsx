"use client";

import { useState, useEffect } from "react";
import { notFound } from "next/navigation";
import Link from "next/link";
import { useI18n } from "@/lib/i18n";
import { CalculatorWidget } from "@/components/calculators/CalculatorWidget";
import { getCalc, CALC_SLUGS, INDEX_T } from "@/components/calculators/data";
import type { Lang } from "@/components/calculators/data";

const LANGS = [
  { value: "en", flag: "🇬🇧" }, { value: "ru", flag: "🇷🇺" }, { value: "de", flag: "🇩🇪" },
  { value: "fr", flag: "🇫🇷" }, { value: "ar", flag: "🇸🇦" }, { value: "tr", flag: "🇹🇷" }, { value: "es", flag: "🇪🇸" },
] as const;

function t(obj: Record<Lang, string>, lang: string): string {
  return (obj as Record<string, string>)[lang] ?? obj.en;
}

// ── Section UI labels ─────────────────────────────────────────────────────────
const L = {
  about:            { en: "About this calculator", ru: "О калькуляторе", ar: "حول هذه الأداة", tr: "Bu hesap makinesi hakkında", de: "Über diesen Rechner", fr: "À propos", es: "Acerca de esta calculadora" },
  related_calcs:    { en: "Related calculators", ru: "Похожие калькуляторы", ar: "أدوات ذات صلة", tr: "İlgili hesap makineleri", de: "Verwandte Rechner", fr: "Calculateurs associés", es: "Calculadoras relacionadas" },
  related_articles: { en: "Articles on this topic", ru: "Статьи по теме", ar: "مقالات حول هذا الموضوع", tr: "Bu konuyla ilgili makaleler", de: "Artikel zu diesem Thema", fr: "Articles sur ce sujet", es: "Artículos sobre este tema" },
  read_article:     { en: "Read →", ru: "Читать →", ar: "اقرأ →", tr: "Oku →", de: "Lesen →", fr: "Lire →", es: "Leer →" },
  how_works:        { en: "How it works", ru: "Как работает", ar: "كيف يعمل", tr: "Nasıl çalışır", de: "So funktionierts", fr: "Comment ça marche", es: "Cómo funciona" },
  articles:         { en: "Articles", ru: "Статьи", ar: "مقالات", tr: "Makaleler", de: "Artikel", fr: "Articles", es: "Artículos" },
  calculators:      { en: "Calculators", ru: "Калькуляторы", ar: "آلات حاسبة", tr: "Hesap makineleri", de: "Rechner", fr: "Calculateurs", es: "Calculadoras" },
  sign_in:          { en: "Sign in", ru: "Войти", ar: "تسجيل الدخول", tr: "Giriş yap", de: "Anmelden", fr: "Connexion", es: "Iniciar sesión" },
  register:         { en: "Register", ru: "Регистрация", ar: "إنشاء حساب", tr: "Kayıt ol", de: "Registrieren", fr: "S'inscrire", es: "Registrarse" },
  disclaimer:       { en: "For educational use only. Always apply clinical judgement.", ru: "Только для образовательных целей. Всегда применяйте клиническое суждение.", ar: "للأغراض التعليمية فقط. اعتمد دائماً على الحكم السريري.", tr: "Yalnızca eğitim amaçlıdır. Her zaman klinik yargınızı kullanın.", de: "Nur zu Bildungszwecken. Immer klinisches Urteilsvermögen anwenden.", fr: "Usage éducatif uniquement. Appliquez toujours votre jugement clinique.", es: "Solo uso educativo. Aplique siempre su juicio clínico." },
} as const satisfies Record<string, Record<Lang, string>>;

// ── Clinical descriptions (English — most important for SEO) ──────────────────
const CALC_ABOUT: Record<string, string> = {
  "egfr-ckd-epi":
    "The CKD-EPI 2021 equation estimates glomerular filtration rate from serum creatinine without a race variable, eliminating racial bias introduced by the 2009 formula. It is the KDIGO-recommended method for staging chronic kidney disease (CKD) and detecting progression. An eGFR below 60 mL/min/1.73 m² persisting for ≥3 months confirms CKD and guides drug dose adjustment, nephrology referral thresholds, and cardiovascular risk stratification.",
  "cockcroft-gault":
    "The Cockcroft-Gault formula estimates creatinine clearance (CrCl) using age, sex, weight, and serum creatinine. Unlike eGFR, it was derived to predict drug clearance rather than true GFR, making it the standard referenced in drug labelling and pharmacokinetic studies. It is especially critical for dosing renally-cleared drugs such as aminoglycosides, vancomycin, digoxin, heparins, and direct oral anticoagulants — where errors can cause toxicity or subtherapeutic levels.",
  "aki":
    "KDIGO 2012 defines acute kidney injury as a rise in serum creatinine ≥0.3 mg/dL within 48 h, a ≥50% rise within 7 days, or urine output below 0.5 mL/kg/h for ≥6 h. The three-stage classification guides monitoring intensity and intervention — from optimising fluids and avoiding nephrotoxins (Stage 1) to renal replacement therapy consideration (Stage 3). Both creatinine and urine output criteria are assessed simultaneously; the higher stage applies.",
  "corrected-calcium":
    "Total serum calcium is bound approximately 40% to albumin, so hypoalbuminaemia artificially lowers measured calcium despite potentially normal ionised calcium. The Payne formula (add 0.8 mg/dL per 1 g/dL drop in albumin below 4 g/dL) corrects for this. Correction is essential in critically ill patients, malnutrition, cirrhosis, and nephrotic syndrome — groups where hypoalbuminaemia is common and true calcium status matters for arrhythmia and neuromuscular risk assessment.",
  "anion-gap":
    "The anion gap (Na⁺ − [Cl⁻ + HCO₃⁻], normal 8–12 mEq/L) identifies unmeasured anions and classifies metabolic acidosis as high-gap (lactic acidosis, ketoacidosis, uraemia, toxins) or normal-gap (hyperchloraemic, diarrhoea, renal tubular acidosis). Albumin correction is essential — hypoalbuminaemia lowers the gap by ~2.5 mEq/L per 1 g/dL fall, masking a true high-gap acidosis. The delta-delta ratio (ΔAG / ΔHCO₃⁻) reveals concurrent mixed disorders.",
  "meld":
    "MELD (Model for End-stage Liver Disease) predicts 90-day mortality in chronic liver disease and portal hypertension using bilirubin, INR, and creatinine. UNOS uses MELD-Na (which adds serum sodium) for transplant allocation in candidates with MELD ≥11. Scores are recalculated every 1–7 days depending on severity; a score above 40 carries approximately 70% 3-month waitlist mortality without transplantation.",
  "bmi":
    "Body mass index (BMI = kg/m²) is the standard WHO screening tool for overweight and obesity. Classification: underweight <18.5, normal 18.5–24.9, overweight 25–29.9, obese Class I 30–34.9, Class II 35–39.9, Class III ≥40. In clinical practice, BMI is a starting point — waist circumference, waist-to-hip ratio, and body composition analysis add important context, particularly in Asian populations (where risk thresholds are lower) and athletes with high muscle mass.",
  "cha2ds2-vasc":
    "CHA₂DS₂-VASc scores annual stroke risk in non-valvular atrial fibrillation. ESC 2020 guidelines recommend initiating oral anticoagulation for men with score ≥2 and women with score ≥3. Anticoagulation should be considered at score ≥1 (men) or ≥2 (women) if there are no contraindications. Always use alongside HAS-BLED to identify correctable bleeding risk factors before prescribing anticoagulants.",
  "has-bled":
    "HAS-BLED estimates annual major bleeding risk in atrial fibrillation patients on anticoagulation. A score ≥3 indicates high bleeding risk and should prompt correction of modifiable factors — uncontrolled hypertension, labile INR (switch to NOAC), excess alcohol, nephropathy — rather than automatic anticoagulant avoidance. In most patients, AF stroke risk exceeds bleeding risk; HAS-BLED informs shared decision-making rather than dictating discontinuation.",
  "wells-dvt":
    "The Wells DVT score stratifies pre-test probability of deep vein thrombosis in symptomatic outpatients. A score ≥2 (high probability) warrants proximal compression ultrasound regardless of D-dimer result. A score of 0–1 with a negative high-sensitivity D-dimer effectively excludes DVT without imaging, reducing unnecessary Doppler studies by approximately 40%. The score is validated for symptomatic proximal DVT and should not be applied in patients currently anticoagulated, pregnant, or postoperative.",
  "heart-score":
    "The HEART score (History, ECG, Age, Risk factors, Troponin) safely identifies low-risk chest pain presentations in the ED. A score ≤3 carries <2% MACE risk at 6 weeks and supports discharge with outpatient follow-up. A score ≥7 is associated with >70% MACE risk and warrants early invasive evaluation. The HEART pathway (two troponins + HEART score) outperforms TIMI and GRACE for risk stratification in undifferentiated chest pain.",
  "curb-65":
    "CURB-65 stratifies severity of community-acquired pneumonia (CAP) using five bedside variables: confusion, urea >7 mmol/L, respiratory rate ≥30, blood pressure <90/60 mmHg, and age ≥65. Score 0–1 supports oral antibiotics and outpatient management; score 2 warrants hospitalisation; score ≥3 indicates severe CAP requiring ICU evaluation. CURB-65 is simpler than PSI/PORT but less granular for very-low-risk stratification in younger patients.",
  "qsofa":
    "Quick SOFA is a 3-point bedside screen for patients outside the ICU at risk of poor outcome from suspected infection. Two or more criteria — altered mental status, respiratory rate ≥22/min, systolic BP ≤100 mmHg — predicts in-hospital mortality ≥10% and should trigger urgent clinical reassessment, organ function testing, blood cultures, and early antibiotics. qSOFA is a screening alert, not a diagnostic tool for sepsis — full SOFA scoring requires laboratory data.",
  "gcs":
    "The Glasgow Coma Scale quantifies consciousness through three components: eye opening (E 1–4), verbal response (V 1–5), and motor response (M 1–6). The minimum score is 3 (deep coma); maximum is 15 (fully alert). GCS ≤8 conventionally defines coma and is the standard threshold for considering airway protection. Serial scoring is more informative than a single measurement — a drop of ≥2 points warrants immediate reassessment for reversible causes including hypoglycaemia, opiate overdose, and rising intracranial pressure.",
  "abcd2":
    "The ABCD² score estimates 2-day stroke risk after a TIA using five variables: Age, Blood pressure, Clinical features, Duration, and Diabetes. A score ≥4 is associated with >4% 2-day stroke risk, warranting immediate dual antiplatelet therapy and urgent neurovascular imaging. ABCD² has limitations in distinguishing TIA from mimics; brain and vascular imaging (CT/CTA or MRI/MRA) is mandatory in all TIA presentations and should not be delayed by score calculation.",
  "child-pugh":
    "The Child-Pugh score classifies hepatic functional reserve in cirrhosis using bilirubin, albumin, INR, ascites severity, and hepatic encephalopathy grade. Class A (5–6 points) indicates well-compensated disease with >95% 1-year survival. Class B (7–9) represents significant functional impairment. Class C (10–15) carries 35–45% 1-year survival without transplantation. The score guides surgical candidacy, predicts variceal bleeding mortality, and informs drug dosing in hepatic impairment.",
};

// ── Related calculators (3 per slug) ─────────────────────────────────────────
const RELATED_CALCS: Record<string, string[]> = {
  "egfr-ckd-epi":      ["cockcroft-gault", "aki", "corrected-calcium"],
  "cockcroft-gault":   ["egfr-ckd-epi", "aki", "anion-gap"],
  "aki":               ["egfr-ckd-epi", "cockcroft-gault", "qsofa"],
  "corrected-calcium": ["anion-gap", "egfr-ckd-epi", "meld"],
  "anion-gap":         ["corrected-calcium", "aki", "egfr-ckd-epi"],
  "meld":              ["child-pugh", "anion-gap", "corrected-calcium"],
  "child-pugh":        ["meld", "anion-gap", "corrected-calcium"],
  "bmi":               ["corrected-calcium", "egfr-ckd-epi", "anion-gap"],
  "cha2ds2-vasc":      ["has-bled", "wells-dvt", "heart-score"],
  "has-bled":          ["cha2ds2-vasc", "wells-dvt", "meld"],
  "wells-dvt":         ["heart-score", "has-bled", "cha2ds2-vasc"],
  "heart-score":       ["wells-dvt", "cha2ds2-vasc", "curb-65"],
  "curb-65":           ["qsofa", "gcs", "heart-score"],
  "qsofa":             ["curb-65", "gcs", "aki"],
  "gcs":               ["qsofa", "curb-65", "abcd2"],
  "abcd2":             ["gcs", "wells-dvt", "qsofa"],
};

// ── Specialty → article category for related articles fetch ───────────────────
const CALC_SPECIALTY: Record<string, string> = {
  "egfr-ckd-epi":      "nephrology",
  "cockcroft-gault":   "nephrology",
  "aki":               "nephrology",
  "corrected-calcium": "nephrology",
  "anion-gap":         "nephrology",
  "meld":              "hepatology",
  "child-pugh":        "hepatology",
  "bmi":               "endocrinology",
  "cha2ds2-vasc":      "cardiology",
  "has-bled":          "cardiology",
  "wells-dvt":         "cardiology",
  "heart-score":       "cardiology",
  "curb-65":           "pulmonology",
  "qsofa":             "critical-care",
  "gcs":               "neurology",
  "abcd2":             "neurology",
};

// ── Numeric calculator metadata ───────────────────────────────────────────────
type NumericCalcMeta = {
  name: Record<Lang, string>;
  subtitle: Record<Lang, string>;
  category: Record<Lang, string>;
  icon: string;
  seoDescription: string;
};

const NUMERIC_CALCS: Record<string, NumericCalcMeta> = {
  "egfr-ckd-epi": {
    name:     { en: "eGFR (CKD-EPI 2021)", ru: "рСКФ (CKD-EPI 2021)", ar: "معدل الترشيح الكبيبي التقديري (CKD-EPI 2021)", tr: "eGFR (CKD-EPI 2021)", de: "eGFR (CKD-EPI 2021)", fr: "DFGe (CKD-EPI 2021)", es: "TFGe (CKD-EPI 2021)" },
    subtitle: { en: "Kidney function and CKD staging", ru: "Функция почек и стадия ХБП", ar: "وظائف الكلى وتصنيف مرض الكلى المزمن", tr: "Böbrek fonksiyonu ve KBH evrelemesi", de: "Nierenfunktion und CKD-Stadienbestimmung", fr: "Fonction rénale et stadification de l'IRC", es: "Función renal y estadificación de ERC" },
    category: { en: "Nephrology", ru: "Нефрология", ar: "أمراض الكلى", tr: "Nefroloji", de: "Nephrologie", fr: "Néphrologie", es: "Nefrología" },
    icon: "🫘",
    seoDescription: "eGFR calculator using CKD-EPI 2021 equation. Estimates kidney function and determines CKD stage. Free, multilingual.",
  },
  "bmi": {
    name:     { en: "BMI Calculator", ru: "Индекс массы тела", ar: "مؤشر كتلة الجسم", tr: "Vücut Kitle İndeksi", de: "BMI-Rechner", fr: "Calculateur IMC", es: "Calculadora IMC" },
    subtitle: { en: "Body mass index and obesity classification (WHO)", ru: "Индекс массы тела и классификация ожирения (ВОЗ)", ar: "مؤشر كتلة الجسم وتصنيف السمنة (WHO)", tr: "Vücut kitle indeksi ve obezite sınıflaması (WHO)", de: "Body-Mass-Index und Adipositas-Klassifikation (WHO)", fr: "Indice de masse corporelle et classification obésité (OMS)", es: "Índice de masa corporal y clasificación de obesidad (OMS)" },
    category: { en: "General", ru: "Общее", ar: "عام", tr: "Genel", de: "Allgemein", fr: "Général", es: "General" },
    icon: "⚖️",
    seoDescription: "BMI calculator with WHO obesity classification (underweight, normal, overweight, obese). Free, multilingual.",
  },
  "corrected-calcium": {
    name:     { en: "Corrected Calcium", ru: "Скорр. кальций", ar: "الكالسيوم المصحح", tr: "Düzeltilmiş Kalsiyum", de: "Korrigiertes Kalzium", fr: "Calcium corrigé", es: "Calcio corregido" },
    subtitle: { en: "Calcium correction for hypoalbuminaemia", ru: "Коррекция кальция при гипоальбуминемии", ar: "تصحيح الكالسيوم في نقص ألبومين الدم", tr: "Hipoalbüminemi için kalsiyum düzeltmesi", de: "Kalziumkorrektur bei Hypoalbuminämie", fr: "Correction calcique pour hypoalbuminémie", es: "Corrección de calcio por hipoalbuminemia" },
    category: { en: "Biochemistry", ru: "Биохимия", ar: "الكيمياء الحيوية", tr: "Biyokimya", de: "Biochemie", fr: "Biochimie", es: "Bioquímica" },
    icon: "🧪",
    seoDescription: "Corrected calcium calculator adjusting for hypoalbuminaemia using the Payne formula. Free, multilingual.",
  },
  "anion-gap": {
    name:     { en: "Anion Gap", ru: "Анионный разрыв", ar: "الفجوة الأيونية", tr: "Anyon Açığı", de: "Anionenlücke", fr: "Trou anionique", es: "Brecha aniónica" },
    subtitle: { en: "Metabolic acidosis classification with albumin correction", ru: "Классификация метаболического ацидоза с поправкой на альбумин", ar: "تصنيف الحماض الأيضي مع تصحيح الألبومين", tr: "Albumin düzeltmeli metabolik asidoz sınıflaması", de: "Metabolische Azidose-Klassifikation mit Albumin-Korrektur", fr: "Classification de l'acidose métabolique avec correction albumine", es: "Clasificación acidosis metabólica con corrección albúmina" },
    category: { en: "Biochemistry", ru: "Биохимия", ar: "الكيمياء الحيوية", tr: "Biyokimya", de: "Biochemie", fr: "Biochimie", es: "Bioquímica" },
    icon: "⚗️",
    seoDescription: "Anion gap calculator with albumin correction for metabolic acidosis classification. Free, multilingual.",
  },
  "meld": {
    name:     { en: "MELD / MELD-Na Score", ru: "Шкала MELD / MELD-Na", ar: "مقياس MELD / MELD-Na", tr: "MELD / MELD-Na Skoru", de: "MELD / MELD-Na Score", fr: "Score MELD / MELD-Na", es: "Puntuación MELD / MELD-Na" },
    subtitle: { en: "Liver disease severity and transplant priority (UNOS)", ru: "Тяжесть заболевания печени и приоритет трансплантации (UNOS)", ar: "شدة مرض الكبد وأولوية زرع الأعضاء (UNOS)", tr: "Karaciğer hastalığı şiddeti ve nakil önceliği (UNOS)", de: "Schweregrad der Lebererkrankung und Transplantationspriorität (UNOS)", fr: "Sévérité de l'hépatopathie et priorité transplantation (UNOS)", es: "Gravedad hepatopatía y prioridad trasplante (UNOS)" },
    category: { en: "Hepatology", ru: "Гепатология", ar: "أمراض الكبد", tr: "Hepatoloji", de: "Hepatologie", fr: "Hépatologie", es: "Hepatología" },
    icon: "🫀",
    seoDescription: "MELD and MELD-Na score calculator for liver disease severity and transplant prioritisation. Free, multilingual.",
  },
  "aki": {
    name:     { en: "AKI Staging (KDIGO)", ru: "Стадии ОПП (KDIGO)", ar: "تصنيف الإصابة الكلوية الحادة (KDIGO)", tr: "ABH Evrelemesi (KDIGO)", de: "AKI-Staging (KDIGO)", fr: "Stadification IRA (KDIGO)", es: "Estadificación IRA (KDIGO)" },
    subtitle: { en: "Acute kidney injury severity by creatinine and urine output (KDIGO 2012)", ru: "Тяжесть ОПП по уровню креатинина и диурезу (KDIGO 2012)", ar: "شدة الإصابة الكلوية الحادة وفق الكرياتينين وإنتاج البول (KDIGO 2012)", tr: "Kreatinin ve idrar çıkışına göre AKI şiddeti (KDIGO 2012)", de: "AKI-Schweregrad nach Kreatinin und Diurese (KDIGO 2012)", fr: "Sévérité de l'IRA selon créatinine et diurèse (KDIGO 2012)", es: "Gravedad IRA según creatinina y diuresis (KDIGO 2012)" },
    category: { en: "Critical Care", ru: "Интенсивная терапия", ar: "الرعاية الحرجة", tr: "Yoğun Bakım", de: "Intensivmedizin", fr: "Soins intensifs", es: "Cuidados intensivos" },
    icon: "🚨",
    seoDescription: "AKI staging calculator using KDIGO 2012 criteria (creatinine and urine output). With per-stage management recommendations. Free, multilingual.",
  },
  "cockcroft-gault": {
    name:     { en: "Cockcroft-Gault CrCl", ru: "Клиренс креатинина (Кокрофт-Голт)", ar: "تصفية الكرياتينين (كوكروفت-غولت)", tr: "Cockcroft-Gault KrKl", de: "Cockcroft-Gault-KrCl", fr: "Clairance créatinine Cockcroft-Gault", es: "ClCr Cockcroft-Gault" },
    subtitle: { en: "Kidney function and drug dosing adjustment", ru: "Функция почек и коррекция доз препаратов", ar: "وظائف الكلى وتعديل جرعة الدواء", tr: "Böbrek fonksiyonu ve ilaç doz ayarlaması", de: "Nierenfunktion und Medikamentendosisanpassung", fr: "Fonction rénale et adaptation posologique", es: "Función renal y ajuste de dosis farmacológica" },
    category: { en: "Nephrology", ru: "Нефрология", ar: "أمراض الكلى", tr: "Nefroloji", de: "Nephrologie", fr: "Néphrologie", es: "Nefrología" },
    icon: "💊",
    seoDescription: "Cockcroft-Gault creatinine clearance calculator for drug dosing in renal impairment. Free, multilingual.",
  },
};

// ── Helper: get name + icon for any calc slug ─────────────────────────────────
function getCalcInfo(slug: string, lang: string): { name: string; icon: string; subtitle: string } {
  const num = NUMERIC_CALCS[slug];
  if (num) return { name: t(num.name, lang), icon: num.icon, subtitle: t(num.subtitle, lang) };
  const sc = getCalc(slug);
  if (sc) return { name: t(sc.nameI18n, lang), icon: sc.icon, subtitle: t(sc.subtitle, lang) };
  return { name: slug, icon: "🔢", subtitle: "" };
}

// ── Related articles component ────────────────────────────────────────────────
type ArticlePreview = { slug: string; title: string; excerpt?: string; category?: string };

function RelatedArticles({ specialty, lang, label, readLabel }: {
  specialty: string; lang: string; label: string; readLabel: string;
}) {
  const [articles, setArticles] = useState<ArticlePreview[]>([]);

  useEffect(() => {
    const api = process.env.NEXT_PUBLIC_API_URL ?? "https://medmind.pro/api/v1";
    fetch(`${api}/articles/category/${specialty}?limit=4&locale=${lang}`)
      .then(r => r.ok ? r.json() : [])
      .then(d => setArticles(Array.isArray(d) ? d.slice(0, 4) : []))
      .catch(() => {});
  }, [specialty, lang]);

  if (articles.length === 0) return null;

  return (
    <section className="max-w-5xl mx-auto px-4 sm:px-6 pb-14">
      <h2 className="font-syne font-bold text-lg text-ink mb-5">{label}</h2>
      <div className="grid sm:grid-cols-2 gap-3">
        {articles.map(a => (
          <Link
            key={a.slug}
            href={`/articles/${a.slug}`}
            className="group block bg-surface border border-border rounded-xl p-4 hover:border-ink-3 transition-colors"
          >
            <p className="font-syne font-semibold text-sm text-ink group-hover:text-red transition-colors leading-snug mb-1 line-clamp-2">
              {a.title}
            </p>
            {a.excerpt && (
              <p className="text-ink-3 text-xs leading-relaxed line-clamp-2 mb-2">{a.excerpt}</p>
            )}
            <span className="text-xs font-syne text-ink-3 group-hover:text-ink transition-colors">{readLabel}</span>
          </Link>
        ))}
      </div>
    </section>
  );
}

// ── Footer link groups ────────────────────────────────────────────────────────
const FOOTER_CALCS = [
  { group: "Cardiology", slugs: ["cha2ds2-vasc", "has-bled", "heart-score", "wells-dvt"] },
  { group: "Nephrology", slugs: ["egfr-ckd-epi", "cockcroft-gault", "aki", "corrected-calcium"] },
  { group: "Critical Care", slugs: ["qsofa", "gcs", "curb-65", "abcd2"] },
  { group: "Hepatology / Other", slugs: ["meld", "child-pugh", "anion-gap", "bmi"] },
];

// ── Page ──────────────────────────────────────────────────────────────────────
export default function CalculatorPage({ params }: { params: { slug: string } }) {
  const { slug } = params;
  const { locale, setLocale } = useI18n();
  const lang = locale as string;

  const validSlugs: readonly string[] = CALC_SLUGS;
  if (!validSlugs.includes(slug)) notFound();

  const calc       = getCalc(slug);
  const numericMeta = NUMERIC_CALCS[slug];
  const isNumeric   = !!numericMeta;

  const name     = isNumeric ? t(numericMeta.name, lang)     : t(calc!.nameI18n, lang);
  const subtitle = isNumeric ? t(numericMeta.subtitle, lang) : t(calc!.subtitle, lang);
  const category = isNumeric ? t(numericMeta.category, lang) : t(calc!.categoryI18n, lang);
  const icon     = isNumeric ? numericMeta.icon              : calc!.icon;
  const seodesc  = isNumeric ? numericMeta.seoDescription    : t(calc!.seoDescription, "en");
  const about    = CALC_ABOUT[slug] ?? "";
  const relatedSlugs = RELATED_CALCS[slug] ?? [];
  const specialty    = CALC_SPECIALTY[slug] ?? "cardiology";

  const jsonLd = [
    {
      "@context": "https://schema.org",
      "@type": "MedicalWebPage",
      name: `${name} — MedMind AI`,
      description: seodesc,
      url: `https://medmind.pro/calculators/${slug}`,
      audience: { "@type": "MedicalAudience", audienceType: "Clinician" },
      publisher: { "@type": "Organization", name: "MedMind AI", url: "https://medmind.pro" },
      inLanguage: lang,
    },
    about ? {
      "@context": "https://schema.org",
      "@type": "FAQPage",
      mainEntity: [
        {
          "@type": "Question",
          name: `What is the ${name}?`,
          acceptedAnswer: { "@type": "Answer", text: about },
        },
        {
          "@type": "Question",
          name: `When should I use the ${name}?`,
          acceptedAnswer: {
            "@type": "Answer",
            text: `The ${name} is used in ${category} practice. ${subtitle}. ${seodesc}`,
          },
        },
      ],
    } : null,
  ].filter(Boolean);

  return (
    <div className="min-h-screen bg-bg">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

      {/* ── Nav ── */}
      <nav className="bg-surface border-b border-border sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-3">
          <Link href="/" className="font-syne font-extrabold text-xl sm:text-2xl tracking-tight text-ink flex-shrink-0">
            Med<span className="text-red">Mind</span>
          </Link>
          <div className="hidden md:flex items-center gap-1">
            <Link href="/how-it-works" className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2">
              {t(L.how_works, lang)}
            </Link>
            <Link href="/articles" className="font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2">
              {t(L.articles, lang)}
            </Link>
            <Link href="/calculators" className="font-syne font-semibold text-sm text-ink hover:text-red transition-colors px-3 py-2">
              {t(L.calculators, lang)}
            </Link>
          </div>
          <div className="flex items-center gap-2">
            <select value={locale} onChange={e => setLocale(e.target.value as Lang)}
              className="hidden sm:block text-xs font-syne border border-border rounded px-1.5 py-1 bg-bg text-ink focus:outline-none">
              {LANGS.map(l => <option key={l.value} value={l.value}>{l.flag}</option>)}
            </select>
            <Link href="/login" className="hidden sm:block font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2">
              {t(L.sign_in, lang)}
            </Link>
            <Link href="/register" className="font-syne font-bold text-sm bg-ink text-white px-3 sm:px-4 py-2 rounded hover:bg-red transition-colors whitespace-nowrap">
              {t(L.register, lang)}
            </Link>
          </div>
        </div>
      </nav>

      {/* ── Header ── */}
      <section className="max-w-5xl mx-auto px-4 sm:px-6 pt-10 pb-6">
        <nav className="flex items-center gap-2 text-xs font-syne text-ink-3 mb-6">
          <Link href="/calculators" className="hover:text-ink transition-colors">{t(INDEX_T.all_calculators, lang)}</Link>
          <span>/</span>
          <span className="text-ink">{name}</span>
        </nav>
        <div className="flex items-start gap-4 mb-2">
          <span className="text-3xl">{icon}</span>
          <div>
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <h1 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink leading-tight">{name}</h1>
              <span className="text-xs font-syne font-semibold text-ink-3 bg-surface border border-border px-2 py-0.5 rounded-full">
                {category}
              </span>
            </div>
            <p className="text-ink-2 text-sm sm:text-base leading-relaxed">{subtitle}</p>
          </div>
        </div>
      </section>

      {/* ── Calculator widget ── */}
      <section className="max-w-5xl mx-auto px-4 sm:px-6 pb-12">
        <CalculatorWidget slug={slug} />
      </section>

      {/* ── About this calculator ── */}
      {about && (
        <section className="max-w-5xl mx-auto px-4 sm:px-6 pb-12">
          <div className="bg-surface border border-border rounded-2xl p-6 sm:p-8">
            <h2 className="font-syne font-bold text-lg text-ink mb-3">{t(L.about, lang)}</h2>
            <p className="text-ink-2 text-sm sm:text-base leading-relaxed">{about}</p>
          </div>
        </section>
      )}

      {/* ── Related calculators ── */}
      {relatedSlugs.length > 0 && (
        <section className="max-w-5xl mx-auto px-4 sm:px-6 pb-12">
          <h2 className="font-syne font-bold text-lg text-ink mb-5">{t(L.related_calcs, lang)}</h2>
          <div className="grid sm:grid-cols-3 gap-3">
            {relatedSlugs.map(rs => {
              const info = getCalcInfo(rs, lang);
              return (
                <Link
                  key={rs}
                  href={`/calculators/${rs}`}
                  className="group flex items-start gap-3 bg-surface border border-border rounded-xl p-4 hover:border-ink-3 transition-colors"
                >
                  <span className="text-2xl flex-shrink-0">{info.icon}</span>
                  <div className="min-w-0">
                    <p className="font-syne font-semibold text-sm text-ink group-hover:text-red transition-colors leading-snug mb-0.5 line-clamp-2">
                      {info.name}
                    </p>
                    <p className="text-ink-3 text-xs leading-snug line-clamp-2">{info.subtitle}</p>
                  </div>
                </Link>
              );
            })}
          </div>
        </section>
      )}

      {/* ── Related articles ── */}
      <RelatedArticles
        specialty={specialty}
        lang={lang}
        label={t(L.related_articles, lang)}
        readLabel={t(L.read_article, lang)}
      />

      {/* ── Footer ── */}
      <footer className="border-t border-border bg-surface mt-4">
        {/* Disclaimer */}
        <div className="max-w-6xl mx-auto px-6 pt-6 pb-3">
          <p className="text-ink-3 text-xs text-center leading-relaxed border border-border rounded-lg px-4 py-3 bg-bg max-w-3xl mx-auto">
            {t(INDEX_T.footer_note, lang)}
          </p>
        </div>

        {/* Links grid */}
        <div className="max-w-6xl mx-auto px-6 py-8 grid grid-cols-2 sm:grid-cols-4 gap-6">
          {FOOTER_CALCS.map(group => (
            <div key={group.group}>
              <p className="font-syne font-bold text-xs text-ink mb-3 uppercase tracking-wide">{group.group}</p>
              <ul className="space-y-2">
                {group.slugs.map(s => {
                  const info = getCalcInfo(s, lang);
                  return (
                    <li key={s}>
                      <Link
                        href={`/calculators/${s}`}
                        className={`font-syne text-xs transition-colors ${s === slug ? "text-ink font-semibold" : "text-ink-3 hover:text-ink"}`}
                      >
                        {info.name}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom bar */}
        <div className="border-t border-border">
          <div className="max-w-6xl mx-auto px-6 py-4 flex flex-col sm:flex-row items-center justify-between gap-3">
            <Link href="/" className="font-syne font-extrabold text-base text-ink">
              Med<span className="text-red">Mind</span>
              <span className="font-normal text-ink-3 text-xs ml-2">AI Education Platform</span>
            </Link>
            <div className="flex gap-4 flex-wrap justify-center text-xs font-syne text-ink-3">
              <Link href="/articles"    className="hover:text-ink transition-colors">{t(L.articles, lang)}</Link>
              <Link href="/calculators" className="hover:text-ink transition-colors">{t(L.calculators, lang)}</Link>
              <Link href="/how-it-works" className="hover:text-ink transition-colors">{t(L.how_works, lang)}</Link>
              <Link href="/pricing"     className="hover:text-ink transition-colors">Pricing</Link>
              <Link href="/login"       className="hover:text-ink transition-colors">{t(L.sign_in, lang)}</Link>
            </div>
            <div className="text-ink-3 text-xs font-syne">© 2026 MedMind AI.</div>
          </div>
        </div>
      </footer>
    </div>
  );
}
