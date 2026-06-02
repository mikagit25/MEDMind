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

  // ── 5. Glasgow Coma Scale ─────────────────────────────────────────────────
  {
    slug: "gcs",
    name: "Glasgow Coma Scale (GCS)",
    nameI18n: { en: "Glasgow Coma Scale (GCS)", ru: "Шкала комы Глазго (ШКГ)", ar: "مقياس غلاسكو للغيبوبة", tr: "Glasgow Koma Skalası (GKS)", de: "Glasgow Koma Skala (GCS)", fr: "Échelle de Glasgow (GCS)", es: "Escala de Coma de Glasgow (GCS)" },
    subtitle: { en: "Level of consciousness after brain injury", ru: "Уровень сознания после травмы мозга", ar: "مستوى الوعي بعد إصابة الدماغ", tr: "Beyin hasarı sonrası bilinç düzeyi", de: "Bewusstseinslage nach Hirnverletzung", fr: "Niveau de conscience après lésion cérébrale", es: "Nivel de conciencia tras lesión cerebral" },
    seoDescription: { en: "Glasgow Coma Scale calculator. Assess level of consciousness with eye, verbal and motor responses. Severity classification for brain injury.", ru: "Калькулятор шкалы комы Глазго. Оценка уровня сознания по открыванию глаз, речи и движениям.", ar: "آلة حاسبة لمقياس غلاسكو للغيبوبة. تقييم مستوى الوعي.", tr: "Glasgow Koma Skalası hesaplayıcı. Göz, sözel ve motor yanıtlarla bilinç düzeyi değerlendirmesi.", de: "Glasgow-Koma-Skala-Rechner. Bewusstseinsbewertung durch Augen-, Sprach- und Motorikreaktion.", fr: "Calculateur Échelle de Glasgow. Évaluation de la conscience par réponses oculaires, verbales et motrices.", es: "Calculadora Escala de Glasgow. Evaluación de conciencia mediante respuestas ocular, verbal y motora." },
    category: "neurology",
    categoryI18n: { en: "Neurology", ru: "Неврология", ar: "طب الأعصاب", tr: "Nöroloji", de: "Neurologie", fr: "Neurologie", es: "Neurología" },
    icon: "🧠",
    maxScore: 15,
    reference: "Teasdale G, Jennett B. Lancet. 1974;2:81–84 · BMJ. 1978",
    fields: [
      {
        type: "select", id: "eye",
        label: { en: "Eye opening (E)", ru: "Открывание глаз (E)", ar: "فتح العينين (E)", tr: "Göz açma (E)", de: "Augenöffnung (E)", fr: "Ouverture des yeux (E)", es: "Apertura ocular (E)" },
        options: [
          { value: 1, label: { en: "1 — None", ru: "1 — Отсутствует", ar: "1 — لا يوجد", tr: "1 — Yok", de: "1 — Keine", fr: "1 — Absente", es: "1 — Ninguna" } },
          { value: 2, label: { en: "2 — To pain", ru: "2 — На боль", ar: "2 — عند الألم", tr: "2 — Ağrıya", de: "2 — Auf Schmerz", fr: "2 — À la douleur", es: "2 — Al dolor" } },
          { value: 3, label: { en: "3 — To voice", ru: "3 — На голос", ar: "3 — عند الصوت", tr: "3 — Sese", de: "3 — Auf Aufforderung", fr: "3 — À la voix", es: "3 — A la voz" } },
          { value: 4, label: { en: "4 — Spontaneous", ru: "4 — Спонтанное", ar: "4 — تلقائي", tr: "4 — Kendiliğinden", de: "4 — Spontan", fr: "4 — Spontanée", es: "4 — Espontánea" } },
        ],
      },
      {
        type: "select", id: "verbal",
        label: { en: "Verbal response (V)", ru: "Речевая реакция (V)", ar: "الاستجابة اللفظية (V)", tr: "Sözel yanıt (V)", de: "Verbale Reaktion (V)", fr: "Réponse verbale (V)", es: "Respuesta verbal (V)" },
        options: [
          { value: 1, label: { en: "1 — None", ru: "1 — Отсутствует", ar: "1 — لا يوجد", tr: "1 — Yok", de: "1 — Keine", fr: "1 — Absente", es: "1 — Ninguna" } },
          { value: 2, label: { en: "2 — Incomprehensible sounds", ru: "2 — Непонятные звуки", ar: "2 — أصوات غير مفهومة", tr: "2 — Anlaşılmaz sesler", de: "2 — Unverständliche Laute", fr: "2 — Sons incompréhensibles", es: "2 — Sonidos incomprensibles" } },
          { value: 3, label: { en: "3 — Inappropriate words", ru: "3 — Бессвязные слова", ar: "3 — كلمات غير مناسبة", tr: "3 — Uygunsuz kelimeler", de: "3 — Unangemessene Wörter", fr: "3 — Mots inappropriés", es: "3 — Palabras inapropiadas" } },
          { value: 4, label: { en: "4 — Confused", ru: "4 — Спутанность", ar: "4 — مرتبك", tr: "4 — Konfüze", de: "4 — Verwirrt", fr: "4 — Confus", es: "4 — Confuso" } },
          { value: 5, label: { en: "5 — Oriented", ru: "5 — Ориентирован", ar: "5 — موجَّه", tr: "5 — Oryante", de: "5 — Orientiert", fr: "5 — Orienté", es: "5 — Orientado" } },
        ],
      },
      {
        type: "select", id: "motor",
        label: { en: "Motor response (M)", ru: "Двигательная реакция (M)", ar: "الاستجابة الحركية (M)", tr: "Motor yanıt (M)", de: "Motorische Reaktion (M)", fr: "Réponse motrice (M)", es: "Respuesta motora (M)" },
        options: [
          { value: 1, label: { en: "1 — None", ru: "1 — Отсутствует", ar: "1 — لا يوجد", tr: "1 — Yok", de: "1 — Keine", fr: "1 — Absente", es: "1 — Ninguna" } },
          { value: 2, label: { en: "2 — Extension (decerebrate)", ru: "2 — Разгибание (децеребрация)", ar: "2 — امتداد (تصلب مخيخي)", tr: "2 — Ekstansiyon (deserebrasyon)", de: "2 — Strecksynergismen (Dezerebration)", fr: "2 — Extension (décérébration)", es: "2 — Extensión (descerebración)" } },
          { value: 3, label: { en: "3 — Flexion (decorticate)", ru: "3 — Сгибание (декортикация)", ar: "3 — ثني (تقشير القشرة)", tr: "3 — Fleksiyon (dekortikazon)", de: "3 — Beugesynergismen (Dekortikation)", fr: "3 — Flexion (décortication)", es: "3 — Flexión (descorticación)" } },
          { value: 4, label: { en: "4 — Withdrawal", ru: "4 — Отдёргивание", ar: "4 — سحب", tr: "4 — Çekme", de: "4 — Ungezielte Abwehrbewegung", fr: "4 — Retrait", es: "4 — Retirada" } },
          { value: 5, label: { en: "5 — Localizes pain", ru: "5 — Локализует боль", ar: "5 — تحديد الألم", tr: "5 — Ağrıyı lokalize etme", de: "5 — Gezielte Schmerzabwehr", fr: "5 — Localise la douleur", es: "5 — Localiza el dolor" } },
          { value: 6, label: { en: "6 — Obeys commands", ru: "6 — Выполняет команды", ar: "6 — يتبع الأوامر", tr: "6 — Komutlara uyma", de: "6 — Befolgt Aufforderungen", fr: "6 — Obéit aux ordres", es: "6 — Obedece órdenes" } },
        ],
      },
    ],
    risks: [
      { minScore: 3, maxScore: 8, level: "high", labelKey: "high_risk", color: "red",
        description: { en: "Severe brain injury. GCS 3–8.", ru: "Тяжёлая черепно-мозговая травма. ШКГ 3–8.", ar: "إصابة دماغية شديدة. مقياس GCS 3–8.", tr: "Ciddi beyin hasarı. GKS 3–8.", de: "Schweres Schädel-Hirn-Trauma. GCS 3–8.", fr: "Traumatisme crânien grave. GCS 3–8.", es: "Traumatismo craneoencefálico grave. GCS 3–8." },
        recommendation: { en: "Immediate airway management. Neurosurgery consult. CT head urgently. Consider intubation for GCS ≤8.", ru: "Немедленное обеспечение дыхательных путей. Нейрохирург. КТ головы срочно. Интубация при ШКГ ≤8.", ar: "إدارة فورية لمجرى الهواء. استشارة جراحة الأعصاب. CT الرأس بشكل عاجل. النظر في التنبيب لـ GCS ≤8.", tr: "Acil havayolu yönetimi. Nöroşirurji konsültasyonu. Acil baş BT. GCS ≤8 için entübasyon.", de: "Sofortige Atemwegssicherung. Neurochirurgie-Konsil. Dringendes CCT. Intubation bei GCS ≤8.", fr: "Prise en charge immédiate des voies aériennes. Avis neurochirurgical. TDM cérébral urgent. Intubation si GCS ≤8.", es: "Manejo inmediato de la vía aérea. Consulta a neurocirugía. TC craneal urgente. Intubación si GCS ≤8." } },
      { minScore: 9, maxScore: 12, level: "moderate", labelKey: "moderate_risk", color: "amber",
        description: { en: "Moderate brain injury. GCS 9–12.", ru: "Средне-тяжёлая ЧМТ. ШКГ 9–12.", ar: "إصابة دماغية متوسطة. مقياس GCS 9–12.", tr: "Orta dereceli beyin hasarı. GKS 9–12.", de: "Mittelschweres SHT. GCS 9–12.", fr: "Traumatisme crânien modéré. GCS 9–12.", es: "TCE moderado. GCS 9–12." },
        recommendation: { en: "Hospital admission. CT head. Frequent neurological reassessment. Neurosurgery review.", ru: "Госпитализация. КТ головы. Частая неврологическая переоценка. Нейрохирург.", ar: "دخول المستشفى. CT الرأس. إعادة تقييم عصبية متكررة. مراجعة جراحة الأعصاب.", tr: "Hastane yatışı. Baş BT. Sık nörolojik yeniden değerlendirme. Nöroşirurji.", de: "Stationäre Aufnahme. CCT. Engmaschige neurologische Überwachung. Neurochirurgie.", fr: "Hospitalisation. TDM cérébral. Réévaluation neurologique fréquente. Avis neurochirurgical.", es: "Ingreso hospitalario. TC craneal. Reevaluación neurológica frecuente. Revisión neurocirugía." } },
      { minScore: 13, maxScore: 15, level: "low", labelKey: "low_risk", color: "green",
        description: { en: "Mild brain injury. GCS 13–15.", ru: "Лёгкая ЧМТ. ШКГ 13–15.", ar: "إصابة دماغية خفيفة. GCS 13–15.", tr: "Hafif beyin hasarı. GKS 13–15.", de: "Leichtes SHT. GCS 13–15.", fr: "Traumatisme crânien léger. GCS 13–15.", es: "TCE leve. GCS 13–15." },
        recommendation: { en: "CT head per clinical judgment (use NEXUS/Canadian CT Head Rules). Observe. Discharge with clear head injury instructions if CT negative.", ru: "КТ головы по клиническим показаниям. Наблюдение. Выписка с инструкциями при отсутствии патологии на КТ.", ar: "CT الرأس وفق الحكم السريري. المراقبة. الخروج مع تعليمات إصابة الرأس إذا كان CT سلبياً.", tr: "Klinik değerlendirmeye göre baş BT. Gözlem. BT negatifse başağrısı talimatlarıyla taburculuk.", de: "CCT nach klinischem Ermessen. Überwachung. Entlassung mit Verhaltensregeln bei unauffälligem CCT.", fr: "TDM cérébral selon jugement clinique. Surveillance. Sortie avec consignes si TDM négatif.", es: "TC craneal según juicio clínico. Observación. Alta con instrucciones si TC negativo." } },
    ],
  },

  // ── 6. qSOFA ─────────────────────────────────────────────────────────────
  {
    slug: "qsofa",
    name: "qSOFA Score",
    nameI18n: { en: "qSOFA Score", ru: "Шкала qSOFA", ar: "نتيجة qSOFA", tr: "qSOFA Skoru", de: "qSOFA Score", fr: "Score qSOFA", es: "Score qSOFA" },
    subtitle: { en: "Quick sepsis-related organ failure assessment", ru: "Быстрая оценка органной недостаточности при сепсисе", ar: "التقييم السريع لفشل الأعضاء المرتبط بالإنتان", tr: "Hızlı sepsis ilişkili organ yetmezliği değerlendirmesi", de: "Schnelle Sepsis-assoziierte Organversagen-Beurteilung", fr: "Évaluation rapide de la défaillance d'organe liée au sepsis", es: "Evaluación rápida de disfunción orgánica asociada a sepsis" },
    seoDescription: { en: "qSOFA calculator for sepsis screening outside the ICU. Identifies patients at risk of poor outcomes from suspected infection.", ru: "Калькулятор qSOFA для скрининга сепсиса вне ОРИТ.", ar: "آلة حاسبة qSOFA لفحص الإنتان خارج وحدة العناية المركزة.", tr: "YBÜ dışında sepsis taraması için qSOFA hesaplayıcı.", de: "qSOFA-Rechner zur Sepsis-Früherkennung außerhalb der Intensivstation.", fr: "Calculateur qSOFA pour le dépistage du sepsis hors réanimation.", es: "Calculadora qSOFA para cribado de sepsis fuera de UCI." },
    category: "critical care",
    categoryI18n: { en: "Critical Care", ru: "Интенсивная терапия", ar: "الرعاية الحرجة", tr: "Yoğun Bakım", de: "Intensivmedizin", fr: "Soins intensifs", es: "Cuidados críticos" },
    icon: "🔴",
    maxScore: 3,
    reference: "Seymour CW et al. JAMA. 2016;315:762–774 · Surviving Sepsis Campaign",
    note: { en: "qSOFA is a screening tool — a positive screen (≥2) should prompt full SOFA assessment, lactate and blood cultures.", ru: "qSOFA — инструмент скрининга. Положительный (≥2) требует полного SOFA, лактата и гемокультур.", ar: "qSOFA أداة فحص — النتيجة الإيجابية (≥2) تستدعي تقييم SOFA الكامل، اللاكتات وزراعات الدم.", tr: "qSOFA bir tarama aracıdır — pozitif sonuç (≥2) tam SOFA değerlendirmesi, laktat ve kan kültürlerini gerektirir.", de: "qSOFA ist ein Screening-Instrument — positives Ergebnis (≥2) erfordert vollständiges SOFA, Laktat und Blutkulturen.", fr: "qSOFA est un outil de dépistage — résultat positif (≥2) → évaluation SOFA complète, lactate et hémocultures.", es: "qSOFA es herramienta de cribado — positivo (≥2) requiere SOFA completo, lactato y hemocultivos." },
    fields: [
      { type: "checkbox", points: 1, label: { en: "Respiratory rate ≥ 22 breaths/min", ru: "ЧД ≥ 22/мин", ar: "معدل التنفس ≥ 22 نفساً في الدقيقة", tr: "Solunum hızı ≥ 22/dak", de: "Atemfrequenz ≥ 22/min", fr: "Fréquence respiratoire ≥ 22/min", es: "FR ≥ 22 resp/min" } },
      { type: "checkbox", points: 1, label: { en: "Altered mentation (GCS < 15)", ru: "Нарушение сознания (ШКГ < 15)", ar: "اضطراب في التفكير (GCS < 15)", tr: "Mental durum değişikliği (GKS < 15)", de: "Bewusstseinsveränderung (GCS < 15)", fr: "Altération de la conscience (GCS < 15)", es: "Alteración del estado mental (GCS < 15)" } },
      { type: "checkbox", points: 1, label: { en: "Systolic BP ≤ 100 mmHg", ru: "Систол. АД ≤ 100 мм рт.ст.", ar: "ضغط الدم الانقباضي ≤ 100 ملم زئبق", tr: "Sistolik KB ≤ 100 mmHg", de: "Systolischer RR ≤ 100 mmHg", fr: "PAS ≤ 100 mmHg", es: "PAS ≤ 100 mmHg" } },
    ],
    risks: [
      { minScore: 0, maxScore: 1, level: "low", labelKey: "low_risk", color: "green",
        description: { en: "Low risk. qSOFA < 2.", ru: "Низкий риск. qSOFA < 2.", ar: "خطر منخفض. qSOFA < 2.", tr: "Düşük risk. qSOFA < 2.", de: "Geringes Risiko. qSOFA < 2.", fr: "Risque faible. qSOFA < 2.", es: "Riesgo bajo. qSOFA < 2." },
        recommendation: { en: "Continue monitoring. Reassess if clinical status changes.", ru: "Продолжать наблюдение. Переоценить при изменении состояния.", ar: "متابعة المراقبة. إعادة التقييم إذا تغيرت الحالة السريرية.", tr: "İzlemeye devam edin. Klinik durum değişirse yeniden değerlendirin.", de: "Überwachung fortsetzen. Neu beurteilen bei Zustandsänderung.", fr: "Poursuivre la surveillance. Réévaluer si l'état clinique change.", es: "Continuar monitorización. Reevaluar si cambia el estado clínico." } },
      { minScore: 2, maxScore: 3, level: "high", labelKey: "high_risk", color: "red",
        description: { en: "High risk of poor outcomes. Suspected sepsis.", ru: "Высокий риск неблагоприятного исхода. Подозрение на сепсис.", ar: "خطر مرتفع من نتائج سلبية. الاشتباه بالإنتان.", tr: "Kötü sonuç riski yüksek. Sepsis şüphesi.", de: "Hohes Risiko für schlechte Outcome. Sepsisverdacht.", fr: "Risque élevé de mauvais pronostic. Sepsis suspecté.", es: "Alto riesgo de mal pronóstico. Sospecha de sepsis." },
        recommendation: { en: "Urgent full assessment: blood cultures, lactate, CBC, CMP. IV access and fluids. Senior review. Consider ICU.", ru: "Срочная полная оценка: гемокультуры, лактат, ОАК, БМП. Венозный доступ. ОРИТ.", ar: "تقييم كامل عاجل: زراعات الدم، اللاكتات، تعداد الدم. وصول وريدي وسوائل. مراجعة أولوية. النظر في العناية المركزة.", tr: "Acil tam değerlendirme: kan kültürleri, laktat, tam kan sayımı. İV erişim ve sıvı. YBÜ değerlendirmesi.", de: "Dringende Volluntersuchung: Blutkulturen, Laktat, BB, BMP. IV-Zugang. Intensivstation erwägen.", fr: "Bilan complet urgent: hémocultures, lactate, NFS, bilan métabolique. Accès veineux. Évaluer réanimation.", es: "Evaluación completa urgente: hemocultivos, lactato, hemograma. Acceso IV y fluidos. Valorar UCI." } },
    ],
  },

  // ── 7. HAS-BLED ───────────────────────────────────────────────────────────
  {
    slug: "has-bled",
    name: "HAS-BLED Score",
    nameI18n: { en: "HAS-BLED Score", ru: "Шкала HAS-BLED", ar: "نتيجة HAS-BLED", tr: "HAS-BLED Skoru", de: "HAS-BLED Score", fr: "Score HAS-BLED", es: "Score HAS-BLED" },
    subtitle: { en: "Bleeding risk on anticoagulation in atrial fibrillation", ru: "Риск кровотечения на антикоагуляции при ФП", ar: "خطر النزيف مع مضادات التخثر في الرجفان الأذيني", tr: "Atriyal fibrilasyonda antikoagülasyonda kanama riski", de: "Blutungsrisiko unter Antikoagulation bei Vorhofflimmern", fr: "Risque hémorragique sous anticoagulants dans la fibrillation auriculaire", es: "Riesgo hemorrágico con anticoagulación en fibrilación auricular" },
    seoDescription: { en: "HAS-BLED calculator for bleeding risk on anticoagulation in AFib. Use alongside CHA₂DS₂-VASc to guide anticoagulation decisions.", ru: "Калькулятор HAS-BLED для оценки риска кровотечения при антикоагуляции в контексте ФП.", ar: "آلة حاسبة HAS-BLED لتقييم خطر النزيف مع مضادات التخثر في الرجفان الأذيني.", tr: "Atriyal fibrilasyonda antikoagülasyon kanama riski için HAS-BLED hesaplayıcı.", de: "HAS-BLED-Rechner für Blutungsrisiko unter Antikoagulation bei Vorhofflimmern.", fr: "Calculateur HAS-BLED pour le risque hémorragique sous anticoagulants en FA.", es: "Calculadora HAS-BLED para riesgo hemorrágico con anticoagulación en FA." },
    category: "cardiology",
    categoryI18n: { en: "Cardiology", ru: "Кардиология", ar: "أمراض القلب", tr: "Kardiyoloji", de: "Kardiologie", fr: "Cardiologie", es: "Cardiología" },
    icon: "💊",
    maxScore: 9,
    reference: "Pisters R et al. Chest. 2010;138:1093–1100 · ESC Guidelines 2020",
    relatedSlug: "atrial-fibrillation",
    relatedLabelI18n: { en: "Use with CHA₂DS₂-VASc →", ru: "Использовать вместе с CHA₂DS₂-VASc →", ar: "استخدم مع CHA₂DS₂-VASc →", tr: "CHA₂DS₂-VASc ile birlikte kullanın →", de: "Zusammen mit CHA₂DS₂-VASc →", fr: "Utiliser avec CHA₂DS₂-VASc →", es: "Usar junto con CHA₂DS₂-VASc →" },
    note: { en: "A high HAS-BLED score should prompt correction of modifiable risk factors — not necessarily avoidance of anticoagulation.", ru: "Высокий HAS-BLED требует коррекции управляемых факторов, но не обязательно отмены антикоагуляции.", ar: "نتيجة HAS-BLED المرتفعة تستدعي تصحيح عوامل الخطر القابلة للتعديل، وليس بالضرورة تجنب مضادات التخثر.", tr: "Yüksek HAS-BLED skoru, değiştirilebilir risk faktörlerinin düzeltilmesini gerektirir — antikoagülasyondan kaçınmak değil.", de: "Ein hoher HAS-BLED-Score sollte zur Korrektur beeinflussbarer Risikofaktoren führen — nicht zur Ablehnung der Antikoagulation.", fr: "Un score HAS-BLED élevé doit conduire à corriger les facteurs de risque modifiables — pas nécessairement à éviter l'anticoagulation.", es: "Una puntuación HAS-BLED alta debe llevar a corregir factores de riesgo modificables, no necesariamente a evitar la anticoagulación." },
    fields: [
      { type: "checkbox", points: 1, label: { en: "Hypertension (uncontrolled, SBP > 160 mmHg)", ru: "АГ (неконтролируемая, систол. > 160 мм рт.ст.)", ar: "ارتفاع ضغط الدم غير المسيطر عليه (SBP > 160 ملم زئبق)", tr: "Hipertansiyon (kontrolsüz, SKB > 160 mmHg)", de: "Hypertonie (unkontrolliert, RR > 160 mmHg)", fr: "Hypertension (non contrôlée, PAS > 160 mmHg)", es: "Hipertensión no controlada (PAS > 160 mmHg)" } },
      { type: "checkbox", points: 1, label: { en: "Abnormal renal function (dialysis, transplant, or creatinine > 200 μmol/L)", ru: "Нарушение функции почек (диализ, трансплантат, или креатинин > 200 мкмоль/л)", ar: "خلل وظائف الكلى (غسيل كلوي، زرع، أو كرياتينين > 200 ميكرومول/لتر)", tr: "Anormal böbrek fonksiyonu (diyaliz, transplant veya kreatinin > 200 μmol/L)", de: "Abnorme Nierenfunktion (Dialyse, Transplantation oder Kreatinin > 200 μmol/l)", fr: "Dysfonction rénale (dialyse, greffe ou créatinine > 200 μmol/L)", es: "Disfunción renal (diálisis, trasplante o creatinina > 200 μmol/L)" } },
      { type: "checkbox", points: 1, label: { en: "Abnormal liver function (cirrhosis, or bilirubin > 2× + AST/ALT/ALP > 3×)", ru: "Нарушение функции печени (цирроз, или билирубин > 2× + АСТ/АЛТ/ЩФ > 3×)", ar: "خلل وظائف الكبد (تشمع أو بيليروبين > 2× + AST/ALT/ALP > 3×)", tr: "Anormal karaciğer fonksiyonu (siroz veya bilirubin > 2× + AST/ALT/ALP > 3×)", de: "Abnorme Leberfunktion (Zirrhose oder Bilirubin > 2× + AST/ALT/ALP > 3×)", fr: "Dysfonction hépatique (cirrhose ou bilirubine > 2× + ASAT/ALAT/PAL > 3×)", es: "Disfunción hepática (cirrosis o bilirrubina > 2× + AST/ALT/ALP > 3×)" } },
      { type: "checkbox", points: 1, label: { en: "Stroke history", ru: "Инсульт в анамнезе", ar: "تاريخ السكتة الدماغية", tr: "İnme öyküsü", de: "Schlaganfall in der Vorgeschichte", fr: "Antécédent d'AVC", es: "Antecedente de ictus" } },
      { type: "checkbox", points: 1, label: { en: "Bleeding history or predisposition (anaemia, bleeding diathesis)", ru: "Кровотечение в анамнезе или предрасположенность (анемия, диатез)", ar: "تاريخ النزيف أو الاستعداد له (فقر الدم، نزعة النزيف)", tr: "Kanama öyküsü veya yatkınlığı (anemi, kanama diyatezi)", de: "Blutungsanamnese oder -prädisposition (Anämie, hämorrhagische Diathese)", fr: "Antécédent de saignement ou prédisposition (anémie, diathèse hémorragique)", es: "Antecedente de sangrado o predisposición (anemia, diátesis hemorrágica)" } },
      { type: "checkbox", points: 1, label: { en: "Labile INR (TTR < 60% of time in therapeutic range)", ru: "Нестабильный МНО (ВТД < 60%)", ar: "INR غير مستقر (TTR < 60%)", tr: "Labil INR (TTR < %60)", de: "Labiler INR (TTR < 60 %)", fr: "INR labile (TTR < 60 %)", es: "INR lábil (TTR < 60%)" } },
      { type: "checkbox", points: 1, label: { en: "Elderly (age > 65 years)", ru: "Пожилой возраст (> 65 лет)", ar: "كبير السن (> 65 سنة)", tr: "Yaşlı (> 65 yaş)", de: "Hohes Alter (> 65 Jahre)", fr: "Âge avancé (> 65 ans)", es: "Edad avanzada (> 65 años)" } },
      { type: "checkbox", points: 1, label: { en: "Drugs (antiplatelet agents or NSAIDs)", ru: "Препараты (антиагреганты или НПВС)", ar: "أدوية (عوامل مضادة للصفيحات أو NSAIDs)", tr: "İlaçlar (antiplatelet veya NSAİİ)", de: "Medikamente (Thrombozytenaggregationshemmer oder NSAR)", fr: "Médicaments (antiagrégants ou AINS)", es: "Fármacos (antiagregantes o AINE)" } },
      { type: "checkbox", points: 1, label: { en: "Alcohol use (≥ 8 drinks/week)", ru: "Алкоголь (≥ 8 доз в неделю)", ar: "استخدام الكحول (≥ 8 مشروبات/أسبوع)", tr: "Alkol kullanımı (≥ 8 içecek/hafta)", de: "Alkohol (≥ 8 Getränke/Woche)", fr: "Consommation d'alcool (≥ 8 verres/semaine)", es: "Alcohol (≥ 8 bebidas/semana)" } },
    ],
    risks: [
      { minScore: 0, maxScore: 1, level: "low", labelKey: "low_risk", color: "green",
        description: { en: "Low bleeding risk (~1% annual risk of major bleeding).", ru: "Низкий риск кровотечения (~1% годовой риск большого кровотечения).", ar: "خطر نزيف منخفض (~1% خطر سنوي لنزيف كبير).", tr: "Düşük kanama riski (~%1 yıllık majör kanama riski).", de: "Geringes Blutungsrisiko (~1 % jährliches Risiko für schwere Blutung).", fr: "Faible risque hémorragique (~1 % de risque annuel de saignement majeur).", es: "Riesgo hemorrágico bajo (~1% riesgo anual de sangrado mayor)." },
        recommendation: { en: "Anticoagulation generally appropriate. Review annually.", ru: "Антикоагуляция, как правило, оправдана. Ежегодный пересмотр.", ar: "مضادات التخثر مناسبة عموماً. مراجعة سنوية.", tr: "Antikoagülasyon genellikle uygundur. Yıllık gözden geçirme.", de: "Antikoagulation im Allgemeinen angemessen. Jährliche Überprüfung.", fr: "Anticoagulation généralement appropriée. Réévaluation annuelle.", es: "Anticoagulación generalmente apropiada. Revisión anual." } },
      { minScore: 2, maxScore: 2, level: "moderate", labelKey: "moderate_risk", color: "amber",
        description: { en: "Moderate bleeding risk (~2% annual risk).", ru: "Умеренный риск кровотечения (~2% годовой риск).", ar: "خطر نزيف متوسط (~2% خطر سنوي).", tr: "Orta kanama riski (~%2 yıllık risk).", de: "Mäßiges Blutungsrisiko (~2 % jährliches Risiko).", fr: "Risque hémorragique modéré (~2 % annuel).", es: "Riesgo hemorrágico moderado (~2% anual)." },
        recommendation: { en: "Weigh bleeding vs thrombotic risk. Correct modifiable factors. Monitor closely on anticoagulation.", ru: "Сопоставить риски кровотечения и тромбоза. Устранить управляемые факторы.", ar: "الموازنة بين خطر النزيف والتخثر. تصحيح العوامل القابلة للتعديل.", tr: "Kanama ve trombotik riski dengeleyin. Değiştirilebilir faktörleri düzeltin.", de: "Blutungs- vs. Thromboserisiko abwägen. Beeinflussbare Faktoren korrigieren.", fr: "Peser le risque hémorragique vs thrombotique. Corriger les facteurs modifiables.", es: "Equilibrar riesgo hemorrágico vs trombótico. Corregir factores modificables." } },
      { minScore: 3, maxScore: 9, level: "high", labelKey: "high_risk", color: "red",
        description: { en: "High bleeding risk (≥3% annual risk of major bleeding).", ru: "Высокий риск кровотечения (≥3% годового риска большого кровотечения).", ar: "خطر نزيف مرتفع (≥3% خطر سنوي لنزيف كبير).", tr: "Yüksek kanama riski (≥%3 yıllık majör kanama riski).", de: "Hohes Blutungsrisiko (≥ 3 % jährliches Risiko für schwere Blutung).", fr: "Risque hémorragique élevé (≥ 3 % annuel).", es: "Riesgo hemorrágico alto (≥3% anual de sangrado mayor)." },
        recommendation: { en: "Identify and correct all modifiable risk factors before initiating/continuing anticoagulation. Regular follow-up.", ru: "Выявить и устранить все управляемые факторы. Регулярное наблюдение.", ar: "تحديد وتصحيح جميع عوامل الخطر القابلة للتعديل قبل البدء/الاستمرار في مضادات التخثر.", tr: "Antikoagülasyona başlamadan/sürdürmeden önce tüm değiştirilebilir risk faktörlerini tespit edin ve düzeltin.", de: "Alle beeinflussbaren Risikofaktoren identifizieren und korrigieren vor Beginn/Fortführung der Antikoagulation.", fr: "Identifier et corriger tous les facteurs modifiables avant d'initier/poursuivre l'anticoagulation.", es: "Identificar y corregir todos los factores modificables antes de iniciar/continuar anticoagulación." } },
    ],
  },

  // ── 8. ABCD² Score ────────────────────────────────────────────────────────
  {
    slug: "abcd2",
    name: "ABCD² Score",
    nameI18n: { en: "ABCD² Score (TIA)", ru: "Шкала ABCD² (ТИА)", ar: "نتيجة ABCD² (النوبة الإقفارية العابرة)", tr: "ABCD² Skoru (TİA)", de: "ABCD²-Score (TIA)", fr: "Score ABCD² (AIT)", es: "Score ABCD² (AIT)" },
    subtitle: { en: "Short-term stroke risk after TIA", ru: "Краткосрочный риск инсульта после ТИА", ar: "خطر السكتة الدماغية قصير الأمد بعد النوبة الإقفارية العابرة", tr: "TİA sonrası kısa vadeli inme riski", de: "Kurzfristiges Schlaganfallrisiko nach TIA", fr: "Risque d'AVC à court terme après AIT", es: "Riesgo de ictus a corto plazo tras AIT" },
    seoDescription: { en: "ABCD² calculator for stroke risk after TIA. Guides urgent workup and admission decisions. 2-day and 7-day stroke risk stratification.", ru: "Калькулятор ABCD² для риска инсульта после ТИА. Помогает принять решение о госпитализации.", ar: "آلة حاسبة ABCD² لخطر السكتة الدماغية بعد النوبة الإقفارية العابرة.", tr: "TİA sonrası inme riski için ABCD² hesaplayıcı.", de: "ABCD²-Rechner für Schlaganfallrisiko nach TIA. Entscheidungshilfe für Notfallabklärung.", fr: "Calculateur ABCD² pour le risque d'AVC après AIT.", es: "Calculadora ABCD² para riesgo de ictus tras AIT." },
    category: "neurology",
    categoryI18n: { en: "Neurology", ru: "Неврология", ar: "طب الأعصاب", tr: "Nöroloji", de: "Neurologie", fr: "Neurologie", es: "Neurología" },
    icon: "🫀",
    maxScore: 7,
    reference: "Johnston SC et al. Lancet. 2007;369:283–292",
    fields: [
      { type: "checkbox", points: 1, label: { en: "Age ≥ 60 years", ru: "Возраст ≥ 60 лет", ar: "العمر ≥ 60 سنة", tr: "Yaş ≥ 60", de: "Alter ≥ 60 Jahre", fr: "Âge ≥ 60 ans", es: "Edad ≥ 60 años" } },
      { type: "checkbox", points: 1, label: { en: "Blood pressure ≥ 140/90 mmHg at presentation", ru: "АД ≥ 140/90 мм рт.ст. при поступлении", ar: "ضغط الدم ≥ 140/90 ملم زئبق عند التقديم", tr: "Başvuruda KB ≥ 140/90 mmHg", de: "Blutdruck ≥ 140/90 mmHg bei Aufnahme", fr: "PA ≥ 140/90 mmHg à la présentation", es: "PA ≥ 140/90 mmHg en la presentación" } },
      {
        type: "select", id: "clinical",
        label: { en: "Clinical features", ru: "Клинические признаки", ar: "المظاهر السريرية", tr: "Klinik özellikler", de: "Klinische Merkmale", fr: "Caractéristiques cliniques", es: "Características clínicas" },
        options: [
          { value: 0, label: { en: "0 — Other symptoms", ru: "0 — Другие симптомы", ar: "0 — أعراض أخرى", tr: "0 — Diğer semptomlar", de: "0 — Andere Symptome", fr: "0 — Autres symptômes", es: "0 — Otros síntomas" } },
          { value: 1, label: { en: "1 — Speech disturbance without weakness", ru: "1 — Нарушение речи без слабости", ar: "1 — اضطراب الكلام دون ضعف", tr: "1 — Güçsüzlük olmaksızın konuşma bozukluğu", de: "1 — Sprachstörung ohne Lähmung", fr: "1 — Trouble de la parole sans déficit moteur", es: "1 — Alteración del habla sin debilidad" } },
          { value: 2, label: { en: "2 — Unilateral weakness", ru: "2 — Односторонняя слабость", ar: "2 — ضعف من جانب واحد", tr: "2 — Unilateral güçsüzlük", de: "2 — Unilaterale Schwäche", fr: "2 — Déficit moteur unilatéral", es: "2 — Debilidad unilateral" } },
        ],
      },
      {
        type: "select", id: "duration",
        label: { en: "Duration of TIA symptoms", ru: "Длительность симптомов ТИА", ar: "مدة أعراض النوبة الإقفارية العابرة", tr: "TİA semptomlarının süresi", de: "Dauer der TIA-Symptome", fr: "Durée des symptômes de l'AIT", es: "Duración de los síntomas del AIT" },
        options: [
          { value: 0, label: { en: "0 — < 10 minutes", ru: "0 — < 10 минут", ar: "0 — < 10 دقائق", tr: "0 — < 10 dakika", de: "0 — < 10 Minuten", fr: "0 — < 10 minutes", es: "0 — < 10 minutos" } },
          { value: 1, label: { en: "1 — 10–59 minutes", ru: "1 — 10–59 минут", ar: "1 — 10–59 دقيقة", tr: "1 — 10–59 dakika", de: "1 — 10–59 Minuten", fr: "1 — 10–59 minutes", es: "1 — 10–59 minutos" } },
          { value: 2, label: { en: "2 — ≥ 60 minutes", ru: "2 — ≥ 60 минут", ar: "2 — ≥ 60 دقيقة", tr: "2 — ≥ 60 dakika", de: "2 — ≥ 60 Minuten", fr: "2 — ≥ 60 minutes", es: "2 — ≥ 60 minutos" } },
        ],
      },
      { type: "checkbox", points: 1, label: { en: "Diabetes mellitus", ru: "Сахарный диабет", ar: "داء السكري", tr: "Diabetes mellitus", de: "Diabetes mellitus", fr: "Diabète sucré", es: "Diabetes mellitus" } },
    ],
    risks: [
      { minScore: 0, maxScore: 3, level: "low", labelKey: "low_risk", color: "green",
        description: { en: "Low risk. 2-day stroke risk ~1%, 7-day ~1.2%.", ru: "Низкий риск. Риск инсульта за 2 дня ~1%, за 7 дней ~1,2%.", ar: "خطر منخفض. خطر السكتة الدماغية خلال يومين ~1%، خلال 7 أيام ~1.2%.", tr: "Düşük risk. 2 günlük inme riski ~%1, 7 günlük ~%1,2.", de: "Geringes Risiko. 2-Tage-Schlaganfallrisiko ~1 %, 7-Tage ~1,2 %.", fr: "Risque faible. Risque d'AVC à 2 j ~1 %, à 7 j ~1,2 %.", es: "Riesgo bajo. Riesgo de ictus a 2 días ~1%, a 7 días ~1,2%." },
        recommendation: { en: "Urgent outpatient TIA clinic (within 24 h). Start antiplatelet therapy. Vascular imaging and ECG.", ru: "Срочный амбулаторный прием (в течение 24 ч). Антиагрегантная терапия. Сосудистая визуализация и ЭКГ.", ar: "عيادة TIA خارجية عاجلة (خلال 24 ساعة). بدء العلاج المضاد للصفيحات. تصوير الأوعية وتخطيط القلب.", tr: "Acil ayaktan TİA kliniği (24 saat içinde). Antiplatelet tedaviyi başlayın. Vasküler görüntüleme ve EKG.", de: "Dringende TIA-Ambulanz (innerhalb 24 h). Thrombozytenaggregationshemmung. Gefäßdiagnostik und EKG.", fr: "Consultation AIT urgente (dans 24 h). Antiagrégants. Imagerie vasculaire et ECG.", es: "Clínica AIT urgente (en 24 h). Antiagregante. Imagen vascular y ECG." } },
      { minScore: 4, maxScore: 5, level: "moderate", labelKey: "moderate_risk", color: "amber",
        description: { en: "Moderate risk. 2-day stroke risk ~4%, 7-day ~3.1%.", ru: "Умеренный риск. Риск инсульта за 2 дня ~4%, за 7 дней ~3,1%.", ar: "خطر متوسط. خطر السكتة الدماغية خلال يومين ~4%، خلال 7 أيام ~3.1%.", tr: "Orta risk. 2 günlük inme riski ~%4, 7 günlük ~%3,1.", de: "Mäßiges Risiko. 2-Tage-Schlaganfallrisiko ~4 %, 7-Tage ~3,1 %.", fr: "Risque modéré. Risque d'AVC à 2 j ~4 %, à 7 j ~3,1 %.", es: "Riesgo moderado. Riesgo de ictus a 2 días ~4%, a 7 días ~3,1%." },
        recommendation: { en: "Consider hospital admission or same-day specialist evaluation. Urgent imaging (CT/MRI brain, carotid US). Dual antiplatelet if no contraindication.", ru: "Рассмотреть госпитализацию или срочную консультацию специалиста. Срочная визуализация. Двойная антиагрегантная терапия.", ar: "النظر في دخول المستشفى أو تقييم متخصص في نفس اليوم. تصوير عاجل. ثنائي مضادات الصفيحات.", tr: "Hastane yatışı veya aynı gün uzman değerlendirmesi düşünün. Acil görüntüleme. Çift antiplatelet.", de: "Krankenhausaufnahme oder sofortige Facharztvorstellung erwägen. Dringende Bildgebung. Duale Thrombozytenaggregationshemmung.", fr: "Envisager une hospitalisation ou évaluation spécialisée le jour même. Imagerie urgente. Double antiagréation.", es: "Considerar ingreso u evaluación especializada el mismo día. Imagen urgente. Doble antiagregación." } },
      { minScore: 6, maxScore: 7, level: "high", labelKey: "high_risk", color: "red",
        description: { en: "High risk. 2-day stroke risk ~8%, 7-day ~9.8%.", ru: "Высокий риск. Риск инсульта за 2 дня ~8%, за 7 дней ~9,8%.", ar: "خطر مرتفع. خطر السكتة الدماغية خلال يومين ~8%، خلال 7 أيام ~9.8%.", tr: "Yüksek risk. 2 günlük inme riski ~%8, 7 günlük ~%9,8.", de: "Hohes Risiko. 2-Tage-Schlaganfallrisiko ~8 %, 7-Tage ~9,8 %.", fr: "Risque élevé. Risque d'AVC à 2 j ~8 %, à 7 j ~9,8 %.", es: "Riesgo alto. Riesgo de ictus a 2 días ~8%, a 7 días ~9,8%." },
        recommendation: { en: "Admit to hospital. Urgent brain imaging (MRI preferred). ECG monitoring. Early neurology/stroke team review.", ru: "Госпитализация. Срочная визуализация мозга (МРТ предпочтительно). Мониторинг ЭКГ. Ранняя консультация невролога/инсультной бригады.", ar: "دخول المستشفى. تصوير الدماغ العاجل (MRI مفضل). مراقبة تخطيط القلب. مراجعة مبكرة من طبيب الأعصاب/فريق السكتة.", tr: "Hastane yatışı. Acil beyin görüntülemesi (MRI tercih edilir). EKG monitörizasyonu. Erken nöroloji/inme ekibi değerlendirmesi.", de: "Stationäre Aufnahme. Dringende Hirnbildgebung (MRT bevorzugt). EKG-Monitoring. Frühzeitiges Neurologie-/Stroke-Unit-Konsil.", fr: "Hospitalisation. Imagerie cérébrale urgente (IRM préférée). Monitoring ECG. Évaluation précoce neurologie/unité AVC.", es: "Ingreso hospitalario. Imagen cerebral urgente (MRI preferida). Monitorización ECG. Revisión precoz neurología/unidad ictus." } },
    ],
  },

  // ── 9. Child-Pugh Score ───────────────────────────────────────────────────
  {
    slug: "child-pugh",
    name: "Child-Pugh Score",
    nameI18n: { en: "Child-Pugh Score", ru: "Шкала Чайлд–Пью", ar: "نتيجة Child-Pugh", tr: "Child-Pugh Skoru", de: "Child-Pugh Score", fr: "Score de Child-Pugh", es: "Score de Child-Pugh" },
    subtitle: { en: "Severity of liver cirrhosis and surgical risk", ru: "Тяжесть цирроза печени и хирургический риск", ar: "شدة تشمع الكبد وخطر الجراحة", tr: "Karaciğer sirozu şiddeti ve cerrahi risk", de: "Schweregrad der Leberzirrhose und Operationsrisiko", fr: "Sévérité de la cirrhose hépatique et risque chirurgical", es: "Gravedad de la cirrosis hepática y riesgo quirúrgico" },
    seoDescription: { en: "Child-Pugh calculator for liver cirrhosis severity. Classifies into Class A, B, C with prognosis and surgical risk.", ru: "Калькулятор Чайлд-Пью для оценки тяжести цирроза печени. Классы A, B, C с прогнозом и хирургическим риском.", ar: "آلة حاسبة Child-Pugh لشدة تشمع الكبد. يصنف إلى فئة A وB وC مع التشخيص وخطر الجراحة.", tr: "Karaciğer siroz şiddeti için Child-Pugh hesaplayıcı. A, B, C sınıflarını prognoz ve cerrahi riskle sınıflandırır.", de: "Child-Pugh-Rechner für den Schweregrad der Leberzirrhose. Klassifizierung A, B, C mit Prognose und OP-Risiko.", fr: "Calculateur Child-Pugh pour la sévérité de la cirrhose. Classification en classe A, B, C avec pronostic et risque chirurgical.", es: "Calculadora Child-Pugh para severidad de cirrosis hepática. Clasifica en A, B, C con pronóstico y riesgo quirúrgico." },
    category: "hepatology",
    categoryI18n: { en: "Hepatology", ru: "Гепатология", ar: "أمراض الكبد", tr: "Hepatoloji", de: "Hepatologie", fr: "Hépatologie", es: "Hepatología" },
    icon: "🫀",
    maxScore: 15,
    reference: "Child CG, Turcotte JG. Surgery. 1964 · Pugh RN et al. Br J Surg. 1973;60:646",
    fields: [
      {
        type: "select", id: "encephalopathy",
        label: { en: "Hepatic encephalopathy", ru: "Печёночная энцефалопатия", ar: "الاعتلال الدماغي الكبدي", tr: "Hepatik ensefalopati", de: "Hepatische Enzephalopathie", fr: "Encéphalopathie hépatique", es: "Encefalopatía hepática" },
        options: [
          { value: 1, label: { en: "1 — None", ru: "1 — Отсутствует", ar: "1 — لا يوجد", tr: "1 — Yok", de: "1 — Keine", fr: "1 — Absente", es: "1 — Ninguna" } },
          { value: 2, label: { en: "2 — Grade I–II (mild, controlled)", ru: "2 — Степень I–II (лёгкая, контролируемая)", ar: "2 — الدرجة I–II (خفيف، مُتحكَّم فيه)", tr: "2 — Grade I–II (hafif, kontrollü)", de: "2 — Grad I–II (leicht, behandelbar)", fr: "2 — Grade I–II (légère, contrôlée)", es: "2 — Grado I–II (leve, controlada)" } },
          { value: 3, label: { en: "3 — Grade III–IV (severe, refractory)", ru: "3 — Степень III–IV (тяжёлая, рефрактерная)", ar: "3 — الدرجة III–IV (شديد، مقاوم للعلاج)", tr: "3 — Grade III–IV (ciddi, refrakter)", de: "3 — Grad III–IV (schwer, therapierefraktär)", fr: "3 — Grade III–IV (sévère, réfractaire)", es: "3 — Grado III–IV (grave, refractaria)" } },
        ],
      },
      {
        type: "select", id: "ascites",
        label: { en: "Ascites", ru: "Асцит", ar: "استسقاء البطن", tr: "Asit", de: "Aszites", fr: "Ascite", es: "Ascitis" },
        options: [
          { value: 1, label: { en: "1 — Absent", ru: "1 — Отсутствует", ar: "1 — غائب", tr: "1 — Yok", de: "1 — Kein", fr: "1 — Absente", es: "1 — Ausente" } },
          { value: 2, label: { en: "2 — Mild (diuretic-responsive)", ru: "2 — Лёгкий (поддаётся диуретикам)", ar: "2 — خفيف (يستجيب للمدرات)", tr: "2 — Hafif (diüretiğe yanıt verir)", de: "2 — Gering (diuretikaresponsiv)", fr: "2 — Modérée (sensible aux diurétiques)", es: "2 — Leve (responde a diuréticos)" } },
          { value: 3, label: { en: "3 — Severe (refractory)", ru: "3 — Тяжёлый (рефрактерный)", ar: "3 — شديد (مقاوم للعلاج)", tr: "3 — Ciddi (refrakter)", de: "3 — Ausgeprägt (therapierefraktär)", fr: "3 — Sévère (réfractaire)", es: "3 — Grave (refractaria)" } },
        ],
      },
      {
        type: "select", id: "bilirubin",
        label: { en: "Bilirubin (μmol/L)", ru: "Билирубин (мкмоль/л)", ar: "البيليروبين (ميكرومول/لتر)", tr: "Bilirubin (μmol/L)", de: "Bilirubin (μmol/l)", fr: "Bilirubine (μmol/L)", es: "Bilirrubina (μmol/L)" },
        hint: { en: "mg/dL: <2 / 2–3 / >3", ru: "мг/дл: <34 / 34–51 / >51", ar: "ملغ/ديسيلتر: <2 / 2–3 / >3", tr: "mg/dL: <2 / 2–3 / >3", de: "mg/dl: <2 / 2–3 / >3", fr: "mg/dL: <2 / 2–3 / >3", es: "mg/dL: <2 / 2–3 / >3" },
        options: [
          { value: 1, label: { en: "1 — < 34 μmol/L (< 2 mg/dL)", ru: "1 — < 34 мкмоль/л", ar: "1 — < 34 ميكرومول/لتر", tr: "1 — < 34 μmol/L", de: "1 — < 34 μmol/l", fr: "1 — < 34 μmol/L", es: "1 — < 34 μmol/L" } },
          { value: 2, label: { en: "2 — 34–51 μmol/L (2–3 mg/dL)", ru: "2 — 34–51 мкмоль/л", ar: "2 — 34–51 ميكرومول/لتر", tr: "2 — 34–51 μmol/L", de: "2 — 34–51 μmol/l", fr: "2 — 34–51 μmol/L", es: "2 — 34–51 μmol/L" } },
          { value: 3, label: { en: "3 — > 51 μmol/L (> 3 mg/dL)", ru: "3 — > 51 мкмоль/л", ar: "3 — > 51 ميكرومول/لتر", tr: "3 — > 51 μmol/L", de: "3 — > 51 μmol/l", fr: "3 — > 51 μmol/L", es: "3 — > 51 μmol/L" } },
        ],
      },
      {
        type: "select", id: "albumin",
        label: { en: "Albumin (g/L)", ru: "Альбумин (г/л)", ar: "الألبومين (غ/لتر)", tr: "Albumin (g/L)", de: "Albumin (g/l)", fr: "Albumine (g/L)", es: "Albúmina (g/L)" },
        options: [
          { value: 1, label: { en: "1 — > 35 g/L", ru: "1 — > 35 г/л", ar: "1 — > 35 غ/لتر", tr: "1 — > 35 g/L", de: "1 — > 35 g/l", fr: "1 — > 35 g/L", es: "1 — > 35 g/L" } },
          { value: 2, label: { en: "2 — 28–35 g/L", ru: "2 — 28–35 г/л", ar: "2 — 28–35 غ/لتر", tr: "2 — 28–35 g/L", de: "2 — 28–35 g/l", fr: "2 — 28–35 g/L", es: "2 — 28–35 g/L" } },
          { value: 3, label: { en: "3 — < 28 g/L", ru: "3 — < 28 г/л", ar: "3 — < 28 غ/لتر", tr: "3 — < 28 g/L", de: "3 — < 28 g/l", fr: "3 — < 28 g/L", es: "3 — < 28 g/L" } },
        ],
      },
      {
        type: "select", id: "pt",
        label: { en: "Prothrombin time prolongation (seconds)", ru: "Удлинение протромбинового времени (сек)", ar: "إطالة زمن البروثرومبين (ثوانٍ)", tr: "Protrombin zamanı uzaması (saniye)", de: "Prothrombinzeit-Verlängerung (Sek.)", fr: "Allongement du temps de prothrombine (s)", es: "Prolongación del tiempo de protrombina (segundos)" },
        hint: { en: "Or INR: <1.7 / 1.7–2.3 / >2.3", ru: "Или МНО: <1,7 / 1,7–2,3 / >2,3", ar: "أو INR: <1.7 / 1.7–2.3 / >2.3", tr: "Veya INR: <1,7 / 1,7–2,3 / >2,3", de: "Oder INR: <1,7 / 1,7–2,3 / >2,3", fr: "Ou INR: <1,7 / 1,7–2,3 / >2,3", es: "O INR: <1,7 / 1,7–2,3 / >2,3" },
        options: [
          { value: 1, label: { en: "1 — < 4 sec (INR < 1.7)", ru: "1 — < 4 сек (МНО < 1,7)", ar: "1 — < 4 ثوانٍ (INR < 1.7)", tr: "1 — < 4 sn (INR < 1,7)", de: "1 — < 4 Sek. (INR < 1,7)", fr: "1 — < 4 s (INR < 1,7)", es: "1 — < 4 seg (INR < 1,7)" } },
          { value: 2, label: { en: "2 — 4–6 sec (INR 1.7–2.3)", ru: "2 — 4–6 сек (МНО 1,7–2,3)", ar: "2 — 4–6 ثوانٍ (INR 1.7–2.3)", tr: "2 — 4–6 sn (INR 1,7–2,3)", de: "2 — 4–6 Sek. (INR 1,7–2,3)", fr: "2 — 4–6 s (INR 1,7–2,3)", es: "2 — 4–6 seg (INR 1,7–2,3)" } },
          { value: 3, label: { en: "3 — > 6 sec (INR > 2.3)", ru: "3 — > 6 сек (МНО > 2,3)", ar: "3 — > 6 ثوانٍ (INR > 2.3)", tr: "3 — > 6 sn (INR > 2,3)", de: "3 — > 6 Sek. (INR > 2,3)", fr: "3 — > 6 s (INR > 2,3)", es: "3 — > 6 seg (INR > 2,3)" } },
        ],
      },
    ],
    risks: [
      { minScore: 5, maxScore: 6, level: "low", labelKey: "low_risk", color: "green",
        description: { en: "Class A — Well-compensated cirrhosis. 1-year survival ~100%, 2-year ~85%.", ru: "Класс A — Компенсированный цирроз. Выживаемость 1 год ~100%, 2 года ~85%.", ar: "الفئة A — تشمع مُعوَّض. البقاء 1 سنة ~100%، 2 سنة ~85%.", tr: "Sınıf A — İyi kompanse siroz. 1 yıllık yaşam ~%100, 2 yıllık ~%85.", de: "Klasse A — Kompensierte Zirrhose. 1-Jahres-Überleben ~100 %, 2-Jahres ~85 %.", fr: "Classe A — Cirrhose bien compensée. Survie 1 an ~100 %, 2 ans ~85 %.", es: "Clase A — Cirrosis bien compensada. Supervivencia 1 año ~100%, 2 años ~85%." },
        recommendation: { en: "Elective surgery acceptable (operative mortality ~10%). Regular hepatology follow-up.", ru: "Плановая операция возможна (летальность ~10%). Регулярное наблюдение гепатолога.", ar: "الجراحة الاختيارية مقبولة (وفيات جراحية ~10%). متابعة منتظمة مع طبيب الكبد.", tr: "Elektif cerrahi kabul edilebilir (operatif mortalite ~%10). Düzenli hepatoloji takibi.", de: "Elektive Operation vertretbar (Operationsletalität ~10 %). Regelmäßige hepatologische Kontrollen.", fr: "Chirurgie élective acceptable (mortalité opératoire ~10 %). Suivi hépatologique régulier.", es: "Cirugía electiva aceptable (mortalidad operatoria ~10%). Seguimiento hepatológico regular." } },
      { minScore: 7, maxScore: 9, level: "moderate", labelKey: "moderate_risk", color: "amber",
        description: { en: "Class B — Significant functional compromise. 1-year survival ~81%, 2-year ~57%.", ru: "Класс B — Значительное нарушение функции. Выживаемость 1 год ~81%, 2 года ~57%.", ar: "الفئة B — تأثر وظيفي كبير. البقاء 1 سنة ~81%، 2 سنة ~57%.", tr: "Sınıf B — Önemli fonksiyonel bozukluk. 1 yıllık yaşam ~%81, 2 yıllık ~%57.", de: "Klasse B — Erhebliche Funktionseinschränkung. 1-Jahres-Überleben ~81 %, 2-Jahres ~57 %.", fr: "Classe B — Altération fonctionnelle significative. Survie 1 an ~81 %, 2 ans ~57 %.", es: "Clase B — Compromiso funcional significativo. Supervivencia 1 año ~81%, 2 años ~57%." },
        recommendation: { en: "Liver transplantation evaluation. Surgery only if essential (mortality 30–40%). Nutritional support. TIPS assessment.", ru: "Оценка трансплантации печени. Операция только при крайней необходимости (летальность 30–40%). Нутритивная поддержка.", ar: "تقييم زرع الكبد. الجراحة فقط إذا كانت ضرورية (وفيات 30–40%). دعم غذائي.", tr: "Karaciğer nakli değerlendirmesi. Cerrahi yalnızca zorunluysa (mortalite %30–40). Beslenme desteği.", de: "Lebertransplantations-Evaluation. Operation nur wenn unbedingt notwendig (Letalität 30–40 %). Ernährungsunterstützung.", fr: "Évaluation transplantation hépatique. Chirurgie uniquement si indispensable (mortalité 30–40 %). Soutien nutritionnel.", es: "Evaluación para trasplante hepático. Cirugía solo si es esencial (mortalidad 30–40%). Soporte nutricional." } },
      { minScore: 10, maxScore: 15, level: "high", labelKey: "high_risk", color: "red",
        description: { en: "Class C — Decompensated cirrhosis. 1-year survival ~45%, 2-year ~35%.", ru: "Класс C — Декомпенсированный цирроз. Выживаемость 1 год ~45%, 2 года ~35%.", ar: "الفئة C — تشمع غير مُعوَّض. البقاء 1 سنة ~45%، 2 سنة ~35%.", tr: "Sınıf C — Dekompanse siroz. 1 yıllık yaşam ~%45, 2 yıllık ~%35.", de: "Klasse C — Dekompensierte Zirrhose. 1-Jahres-Überleben ~45 %, 2-Jahres ~35 %.", fr: "Classe C — Cirrhose décompensée. Survie 1 an ~45 %, 2 ans ~35 %.", es: "Clase C — Cirrosis descompensada. Supervivencia 1 año ~45%, 2 años ~35%." },
        recommendation: { en: "Liver transplantation if eligible. Avoid elective surgery (mortality > 80%). Palliative care discussion. MELD-based waitlist prioritization.", ru: "Трансплантация печени при наличии показаний. Избегать плановых операций (летальность > 80%). Паллиативная помощь. Приоритизация по MELD.", ar: "زرع الكبد إذا كان مؤهلاً. تجنب الجراحة الاختيارية (وفيات > 80%). مناقشة الرعاية التلطيفية.", tr: "Uygunsa karaciğer nakli. Elektif cerrahiden kaçının (mortalite > %80). Palyatif bakım tartışması.", de: "Lebertransplantation wenn möglich. Elektive Operationen vermeiden (Letalität > 80 %). Palliativmedizinische Diskussion.", fr: "Transplantation hépatique si éligible. Éviter chirurgie élective (mortalité > 80 %). Discussion soins palliatifs.", es: "Trasplante hepático si es elegible. Evitar cirugía electiva (mortalidad > 80%). Discusión cuidados paliativos." } },
    ],
  },
];

// ── Lookup helpers ───────────────────────────────────────────────────────────

export function getCalc(slug: string): CalcMeta | undefined {
  return CALCULATORS.find(c => c.slug === slug);
}

export const CALC_SLUGS = [
  "cha2ds2-vasc", "curb-65", "wells-dvt", "heart-score", "egfr-ckd-epi",
  "gcs", "qsofa", "has-bled", "abcd2", "child-pugh",
  "bmi", "corrected-calcium", "anion-gap", "meld", "cockcroft-gault",
] as const;

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
  biochemistry: { en: "Biochemistry", ru: "Биохимия", ar: "الكيمياء الحيوية", tr: "Biyokimya", de: "Biochemie", fr: "Biochimie", es: "Bioquímica" },
  hepatology: { en: "Hepatology", ru: "Гепатология", ar: "أمراض الكبد", tr: "Hepatoloji", de: "Hepatologie", fr: "Hépatologie", es: "Hepatología" },
  general: { en: "General", ru: "Общее", ar: "عام", tr: "Genel", de: "Allgemein", fr: "Général", es: "General" },
  bmi_name: { en: "BMI Calculator", ru: "Индекс массы тела", ar: "مؤشر كتلة الجسم", tr: "Vücut Kitle İndeksi", de: "BMI-Rechner", fr: "Calculateur IMC", es: "Calculadora IMC" },
  bmi_sub: { en: "Body mass index and obesity classification (WHO)", ru: "Индекс массы тела и классификация ожирения (ВОЗ)", ar: "مؤشر كتلة الجسم وتصنيف السمنة (WHO)", tr: "Vücut kitle indeksi ve obezite sınıflaması (WHO)", de: "Body-Mass-Index und Adipositas-Klassifikation (WHO)", fr: "Indice de masse corporelle et classification obésité (OMS)", es: "Índice de masa corporal y clasificación de obesidad (OMS)" },
  calcium_name: { en: "Corrected Calcium", ru: "Скорр. кальций", ar: "الكالسيوم المصحح", tr: "Düzeltilmiş Kalsiyum", de: "Korrigiertes Kalzium", fr: "Calcium corrigé", es: "Calcio corregido" },
  calcium_sub: { en: "Calcium correction for hypoalbuminaemia", ru: "Коррекция кальция при гипоальбуминемии", ar: "تصحيح الكالسيوم في نقص ألبومين الدم", tr: "Hipoalbüminemi için kalsiyum düzeltmesi", de: "Kalziumkorrektur bei Hypoalbuminämie", fr: "Correction calcique pour hypoalbuminémie", es: "Corrección de calcio por hipoalbuminemia" },
  aniongap_name: { en: "Anion Gap", ru: "Анионный разрыв", ar: "الفجوة الأيونية", tr: "Anyon Açığı", de: "Anionenlücke", fr: "Trou anionique", es: "Brecha aniónica" },
  aniongap_sub: { en: "Metabolic acidosis classification with albumin correction", ru: "Классификация метаболического ацидоза с поправкой на альбумин", ar: "تصنيف الحماض الأيضي مع تصحيح الألبومين", tr: "Albumin düzeltmeli metabolik asidoz sınıflaması", de: "Metabolische Azidose-Klassifikation mit Albumin-Korrektur", fr: "Classification de l'acidose métabolique avec correction albumine", es: "Clasificación acidosis metabólica con corrección albúmina" },
  meld_name: { en: "MELD / MELD-Na", ru: "Шкала MELD / MELD-Na", ar: "مقياس MELD / MELD-Na", tr: "MELD / MELD-Na Skoru", de: "MELD / MELD-Na Score", fr: "Score MELD / MELD-Na", es: "Puntuación MELD / MELD-Na" },
  meld_sub: { en: "Liver disease severity and transplant priority (UNOS)", ru: "Тяжесть заболевания печени и приоритет трансплантации (UNOS)", ar: "شدة مرض الكبد وأولوية زرع الأعضاء (UNOS)", tr: "Karaciğer hastalığı şiddeti ve nakil önceliği (UNOS)", de: "Schweregrad der Lebererkrankung und Transplantationspriorität (UNOS)", fr: "Sévérité de l'hépatopathie et priorité transplantation (UNOS)", es: "Gravedad hepatopatía y prioridad trasplante (UNOS)" },
  cg_name: { en: "Cockcroft-Gault CrCl", ru: "Клиренс креатинина (Кокрофт-Голт)", ar: "تصفية الكرياتينين (كوكروفت-غولت)", tr: "Cockcroft-Gault KrKl", de: "Cockcroft-Gault-KrCl", fr: "Clairance créatinine Cockcroft-Gault", es: "ClCr Cockcroft-Gault" },
  cg_sub: { en: "Kidney function and drug dosing adjustment", ru: "Функция почек и коррекция доз препаратов", ar: "وظائف الكلى وتعديل جرعة الدواء", tr: "Böbrek fonksiyonu ve ilaç doz ayarlaması", de: "Nierenfunktion und Medikamentendosisanpassung", fr: "Fonction rénale et adaptation posologique", es: "Función renal y ajuste de dosis farmacológica" },
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
