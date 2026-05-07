/**
 * Article category helpers shared between server and client components.
 * Keys map to articles.cat_* locale keys.
 */

export const CATEGORY_ICONS: Record<string, string> = {
  diseases: "🫀",
  drugs: "💊",
  procedures: "🔬",
  symptoms: "🩺",
  diagnostics: "🧪",
  emergency: "🚑",
  nutrition: "🥗",
  pediatrics: "👶",
  cardiology: "❤️",
  neurology: "🧠",
  oncology: "🎗️",
  surgery: "✂️",
  psychiatry: "🧘",
  endocrinology: "⚗️",
  "infectious-diseases": "🦠",
  veterinary: "🐾",
};

/** Maps slug → locale key suffix (for t("articles.cat_<key>")) */
export const CATEGORY_KEY: Record<string, string> = {
  diseases: "cat_diseases",
  drugs: "cat_drugs",
  procedures: "cat_procedures",
  symptoms: "cat_symptoms",
  diagnostics: "cat_diagnostics",
  emergency: "cat_emergency",
  nutrition: "cat_nutrition",
  pediatrics: "cat_pediatrics",
  cardiology: "cat_cardiology",
  neurology: "cat_neurology",
  oncology: "cat_oncology",
  surgery: "cat_surgery",
  psychiatry: "cat_psychiatry",
  endocrinology: "cat_endocrinology",
  "infectious-diseases": "cat_infectious_diseases",
  veterinary: "cat_veterinary",
};

/** Static fallback labels (used in server components with locale param). */
const STATIC_LABELS: Record<string, Record<string, string>> = {
  en: {
    diseases: "Diseases & Conditions", drugs: "Drugs & Medications",
    procedures: "Procedures & Techniques", symptoms: "Symptoms & Signs",
    diagnostics: "Diagnostics & Lab Tests", emergency: "Emergency Medicine",
    nutrition: "Nutrition & Prevention", pediatrics: "Pediatrics",
    cardiology: "Cardiology", neurology: "Neurology", oncology: "Oncology",
    surgery: "Surgery", psychiatry: "Psychiatry", endocrinology: "Endocrinology",
    "infectious-diseases": "Infectious Diseases", veterinary: "Veterinary Medicine",
  },
  ru: {
    diseases: "Болезни и состояния", drugs: "Лекарства и препараты",
    procedures: "Процедуры и техники", symptoms: "Симптомы и признаки",
    diagnostics: "Диагностика и анализы", emergency: "Скорая помощь",
    nutrition: "Питание и профилактика", pediatrics: "Педиатрия",
    cardiology: "Кардиология", neurology: "Неврология", oncology: "Онкология",
    surgery: "Хирургия", psychiatry: "Психиатрия", endocrinology: "Эндокринология",
    "infectious-diseases": "Инфекционные болезни", veterinary: "Ветеринарная медицина",
  },
  de: {
    diseases: "Krankheiten & Zustände", drugs: "Medikamente & Arzneimittel",
    procedures: "Verfahren & Techniken", symptoms: "Symptome & Zeichen",
    diagnostics: "Diagnostik & Laborwerte", emergency: "Notfallmedizin",
    nutrition: "Ernährung & Prävention", pediatrics: "Pädiatrie",
    cardiology: "Kardiologie", neurology: "Neurologie", oncology: "Onkologie",
    surgery: "Chirurgie", psychiatry: "Psychiatrie", endocrinology: "Endokrinologie",
    "infectious-diseases": "Infektionskrankheiten", veterinary: "Veterinärmedizin",
  },
  fr: {
    diseases: "Maladies & Conditions", drugs: "Médicaments & Traitements",
    procedures: "Procédures & Techniques", symptoms: "Symptômes & Signes",
    diagnostics: "Diagnostics & Analyses", emergency: "Médecine d'urgence",
    nutrition: "Nutrition & Prévention", pediatrics: "Pédiatrie",
    cardiology: "Cardiologie", neurology: "Neurologie", oncology: "Oncologie",
    surgery: "Chirurgie", psychiatry: "Psychiatrie", endocrinology: "Endocrinologie",
    "infectious-diseases": "Maladies infectieuses", veterinary: "Médecine vétérinaire",
  },
  es: {
    diseases: "Enfermedades y Condiciones", drugs: "Medicamentos y Fármacos",
    procedures: "Procedimientos y Técnicas", symptoms: "Síntomas y Signos",
    diagnostics: "Diagnósticos y Análisis", emergency: "Medicina de Urgencias",
    nutrition: "Nutrición y Prevención", pediatrics: "Pediatría",
    cardiology: "Cardiología", neurology: "Neurología", oncology: "Oncología",
    surgery: "Cirugía", psychiatry: "Psiquiatría", endocrinology: "Endocrinología",
    "infectious-diseases": "Enfermedades Infecciosas", veterinary: "Medicina Veterinaria",
  },
  tr: {
    diseases: "Hastalıklar ve Durumlar", drugs: "İlaçlar ve Preparatlar",
    procedures: "Prosedürler ve Teknikler", symptoms: "Semptomlar ve Belirtiler",
    diagnostics: "Tanı ve Laboratuvar", emergency: "Acil Tıp",
    nutrition: "Beslenme ve Koruyucu Sağlık", pediatrics: "Pediatri",
    cardiology: "Kardiyoloji", neurology: "Nöroloji", oncology: "Onkoloji",
    surgery: "Cerrahi", psychiatry: "Psikiyatri", endocrinology: "Endokrinoloji",
    "infectious-diseases": "Enfeksiyon Hastalıkları", veterinary: "Veteriner Hekimlik",
  },
  ar: {
    diseases: "الأمراض والحالات", drugs: "الأدوية والعقاقير",
    procedures: "الإجراءات والتقنيات", symptoms: "الأعراض والعلامات",
    diagnostics: "التشخيص والمختبر", emergency: "طب الطوارئ",
    nutrition: "التغذية والوقاية", pediatrics: "طب الأطفال",
    cardiology: "أمراض القلب", neurology: "الأعصاب", oncology: "الأورام",
    surgery: "الجراحة", psychiatry: "الطب النفسي", endocrinology: "الغدد الصماء",
    "infectious-diseases": "الأمراض المعدية", veterinary: "الطب البيطري",
  },
};

/** Get category label for a given locale (for server components). */
export function getCategoryLabel(category: string, locale: string): string {
  const labels = STATIC_LABELS[locale] ?? STATIC_LABELS.en;
  return labels[category] ?? category;
}

const MORE_IN: Record<string, string> = {
  en: "More in", ru: "Ещё в разделе", de: "Mehr in",
  fr: "Plus dans", es: "Más en", tr: "Daha fazlası", ar: "المزيد في",
};

export function getMoreIn(locale: string): string {
  return MORE_IN[locale] ?? MORE_IN.en;
}

/** Short category descriptions for SEO (English only — bots don't need locale). */
export const CATEGORY_DESCRIPTIONS: Record<string, string> = {
  diseases: "Evidence-based articles on medical conditions, pathophysiology, diagnosis, and treatment.",
  drugs: "Drug monographs: mechanisms of action, dosing, contraindications, and interactions.",
  procedures: "Step-by-step guides to clinical procedures and techniques.",
  symptoms: "Clinical approach to common and rare symptoms — differential diagnosis and workup.",
  diagnostics: "Laboratory tests, imaging, and diagnostic criteria for clinical practice.",
  emergency: "Rapid-reference articles on acute medical emergencies and critical care.",
  nutrition: "Evidence-based nutritional guidelines and preventive medicine recommendations.",
  pediatrics: "Medical content tailored to pediatric patients — growth, development, and disease.",
  cardiology: "Heart diseases, arrhythmias, heart failure, and cardiovascular pharmacology.",
  neurology: "Neurological disorders, stroke, epilepsy, neurodegenerative diseases.",
  oncology: "Cancer biology, diagnosis, staging, and treatment modalities.",
  surgery: "Surgical principles, operative techniques, and perioperative care.",
  psychiatry: "Mental health conditions, psychopharmacology, and psychiatric emergencies.",
  endocrinology: "Hormonal disorders, diabetes, thyroid, adrenal, and metabolic conditions.",
  "infectious-diseases": "Bacterial, viral, fungal, and parasitic infections — diagnosis and antimicrobial therapy.",
  veterinary: "Veterinary medicine: animal diseases, pharmacology, and clinical techniques.",
};
