export type Lang = "en" | "ru" | "ar" | "tr" | "de" | "fr" | "es";
export type T = Record<Lang, string>;

// ── Shared UI strings ────────────────────────────────────────────────────────

export const UI: Record<string, T> = {
  calculate:      { en: "Calculate", ru: "Вычислить", ar: "احسب", tr: "Hesapla", de: "Berechnen", fr: "Calculer", es: "Calcular" },
  reset:          { en: "Reset", ru: "Сбросить", ar: "إعادة تعيين", tr: "Sıfırla", de: "Zurücksetzen", fr: "Réinitialiser", es: "Reiniciar" },
  score:          { en: "Score", ru: "Счёт", ar: "النتيجة", tr: "Skor", de: "Punktzahl", fr: "Score", es: "Puntuación" },
  risk_level:     { en: "Risk Level", ru: "Уровень риска", ar: "مستوى الخطر", tr: "Risk Düzeyi", de: "Risikoniveau", fr: "Niveau de risque", es: "Nivel de riesgo" },
  low_risk:       { en: "Low Risk", ru: "Низкий риск", ar: "خطر منخفض", tr: "Düşük Risk", de: "Niedriges Risiko", fr: "Risque faible", es: "Riesgo bajo" },
  moderate_risk:  { en: "Moderate Risk", ru: "Умеренный риск", ar: "خطر متوسط", tr: "Orta Risk", de: "Mittleres Risiko", fr: "Risque modéré", es: "Riesgo moderado" },
  high_risk:      { en: "High Risk", ru: "Высокий риск", ar: "خطر مرتفع", tr: "Yüksek Risk", de: "Hohes Risiko", fr: "Risque élevé", es: "Riesgo alto" },
  very_high_risk: { en: "Very High Risk", ru: "Очень высокий риск", ar: "خطر مرتفع جداً", tr: "Çok Yüksek Risk", de: "Sehr hohes Risiko", fr: "Risque très élevé", es: "Riesgo muy alto" },
  yes:            { en: "Yes", ru: "Да", ar: "نعم", tr: "Evet", de: "Ja", fr: "Oui", es: "Sí" },
  no:             { en: "No", ru: "Нет", ar: "لا", tr: "Hayır", de: "Nein", fr: "Non", es: "No" },
  recommendation: { en: "Recommendation", ru: "Рекомендация", ar: "التوصية", tr: "Öneri", de: "Empfehlung", fr: "Recommandation", es: "Recomendación" },
  reference:      { en: "Clinical reference", ru: "Клинический источник", ar: "المرجع السريري", tr: "Klinik referans", de: "Klinische Referenz", fr: "Référence clinique", es: "Referencia clínica" },
  back_to_calcs:  { en: "← All calculators", ru: "← Все калькуляторы", ar: "← جميع الآلات الحاسبة", tr: "← Tüm hesap makineleri", de: "← Alle Rechner", fr: "← Tous les calculateurs", es: "← Todos los calculadores" },
  study_topic:    { en: "Study this topic →", ru: "Изучить тему →", ar: "ادرس هذا الموضوع →", tr: "Bu konuyu çalış →", de: "Thema vertiefen →", fr: "Étudier ce sujet →", es: "Estudiar este tema →" },
  ai_cta_title:   { en: "Get AI clinical interpretation", ru: "Получите AI-интерпретацию", ar: "احصل على التفسير السريري بالذكاء الاصطناعي", tr: "Yapay zeka klinik yorumu alın", de: "KI-Interpretation erhalten", fr: "Obtenir une interprétation IA", es: "Obtener interpretación clínica con IA" },
  ai_cta_desc:    { en: "Create a free account to get Claude AI–powered clinical context, differential diagnoses, and management tips for this result.", ru: "Создайте бесплатный аккаунт, чтобы получить клинический контекст, дифференциальный диагноз и рекомендации от Claude AI.", ar: "أنشئ حساباً مجانياً للحصول على السياق السريري وقائمة التشخيص التفريقي والتوصيات من Claude AI.", tr: "Sonuç için Claude AI destekli klinik bağlam, ayırıcı tanı ve yönetim ipuçları almak için ücretsiz hesap oluşturun.", de: "Erstellen Sie ein kostenloses Konto für KI-gestützte klinische Interpretation, Differentialdiagnosen und Therapieempfehlungen.", fr: "Créez un compte gratuit pour une interprétation clinique, un diagnostic différentiel et des conseils de prise en charge par Claude AI.", es: "Crea una cuenta gratuita para obtener contexto clínico, diagnósticos diferenciales y recomendaciones de manejo con Claude AI." },
  ai_cta_btn:     { en: "Create free account", ru: "Создать бесплатный аккаунт", ar: "إنشاء حساب مجاني", tr: "Ücretsiz hesap oluştur", de: "Kostenloses Konto erstellen", fr: "Créer un compte gratuit", es: "Crear cuenta gratis" },
  points:         { en: "pts", ru: "б", ar: "نقطة", tr: "puan", de: "Pkt.", fr: "pts", es: "pts" },
  male:           { en: "Male", ru: "Мужской", ar: "ذكر", tr: "Erkek", de: "Männlich", fr: "Masculin", es: "Masculino" },
  female:         { en: "Female", ru: "Женский", ar: "أنثى", tr: "Kadın", de: "Weiblich", fr: "Féminin", es: "Femenino" },
  age:            { en: "Age (years)", ru: "Возраст (лет)", ar: "العمر (سنوات)", tr: "Yaş (yıl)", de: "Alter (Jahre)", fr: "Âge (années)", es: "Edad (años)" },
  sex:            { en: "Biological sex", ru: "Биологический пол", ar: "الجنس البيولوجي", tr: "Biyolojik cinsiyet", de: "Biologisches Geschlecht", fr: "Sexe biologique", es: "Sexo biológico" },
  creatinine:     { en: "Serum creatinine", ru: "Креатинин сыворотки", ar: "كرياتينين المصل", tr: "Serum kreatinin", de: "Serum-Kreatinin", fr: "Créatinine sérique", es: "Creatinina sérica" },
  egfr_result:    { en: "Estimated GFR", ru: "Расчётная СКФ", ar: "معدل الترشيح الكبيبي التقديري", tr: "Tahmini GFR", de: "Geschätzte GFR", fr: "DFG estimé", es: "TFG estimada" },
  ckd_stage:      { en: "CKD Stage", ru: "Стадия ХБП", ar: "مرحلة مرض الكلى المزمن", tr: "KBH Evresi", de: "CKD-Stadium", fr: "Stade IRC", es: "Estadio ERC" },
};

// ── Type definitions ─────────────────────────────────────────────────────────

export type FieldDef =
  | { type: "checkbox"; points: number; label: T; hint?: T }
  | { type: "select"; id: string; label: T; hint?: T; options: { value: number; label: T }[] };

export interface RiskBand {
  minScore: number;
  maxScore: number;
  level: "low" | "moderate" | "high" | "very-high";
  labelKey: keyof typeof UI;
  color: "green" | "amber" | "red" | "red-dark";
  description: T;
  recommendation: T;
}

export interface CalcMeta {
  slug: string;
  name: string;
  nameI18n: T;
  subtitle: T;
  seoDescription: T;
  category: string;
  categoryI18n: T;
  icon: string;
  maxScore: number;
  fields: FieldDef[];
  risks: RiskBand[];
  reference: string;
  relatedSlug?: string;
  relatedLabelI18n?: T;
  note?: T;
}

// ── Helper ───────────────────────────────────────────────────────────────────

export function getRiskBand(calcs: CalcMeta, score: number): RiskBand | null {
  return calcs.risks.find(r => score >= r.minScore && score <= r.maxScore) ?? null;
}

// ── Calculator definitions ───────────────────────────────────────────────────

export const CALCULATORS: CalcMeta[] = [

  // ── 1. CHA₂DS₂-VASc ──────────────────────────────────────────────────────
  {
    slug: "cha2ds2-vasc",
    name: "CHA₂DS₂-VASc Score",
    nameI18n: { en: "CHA₂DS₂-VASc Score", ru: "Шкала CHA₂DS₂-VASc", ar: "نتيجة CHA₂DS₂-VASc", tr: "CHA₂DS₂-VASc Skoru", de: "CHA₂DS₂-VASc Score", fr: "Score CHA₂DS₂-VASc", es: "Score CHA₂DS₂-VASc" },
    subtitle: {
      en: "Stroke risk in non-valvular atrial fibrillation",
      ru: "Риск инсульта при неклапанной фибрилляции предсердий",
      ar: "خطر السكتة الدماغية في الرجفان الأذيني غير الصمامي",
      tr: "Kapak dışı atriyal fibrilasyonda inme riski",
      de: "Schlaganfallrisiko bei nicht-valvulärem Vorhofflimmern",
      fr: "Risque d'AVC dans la fibrillation auriculaire non valvulaire",
      es: "Riesgo de ictus en fibrilación auricular no valvular",
    },
    seoDescription: {
      en: "CHA₂DS₂-VASc calculator for stroke risk in atrial fibrillation. Evidence-based anticoagulation guidance per ACC/AHA/ESC guidelines.",
      ru: "Калькулятор CHA₂DS₂-VASc для оценки риска инсульта при ФП. Рекомендации по антикоагуляции по руководствам ACC/AHA/ESC.",
      ar: "آلة حاسبة CHA₂DS₂-VASc لتقييم خطر السكتة الدماغية في الرجفان الأذيني. إرشادات مضادات التخثر وفق ACC/AHA/ESC.",
      tr: "Atriyal fibrilasyonda inme riski için CHA₂DS₂-VASc hesaplayıcı. ACC/AHA/ESC kılavuzlarına göre antikoagülasyon rehberliği.",
      de: "CHA₂DS₂-VASc-Rechner für Schlaganfallrisiko bei Vorhofflimmern. Antikoagulations-Empfehlung nach ACC/AHA/ESC-Leitlinien.",
      fr: "Calculateur CHA₂DS₂-VASc pour le risque d'AVC en fibrillation auriculaire. Recommandations anticoagulantes ACC/AHA/ESC.",
      es: "Calculadora CHA₂DS₂-VASc para riesgo de ictus en fibrilación auricular. Guías ACC/AHA/ESC para anticoagulación.",
    },
    category: "cardiology",
    categoryI18n: { en: "Cardiology", ru: "Кардиология", ar: "أمراض القلب", tr: "Kardiyoloji", de: "Kardiologie", fr: "Cardiologie", es: "Cardiología" },
    icon: "❤️",
    maxScore: 9,
    relatedSlug: "atrial-fibrillation",
    relatedLabelI18n: { en: "Atrial Fibrillation module", ru: "Модуль по ФП", ar: "وحدة الرجفان الأذيني", tr: "Atriyal fibrilasyon modülü", de: "Vorhofflimmern-Modul", fr: "Module fibrillation auriculaire", es: "Módulo de fibrilación auricular" },
    reference: "Lip GYH et al. Chest. 2010;137:263–272 · ESC Guidelines 2020",
    note: {
      en: "A score of 1 due solely to female sex does not warrant anticoagulation — treat as score 0.",
      ru: "Счёт 1 только из-за женского пола не требует антикоагуляции — расценивать как 0.",
      ar: "نتيجة 1 بسبب الجنس الأنثوي فقط لا تستوجب العلاج بمضادات التخثر — تُعامَل كنتيجة 0.",
      tr: "Yalnızca kadın cinsiyetinden kaynaklanan 1 puan antikoagülasyon gerektirmez — 0 olarak değerlendirin.",
      de: "Ein Punkt allein durch weibliches Geschlecht rechtfertigt keine Antikoagulation — wie Score 0 behandeln.",
      fr: "Un score de 1 dû uniquement au sexe féminin ne justifie pas l'anticoagulation — traiter comme score 0.",
      es: "Una puntuación de 1 debida únicamente al sexo femenino no justifica anticoagulación — tratar como 0.",
    },
    fields: [
      { type: "checkbox", points: 1, label: { en: "Congestive heart failure or LV dysfunction", ru: "Сердечная недостаточность или дисфункция ЛЖ", ar: "قصور القلب الاحتقاني أو خلل وظيفي في البطين الأيسر", tr: "Konjestif kalp yetmezliği veya LV disfonksiyonu", de: "Herzinsuffizienz oder LV-Dysfunktion", fr: "Insuffisance cardiaque ou dysfonction VG", es: "Insuficiencia cardíaca o disfunción del VI" } },
      { type: "checkbox", points: 1, label: { en: "Hypertension", ru: "Артериальная гипертензия", ar: "ارتفاع ضغط الدم", tr: "Hipertansiyon", de: "Hypertonie", fr: "Hypertension", es: "Hipertensión" } },
      { type: "checkbox", points: 2, label: { en: "Age ≥ 75 years", ru: "Возраст ≥ 75 лет", ar: "العمر ≥ 75 سنة", tr: "Yaş ≥ 75", de: "Alter ≥ 75 Jahre", fr: "Âge ≥ 75 ans", es: "Edad ≥ 75 años" }, hint: { en: "2 points", ru: "2 балла", ar: "نقطتان", tr: "2 puan", de: "2 Punkte", fr: "2 points", es: "2 puntos" } },
      { type: "checkbox", points: 1, label: { en: "Diabetes mellitus", ru: "Сахарный диабет", ar: "داء السكري", tr: "Diabetes mellitus", de: "Diabetes mellitus", fr: "Diabète sucré", es: "Diabetes mellitus" } },
      { type: "checkbox", points: 2, label: { en: "Prior stroke, TIA, or thromboembolism", ru: "Инсульт, ТИА или тромбоэмболия в анамнезе", ar: "سكتة دماغية أو نوبة نقص تروية عابرة أو جلطة سابقة", tr: "Geçirilmiş inme, TİA veya tromboembolizm", de: "Vorangegangener Schlaganfall, TIA oder Thromboembolie", fr: "AVC, AIT ou thromboembolie antérieurs", es: "Ictus, AIT o tromboembolismo previo" }, hint: { en: "2 points", ru: "2 балла", ar: "نقطتان", tr: "2 puan", de: "2 Punkte", fr: "2 points", es: "2 puntos" } },
      { type: "checkbox", points: 1, label: { en: "Vascular disease (MI, peripheral artery disease, aortic plaque)", ru: "Заболевание сосудов (ИМ, ЗПА, бляшка аорты)", ar: "مرض وعائي (احتشاء عضلة القلب، أمراض الشرايين الطرفية، لويحة أبهرية)", tr: "Vasküler hastalık (MI, periferik arter hastalığı, aort plağı)", de: "Gefäßerkrankung (MI, pAVK, Aortenplaque)", fr: "Maladie vasculaire (IDM, AOMI, plaque aortique)", es: "Enfermedad vascular (IAM, EAP, placa aórtica)" } },
      { type: "checkbox", points: 1, label: { en: "Age 65–74 years", ru: "Возраст 65–74 лет", ar: "العمر 65–74 سنة", tr: "Yaş 65–74", de: "Alter 65–74 Jahre", fr: "Âge 65–74 ans", es: "Edad 65–74 años" } },
      { type: "checkbox", points: 1, label: { en: "Female sex", ru: "Женский пол", ar: "الجنس الأنثوي", tr: "Kadın cinsiyeti", de: "Weibliches Geschlecht", fr: "Sexe féminin", es: "Sexo femenino" } },
    ],
    risks: [
      {
        minScore: 0, maxScore: 0, level: "low", labelKey: "low_risk", color: "green",
        description: { en: "Annual stroke risk ~0%. No anticoagulation recommended.", ru: "Годовой риск инсульта ~0%. Антикоагуляция не показана.", ar: "خطر السكتة الدماغية السنوي ~0%. لا يُوصى بمضادات التخثر.", tr: "Yıllık inme riski ~%0. Antikoagülasyon önerilmez.", de: "Jährliches Schlaganfallrisiko ~0 %. Keine Antikoagulation empfohlen.", fr: "Risque annuel d'AVC ~0 %. Anticoagulation non recommandée.", es: "Riesgo anual de ictus ~0 %. No se recomienda anticoagulación." },
        recommendation: { en: "Antithrombotic therapy not recommended.", ru: "Антитромботическая терапия не рекомендована.", ar: "لا يُوصى بالعلاج المضاد للتخثر.", tr: "Antitrombotik tedavi önerilmez.", de: "Antithrombotische Therapie nicht empfohlen.", fr: "Thérapie antithrombotique non recommandée.", es: "No se recomienda terapia antitrombótica." },
      },
      {
        minScore: 1, maxScore: 1, level: "moderate", labelKey: "moderate_risk", color: "amber",
        description: { en: "Annual stroke risk ~1.3%. Oral anticoagulation may be considered.", ru: "Годовой риск инсульта ~1,3%. Можно рассмотреть антикоагуляцию.", ar: "خطر السكتة الدماغية السنوي ~1.3%. يمكن النظر في مضادات التخثر الفموية.", tr: "Yıllık inme riski ~%1,3. Oral antikoagülasyon düşünülebilir.", de: "Jährliches Schlaganfallrisiko ~1,3 %. Orale Antikoagulation kann erwogen werden.", fr: "Risque annuel d'AVC ~1,3 %. Anticoagulation orale peut être envisagée.", es: "Riesgo anual de ictus ~1,3 %. Se puede considerar anticoagulación oral." },
        recommendation: { en: "Consider anticoagulation — weigh bleeding risk (HAS-BLED).", ru: "Рассмотреть антикоагуляцию — оценить риск кровотечения (HAS-BLED).", ar: "النظر في مضادات التخثر مع تقييم خطر النزيف (HAS-BLED).", tr: "Antikoagülasyon düşünün — kanama riskini değerlendirin (HAS-BLED).", de: "Antikoagulation erwägen — Blutungsrisiko abwägen (HAS-BLED).", fr: "Envisager l'anticoagulation — évaluer le risque hémorragique (HAS-BLED).", es: "Considerar anticoagulación — valorar riesgo hemorrágico (HAS-BLED)." },
      },
      {
        minScore: 2, maxScore: 9, level: "high", labelKey: "high_risk", color: "red",
        description: { en: "Annual stroke risk ≥2.2%. Oral anticoagulation strongly recommended.", ru: "Годовой риск инсульта ≥2,2%. Антикоагуляция настоятельно рекомендована.", ar: "خطر السكتة الدماغية السنوي ≥2.2%. يُوصى بشدة بمضادات التخثر الفموية.", tr: "Yıllık inme riski ≥%2,2. Oral antikoagülasyon güçlü şekilde önerilir.", de: "Jährliches Schlaganfallrisiko ≥2,2 %. Orale Antikoagulation dringend empfohlen.", fr: "Risque annuel d'AVC ≥2,2 %. Anticoagulation orale fortement recommandée.", es: "Riesgo anual de ictus ≥2,2 %. Anticoagulación oral fuertemente recomendada." },
        recommendation: { en: "Start anticoagulation: DOAC preferred over VKA (unless contraindicated).", ru: "Назначить антикоагуляцию: НОАК предпочтительнее варфарина.", ar: "بدء العلاج بمضادات التخثر: يُفضَّل DOAC على VKA (ما لم يكن هناك موانع).", tr: "Antikoagülasyon başlayın: VKA'ya tercihan DOAC kullanın.", de: "Antikoagulation beginnen: DOAK bevorzugt gegenüber VKA.", fr: "Initier l'anticoagulation : AOD préférés aux AVK.", es: "Iniciar anticoagulación: ACOD preferidos sobre AVK." },
      },
    ],
  },

  // ── 2. CURB-65 ───────────────────────────────────────────────────────────
  {
    slug: "curb-65",
    name: "CURB-65 Score",
    nameI18n: { en: "CURB-65 Score", ru: "Шкала CURB-65", ar: "نتيجة CURB-65", tr: "CURB-65 Skoru", de: "CURB-65 Score", fr: "Score CURB-65", es: "Score CURB-65" },
    subtitle: {
      en: "Pneumonia severity and disposition",
      ru: "Тяжесть пневмонии и место лечения",
      ar: "شدة الالتهاب الرئوي وتحديد مكان العلاج",
      tr: "Pnömoni şiddeti ve tedavi yeri belirleme",
      de: "Schweregrad der Pneumonie und Therapieplanung",
      fr: "Sévérité de la pneumonie et orientation thérapeutique",
      es: "Gravedad de la neumonía y decisión terapéutica",
    },
    seoDescription: {
      en: "CURB-65 calculator for community-acquired pneumonia severity. Determines outpatient vs inpatient vs ICU management per BTS guidelines.",
      ru: "Калькулятор CURB-65 для оценки тяжести внебольничной пневмонии. Амбулаторное vs стационарное vs ОРИТ лечение.",
      ar: "آلة حاسبة CURB-65 لتقييم شدة الالتهاب الرئوي المكتسب من المجتمع. تحديد العلاج الخارجي أو الداخلي أو في وحدة العناية المركزة.",
      tr: "Toplum kökenli pnömoni şiddeti için CURB-65 hesaplayıcı. BTS kılavuzlarına göre ayaktan/yatarak/YBÜ tedavi kararı.",
      de: "CURB-65-Rechner für ambulant erworbene Pneumonie. Ambulante vs. stationäre vs. Intensivbehandlung nach BTS-Leitlinien.",
      fr: "Calculateur CURB-65 pour la pneumonie communautaire. Ambulatoire vs hospitalisation vs réanimation selon les recommandations BTS.",
      es: "Calculadora CURB-65 para neumonía adquirida en la comunidad. Tratamiento ambulatorio vs hospitalario vs UCI según guías BTS.",
    },
    category: "pulmonology",
    categoryI18n: { en: "Pulmonology", ru: "Пульмонология", ar: "أمراض الرئة", tr: "Pulmonoloji", de: "Pneumologie", fr: "Pneumologie", es: "Neumología" },
    icon: "🫁",
    maxScore: 5,
    reference: "Lim WS et al. Thorax. 2003;58:377–382 · BTS Pneumonia Guidelines",
    fields: [
      {
        type: "checkbox", points: 1,
        label: { en: "Confusion (new onset)", ru: "Спутанность сознания (новая)", ar: "ارتباك (حديث الحدوث)", tr: "Konfüzyon (yeni başlangıçlı)", de: "Verwirrtheit (neu aufgetreten)", fr: "Confusion (nouveau)", es: "Confusión (de nueva aparición)" },
        hint: { en: "Disorientation to person, place or time", ru: "Дезориентация в личности, месте или времени", ar: "الارتباك في التوجه للشخص أو المكان أو الزمان", tr: "Kişi, yer veya zamana yönelik dezoryantasyon", de: "Desorientiertheit zu Person, Ort oder Zeit", fr: "Désorientation dans le temps, l'espace ou la personne", es: "Desorientación en persona, lugar o tiempo" },
      },
      {
        type: "checkbox", points: 1,
        label: { en: "Urea > 7 mmol/L (BUN > 19 mg/dL)", ru: "Мочевина > 7 ммоль/л (АМК > 19 мг/дл)", ar: "اليوريا > 7 ملمول/لتر (BUN > 19 ملغ/ديسيلتر)", tr: "Üre > 7 mmol/L (BUN > 19 mg/dL)", de: "Harnstoff > 7 mmol/l (BUN > 19 mg/dl)", fr: "Urée > 7 mmol/L (BUN > 19 mg/dL)", es: "Urea > 7 mmol/L (BUN > 19 mg/dL)" },
      },
      {
        type: "checkbox", points: 1,
        label: { en: "Respiratory rate ≥ 30 breaths/min", ru: "Частота дыхания ≥ 30/мин", ar: "معدل التنفس ≥ 30 نفساً في الدقيقة", tr: "Solunum hızı ≥ 30/dak", de: "Atemfrequenz ≥ 30/min", fr: "Fréquence respiratoire ≥ 30/min", es: "Frecuencia respiratoria ≥ 30 resp/min" },
      },
      {
        type: "checkbox", points: 1,
        label: { en: "Low blood pressure (SBP < 90 or DBP ≤ 60 mmHg)", ru: "Низкое АД (систол. < 90 или диастол. ≤ 60 мм рт.ст.)", ar: "انخفاض ضغط الدم (SBP < 90 أو DBP ≤ 60 ملم زئبق)", tr: "Düşük kan basıncı (SKB < 90 veya DKB ≤ 60 mmHg)", de: "Hypotonie (SBD < 90 oder DBD ≤ 60 mmHg)", fr: "Hypotension (PAS < 90 ou PAD ≤ 60 mmHg)", es: "Hipotensión (PAS < 90 o PAD ≤ 60 mmHg)" },
      },
      {
        type: "checkbox", points: 1,
        label: { en: "Age ≥ 65 years", ru: "Возраст ≥ 65 лет", ar: "العمر ≥ 65 سنة", tr: "Yaş ≥ 65", de: "Alter ≥ 65 Jahre", fr: "Âge ≥ 65 ans", es: "Edad ≥ 65 años" },
      },
    ],
    risks: [
      {
        minScore: 0, maxScore: 1, level: "low", labelKey: "low_risk", color: "green",
        description: { en: "30-day mortality ~1.5%. Low severity.", ru: "30-дневная летальность ~1,5%. Низкая тяжесть.", ar: "الوفيات خلال 30 يوماً ~1.5%. شدة منخفضة.", tr: "30 günlük mortalite ~%1,5. Düşük şiddet.", de: "30-Tage-Mortalität ~1,5 %. Geringer Schweregrad.", fr: "Mortalité à 30 j ~1,5 %. Sévérité faible.", es: "Mortalidad a 30 días ~1,5 %. Gravedad baja." },
        recommendation: { en: "Consider outpatient treatment. Close follow-up within 24–48 h.", ru: "Рассмотреть амбулаторное лечение. Повторный осмотр через 24–48 ч.", ar: "النظر في العلاج الخارجي. متابعة خلال 24–48 ساعة.", tr: "Ayaktan tedavi düşünün. 24–48 saatte yakın takip.", de: "Ambulante Therapie erwägen. Kontrolltermin in 24–48 h.", fr: "Traitement ambulatoire envisageable. Réévaluation à 24–48 h.", es: "Considerar tratamiento ambulatorio. Seguimiento en 24–48 h." },
      },
      {
        minScore: 2, maxScore: 2, level: "moderate", labelKey: "moderate_risk", color: "amber",
        description: { en: "30-day mortality ~9.2%. Moderate severity.", ru: "30-дневная летальность ~9,2%. Умеренная тяжесть.", ar: "الوفيات خلال 30 يوماً ~9.2%. شدة متوسطة.", tr: "30 günlük mortalite ~%9,2. Orta şiddet.", de: "30-Tage-Mortalität ~9,2 %. Mäßiger Schweregrad.", fr: "Mortalité à 30 j ~9,2 %. Sévérité modérée.", es: "Mortalidad a 30 días ~9,2 %. Gravedad moderada." },
        recommendation: { en: "Hospital admission recommended. Consider short-stay unit.", ru: "Рекомендована госпитализация. Рассмотреть краткосрочный стационар.", ar: "يُوصى بالدخول إلى المستشفى. النظر في وحدة الإقامة القصيرة.", tr: "Hastane yatışı önerilir. Kısa süreli gözlem birimi düşünün.", de: "Krankenhausaufnahme empfohlen. Kurzzeitstationsaufnahme erwägen.", fr: "Hospitalisation recommandée. Envisager une unité de courte durée.", es: "Se recomienda hospitalización. Considerar unidad de corta estancia." },
      },
      {
        minScore: 3, maxScore: 5, level: "high", labelKey: "high_risk", color: "red",
        description: { en: "30-day mortality ≥22%. High severity.", ru: "30-дневная летальность ≥22%. Высокая тяжесть.", ar: "الوفيات خلال 30 يوماً ≥22%. شدة عالية.", tr: "30 günlük mortalite ≥%22. Yüksek şiddet.", de: "30-Tage-Mortalität ≥22 %. Hoher Schweregrad.", fr: "Mortalité à 30 j ≥22 %. Sévérité élevée.", es: "Mortalidad a 30 días ≥22 %. Gravedad alta." },
        recommendation: { en: "Urgent hospital admission. Consider ICU assessment (especially score ≥4).", ru: "Срочная госпитализация. Рассмотреть ОРИТ (особенно при ≥4).", ar: "دخول المستشفى بشكل عاجل. النظر في تقييم العناية المركزة (خاصةً إذا كانت النتيجة ≥4).", tr: "Acil hastane yatışı. YBÜ değerlendirmesini düşünün (özellikle skor ≥4).", de: "Dringende Krankenhausaufnahme. Intensivstation erwägen (besonders Score ≥4).", fr: "Hospitalisation urgente. Évaluation en réanimation envisagée (surtout score ≥4).", es: "Hospitalización urgente. Considerar UCI (especialmente puntuación ≥4)." },
      },
    ],
  },

  // ── 3. Wells DVT ─────────────────────────────────────────────────────────
  {
    slug: "wells-dvt",
    name: "Wells Criteria for DVT",
    nameI18n: { en: "Wells Criteria for DVT", ru: "Критерии Уэллса для ТГВ", ar: "معايير ويلز لتشخيص التخثر الوريدي العميق", tr: "DVT için Wells Kriterleri", de: "Wells-Kriterien für TVT", fr: "Critères de Wells pour la TVP", es: "Criterios de Wells para TVP" },
    subtitle: {
      en: "Pre-test probability of deep vein thrombosis",
      ru: "Предтестовая вероятность тромбоза глубоких вен",
      ar: "الاحتمالية قبل الاختبار لتجلط الأوردة العميقة",
      tr: "Derin ven trombozu ön test olasılığı",
      de: "Vortestwahrscheinlichkeit einer tiefen Venenthrombose",
      fr: "Probabilité pré-test de thrombose veineuse profonde",
      es: "Probabilidad pre-test de trombosis venosa profunda",
    },
    seoDescription: {
      en: "Wells DVT criteria calculator for pre-test probability of deep vein thrombosis. Guide D-dimer and compression ultrasound ordering.",
      ru: "Критерии Уэллса для предтестовой вероятности ТГВ. Решение о назначении D-димера и УЗИ вен.",
      ar: "آلة حاسبة معايير ويلز لتقدير احتمالية تجلط الأوردة العميقة قبل الاختبار.",
      tr: "DVT ön test olasılığı için Wells kriterleri hesaplayıcı. D-dimer ve kompresyon ultrason kararı.",
      de: "Wells-Kriterien-Rechner für Vortestwahrscheinlichkeit TVT. Entscheidungshilfe für D-Dimer und Ultraschall.",
      fr: "Calculateur Wells TVP pour la probabilité pré-test. Guide pour D-dimères et échographie de compression.",
      es: "Calculadora Wells TVP para probabilidad pre-test. Guía para dímero-D y ecografía de compresión.",
    },
    category: "hematology",
    categoryI18n: { en: "Hematology", ru: "Гематология", ar: "أمراض الدم", tr: "Hematoloji", de: "Hämatologie", fr: "Hématologie", es: "Hematología" },
    icon: "🩸",
    maxScore: 8,
    reference: "Wells PS et al. Lancet. 1997;350:1795–1798 · Ann Intern Med. 2003;138:307",
    fields: [
      { type: "checkbox", points: 1, label: { en: "Active cancer (treatment ongoing, within 6 months, or palliative)", ru: "Активный рак (лечение, 6 мес., паллиатив)", ar: "سرطان نشط (علاج مستمر، خلال 6 أشهر، أو علاج ملطف)", tr: "Aktif kanser (tedavi devam ediyor, 6 ay içinde veya palyatif)", de: "Aktives Malignom (laufende Therapie, ≤6 Mo. oder palliativ)", fr: "Cancer actif (traitement en cours, ≤6 mois ou palliatif)", es: "Cáncer activo (tratamiento en curso, en 6 meses o paliativo)" } },
      { type: "checkbox", points: 1, label: { en: "Paralysis, paresis, or immobilisation of lower limb", ru: "Паралич, парез или иммобилизация нижней конечности", ar: "شلل أو شبه شلل أو تثبيت الطرف السفلي", tr: "Alt ekstremite felci, parezi veya immobilizasyon", de: "Paralyse, Parese oder Immobilisation der unteren Extremität", fr: "Paralysie, parésie ou immobilisation du membre inférieur", es: "Parálisis, paresia o inmovilización del miembro inferior" } },
      { type: "checkbox", points: 1, label: { en: "Bedridden ≥ 3 days or major surgery within 12 weeks", ru: "Постельный режим ≥ 3 дней или крупная операция за 12 нед.", ar: "الراحة في الفراش ≥ 3 أيام أو جراحة كبرى خلال 12 أسبوعاً", tr: "≥3 gün yatak istirahati veya 12 hafta içinde büyük cerrahi", de: "Bettlägerigkeit ≥3 Tage oder größere OP in den letzten 12 Wochen", fr: "Alitement ≥3 jours ou chirurgie majeure dans les 12 semaines", es: "Encamamiento ≥3 días o cirugía mayor en las últimas 12 semanas" } },
      { type: "checkbox", points: 1, label: { en: "Localized tenderness along the deep vein system", ru: "Локальная болезненность по ходу глубоких вен", ar: "ألم موضعي على طول نظام الوريد العميق", tr: "Derin ven sistemi boyunca lokalize hassasiyet", de: "Druckschmerz entlang des tiefen Venensystems", fr: "Douleur localisée sur le trajet du système veineux profond", es: "Sensibilidad localizada a lo largo del sistema venoso profundo" } },
      { type: "checkbox", points: 1, label: { en: "Entire leg swollen", ru: "Отёк всей ноги", ar: "انتفاخ الساق بالكامل", tr: "Tüm bacakta şişlik", de: "Gesamtes Bein geschwollen", fr: "Jambe entière gonflée", es: "Pierna entera hinchada" } },
      { type: "checkbox", points: 1, label: { en: "Calf swelling > 3 cm vs asymptomatic side", ru: "Увеличение икры > 3 см vs бессимптомная сторона", ar: "تورم الساق أكثر من 3 سم مقارنةً بالجانب غير المصاب", tr: "Asemptomatik tarafa kıyasla baldır şişliği > 3 cm", de: "Unterschenkelschwellung > 3 cm vs. asymptomatische Seite", fr: "Gonflement du mollet > 3 cm vs côté asymptomatique", es: "Pantorrilla hinchada > 3 cm vs lado asintomático" } },
      { type: "checkbox", points: 1, label: { en: "Pitting oedema (greater in symptomatic leg)", ru: "Отёк с ямкой (больше в симптомной ноге)", ar: "وذمة ضاغطة (أشد في الساق المصابة)", tr: "Çukurlaşan ödem (semptomatik bacakta daha fazla)", de: "Eindrückbares Ödem (in symptomatischem Bein stärker)", fr: "Œdème avec godet (prédominant du côté symptomatique)", es: "Edema con fóvea (mayor en pierna sintomática)" } },
      { type: "checkbox", points: 1, label: { en: "Collateral superficial veins (non-varicose)", ru: "Коллатеральные поверхностные вены (не варикозные)", ar: "أوردة سطحية جانبية (غير دوالي)", tr: "Kollateral yüzeyel venler (variköz değil)", de: "Kollaterale oberflächliche Venen (nicht variköse)", fr: "Veines superficielles collatérales (non variqueuses)", es: "Venas superficiales colaterales (no varicosas)" } },
      { type: "checkbox", points: -2, label: { en: "Alternative diagnosis as likely or more likely than DVT", ru: "Альтернативный диагноз так же или более вероятен, чем ТГВ", ar: "تشخيص بديل محتمل بنفس القدر أو أكثر من التخثر الوريدي العميق", tr: "DVT'den eşit ya da daha olası alternatif tanı", de: "Alternativdiagnose ebenso wahrscheinlich oder wahrscheinlicher als TVT", fr: "Diagnostic alternatif au moins aussi probable que la TVP", es: "Diagnóstico alternativo igual o más probable que la TVP" }, hint: { en: "−2 points", ru: "−2 балла", ar: "−نقطتان", tr: "−2 puan", de: "−2 Punkte", fr: "−2 points", es: "−2 puntos" } },
    ],
    risks: [
      {
        minScore: -8, maxScore: 0, level: "low", labelKey: "low_risk", color: "green",
        description: { en: "DVT probability ~3%. Low pre-test probability.", ru: "Вероятность ТГВ ~3%. Низкая предтестовая вероятность.", ar: "احتمالية تجلط الأوردة العميقة ~3%. احتمالية منخفضة قبل الاختبار.", tr: "DVT olasılığı ~%3. Düşük ön test olasılığı.", de: "TVT-Wahrscheinlichkeit ~3 %. Niedrige Vortestwahrscheinlichkeit.", fr: "Probabilité de TVP ~3 %. Faible probabilité pré-test.", es: "Probabilidad de TVP ~3 %. Baja probabilidad pre-test." },
        recommendation: { en: "D-dimer testing. If negative → DVT excluded. If positive → ultrasound.", ru: "D-димер. При отрицательном — ТГВ исключён. При положительном — УЗИ.", ar: "اختبار D-dimer. إذا سلبي → استبعاد تجلط الأوردة العميقة. إذا إيجابي → الموجات فوق الصوتية.", tr: "D-dimer testi. Negatifse → DVT dışlanır. Pozitifse → ultrason.", de: "D-Dimer-Test. Bei negativem Ergebnis → TVT ausgeschlossen. Positiv → Ultraschall.", fr: "Test D-dimères. Négatif → TVP exclue. Positif → échographie.", es: "D-dímero. Si negativo → TVP descartada. Si positivo → ecografía." },
      },
      {
        minScore: 1, maxScore: 2, level: "moderate", labelKey: "moderate_risk", color: "amber",
        description: { en: "DVT probability ~17%. Moderate pre-test probability.", ru: "Вероятность ТГВ ~17%. Умеренная предтестовая вероятность.", ar: "احتمالية تجلط الأوردة العميقة ~17%. احتمالية متوسطة قبل الاختبار.", tr: "DVT olasılığı ~%17. Orta ön test olasılığı.", de: "TVT-Wahrscheinlichkeit ~17 %. Mittlere Vortestwahrscheinlichkeit.", fr: "Probabilité de TVP ~17 %. Probabilité pré-test modérée.", es: "Probabilidad de TVP ~17 %. Probabilidad pre-test moderada." },
        recommendation: { en: "D-dimer testing. If negative → DVT unlikely. If positive → ultrasound.", ru: "D-димер. При отрицательном — ТГВ маловероятен. При положительном — УЗИ.", ar: "اختبار D-dimer. إذا سلبي → تجلط الأوردة العميقة غير مرجح. إذا إيجابي → الموجات فوق الصوتية.", tr: "D-dimer testi. Negatifse → DVT olası değil. Pozitifse → ultrason.", de: "D-Dimer-Test. Negativ → TVT unwahrscheinlich. Positiv → Ultraschall.", fr: "Test D-dimères. Négatif → TVP improbable. Positif → échographie.", es: "D-dímero. Si negativo → TVP improbable. Si positivo → ecografía." },
      },
      {
        minScore: 3, maxScore: 8, level: "high", labelKey: "high_risk", color: "red",
        description: { en: "DVT probability ~75%. High pre-test probability.", ru: "Вероятность ТГВ ~75%. Высокая предтестовая вероятность.", ar: "احتمالية تجلط الأوردة العميقة ~75%. احتمالية عالية قبل الاختبار.", tr: "DVT olasılığı ~%75. Yüksek ön test olasılığı.", de: "TVT-Wahrscheinlichkeit ~75 %. Hohe Vortestwahrscheinlichkeit.", fr: "Probabilité de TVP ~75 %. Haute probabilité pré-test.", es: "Probabilidad de TVP ~75 %. Alta probabilidad pre-test." },
        recommendation: { en: "Proceed directly to compression ultrasound. Anticoagulate if delays expected.", ru: "Немедленно назначить УЗИ вен. Начать антикоагуляцию при ожидании задержки.", ar: "التوجه مباشرةً للموجات فوق الصوتية الضاغطة. البدء بمضادات التخثر إذا كان هناك تأخير متوقع.", tr: "Doğrudan kompresyon ultrasonuna gidin. Gecikme bekleniyorsa antikoagülasyon başlayın.", de: "Direkt zur Kompressionssonographie. Bei erwarteter Verzögerung Antikoagulation einleiten.", fr: "Procéder directement à l'échographie de compression. Anticoaguler si délai prévisible.", es: "Proceder directamente a ecografía de compresión. Anticoagular si se prevén retrasos." },
      },
    ],
  },

  // ── 4. HEART Score ───────────────────────────────────────────────────────
  {
    slug: "heart-score",
    name: "HEART Score",
    nameI18n: { en: "HEART Score", ru: "Шкала HEART", ar: "نتيجة HEART", tr: "HEART Skoru", de: "HEART Score", fr: "Score HEART", es: "Score HEART" },
    subtitle: {
      en: "Risk stratification of chest pain in the emergency setting",
      ru: "Стратификация риска боли в груди в приёмном отделении",
      ar: "تصنيف المخاطر لألم الصدر في الطوارئ",
      tr: "Acil serviste göğüs ağrısı risk stratifikasyonu",
      de: "Risikoklassifizierung von Brustschmerzen in der Notaufnahme",
      fr: "Stratification du risque des douleurs thoraciques aux urgences",
      es: "Estratificación del riesgo de dolor torácico en urgencias",
    },
    seoDescription: {
      en: "HEART Score calculator for chest pain risk stratification in the ED. Predicts 30-day MACE risk and guides disposition decisions.",
      ru: "Шкала HEART для стратификации риска боли в груди в скорой помощи. Прогнозирует риск MACE за 30 дней.",
      ar: "آلة حاسبة نتيجة HEART لتصنيف مخاطر ألم الصدر في الطوارئ. تتنبأ بخطر MACE خلال 30 يوماً.",
      tr: "Acil serviste göğüs ağrısı risk sınıflandırması için HEART skoru hesaplayıcı. 30 günlük MACE riskini öngörür.",
      de: "HEART-Score-Rechner zur Risikoklassifikation von Brustschmerzen in der Notaufnahme. Prognose 30-Tage-MACE-Risiko.",
      fr: "Calculateur HEART pour la stratification du risque de douleur thoracique aux urgences. Prédit le risque MACE à 30 jours.",
      es: "Calculadora HEART para estratificación del riesgo de dolor torácico en urgencias. Predice el riesgo de MACE a 30 días.",
    },
    category: "cardiology",
    categoryI18n: { en: "Cardiology", ru: "Кардиология", ar: "أمراض القلب", tr: "Kardiyoloji", de: "Kardiologie", fr: "Cardiologie", es: "Cardiología" },
    icon: "🏥",
    maxScore: 10,
    reference: "Backus BE et al. Crit Pathw Cardiol. 2010;9:164–170 · Eur Heart J Acute Cardiovasc Care. 2017",
    fields: [
      {
        type: "select", id: "history",
        label: { en: "History", ru: "Анамнез", ar: "التاريخ المرضي", tr: "Anamnez", de: "Anamnese", fr: "Antécédents", es: "Historia clínica" },
        options: [
          { value: 0, label: { en: "Slightly suspicious — non-specific history", ru: "Слабо подозрительно — неспецифический анамнез", ar: "مشبوه بشكل طفيف — تاريخ غير محدد", tr: "Hafif şüpheli — non-spesifik öykü", de: "Leicht verdächtig — unspezifische Anamnese", fr: "Légèrement suspect — anamnèse non spécifique", es: "Ligeramente sospechoso — historia inespecífica" } },
          { value: 1, label: { en: "Moderately suspicious — typical features but not all", ru: "Умеренно подозрительно — типичные, но не все признаки", ar: "مشبوه باعتدال — سمات نموذجية لكن ليس كلها", tr: "Orta derecede şüpheli — tipik özellikler ama hepsi değil", de: "Mäßig verdächtig — typische, aber nicht alle Merkmale", fr: "Modérément suspect — caractéristiques typiques mais incomplètes", es: "Moderadamente sospechoso — características típicas pero no todas" } },
          { value: 2, label: { en: "Highly suspicious — classic ACS features", ru: "Высоко подозрительно — классические признаки ОКС", ar: "مشبوه للغاية — سمات متلازمة الشريان التاجي الكلاسيكية", tr: "Yüksek oranda şüpheli — klasik AKS özellikleri", de: "Hochverdächtig — klassische ACS-Merkmale", fr: "Très suspect — présentation classique de SCA", es: "Muy sospechoso — características clásicas de SCA" } },
        ],
      },
      {
        type: "select", id: "ecg",
        label: { en: "ECG", ru: "ЭКГ", ar: "رسم القلب الكهربائي", tr: "EKG", de: "EKG", fr: "ECG", es: "ECG" },
        options: [
          { value: 0, label: { en: "Normal", ru: "Норма", ar: "طبيعي", tr: "Normal", de: "Normal", fr: "Normal", es: "Normal" } },
          { value: 1, label: { en: "Non-specific repolarization disturbance", ru: "Неспецифические нарушения реполяризации", ar: "اضطراب إعادة الاستقطاب غير المحدد", tr: "Non-spesifik repolarizasyon bozukluğu", de: "Unspezifische Repolarisationsstörung", fr: "Trouble de repolarisation non spécifique", es: "Alteración de repolarización inespecífica" } },
          { value: 2, label: { en: "Significant ST deviation", ru: "Значимое отклонение сегмента ST", ar: "انحراف ST ملحوظ", tr: "Anlamlı ST değişikliği", de: "Signifikante ST-Abweichung", fr: "Déviation ST significative", es: "Desviación ST significativa" } },
        ],
      },
      {
        type: "select", id: "age",
        label: { en: "Age", ru: "Возраст", ar: "العمر", tr: "Yaş", de: "Alter", fr: "Âge", es: "Edad" },
        options: [
          { value: 0, label: { en: "< 45 years", ru: "< 45 лет", ar: "< 45 سنة", tr: "< 45 yaş", de: "< 45 Jahre", fr: "< 45 ans", es: "< 45 años" } },
          { value: 1, label: { en: "45–64 years", ru: "45–64 лет", ar: "45–64 سنة", tr: "45–64 yaş", de: "45–64 Jahre", fr: "45–64 ans", es: "45–64 años" } },
          { value: 2, label: { en: "≥ 65 years", ru: "≥ 65 лет", ar: "≥ 65 سنة", tr: "≥ 65 yaş", de: "≥ 65 Jahre", fr: "≥ 65 ans", es: "≥ 65 años" } },
        ],
      },
      {
        type: "select", id: "risk",
        label: { en: "Risk factors", ru: "Факторы риска", ar: "عوامل الخطر", tr: "Risk faktörleri", de: "Risikofaktoren", fr: "Facteurs de risque", es: "Factores de riesgo" },
        hint: { en: "HTN, hypercholesterolaemia, DM, obesity, smoking, family history, atherosclerosis", ru: "АГ, гиперхолестеринемия, СД, ожирение, курение, семейный анамнез, атеросклероз", ar: "ارتفاع ضغط الدم، فرط كوليسترول الدم، السكري، السمنة، التدخين، التاريخ العائلي، تصلب الشرايين", tr: "HTN, hiperkolesterolemi, DM, obezite, sigara, aile öyküsü, ateroskleroz", de: "Hypertonie, Hypercholesterin, DM, Adipositas, Rauchen, Familienanamnese, Atherosklerose", fr: "HTA, hypercholestérolémie, DM, obésité, tabac, antécédents familiaux, athérosclérose", es: "HTA, hipercolesterolemia, DM, obesidad, tabaco, antecedentes familiares, aterosclerosis" },
        options: [
          { value: 0, label: { en: "No known risk factors", ru: "Нет известных факторов риска", ar: "لا توجد عوامل خطر معروفة", tr: "Bilinen risk faktörü yok", de: "Keine bekannten Risikofaktoren", fr: "Aucun facteur de risque connu", es: "Sin factores de riesgo conocidos" } },
          { value: 1, label: { en: "1–2 risk factors", ru: "1–2 фактора риска", ar: "1–2 عوامل خطر", tr: "1–2 risk faktörü", de: "1–2 Risikofaktoren", fr: "1–2 facteur(s) de risque", es: "1–2 factores de riesgo" } },
          { value: 2, label: { en: "≥3 risk factors, history of atherosclerotic disease, or on aspirin", ru: "≥3 факторов риска, атеросклероз в анамнезе или приём аспирина", ar: "≥3 عوامل خطر، تاريخ مرض تصلب الشرايين، أو تناول الأسبرين", tr: "≥3 risk faktörü, aterosklerotik hastalık öyküsü veya aspirin kullanımı", de: "≥3 Risikofaktoren, Atherosklerose bekannt oder Aspirineinnahme", fr: "≥3 facteurs de risque, ATCD d'athérosclérose ou prise d'aspirine", es: "≥3 factores, antecedentes de enfermedad aterosclerótica o toma de aspirina" } },
        ],
      },
      {
        type: "select", id: "troponin",
        label: { en: "Troponin", ru: "Тропонин", ar: "التروبونين", tr: "Troponin", de: "Troponin", fr: "Troponine", es: "Troponina" },
        options: [
          { value: 0, label: { en: "≤ Normal limit", ru: "≤ Нормальный предел", ar: "≤ الحد الطبيعي", tr: "≤ Normal sınır", de: "≤ Normalgrenze", fr: "≤ Limite normale", es: "≤ Límite normal" } },
          { value: 1, label: { en: "1–3× normal limit", ru: "1–3× нормального предела", ar: "1–3× الحد الطبيعي", tr: "1–3× normal sınır", de: "1–3× Normalgrenze", fr: "1–3× limite normale", es: "1–3× límite normal" } },
          { value: 2, label: { en: "> 3× normal limit", ru: "> 3× нормального предела", ar: "> 3× الحد الطبيعي", tr: "> 3× normal sınır", de: "> 3× Normalgrenze", fr: "> 3× limite normale", es: "> 3× límite normal" } },
        ],
      },
    ],
    risks: [
      {
        minScore: 0, maxScore: 3, level: "low", labelKey: "low_risk", color: "green",
        description: { en: "30-day MACE risk ~1.5%. Low risk.", ru: "Риск MACE за 30 дней ~1,5%. Низкий риск.", ar: "خطر MACE خلال 30 يوماً ~1.5%. مخاطرة منخفضة.", tr: "30 günlük MACE riski ~%1,5. Düşük risk.", de: "30-Tage-MACE-Risiko ~1,5 %. Niedriges Risiko.", fr: "Risque MACE à 30 j ~1,5 %. Risque faible.", es: "Riesgo MACE a 30 días ~1,5 %. Riesgo bajo." },
        recommendation: { en: "Safe for early discharge. Outpatient follow-up.", ru: "Безопасная ранняя выписка. Амбулаторное наблюдение.", ar: "الخروج المبكر آمن. متابعة خارجية.", tr: "Erken taburculuk güvenli. Ayaktan takip.", de: "Frühzeitige Entlassung vertretbar. Ambulante Nachsorge.", fr: "Sortie précoce sûre. Suivi ambulatoire.", es: "Alta precoz segura. Seguimiento ambulatorio." },
      },
      {
        minScore: 4, maxScore: 6, level: "moderate", labelKey: "moderate_risk", color: "amber",
        description: { en: "30-day MACE risk ~12–17%. Moderate risk.", ru: "Риск MACE за 30 дней ~12–17%. Умеренный риск.", ar: "خطر MACE خلال 30 يوماً ~12–17%. مخاطرة متوسطة.", tr: "30 günlük MACE riski ~%12–17. Orta risk.", de: "30-Tage-MACE-Risiko ~12–17 %. Mittleres Risiko.", fr: "Risque MACE à 30 j ~12–17 %. Risque modéré.", es: "Riesgo MACE a 30 días ~12–17 %. Riesgo moderado." },
        recommendation: { en: "Admit for observation. Serial troponins and stress testing.", ru: "Госпитализация для наблюдения. Серийные тропонины и нагрузочный тест.", ar: "الدخول للمراقبة. قياسات التروبونين المتسلسلة واختبار الإجهاد.", tr: "Gözlem için yatış. Seri troponin ve stres testi.", de: "Stationäre Überwachung. Serielle Troponine und Belastungstest.", fr: "Hospitalisation pour surveillance. Troponines sérielles et test d'effort.", es: "Ingreso para observación. Troponinas seriadas y prueba de esfuerzo." },
      },
      {
        minScore: 7, maxScore: 10, level: "high", labelKey: "high_risk", color: "red",
        description: { en: "30-day MACE risk ~50–65%. High risk.", ru: "Риск MACE за 30 дней ~50–65%. Высокий риск.", ar: "خطر MACE خلال 30 يوماً ~50–65%. مخاطرة عالية.", tr: "30 günlük MACE riski ~%50–65. Yüksek risk.", de: "30-Tage-MACE-Risiko ~50–65 %. Hohes Risiko.", fr: "Risque MACE à 30 j ~50–65 %. Risque élevé.", es: "Riesgo MACE a 30 días ~50–65 %. Riesgo alto." },
        recommendation: { en: "Early invasive strategy. Cardiology consult. Consider urgent angiography.", ru: "Ранняя инвазивная тактика. Консультация кардиолога. Рассмотреть срочную ангиографию.", ar: "استراتيجية غازية مبكرة. استشارة طب القلب. النظر في تصوير الأوعية التاجية العاجل.", tr: "Erken invaziv strateji. Kardiyoloji konsültasyonu. Acil anjiyografi düşünün.", de: "Frühe invasive Strategie. Kardiologie-Konsil. Koronarangiographie erwägen.", fr: "Stratégie invasive précoce. Consultation cardiologie. Coronarographie urgente envisagée.", es: "Estrategia invasiva precoz. Consulta a cardiología. Considerar angiografía urgente." },
      },
    ],
  },
];

// ── Lookup helpers ───────────────────────────────────────────────────────────

export function getCalc(slug: string): CalcMeta | undefined {
  return CALCULATORS.find(c => c.slug === slug);
}

export const CALC_SLUGS = ["cha2ds2-vasc", "curb-65", "wells-dvt", "heart-score", "egfr-ckd-epi"] as const;

// ── Index page translations ──────────────────────────────────────────────────

export const INDEX_T: Record<string, T> = {
  hero_title: { en: "Clinical Calculators", ru: "Клинические калькуляторы", ar: "الآلات الحاسبة السريرية", tr: "Klinik Hesap Makineleri", de: "Klinische Rechner", fr: "Calculateurs Cliniques", es: "Calculadores Clínicos" },
  hero_sub: {
    en: "Evidence-based scoring tools used daily by clinicians worldwide. Free, multilingual, no account required.",
    ru: "Доказательные шкалы, которыми врачи пользуются каждый день. Бесплатно, мультиязычно, без регистрации.",
    ar: "أدوات تقييم قائمة على الأدلة يستخدمها الأطباء يومياً حول العالم. مجانية، متعددة اللغات، لا يلزم حساب.",
    tr: "Dünya genelinde klinisyenler tarafından günlük kullanılan kanıta dayalı puanlama araçları. Ücretsiz, çok dilli, hesap gerekmez.",
    de: "Evidenzbasierte Scoring-Tools, die täglich von Klinikern weltweit eingesetzt werden. Kostenlos, mehrsprachig, kein Konto erforderlich.",
    fr: "Outils de scoring validés utilisés quotidiennement par les cliniciens du monde entier. Gratuit, multilingue, sans compte.",
    es: "Herramientas de puntuación basadas en evidencia usadas diariamente por clínicos en todo el mundo. Gratuito, multilingüe, sin cuenta.",
  },
  all_calculators: { en: "All Calculators", ru: "Все калькуляторы", ar: "جميع الآلات الحاسبة", tr: "Tüm Hesap Makineleri", de: "Alle Rechner", fr: "Tous les calculateurs", es: "Todos los calculadores" },
  egfr_name: { en: "eGFR (CKD-EPI 2021)", ru: "рСКФ (CKD-EPI 2021)", ar: "معدل الترشيح الكبيبي التقديري (CKD-EPI 2021)", tr: "eGFR (CKD-EPI 2021)", de: "eGFR (CKD-EPI 2021)", fr: "DFGe (CKD-EPI 2021)", es: "TFGe (CKD-EPI 2021)" },
  egfr_sub: { en: "Kidney function and CKD staging", ru: "Функция почек и стадия ХБП", ar: "وظائف الكلى وتصنيف مرض الكلى المزمن", tr: "Böbrek fonksiyonu ve KBH evrelemesi", de: "Nierenfunktion und CKD-Stadienbestimmung", fr: "Fonction rénale et stadification de l'IRC", es: "Función renal y estadificación de ERC" },
  nephrology: { en: "Nephrology", ru: "Нефрология", ar: "أمراض الكلى", tr: "Nefroloji", de: "Nephrologie", fr: "Néphrologie", es: "Nefrología" },
  open_calculator: { en: "Open calculator →", ru: "Открыть калькулятор →", ar: "فتح الآلة الحاسبة →", tr: "Hesap makinesini aç →", de: "Rechner öffnen →", fr: "Ouvrir le calculateur →", es: "Abrir calculadora →" },
  footer_note: {
    en: "These calculators are for educational purposes only. Clinical decisions must account for the full clinical picture. Always use your professional judgement.",
    ru: "Эти калькуляторы предназначены исключительно в образовательных целях. Клинические решения должны учитывать всю клиническую картину.",
    ar: "هذه الآلات الحاسبة لأغراض تعليمية فقط. يجب أن تأخذ القرارات السريرية في الاعتبار الصورة السريرية الكاملة.",
    tr: "Bu hesap makineleri yalnızca eğitim amaçlıdır. Klinik kararlar tam klinik tabloyu hesaba katmalıdır.",
    de: "Diese Rechner dienen ausschließlich Bildungszwecken. Klinische Entscheidungen müssen das gesamte klinische Bild berücksichtigen.",
    fr: "Ces calculateurs sont à des fins éducatives uniquement. Les décisions cliniques doivent tenir compte de l'ensemble du tableau clinique.",
    es: "Estas calculadoras son solo para fines educativos. Las decisiones clínicas deben tener en cuenta el cuadro clínico completo.",
  },
};
