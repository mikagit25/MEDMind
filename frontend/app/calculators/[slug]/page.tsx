"use client";

import { useState, useEffect, useCallback } from "react";
import { notFound } from "next/navigation";
import Link from "next/link";
import { useI18n } from "@/lib/i18n";
import { useAuthStore } from "@/lib/store";
import { CalculatorWidget } from "@/components/calculators/CalculatorWidget";
import { getCalc, CALC_SLUGS, INDEX_T } from "@/components/calculators/data";
import type { Lang } from "@/components/calculators/data";
import { CALC_ABOUT } from "@/components/calculators/descriptions";

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

// ── Related calculators (3 per slug) ─────────────────────────────────────────
const RELATED_CALCS: Record<string, string[]> = {
  "egfr-ckd-epi":        ["cockcroft-gault", "aki", "corrected-calcium"],
  "cockcroft-gault":     ["egfr-ckd-epi", "aki", "ideal-body-weight"],
  "aki":                 ["egfr-ckd-epi", "cockcroft-gault", "sofa"],
  "corrected-calcium":   ["anion-gap", "egfr-ckd-epi", "meld"],
  "anion-gap":           ["corrected-calcium", "aki", "egfr-ckd-epi"],
  "meld":                ["child-pugh", "anion-gap", "corrected-calcium"],
  "child-pugh":          ["meld", "anion-gap", "corrected-calcium"],
  "bmi":                 ["ideal-body-weight", "daily-calories", "target-heart-rate"],
  "cha2ds2-vasc":        ["has-bled", "wells-dvt", "heart-score"],
  "has-bled":            ["cha2ds2-vasc", "wells-dvt", "meld"],
  "wells-dvt":           ["wells-pe", "heart-score", "cha2ds2-vasc"],
  "wells-pe":            ["wells-dvt", "heart-score", "qsofa"],
  "heart-score":         ["wells-dvt", "cha2ds2-vasc", "curb-65"],
  "curb-65":             ["qsofa", "sofa", "heart-score"],
  "qsofa":               ["sofa", "curb-65", "aki"],
  "sofa":                ["qsofa", "gcs", "aki"],
  "gcs":                 ["sofa", "qsofa", "abcd2"],
  "abcd2":               ["gcs", "wells-dvt", "qsofa"],
  "pregnancy-due-date":  ["bmi", "ideal-body-weight", "daily-calories"],
  "ideal-body-weight":   ["bmi", "cockcroft-gault", "daily-calories"],
  "target-heart-rate":   ["bmi", "daily-calories", "ideal-body-weight"],
  "daily-calories":      ["bmi", "ideal-body-weight", "target-heart-rate"],
  "ottawa-ankle":        ["ottawa-knee", "wells-dvt", "gcs"],
  "ottawa-knee":         ["ottawa-ankle", "wells-dvt", "gcs"],
  "framingham-risk":     ["cha2ds2-vasc", "has-bled", "heart-score"],
};

// ── Specialty → article category for related articles fetch ───────────────────
const CALC_SPECIALTY: Record<string, string> = {
  "egfr-ckd-epi":       "nephrology",
  "cockcroft-gault":    "nephrology",
  "aki":                "nephrology",
  "corrected-calcium":  "nephrology",
  "anion-gap":          "nephrology",
  "meld":               "hepatology",
  "child-pugh":         "hepatology",
  "bmi":                "endocrinology",
  "cha2ds2-vasc":       "cardiology",
  "has-bled":           "cardiology",
  "wells-dvt":          "cardiology",
  "wells-pe":           "pulmonology",
  "heart-score":        "cardiology",
  "curb-65":            "pulmonology",
  "qsofa":              "critical-care",
  "sofa":               "critical-care",
  "gcs":                "neurology",
  "abcd2":              "neurology",
  "pregnancy-due-date": "obstetrics",
  "ideal-body-weight":  "endocrinology",
  "target-heart-rate":  "cardiology",
  "daily-calories":     "endocrinology",
  "ottawa-ankle":       "emergency-medicine",
  "ottawa-knee":        "emergency-medicine",
  "framingham-risk":    "cardiology",
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
  "pregnancy-due-date": {
    name:     { en: "Pregnancy Due Date", ru: "Срок беременности и ПДР", ar: "تاريخ الولادة المتوقع", tr: "Doğum Tarihi Hesabı", de: "Geburtstermin-Rechner", fr: "Date d'accouchement", es: "Fecha probable de parto" },
    subtitle: { en: "Estimated due date and gestational age (Naegele's rule)", ru: "Предполагаемая дата родов и гестационный возраст", ar: "التاريخ المتوقع للولادة وعمر الحمل", tr: "Tahmini doğum tarihi ve gestasyonel yaş", de: "Voraussichtlicher Geburtstermin und Gestationsalter", fr: "Date prévue d'accouchement et âge gestationnel", es: "Fecha probable de parto y edad gestacional" },
    category: { en: "Obstetrics", ru: "Акушерство", ar: "التوليد", tr: "Obstetri", de: "Geburtshilfe", fr: "Obstétrique", es: "Obstetricia" },
    icon: "🤰",
    seoDescription: "Pregnancy due date calculator using Naegele's rule (LMP + 280 days). Shows gestational age and trimester. Free, multilingual.",
  },
  "ideal-body-weight": {
    name:     { en: "Ideal Body Weight (IBW)", ru: "Идеальный вес тела", ar: "الوزن المثالي للجسم", tr: "İdeal Vücut Ağırlığı", de: "Idealgewicht (IBW)", fr: "Poids idéal (IBW)", es: "Peso Corporal Ideal (IBW)" },
    subtitle: { en: "Devine formula — ideal and adjusted weight for drug dosing", ru: "Формула Девина — идеальный и скорректированный вес для дозирования", ar: "معادلة ديفين — الوزن المثالي والمعدّل لجرعات الأدوية", tr: "Devine formülü — ilaç dozajı için ideal ve düzeltilmiş ağırlık", de: "Devine-Formel — Ideal- und angepasstes Gewicht für Dosierung", fr: "Formule Devine — poids idéal et ajusté pour dosage médicamenteux", es: "Fórmula de Devine — peso ideal y ajustado para dosificación" },
    category: { en: "General", ru: "Общее", ar: "عام", tr: "Genel", de: "Allgemein", fr: "Général", es: "General" },
    icon: "⚖️",
    seoDescription: "Ideal body weight calculator using Devine formula. Also calculates adjusted body weight for drug dosing in obese patients. Free, multilingual.",
  },
  "target-heart-rate": {
    name:     { en: "Target Heart Rate", ru: "Целевая ЧСС", ar: "معدل ضربات القلب المستهدف", tr: "Hedef Kalp Hızı", de: "Zielherzfrequenz", fr: "Fréquence cardiaque cible", es: "Frecuencia cardíaca objetivo" },
    subtitle: { en: "Training zones by Karvonen method (heart rate reserve)", ru: "Тренировочные зоны по методу Карвонена (резерв ЧСС)", ar: "مناطق التدريب بطريقة كارفونن (احتياطي معدل ضربات القلب)", tr: "Karvonen yöntemiyle antrenman bölgeleri (kalp hızı rezervi)", de: "Trainingszonen nach Karvonen (Herzfrequenz-Reserve)", fr: "Zones d'entraînement Karvonen (réserve fréquence cardiaque)", es: "Zonas de entrenamiento Karvonen (reserva de FC)" },
    category: { en: "Cardiology", ru: "Кардиология", ar: "أمراض القلب", tr: "Kardiyoloji", de: "Kardiologie", fr: "Cardiologie", es: "Cardiología" },
    icon: "💓",
    seoDescription: "Target heart rate calculator using Karvonen method. Shows 4 training zones from 50% to 90% HRR. Free, multilingual.",
  },
  "daily-calories": {
    name:     { en: "Daily Calorie Needs", ru: "Суточная потребность в калориях", ar: "احتياجات السعرات الحرارية اليومية", tr: "Günlük Kalori İhtiyacı", de: "Täglicher Kalorienbedarf", fr: "Besoins caloriques quotidiens", es: "Necesidades calóricas diarias" },
    subtitle: { en: "BMR and TDEE using Mifflin-St Jeor equation", ru: "BMR и TDEE по формуле Миффлина-Сент-Жора", ar: "BMR و TDEE باستخدام معادلة ميفلين-سانت جيور", tr: "Mifflin-St Jeor ile BMR ve TDEE", de: "BMR und TDEE nach Mifflin-St-Jeor-Gleichung", fr: "BMR et TDEE (équation de Mifflin-St Jeor)", es: "TMB y TDEE (ecuación de Mifflin-St Jeor)" },
    category: { en: "General", ru: "Общее", ar: "عام", tr: "Genel", de: "Allgemein", fr: "Général", es: "General" },
    icon: "🍎",
    seoDescription: "Daily calorie needs calculator using Mifflin-St Jeor equation. Calculates BMR and TDEE with 5 activity levels. Free, multilingual.",
  },
  "framingham-risk": {
    name:     { en: "Framingham Risk Score", ru: "Шкала риска Фрамингема", ar: "درجة خطر فرامينغهام", tr: "Framingham Risk Skoru", de: "Framingham-Risiko-Score", fr: "Score de risque de Framingham", es: "Puntuación de riesgo de Framingham" },
    subtitle: { en: "10-year cardiovascular disease risk (NCEP ATP III)", ru: "10-летний риск сердечно-сосудистых событий (NCEP ATP III)", ar: "خطر أمراض القلب والأوعية الدموية خلال 10 سنوات (NCEP ATP III)", tr: "10 yıllık kardiyovasküler hastalık riski (NCEP ATP III)", de: "10-Jahres-Kardiovaskuläres Risiko (NCEP ATP III)", fr: "Risque cardiovasculaire à 10 ans (NCEP ATP III)", es: "Riesgo cardiovascular a 10 años (NCEP ATP III)" },
    category: { en: "Cardiology", ru: "Кардиология", ar: "أمراض القلب", tr: "Kardiyoloji", de: "Kardiologie", fr: "Cardiologie", es: "Cardiología" },
    icon: "🫀",
    seoDescription: "Framingham Risk Score calculator for 10-year cardiovascular disease risk. Uses NCEP ATP III 2001 algorithm. Free, multilingual.",
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

// ── Static article metadata (slug → title) ───────────────────────────────────
const ARTICLE_META: Record<string, string> = {
  "anticoagulation-warfarin-vs-doacs-reversal-agents":                                      "Anticoagulation: Warfarin vs. DOACs & Reversal Agents",
  "antithrombotic-therapy-in-atrial-fibrillation-and-post-pci-triple-therapy-management":   "Antithrombotic Therapy in AF and Post-PCI Triple Therapy",
  "ischemic-stroke-pathophysiology-diagnosis-and-evidence-based-management":                 "Ischemic Stroke: Pathophysiology, Diagnosis & Management",
  "acute-ischemic-stroke-management-and-tpa-thrombolytic-protocol":                         "Acute Ischemic Stroke Management & tPA Protocol",
  "stroke-recognition-fast-acronym":                                                         "Stroke Recognition: FAST Acronym",
  "deep-vein-thrombosis-dvt-prevention-risk-stratification-prophylaxis-and-management":     "DVT: Risk Stratification, Prophylaxis & Management",
  "ddimer-wells-score-and-pretest-probability-in-the-diagnosis-of-venous-thromboembolism":  "D-Dimer, Wells Score & Pretest Probability in VTE Diagnosis",
  "radiological-assessment-of-pulmonary-embolism-and-ct-pulmonary-angiography-evidencebased-d": "Radiological Assessment of PE & CTPA Evidence-Based Guide",
  "estimating-gfr-with-creatinine-mdrd-vs-ckdepi-and-ckd-staging-in-clinical-practice":    "Estimating GFR: MDRD vs CKD-EPI & CKD Staging",
  "acute-kidney-injury-management":                                                          "Acute Kidney Injury Management",
  "apixaban-for-stroke-prevention-in-afib-with-renal-adjustment":                           "Apixaban for Stroke Prevention in AF: Renal Dose Adjustment",
  "enoxaparin-lmwh-dvt-prophylaxis-renal-adjustment":                                       "Enoxaparin (LMWH) DVT Prophylaxis: Renal Adjustment",
  "sepsisassociated-acute-kidney-injury-ngal-cystatin-c-biomarkers-in-critical-care":       "Sepsis-Associated AKI: NGAL, Cystatin C Biomarkers",
  "indications-for-renal-replacement-therapy-in-critical-care-crrt-versus-intermittent-hemodi": "Renal Replacement Therapy in Critical Care: CRRT vs IHD",
  "hepatic-encephalopathy-pathophysiology-clinical-presentation-and-management":             "Hepatic Encephalopathy: Pathophysiology & Management",
  "hepatic-dosing-and-child-pugh-score-in-drug-clearance":                                  "Hepatic Dosing & Child-Pugh Score in Drug Clearance",
  "serumascites-albumin-gradient-saagguided-differential-diagnosis-and-management-of-ascites-": "Serum-Ascites Albumin Gradient (SAAG): Diagnosis & Management of Ascites",
  "ascites-evaluation-and-paracentesis-saag-based-diagnosis-and-management":                "Ascites Evaluation & Paracentesis: SAAG-Based Management",
  "sequential-organ-failure-assessment-sofa-score-in-multiorgan-dysfunction":               "SOFA Score in Multi-Organ Dysfunction",
  "goaldirected-lactate-clearance-in-septic-shock-diagnostic-and-therapeutic-framework":    "Goal-Directed Lactate Clearance in Septic Shock",
  "vasopressor-therapy-in-critical-care-norepinephrine-vasopressin-and-angiotensin-ii":     "Vasopressor Therapy in Critical Care: NE, Vasopressin & ATII",
  "emergency-department-sepsis-recognition-using-qsofa-score":                              "ED Sepsis Recognition Using qSOFA Score",
  "goaldirected-lactate-clearance-in-septic-shock-diagnostic-and-therapeutic-strategies":   "Lactate-Guided Management in Septic Shock",
  "lactate-guided-sepsis-management-diagnostics-interpretation":                            "Lactate-Guided Sepsis Management: Diagnostics & Interpretation",
  "curb-65-and-psi-for-risk-stratification-in-community-acquired-pneumonia":                "CURB-65 & PSI for CAP Risk Stratification",
  "community-acquired-pneumonia-diagnosis-management-and-clinical-outcomes":                "Community-Acquired Pneumonia: Diagnosis & Management",
  "hospital-acquired-pneumonia-epidemiology-pathophysiology-and-management":                "Hospital-Acquired Pneumonia: Epidemiology & Management",
  "obesity-management-with-glp-1-agonists":                                                 "Obesity Management with GLP-1 Agonists",
  "phenterminetopiramate-combination-therapy-for-obesity-clinical-use-efficacy-and-safety": "Phentermine-Topiramate Combination Therapy for Obesity",
  "semaglutidebased-glp1-receptor-agonist-therapy-and-bariatric-surgery-in-adult-obesity":  "Semaglutide & Bariatric Surgery in Adult Obesity",
  "anion-gap-metabolic-acidosis-comprehensive-clinical-approach-and-management":            "Anion Gap Metabolic Acidosis: Clinical Approach & Management",
  "acidbase-disorders-clinical-application-of-the-hendersonhasselbalch-equation":           "Acid-Base Disorders: Henderson-Hasselbalch in Clinical Practice",
  "anticoagulation-reversal-agents":                                                         "Anticoagulation Reversal Agents",
};

// ── Curated articles always shown per calculator ──────────────────────────────
const CALC_ARTICLES: Record<string, string[]> = {
  "cha2ds2-vasc":   ["antithrombotic-therapy-in-atrial-fibrillation-and-post-pci-triple-therapy-management", "anticoagulation-warfarin-vs-doacs-reversal-agents"],
  "has-bled":       ["anticoagulation-reversal-agents", "anticoagulation-warfarin-vs-doacs-reversal-agents"],
  "wells-dvt":      ["deep-vein-thrombosis-dvt-prevention-risk-stratification-prophylaxis-and-management", "ddimer-wells-score-and-pretest-probability-in-the-diagnosis-of-venous-thromboembolism"],
  "wells-pe":       ["radiological-assessment-of-pulmonary-embolism-and-ct-pulmonary-angiography-evidencebased-d", "ddimer-wells-score-and-pretest-probability-in-the-diagnosis-of-venous-thromboembolism"],
  "heart-score":    ["ischemic-stroke-pathophysiology-diagnosis-and-evidence-based-management", "ddimer-wells-score-and-pretest-probability-in-the-diagnosis-of-venous-thromboembolism"],
  "abcd2":          ["ischemic-stroke-pathophysiology-diagnosis-and-evidence-based-management", "stroke-recognition-fast-acronym"],
  "egfr-ckd-epi":   ["estimating-gfr-with-creatinine-mdrd-vs-ckdepi-and-ckd-staging-in-clinical-practice", "apixaban-for-stroke-prevention-in-afib-with-renal-adjustment"],
  "cockcroft-gault":["estimating-gfr-with-creatinine-mdrd-vs-ckdepi-and-ckd-staging-in-clinical-practice", "enoxaparin-lmwh-dvt-prophylaxis-renal-adjustment"],
  "aki":            ["acute-kidney-injury-management", "sepsisassociated-acute-kidney-injury-ngal-cystatin-c-biomarkers-in-critical-care"],
  "anion-gap":      ["anion-gap-metabolic-acidosis-comprehensive-clinical-approach-and-management", "acidbase-disorders-clinical-application-of-the-hendersonhasselbalch-equation"],
  "meld":           ["hepatic-encephalopathy-pathophysiology-clinical-presentation-and-management", "hepatic-dosing-and-child-pugh-score-in-drug-clearance"],
  "child-pugh":     ["hepatic-dosing-and-child-pugh-score-in-drug-clearance", "hepatic-encephalopathy-pathophysiology-clinical-presentation-and-management"],
  "sofa":           ["sequential-organ-failure-assessment-sofa-score-in-multiorgan-dysfunction", "goaldirected-lactate-clearance-in-septic-shock-diagnostic-and-therapeutic-framework"],
  "qsofa":          ["emergency-department-sepsis-recognition-using-qsofa-score", "goaldirected-lactate-clearance-in-septic-shock-diagnostic-and-therapeutic-strategies"],
  "curb-65":        ["curb-65-and-psi-for-risk-stratification-in-community-acquired-pneumonia", "community-acquired-pneumonia-diagnosis-management-and-clinical-outcomes"],
  "bmi":            ["obesity-management-with-glp-1-agonists", "semaglutidebased-glp1-receptor-agonist-therapy-and-bariatric-surgery-in-adult-obesity"],
};

// ── Result-band-specific article recommendations ──────────────────────────────
const CALC_RESULT_ARTICLES: Record<string, Partial<Record<"green"|"amber"|"red"|"red-dark", string[]>>> = {
  "cha2ds2-vasc": {
    amber: ["anticoagulation-warfarin-vs-doacs-reversal-agents"],
    red:   ["anticoagulation-warfarin-vs-doacs-reversal-agents", "antithrombotic-therapy-in-atrial-fibrillation-and-post-pci-triple-therapy-management"],
  },
  "has-bled": {
    red:   ["anticoagulation-reversal-agents"],
  },
  "wells-dvt": {
    amber: ["deep-vein-thrombosis-dvt-prevention-risk-stratification-prophylaxis-and-management"],
    red:   ["deep-vein-thrombosis-dvt-prevention-risk-stratification-prophylaxis-and-management", "anticoagulation-warfarin-vs-doacs-reversal-agents"],
  },
  "wells-pe": {
    amber: ["radiological-assessment-of-pulmonary-embolism-and-ct-pulmonary-angiography-evidencebased-d"],
    red:   ["radiological-assessment-of-pulmonary-embolism-and-ct-pulmonary-angiography-evidencebased-d", "anticoagulation-warfarin-vs-doacs-reversal-agents"],
  },
  "abcd2": {
    amber: ["acute-ischemic-stroke-management-and-tpa-thrombolytic-protocol"],
    red:   ["acute-ischemic-stroke-management-and-tpa-thrombolytic-protocol", "stroke-recognition-fast-acronym"],
  },
  "egfr-ckd-epi": {
    amber: ["enoxaparin-lmwh-dvt-prophylaxis-renal-adjustment", "apixaban-for-stroke-prevention-in-afib-with-renal-adjustment"],
    red:   ["indications-for-renal-replacement-therapy-in-critical-care-crrt-versus-intermittent-hemodi", "apixaban-for-stroke-prevention-in-afib-with-renal-adjustment"],
  },
  "aki": {
    amber: ["indications-for-renal-replacement-therapy-in-critical-care-crrt-versus-intermittent-hemodi"],
    red:   ["indications-for-renal-replacement-therapy-in-critical-care-crrt-versus-intermittent-hemodi", "sepsisassociated-acute-kidney-injury-ngal-cystatin-c-biomarkers-in-critical-care"],
  },
  "meld": {
    amber: ["serumascites-albumin-gradient-saagguided-differential-diagnosis-and-management-of-ascites-"],
    red:   ["ascites-evaluation-and-paracentesis-saag-based-diagnosis-and-management", "serumascites-albumin-gradient-saagguided-differential-diagnosis-and-management-of-ascites-"],
  },
  "sofa": {
    amber: ["goaldirected-lactate-clearance-in-septic-shock-diagnostic-and-therapeutic-framework"],
    red:   ["vasopressor-therapy-in-critical-care-norepinephrine-vasopressin-and-angiotensin-ii", "goaldirected-lactate-clearance-in-septic-shock-diagnostic-and-therapeutic-framework"],
  },
  "qsofa": {
    amber: ["lactate-guided-sepsis-management-diagnostics-interpretation"],
    red:   ["lactate-guided-sepsis-management-diagnostics-interpretation", "vasopressor-therapy-in-critical-care-norepinephrine-vasopressin-and-angiotensin-ii"],
  },
  "curb-65": {
    amber: ["community-acquired-pneumonia-diagnosis-management-and-clinical-outcomes"],
    red:   ["hospital-acquired-pneumonia-epidemiology-pathophysiology-and-management", "community-acquired-pneumonia-diagnosis-management-and-clinical-outcomes"],
  },
  "bmi": {
    amber: ["obesity-management-with-glp-1-agonists"],
    red:   ["phenterminetopiramate-combination-therapy-for-obesity-clinical-use-efficacy-and-safety", "semaglutidebased-glp1-receptor-agonist-therapy-and-bariatric-surgery-in-adult-obesity"],
  },
  "anion-gap": {
    red:   ["anion-gap-metabolic-acidosis-comprehensive-clinical-approach-and-management", "acidbase-disorders-clinical-application-of-the-hendersonhasselbalch-equation"],
  },
};

// ── Curated articles component (static, no API fetch) ─────────────────────────
function CuratedArticles({ slugs, lang, label, readLabel }: {
  slugs: string[]; lang: string; label: string; readLabel: string;
}) {
  const known = slugs.filter(s => ARTICLE_META[s]);
  if (known.length === 0) return null;
  return (
    <section className="max-w-5xl mx-auto px-4 sm:px-6 pb-14">
      <h2 className="font-syne font-bold text-lg text-ink mb-5">{label}</h2>
      <div className="grid sm:grid-cols-2 gap-3">
        {known.map(s => (
          <Link
            key={s}
            href={`/articles/${s}`}
            className="group block bg-surface border border-border rounded-xl p-4 hover:border-ink-3 transition-colors"
          >
            <p className="font-syne font-semibold text-sm text-ink group-hover:text-red transition-colors leading-snug line-clamp-2">
              {ARTICLE_META[s]}
            </p>
            <span className="mt-2 block text-xs font-syne text-ink-3 group-hover:text-ink transition-colors">{readLabel}</span>
          </Link>
        ))}
      </div>
    </section>
  );
}

// ── Result-based article recommendations ─────────────────────────────────────
const RESULT_LABELS: Record<Lang, string> = {
  en: "Recommended reading for your result",
  ru: "Рекомендуемые статьи по результату",
  ar: "قراءة موصى بها لنتيجتك",
  tr: "Sonucunuz için önerilen okuma",
  de: "Empfohlene Lektüre zu Ihrem Ergebnis",
  fr: "Lecture recommandée pour votre résultat",
  es: "Lectura recomendada según su resultado",
};

function ResultArticles({ calcSlug, band, lang, readLabel }: {
  calcSlug: string; band: "green"|"amber"|"red"|"red-dark"|null; lang: string; readLabel: string;
}) {
  if (!band || band === "green") return null;
  const bandKey = (band === "red-dark" ? "red" : band) as "amber"|"red";
  const slugs = CALC_RESULT_ARTICLES[calcSlug]?.[bandKey] ?? [];
  if (slugs.length === 0) return null;
  const label = (RESULT_LABELS as Record<string, string>)[lang] ?? RESULT_LABELS.en;

  const bandColors: Record<string, string> = {
    amber: "border-amber/40 bg-amber-light",
    red:   "border-red/20 bg-red/5",
  };

  return (
    <section className="max-w-5xl mx-auto px-4 sm:px-6 pb-10">
      <div className={`rounded-2xl border p-6 ${bandColors[bandKey] ?? ""}`}>
        <h2 className="font-syne font-bold text-base text-ink mb-4">{label}</h2>
        <div className="grid sm:grid-cols-2 gap-3">
          {slugs.filter(s => ARTICLE_META[s]).map(s => (
            <Link
              key={s}
              href={`/articles/${s}`}
              className="group block bg-surface border border-border rounded-xl p-4 hover:border-ink-3 transition-colors"
            >
              <p className="font-syne font-semibold text-sm text-ink group-hover:text-red transition-colors leading-snug line-clamp-2">
                {ARTICLE_META[s]}
              </p>
              <span className="mt-2 block text-xs font-syne text-ink-3 group-hover:text-ink transition-colors">{readLabel}</span>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── Footer link groups ────────────────────────────────────────────────────────
const FOOTER_CALCS = [
  { group: "Cardiology",        slugs: ["cha2ds2-vasc", "has-bled", "heart-score", "wells-dvt", "wells-pe", "target-heart-rate", "framingham-risk"] },
  { group: "Nephrology",        slugs: ["egfr-ckd-epi", "cockcroft-gault", "aki", "corrected-calcium"] },
  { group: "Critical Care",     slugs: ["sofa", "qsofa", "gcs", "curb-65", "abcd2"] },
  { group: "Emergency",         slugs: ["ottawa-ankle", "ottawa-knee"] },
  { group: "General",           slugs: ["bmi", "ideal-body-weight", "daily-calories", "pregnancy-due-date", "meld", "child-pugh", "anion-gap"] },
];

// ── Page ──────────────────────────────────────────────────────────────────────
export default function CalculatorPage({ params }: { params: { slug: string } }) {
  const { slug } = params;
  const { locale, setLocale } = useI18n();
  const lang = locale as string;
  const { isAuthenticated, _hasHydrated } = useAuthStore();
  const loggedIn = _hasHydrated ? isAuthenticated : null;

  const validSlugs: readonly string[] = CALC_SLUGS;
  if (!validSlugs.includes(slug)) notFound();

  const [resultBand, setResultBand] = useState<"green"|"amber"|"red"|"red-dark"|null>(null);
  const handleResult = useCallback((color: "green"|"amber"|"red"|"red-dark"|null) => {
    setResultBand(color);
  }, []);

  const calc       = getCalc(slug);
  const numericMeta = NUMERIC_CALCS[slug];
  const isNumeric   = !!numericMeta;

  const name     = isNumeric ? t(numericMeta.name, lang)     : t(calc!.nameI18n, lang);
  const subtitle = isNumeric ? t(numericMeta.subtitle, lang) : t(calc!.subtitle, lang);
  const category = isNumeric ? t(numericMeta.category, lang) : t(calc!.categoryI18n, lang);
  const icon     = isNumeric ? numericMeta.icon              : calc!.icon;
  const seodesc  = isNumeric ? numericMeta.seoDescription    : t(calc!.seoDescription, "en");
  const about    = CALC_ABOUT[slug]?.[lang as Lang] ?? CALC_ABOUT[slug]?.en ?? "";
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
            {loggedIn === null ? (
              <div className="w-24 h-8 rounded bg-surface animate-pulse" />
            ) : loggedIn ? (
              <Link href="/dashboard" className="font-syne font-bold text-sm bg-ink text-white px-3 sm:px-4 py-2 rounded hover:bg-red transition-colors whitespace-nowrap">
                {lang === "ru" ? "Кабинет →" : lang === "ar" ? "لوحة التحكم →" : lang === "de" ? "Dashboard →" : lang === "fr" ? "Tableau de bord →" : lang === "es" ? "Panel →" : lang === "tr" ? "Panel →" : "Dashboard →"}
              </Link>
            ) : (
              <>
                <Link href="/login" className="hidden sm:block font-syne font-semibold text-sm text-ink-2 hover:text-ink transition-colors px-3 py-2">
                  {t(L.sign_in, lang)}
                </Link>
                <Link href="/register" className="font-syne font-bold text-sm bg-ink text-white px-3 sm:px-4 py-2 rounded hover:bg-red transition-colors whitespace-nowrap">
                  {t(L.register, lang)}
                </Link>
              </>
            )}
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
        <CalculatorWidget slug={slug} onResult={handleResult} />
      </section>

      {/* ── Result-based article recommendations ── */}
      <ResultArticles
        calcSlug={slug}
        band={resultBand}
        lang={lang}
        readLabel={t(L.read_article, lang)}
      />

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

      {/* ── Curated related articles ── */}
      <CuratedArticles
        slugs={CALC_ARTICLES[slug] ?? []}
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
