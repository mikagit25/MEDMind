export type LearnLocale = "en" | "ru" | "ar" | "tr" | "de" | "fr" | "es";

export interface LearnStrings {
  // Layout
  nav_glossary: string;
  nav_topics: string;
  nav_drugs: string;
  nav_get_started: string;
  disclaimer: string;
  footer_tagline: string;
  // Pet health index page
  pets_h1: string;
  pets_subtitle: string;
  pets_disclaimer: string;
  pets_lesson_singular: string;
  pets_lesson_plural: string;
  pets_empty: string;
  pets_pro_h2: string;
  pets_pro_desc: string;
  pets_pro_btn: string;
  // Pet module detail page
  pets_back: string;
  pets_key_points: string;
  pets_glossary_section: string;
  pets_glossary_full: string;
  pets_vet_h2: string;
  pets_vet_desc: string;
  pets_vet_btn: string;
  pets_footer_note: string;
  // Veterinary professional page (/learn/vet)
  vet_h1: string;
  vet_badge: string;
  vet_subtitle: string;
  vet_disclaimer: string;
  vet_specs_title: string;
  vet_modules_label: string;
  vet_cta_h2: string;
  vet_cta_desc: string;
  vet_cta_login: string;
  vet_cta_signup: string;
  vet_pet_owners: string;
  vet_pet_owners_link: string;
  // Hub card for vet (on /learn page)
  card_vet_title: string;
  card_vet_subtitle: string;
  card_vet_desc: string;
  card_vet_cta: string;
  // Hub hero
  hub_badge: string;
  hub_h1: string;
  hub_h1_accent: string;
  hub_subtitle: string;
  hub_stat_topics: string;
  hub_stat_drugs: string;
  hub_stat_glossary: string;
  hub_btn_browse: string;
  hub_btn_signup: string;
  hub_by_specialty: string;
  // Specialty quick-nav on hub
  spec_cardiology: string;
  spec_neurology: string;
  spec_internal: string;
  spec_pharmacology: string;
  spec_pediatrics: string;
  spec_surgery: string;
  spec_obstetrics: string;
  spec_psychiatry: string;
  // Section cards
  card_topics_title: string;
  card_topics_subtitle: string;
  card_topics_desc: string;
  card_topics_cta: string;
  card_drugs_title: string;
  card_drugs_subtitle: string;
  card_drugs_desc: string;
  card_drugs_cta: string;
  card_glossary_title: string;
  card_glossary_subtitle: string;
  card_glossary_desc: string;
  card_glossary_cta: string;
  card_pets_title: string;
  card_pets_subtitle: string;
  card_pets_desc: string;
  card_pets_cta: string;
  // Professional CTA on hub
  pro_h2: string;
  pro_desc: string;
  pro_start: string;
  pro_how: string;
  // Topics index page  ({count} and {specs} placeholders)
  topics_h1: string;
  topics_count: string;
  topics_empty_desc: string;
  topics_coming_soon: string;
  topics_coming_desc: string;
  topics_notify: string;
  topics_cta_h2: string;
  topics_cta_desc: string;
  topics_cta_btn: string;
  // Drugs index page  ({count} and {search} placeholders)
  drugs_h1: string;
  drugs_count: string;
  drugs_empty_desc: string;
  drugs_disclaimer: string;
  drugs_search_placeholder: string;
  drugs_search_btn: string;
  drugs_no_results: string;
  drugs_no_results_hint: string;
  drugs_coming_soon: string;
  drugs_coming_desc: string;
  drugs_clear_search: string;
  drugs_cta_h2: string;
  drugs_cta_desc: string;
  drugs_cta_btn: string;
}

const translations: Record<LearnLocale, LearnStrings> = {
  // ── English ──────────────────────────────────────────────────────────────────
  en: {
    nav_glossary: "Glossary",
    nav_topics: "Topics",
    nav_drugs: "Drugs",
    nav_get_started: "Get Started Free",
    disclaimer:
      "Educational content only. This information does not replace professional medical advice. Always consult a qualified healthcare provider for diagnosis and treatment.",
    footer_tagline:
      "Educational platform for medical students, physicians & everyone curious about medicine",
    hub_badge: "Free · No account required",
    hub_h1: "Understand medicine,",
    hub_h1_accent: "without a medical degree",
    hub_subtitle:
      "Plain-language guides on medical topics, drugs, and conditions — written for patients, students, and anyone curious about health.",
    hub_stat_topics: "medical topics",
    hub_stat_drugs: "drug guides",
    hub_stat_glossary: "glossary terms",
    hub_btn_browse: "Browse All Topics",
    hub_btn_signup: "Full Access — Free Signup",
    hub_by_specialty: "Browse by specialty",
    spec_cardiology: "Cardiology",
    spec_neurology: "Neurology",
    spec_internal: "Internal Medicine",
    spec_pharmacology: "Pharmacology",
    spec_pediatrics: "Pediatrics",
    spec_surgery: "Surgery",
    spec_obstetrics: "Obstetrics",
    spec_psychiatry: "Psychiatry",
    card_topics_title: "Medical Topics",
    card_topics_subtitle: "Browse by specialty",
    card_topics_desc:
      "Cardiology, neurology, pharmacology, surgery and more — each topic broken down into clear, jargon-free lessons. Understand what your doctor is talking about.",
    card_topics_cta: "Explore Topics →",
    card_drugs_title: "Drug Guide",
    card_drugs_subtitle: "What medications do",
    card_drugs_desc:
      "Understand the purpose, mechanism, and safety of common medications. Plain explanations without dosing — always consult your doctor before taking or stopping any drug.",
    card_drugs_cta: "Browse Drugs →",
    card_glossary_title: "Medical Glossary",
    card_glossary_subtitle: "Terms explained simply",
    card_glossary_desc:
      "A-Z glossary of medical terms translated into everyday language. Never be confused by a diagnosis or lab report again.",
    card_glossary_cta: "Open Glossary →",
    card_pets_title: "Pet Health",
    card_pets_subtitle: "Veterinary guides for owners",
    card_pets_desc:
      "Learn about common conditions, medications, and when to see a vet. Written for pet owners, not veterinarians.",
    card_pets_cta: "Pet Health Guide →",
    pro_h2: "Are you a healthcare professional?",
    pro_desc:
      "Get access to full clinical lessons, AI tutor, case simulations, flashcards, drug dosing, and CME tracking.",
    pro_start: "Start Free →",
    pro_how: "How it works",
    topics_h1: "Medical Topics",
    topics_count: "{count} topics across {specs} specialties — explained in plain language.",
    topics_empty_desc: "Plain-language health guides for patients, students, and curious minds.",
    topics_coming_soon: "Topics coming soon",
    topics_coming_desc:
      "We're generating plain-language summaries for all our medical content.",
    topics_notify: "Get notified when it's ready",
    topics_cta_h2: "Ready to go deeper?",
    topics_cta_desc:
      "Full lessons, AI tutor, flashcards, and clinical cases — for students, physicians, and curious minds.",
    topics_cta_btn: "Start Learning Free →",
    drugs_h1: "Drug Guide",
    drugs_count: "{count} medications explained in plain language.",
    drugs_empty_desc: "Plain-language medication guides for patients and curious minds.",
    drugs_disclaimer:
      "This is educational information only — no dosing advice. Always consult your doctor or pharmacist.",
    drugs_search_placeholder: "Search medications…",
    drugs_search_btn: "Search",
    drugs_no_results: "No results found",
    drugs_no_results_hint: 'No medications matched "{search}". Try a different term.',
    drugs_coming_soon: "Drug guides coming soon",
    drugs_coming_desc: "We're building plain-language guides for all major medications.",
    drugs_clear_search: "Clear search",
    drugs_cta_h2: "Need full clinical details?",
    drugs_cta_desc:
      "Dosing, interactions, adverse effects, and clinical pearls — available for healthcare professionals.",
    drugs_cta_btn: "Create Free Account →",
    pets_h1: "Pet Health Guides",
    pets_subtitle: "Evidence-based health information for dog and cat owners — written in plain language by veterinary professionals. No jargon, no dosing advice, just what you actually need to know.",
    pets_disclaimer: "This content is for educational purposes only and does not constitute veterinary advice. If your pet is unwell, contact a veterinarian immediately.",
    pets_lesson_singular: "lesson",
    pets_lesson_plural: "lessons",
    pets_empty: "Pet health content coming soon.",
    pets_pro_h2: "Veterinary students & professionals",
    pets_pro_desc: "Access full clinical modules, drug dosing by species, MCQs, clinical cases, and spaced repetition flashcards.",
    pets_pro_btn: "Browse Veterinary Modules →",
    pets_back: "← Back to all pet health guides",
    pets_key_points: "Key points",
    pets_glossary_section: "Glossary for this section",
    pets_glossary_full: "Complete Glossary",
    pets_vet_h2: "Are you a vet or vet student?",
    pets_vet_desc: "Access full clinical modules with drug dosing, clinical cases, and spaced repetition.",
    pets_vet_btn: "Explore Veterinary Modules →",
    pets_footer_note: "The information on this page is for general educational purposes only and does not constitute veterinary medical advice. Always consult a qualified veterinarian for your pet's health concerns.",
    vet_h1: "Veterinary Medicine",
    vet_badge: "For vet students & professionals",
    vet_subtitle: "Clinical modules covering small animals, large animals, exotics, pharmacology, surgery, and more — written for veterinary students and practitioners.",
    vet_disclaimer: "Clinical educational content for veterinary professionals. Not a substitute for clinical judgment.",
    vet_specs_title: "Specialties covered",
    vet_modules_label: "modules",
    vet_cta_h2: "Full access for veterinary professionals",
    vet_cta_desc: "Species-adjusted drug dosing, clinical cases, MCQs, spaced repetition flashcards, and CME tracking — all in one platform.",
    vet_cta_login: "Log in",
    vet_cta_signup: "Create free account →",
    vet_pet_owners: "Looking for pet owner guides?",
    vet_pet_owners_link: "Pet Health Guides →",
    card_vet_title: "Veterinary Medicine",
    card_vet_subtitle: "For vet students & professionals",
    card_vet_desc: "Clinical modules on small animals, large animals, pharmacology, surgery, and exotic species — with species-adjusted drug dosing and clinical cases.",
    card_vet_cta: "Explore Vet Modules →",
  },

  // ── Russian ───────────────────────────────────────────────────────────────────
  ru: {
    nav_glossary: "Глоссарий",
    nav_topics: "Темы",
    nav_drugs: "Препараты",
    nav_get_started: "Начать бесплатно",
    disclaimer:
      "Только образовательный контент. Эта информация не заменяет профессиональную медицинскую консультацию. Всегда обращайтесь к квалифицированному специалисту по вопросам диагностики и лечения.",
    footer_tagline:
      "Образовательная платформа для студентов-медиков, врачей и всех, кто интересуется медициной",
    hub_badge: "Бесплатно · Без регистрации",
    hub_h1: "Понимайте медицину,",
    hub_h1_accent: "без медицинского образования",
    hub_subtitle:
      "Простые объяснения медицинских тем, препаратов и заболеваний — для пациентов, студентов и всех, кто интересуется здоровьем.",
    hub_stat_topics: "медицинских тем",
    hub_stat_drugs: "справок о препаратах",
    hub_stat_glossary: "терминов в глоссарии",
    hub_btn_browse: "Все темы",
    hub_btn_signup: "Полный доступ — бесплатная регистрация",
    hub_by_specialty: "По специальности",
    spec_cardiology: "Кардиология",
    spec_neurology: "Неврология",
    spec_internal: "Терапия",
    spec_pharmacology: "Фармакология",
    spec_pediatrics: "Педиатрия",
    spec_surgery: "Хирургия",
    spec_obstetrics: "Акушерство и гинекология",
    spec_psychiatry: "Психиатрия",
    card_topics_title: "Медицинские темы",
    card_topics_subtitle: "По специальностям",
    card_topics_desc:
      "Кардиология, неврология, фармакология, хирургия и многое другое — каждая тема объяснена чётко и без жаргона. Поймите, что говорит ваш врач.",
    card_topics_cta: "Смотреть темы →",
    card_drugs_title: "Справочник препаратов",
    card_drugs_subtitle: "Как работают лекарства",
    card_drugs_desc:
      "Узнайте о назначении, механизме действия и безопасности распространённых препаратов. Без рекомендаций по дозировке — всегда консультируйтесь с врачом.",
    card_drugs_cta: "Просмотреть препараты →",
    card_glossary_title: "Медицинский глоссарий",
    card_glossary_subtitle: "Термины простым языком",
    card_glossary_desc:
      "Глоссарий медицинских терминов от А до Я на понятном языке. Никогда больше не запутайтесь в диагнозе или лабораторных данных.",
    card_glossary_cta: "Открыть глоссарий →",
    card_pets_title: "Здоровье питомцев",
    card_pets_subtitle: "Ветеринарные руководства для владельцев",
    card_pets_desc:
      "Узнайте о распространённых болезнях, препаратах и когда обращаться к ветеринару. Написано для владельцев, а не ветеринаров.",
    card_pets_cta: "Руководство по здоровью питомца →",
    pro_h2: "Вы медицинский работник?",
    pro_desc:
      "Получите доступ к полным клиническим урокам, AI-тьютору, симуляторам кейсов, карточкам, дозировкам препаратов и отслеживанию CME.",
    pro_start: "Начать бесплатно →",
    pro_how: "Как это работает",
    topics_h1: "Медицинские темы",
    topics_count: "{count} тем в {specs} специальностях — объяснены простым языком.",
    topics_empty_desc:
      "Руководства по здоровью на понятном языке для пациентов, студентов и любопытных умов.",
    topics_coming_soon: "Темы скоро появятся",
    topics_coming_desc:
      "Мы создаём доступные объяснения для всего нашего медицинского контента.",
    topics_notify: "Уведомить, когда будет готово",
    topics_cta_h2: "Хотите глубже?",
    topics_cta_desc:
      "Полные уроки, AI-тьютор, карточки и клинические кейсы — для студентов, врачей и всех любопытных.",
    topics_cta_btn: "Учиться бесплатно →",
    drugs_h1: "Справочник препаратов",
    drugs_count: "{count} препаратов объяснены простым языком.",
    drugs_empty_desc:
      "Руководства по препаратам на понятном языке для пациентов и всех интересующихся.",
    drugs_disclaimer:
      "Только образовательная информация — без рекомендаций по дозировке. Всегда консультируйтесь с врачом или фармацевтом.",
    drugs_search_placeholder: "Найти препарат…",
    drugs_search_btn: "Найти",
    drugs_no_results: "Ничего не найдено",
    drugs_no_results_hint: 'По запросу "{search}" препаратов не найдено. Попробуйте другой термин.',
    drugs_coming_soon: "Справочник препаратов скоро появится",
    drugs_coming_desc: "Мы создаём доступные руководства по всем основным препаратам.",
    drugs_clear_search: "Очистить поиск",
    drugs_cta_h2: "Нужны полные клинические данные?",
    drugs_cta_desc:
      "Дозировки, взаимодействия, побочные эффекты и клинические жемчужины — доступно для медицинских работников.",
    drugs_cta_btn: "Создать бесплатный аккаунт →",
    pets_h1: "Здоровье питомцев",
    pets_subtitle: "Достоверная информация о здоровье собак и кошек — написана простым языком ветеринарными специалистами. Без жаргона, без рекомендаций по дозировке — только то, что вам действительно нужно знать.",
    pets_disclaimer: "Этот контент предназначен только для образовательных целей и не является ветеринарной консультацией. Если ваш питомец нездоров, немедленно обратитесь к ветеринару.",
    pets_lesson_singular: "урок",
    pets_lesson_plural: "уроков",
    pets_empty: "Контент о здоровье питомцев скоро появится.",
    pets_pro_h2: "Студенты и специалисты ветеринарии",
    pets_pro_desc: "Полные клинические модули, дозирование препаратов по видам, тестовые вопросы, клинические кейсы и карточки для интервального повторения.",
    pets_pro_btn: "Ветеринарные модули →",
    pets_back: "← Все руководства по здоровью питомцев",
    pets_key_points: "Ключевые моменты",
    pets_glossary_section: "Глоссарий раздела",
    pets_glossary_full: "Полный глоссарий",
    pets_vet_h2: "Вы ветеринар или студент-ветеринар?",
    pets_vet_desc: "Полные клинические модули с дозировкой препаратов, клинические кейсы и интервальное повторение.",
    pets_vet_btn: "Ветеринарные модули →",
    pets_footer_note: "Информация на этой странице предназначена исключительно для образовательных целей и не является ветеринарной медицинской консультацией. При любых проблемах со здоровьем питомца всегда обращайтесь к квалифицированному ветеринару.",
    vet_h1: "Ветеринарная медицина",
    vet_badge: "Для студентов и специалистов ветеринарии",
    vet_subtitle: "Клинические модули по мелким и крупным животным, экзотике, фармакологии, хирургии и многому другому — для студентов-ветеринаров и практикующих специалистов.",
    vet_disclaimer: "Клинический образовательный контент для ветеринарных специалистов. Не заменяет клиническое суждение.",
    vet_specs_title: "Охватываемые специальности",
    vet_modules_label: "модулей",
    vet_cta_h2: "Полный доступ для ветеринарных специалистов",
    vet_cta_desc: "Дозирование препаратов по видам, клинические кейсы, тестовые вопросы, интервальное повторение и отслеживание CME — всё в одной платформе.",
    vet_cta_login: "Войти",
    vet_cta_signup: "Создать бесплатный аккаунт →",
    vet_pet_owners: "Ищете руководства для владельцев питомцев?",
    vet_pet_owners_link: "Здоровье питомцев →",
    card_vet_title: "Ветеринарная медицина",
    card_vet_subtitle: "Для студентов и специалистов",
    card_vet_desc: "Клинические модули по мелким и крупным животным, фармакологии, хирургии и экзотическим видам — с дозированием препаратов по видам и клиническими кейсами.",
    card_vet_cta: "Ветеринарные модули →",
  },

  // ── Arabic ────────────────────────────────────────────────────────────────────
  ar: {
    nav_glossary: "المسرد",
    nav_topics: "المواضيع",
    nav_drugs: "الأدوية",
    nav_get_started: "ابدأ مجاناً",
    disclaimer:
      "محتوى تعليمي فقط. لا تُغني هذه المعلومات عن الاستشارة الطبية المتخصصة. استشر دائماً مقدم رعاية صحية مؤهلاً للتشخيص والعلاج.",
    footer_tagline:
      "منصة تعليمية لطلاب الطب والأطباء وكل من يهتم بالطب",
    hub_badge: "مجاني · لا يتطلب حساباً",
    hub_h1: "افهم الطب،",
    hub_h1_accent: "بدون شهادة طبية",
    hub_subtitle:
      "أدلة بلغة بسيطة حول المواضيع الطبية والأدوية والأمراض — مكتوبة للمرضى والطلاب وكل من يهتم بصحته.",
    hub_stat_topics: "موضوعاً طبياً",
    hub_stat_drugs: "دليل دواء",
    hub_stat_glossary: "مصطلح في المسرد",
    hub_btn_browse: "تصفح جميع المواضيع",
    hub_btn_signup: "وصول كامل — تسجيل مجاني",
    hub_by_specialty: "تصفح حسب التخصص",
    spec_cardiology: "أمراض القلب",
    spec_neurology: "الأعصاب",
    spec_internal: "الطب الداخلي",
    spec_pharmacology: "علم الأدوية",
    spec_pediatrics: "طب الأطفال",
    spec_surgery: "الجراحة",
    spec_obstetrics: "التوليد وأمراض النساء",
    spec_psychiatry: "الطب النفسي",
    card_topics_title: "المواضيع الطبية",
    card_topics_subtitle: "تصفح حسب التخصص",
    card_topics_desc:
      "أمراض القلب والأعصاب والأدوية والجراحة وغيرها — كل موضوع مشروح بوضوح وبدون مصطلحات معقدة. افهم ما يقوله طبيبك.",
    card_topics_cta: "استكشاف المواضيع →",
    card_drugs_title: "دليل الأدوية",
    card_drugs_subtitle: "ما تفعله الأدوية",
    card_drugs_desc:
      "افهم الغرض والآلية وسلامة الأدوية الشائعة. شروحات بسيطة بدون جرعات — استشر طبيبك دائماً قبل تناول أي دواء أو إيقافه.",
    card_drugs_cta: "تصفح الأدوية →",
    card_glossary_title: "المسرد الطبي",
    card_glossary_subtitle: "المصطلحات بلغة بسيطة",
    card_glossary_desc:
      "مسرد أبجدي للمصطلحات الطبية مترجم إلى لغة يومية. لن تتعثر بعد الآن أمام التشخيصات أو نتائج المختبر.",
    card_glossary_cta: "فتح المسرد →",
    card_pets_title: "صحة الحيوانات الأليفة",
    card_pets_subtitle: "أدلة بيطرية لأصحاب الحيوانات",
    card_pets_desc:
      "تعرف على الأمراض الشائعة والأدوية ومتى تزور الطبيب البيطري. مكتوب لأصحاب الحيوانات وليس للأطباء البيطريين.",
    card_pets_cta: "دليل صحة الحيوانات →",
    pro_h2: "هل أنت من العاملين في مجال الرعاية الصحية؟",
    pro_desc:
      "احصل على دروس سريرية كاملة ومعلم ذكاء اصطناعي وحالات محاكاة وبطاقات تعليمية وجرعات الأدوية وتتبع التعليم المستمر.",
    pro_start: "ابدأ مجاناً →",
    pro_how: "كيف يعمل",
    topics_h1: "المواضيع الطبية",
    topics_count: "{count} موضوعاً في {specs} تخصصاً — مشروحة بلغة بسيطة.",
    topics_empty_desc: "أدلة صحية بلغة بسيطة للمرضى والطلاب وكل المهتمين.",
    topics_coming_soon: "المواضيع قريباً",
    topics_coming_desc: "نحن نُنشئ ملخصات بلغة بسيطة لجميع محتوياتنا الطبية.",
    topics_notify: "أبلغني عند الجاهزية",
    topics_cta_h2: "هل تريد التعمق أكثر؟",
    topics_cta_desc:
      "دروس كاملة ومعلم ذكاء اصطناعي وبطاقات تعليمية وحالات سريرية — للطلاب والأطباء وكل المهتمين.",
    topics_cta_btn: "ابدأ التعلم مجاناً →",
    drugs_h1: "دليل الأدوية",
    drugs_count: "{count} دواء مشروح بلغة بسيطة.",
    drugs_empty_desc: "أدلة الأدوية بلغة بسيطة للمرضى والمهتمين.",
    drugs_disclaimer:
      "هذه معلومات تعليمية فقط — لا توصيات بالجرعات. استشر طبيبك أو الصيدلاني دائماً.",
    drugs_search_placeholder: "ابحث عن دواء…",
    drugs_search_btn: "بحث",
    drugs_no_results: "لا توجد نتائج",
    drugs_no_results_hint: 'لم يُطابق أي دواء "{search}". جرب مصطلحاً مختلفاً.',
    drugs_coming_soon: "أدلة الأدوية قريباً",
    drugs_coming_desc: "نحن نبني أدلة بلغة بسيطة لجميع الأدوية الرئيسية.",
    drugs_clear_search: "مسح البحث",
    drugs_cta_h2: "تحتاج تفاصيل سريرية كاملة؟",
    drugs_cta_desc:
      "الجرعات والتفاعلات والآثار الجانبية والنقاط السريرية — متاحة للمتخصصين الصحيين.",
    drugs_cta_btn: "إنشاء حساب مجاني →",
    pets_h1: "أدلة صحة الحيوانات الأليفة",
    pets_subtitle: "معلومات صحية موثوقة لأصحاب الكلاب والقطط — مكتوبة بلغة بسيطة من قبل متخصصين بيطريين. بدون مصطلحات معقدة، بدون جرعات، فقط ما تحتاج لمعرفته حقاً.",
    pets_disclaimer: "هذا المحتوى لأغراض تعليمية فقط ولا يشكل استشارة بيطرية. إذا كان حيوانك الأليف مريضاً، اتصل بطبيب بيطري فوراً.",
    pets_lesson_singular: "درس",
    pets_lesson_plural: "دروس",
    pets_empty: "محتوى صحة الحيوانات قريباً.",
    pets_pro_h2: "طلاب وأخصائيو البيطرة",
    pets_pro_desc: "وحدات سريرية كاملة، جرعات الأدوية حسب النوع، أسئلة اختبار، حالات سريرية، وبطاقات مراجعة متباعدة.",
    pets_pro_btn: "تصفح الوحدات البيطرية →",
    pets_back: "← العودة إلى جميع أدلة صحة الحيوانات",
    pets_key_points: "النقاط الرئيسية",
    pets_glossary_section: "مسرد هذا القسم",
    pets_glossary_full: "المسرد الكامل",
    pets_vet_h2: "هل أنت طبيب بيطري أو طالب بيطرة؟",
    pets_vet_desc: "وحدات سريرية كاملة مع جرعات الأدوية والحالات السريرية والمراجعة المتباعدة.",
    pets_vet_btn: "استكشاف الوحدات البيطرية →",
    pets_footer_note: "المعلومات على هذه الصفحة لأغراض تعليمية عامة فقط ولا تشكل استشارة طبية بيطرية. استشر دائماً طبيباً بيطرياً مؤهلاً لأي مخاوف تتعلق بصحة حيوانك الأليف.",
    vet_h1: "الطب البيطري",
    vet_badge: "لطلاب وأخصائيي البيطرة",
    vet_subtitle: "وحدات سريرية تغطي الحيوانات الصغيرة والكبيرة والغريبة والأدوية والجراحة وأكثر — للطلاب والممارسين البيطريين.",
    vet_disclaimer: "محتوى تعليمي سريري للمتخصصين البيطريين. لا يغني عن الحكم السريري.",
    vet_specs_title: "التخصصات المشمولة",
    vet_modules_label: "وحدات",
    vet_cta_h2: "وصول كامل للمتخصصين البيطريين",
    vet_cta_desc: "جرعات الأدوية حسب النوع، الحالات السريرية، أسئلة الاختبار، المراجعة المتباعدة، وتتبع التعليم المستمر — كل ذلك في منصة واحدة.",
    vet_cta_login: "تسجيل الدخول",
    vet_cta_signup: "إنشاء حساب مجاني →",
    vet_pet_owners: "تبحث عن أدلة لأصحاب الحيوانات؟",
    vet_pet_owners_link: "أدلة صحة الحيوانات الأليفة →",
    card_vet_title: "الطب البيطري",
    card_vet_subtitle: "للطلاب والمتخصصين",
    card_vet_desc: "وحدات سريرية في الحيوانات الصغيرة والكبيرة والأدوية والجراحة والأنواع الغريبة — مع جرعات الأدوية حسب النوع والحالات السريرية.",
    card_vet_cta: "استكشاف الوحدات البيطرية →",
  },

  // ── Turkish ───────────────────────────────────────────────────────────────────
  tr: {
    nav_glossary: "Sözlük",
    nav_topics: "Konular",
    nav_drugs: "İlaçlar",
    nav_get_started: "Ücretsiz Başla",
    disclaimer:
      "Yalnızca eğitim amaçlıdır. Bu bilgiler profesyonel tıbbi tavsiyenin yerini tutmaz. Tanı ve tedavi için her zaman nitelikli bir sağlık uzmanına danışın.",
    footer_tagline:
      "Tıp öğrencileri, hekimler ve tıbba meraklı herkes için eğitim platformu",
    hub_badge: "Ücretsiz · Hesap gerekmez",
    hub_h1: "Tıbbı anlayın,",
    hub_h1_accent: "tıp diplomasına gerek kalmadan",
    hub_subtitle:
      "Tıbbi konular, ilaçlar ve hastalıklar hakkında sade dilde rehberler — hastalar, öğrenciler ve sağlığa meraklı herkes için.",
    hub_stat_topics: "tıbbi konu",
    hub_stat_drugs: "ilaç rehberi",
    hub_stat_glossary: "sözlük terimi",
    hub_btn_browse: "Tüm Konuları Gözat",
    hub_btn_signup: "Tam Erişim — Ücretsiz Kayıt",
    hub_by_specialty: "Uzmanlığa göre gözat",
    spec_cardiology: "Kardiyoloji",
    spec_neurology: "Nöroloji",
    spec_internal: "İç Hastalıkları",
    spec_pharmacology: "Farmakoloji",
    spec_pediatrics: "Pediatri",
    spec_surgery: "Cerrahi",
    spec_obstetrics: "Obstetri ve Jinekoloji",
    spec_psychiatry: "Psikiyatri",
    card_topics_title: "Tıbbi Konular",
    card_topics_subtitle: "Uzmanlığa göre gözat",
    card_topics_desc:
      "Kardiyoloji, nöroloji, farmakoloji, cerrahi ve daha fazlası — her konu net ve jargonsuz derslerle anlatılmıştır. Doktorunuzun ne söylediğini anlayın.",
    card_topics_cta: "Konuları Keşfet →",
    card_drugs_title: "İlaç Rehberi",
    card_drugs_subtitle: "İlaçlar ne işe yarar",
    card_drugs_desc:
      "Yaygın ilaçların amacını, mekanizmasını ve güvenliğini anlayın. Doz önerisi olmadan sade açıklamalar — her zaman doktorunuza danışın.",
    card_drugs_cta: "İlaçları Gözat →",
    card_glossary_title: "Tıbbi Sözlük",
    card_glossary_subtitle: "Terimler sade dilde",
    card_glossary_desc:
      "Tıbbi terimlerin A-Z sözlüğü, günlük dile çevrilmiş. Bir daha tanı veya lab raporu karşısında şaşırmayın.",
    card_glossary_cta: "Sözlüğü Aç →",
    card_pets_title: "Evcil Hayvan Sağlığı",
    card_pets_subtitle: "Sahipler için veteriner rehberleri",
    card_pets_desc:
      "Yaygın hastalıklar, ilaçlar ve veterinere ne zaman gidileceği hakkında bilgi edinin. Veterinerler için değil, sahipler için yazılmıştır.",
    card_pets_cta: "Evcil Hayvan Rehberi →",
    pro_h2: "Sağlık profesyoneli misiniz?",
    pro_desc:
      "Tam klinik derslere, AI tutora, vaka simülasyonlarına, flash kartlara, ilaç doz bilgilerine ve CME takibine erişin.",
    pro_start: "Ücretsiz Başla →",
    pro_how: "Nasıl çalışır",
    topics_h1: "Tıbbi Konular",
    topics_count: "{specs} uzmanlık dalında {count} konu — sade dilde açıklandı.",
    topics_empty_desc:
      "Hastalar, öğrenciler ve meraklı zihinler için sade dilde sağlık rehberleri.",
    topics_coming_soon: "Konular yakında geliyor",
    topics_coming_desc:
      "Tüm tıbbi içeriğimiz için sade dil özetleri oluşturuyoruz.",
    topics_notify: "Hazır olduğunda bildir",
    topics_cta_h2: "Daha derine inmek ister misiniz?",
    topics_cta_desc:
      "Tam dersler, AI tutor, flash kartlar ve klinik vakalar — öğrenciler, hekimler ve meraklı zihinler için.",
    topics_cta_btn: "Ücretsiz Öğrenmeye Başla →",
    drugs_h1: "İlaç Rehberi",
    drugs_count: "{count} ilaç sade dilde açıklandı.",
    drugs_empty_desc: "Hastalar ve meraklı zihinler için sade dilde ilaç rehberleri.",
    drugs_disclaimer:
      "Bu yalnızca eğitim bilgisidir — doz önerisi içermez. Her zaman doktorunuza veya eczacınıza danışın.",
    drugs_search_placeholder: "İlaç ara…",
    drugs_search_btn: "Ara",
    drugs_no_results: "Sonuç bulunamadı",
    drugs_no_results_hint: '"{search}" ile eşleşen ilaç yok. Farklı bir terim deneyin.',
    drugs_coming_soon: "İlaç rehberleri yakında geliyor",
    drugs_coming_desc: "Tüm ana ilaçlar için sade dil rehberleri oluşturuyoruz.",
    drugs_clear_search: "Aramayı temizle",
    drugs_cta_h2: "Tam klinik detaylara mı ihtiyacınız var?",
    drugs_cta_desc:
      "Doz, etkileşimler, yan etkiler ve klinik notlar — sağlık profesyonelleri için mevcut.",
    drugs_cta_btn: "Ücretsiz Hesap Oluştur →",
    pets_h1: "Evcil Hayvan Sağlık Rehberleri",
    pets_subtitle: "Köpek ve kedi sahipleri için veteriner uzmanları tarafından sade dilde yazılmış güvenilir sağlık bilgileri. Jargon yok, doz tavsiyesi yok, sadece bilmeniz gerekenler.",
    pets_disclaimer: "Bu içerik yalnızca eğitim amaçlıdır ve veteriner tavsiyesi niteliği taşımaz. Hayvanınız hastaysa hemen bir veterinere başvurun.",
    pets_lesson_singular: "ders",
    pets_lesson_plural: "ders",
    pets_empty: "Evcil hayvan sağlığı içeriği yakında geliyor.",
    pets_pro_h2: "Veteriner öğrencileri ve profesyonelleri",
    pets_pro_desc: "Tam klinik modüller, türe göre ilaç dozları, MCQ'lar, klinik vakalar ve aralıklı tekrar kartları.",
    pets_pro_btn: "Veteriner Modüllerini Gözat →",
    pets_back: "← Tüm evcil hayvan sağlık rehberlerine dön",
    pets_key_points: "Temel noktalar",
    pets_glossary_section: "Bu bölümün sözlüğü",
    pets_glossary_full: "Tam Sözlük",
    pets_vet_h2: "Veteriner veya veteriner öğrencisi misiniz?",
    pets_vet_desc: "İlaç dozları, klinik vakalar ve aralıklı tekrar ile tam klinik modüllere erişin.",
    pets_vet_btn: "Veteriner Modüllerini Keşfet →",
    pets_footer_note: "Bu sayfadaki bilgiler yalnızca genel eğitim amaçlıdır ve veteriner tıbbi tavsiyesi niteliği taşımaz. Hayvanınızın sağlığıyla ilgili endişeleriniz için her zaman nitelikli bir veterinere danışın.",
    vet_h1: "Veteriner Tıbbı",
    vet_badge: "Veteriner öğrencileri ve profesyonelleri için",
    vet_subtitle: "Küçük hayvanlar, büyük hayvanlar, egzotikler, farmakoloji, cerrahi ve daha fazlasını kapsayan klinik modüller — veteriner öğrencileri ve uygulayıcıları için.",
    vet_disclaimer: "Veteriner profesyonelleri için klinik eğitim içeriği. Klinik yargının yerini tutmaz.",
    vet_specs_title: "Kapsanan uzmanlıklar",
    vet_modules_label: "modül",
    vet_cta_h2: "Veteriner profesyonelleri için tam erişim",
    vet_cta_desc: "Türe göre ilaç dozları, klinik vakalar, MCQ'lar, aralıklı tekrar ve CME takibi — tek bir platformda.",
    vet_cta_login: "Giriş yap",
    vet_cta_signup: "Ücretsiz hesap oluştur →",
    vet_pet_owners: "Evcil hayvan sahibi rehberleri mi arıyorsunuz?",
    vet_pet_owners_link: "Evcil Hayvan Sağlık Rehberleri →",
    card_vet_title: "Veteriner Tıbbı",
    card_vet_subtitle: "Öğrenciler ve profesyoneller için",
    card_vet_desc: "Küçük hayvanlar, büyük hayvanlar, farmakoloji, cerrahi ve egzotik türlere ilişkin klinik modüller — türe göre ilaç dozları ve klinik vakalarla.",
    card_vet_cta: "Vet Modüllerini Keşfet →",
  },

  // ── German ────────────────────────────────────────────────────────────────────
  de: {
    nav_glossary: "Glossar",
    nav_topics: "Themen",
    nav_drugs: "Medikamente",
    nav_get_started: "Kostenlos starten",
    disclaimer:
      "Nur Bildungsinhalte. Diese Informationen ersetzen keine professionelle medizinische Beratung. Wenden Sie sich für Diagnose und Behandlung immer an einen qualifizierten Arzt.",
    footer_tagline:
      "Bildungsplattform für Medizinstudenten, Ärzte und alle, die Medizin verstehen wollen",
    hub_badge: "Kostenlos · Kein Konto erforderlich",
    hub_h1: "Medizin verstehen,",
    hub_h1_accent: "ohne Medizinstudium",
    hub_subtitle:
      "Verständliche Erklärungen zu medizinischen Themen, Medikamenten und Erkrankungen — für Patienten, Studenten und alle Neugierigen.",
    hub_stat_topics: "medizinische Themen",
    hub_stat_drugs: "Medikamentenführer",
    hub_stat_glossary: "Glossarbegriffe",
    hub_btn_browse: "Alle Themen durchsuchen",
    hub_btn_signup: "Vollzugriff — Kostenlose Registrierung",
    hub_by_specialty: "Nach Fachgebiet suchen",
    spec_cardiology: "Kardiologie",
    spec_neurology: "Neurologie",
    spec_internal: "Innere Medizin",
    spec_pharmacology: "Pharmakologie",
    spec_pediatrics: "Pädiatrie",
    spec_surgery: "Chirurgie",
    spec_obstetrics: "Geburtshilfe & Gynäkologie",
    spec_psychiatry: "Psychiatrie",
    card_topics_title: "Medizinische Themen",
    card_topics_subtitle: "Nach Fachgebiet durchsuchen",
    card_topics_desc:
      "Kardiologie, Neurologie, Pharmakologie, Chirurgie und mehr — jedes Thema verständlich ohne Fachjargon erklärt. Verstehen Sie, was Ihr Arzt meint.",
    card_topics_cta: "Themen erkunden →",
    card_drugs_title: "Medikamentenführer",
    card_drugs_subtitle: "Was Medikamente bewirken",
    card_drugs_desc:
      "Verstehen Sie Zweck, Wirkungsweise und Sicherheit gängiger Medikamente. Verständliche Erklärungen ohne Dosierungsangaben — konsultieren Sie immer Ihren Arzt.",
    card_drugs_cta: "Medikamente durchsuchen →",
    card_glossary_title: "Medizinisches Glossar",
    card_glossary_subtitle: "Fachbegriffe einfach erklärt",
    card_glossary_desc:
      "A-Z Glossar medizinischer Begriffe in Alltagssprache übersetzt. Nie mehr verwirrt von Diagnosen oder Laborbefunden.",
    card_glossary_cta: "Glossar öffnen →",
    card_pets_title: "Tiergesundheit",
    card_pets_subtitle: "Veterinärführer für Tierhalter",
    card_pets_desc:
      "Erfahren Sie mehr über häufige Erkrankungen, Medikamente und wann ein Tierarztbesuch nötig ist. Geschrieben für Tierhalter, nicht für Tierärzte.",
    card_pets_cta: "Tiergesundheitsführer →",
    pro_h2: "Sind Sie im Gesundheitswesen tätig?",
    pro_desc:
      "Erhalten Sie Zugang zu vollständigen klinischen Lektionen, KI-Tutor, Fallsimulationen, Lernkarten, Medikamentendosierung und CME-Tracking.",
    pro_start: "Kostenlos starten →",
    pro_how: "So funktioniert's",
    topics_h1: "Medizinische Themen",
    topics_count: "{count} Themen in {specs} Fachgebieten — in verständlicher Sprache erklärt.",
    topics_empty_desc:
      "Verständliche Gesundheitsführer für Patienten, Studenten und neugierige Köpfe.",
    topics_coming_soon: "Themen kommen bald",
    topics_coming_desc:
      "Wir erstellen verständliche Zusammenfassungen für alle unsere medizinischen Inhalte.",
    topics_notify: "Benachrichtigen, wenn bereit",
    topics_cta_h2: "Möchten Sie tiefer eintauchen?",
    topics_cta_desc:
      "Vollständige Lektionen, KI-Tutor, Lernkarten und klinische Fälle — für Studenten, Ärzte und neugierige Köpfe.",
    topics_cta_btn: "Kostenlos lernen →",
    drugs_h1: "Medikamentenführer",
    drugs_count: "{count} Medikamente in verständlicher Sprache erklärt.",
    drugs_empty_desc: "Verständliche Medikamentenführer für Patienten und Neugierige.",
    drugs_disclaimer:
      "Dies sind nur Bildungsinformationen — keine Dosierungsempfehlungen. Konsultieren Sie immer Ihren Arzt oder Apotheker.",
    drugs_search_placeholder: "Medikament suchen…",
    drugs_search_btn: "Suchen",
    drugs_no_results: "Keine Ergebnisse gefunden",
    drugs_no_results_hint: 'Keine Medikamente für "{search}" gefunden. Versuchen Sie einen anderen Begriff.',
    drugs_coming_soon: "Medikamentenführer kommt bald",
    drugs_coming_desc: "Wir erstellen verständliche Führung für alle wichtigen Medikamente.",
    drugs_clear_search: "Suche löschen",
    drugs_cta_h2: "Vollständige klinische Details benötigt?",
    drugs_cta_desc:
      "Dosierung, Wechselwirkungen, Nebenwirkungen und klinische Hinweise — für medizinische Fachkräfte verfügbar.",
    drugs_cta_btn: "Kostenloses Konto erstellen →",
    pets_h1: "Tiergesundheitsratgeber",
    pets_subtitle: "Evidenzbasierte Gesundheitsinformationen für Hunde- und Katzenbesitzer — in verständlicher Sprache von Veterinärfachleuten verfasst. Kein Fachjargon, keine Dosierungsempfehlungen.",
    pets_disclaimer: "Dieser Inhalt dient nur zu Bildungszwecken und stellt keine Tierarztberatung dar. Wenn Ihr Tier krank ist, wenden Sie sich sofort an einen Tierarzt.",
    pets_lesson_singular: "Lektion",
    pets_lesson_plural: "Lektionen",
    pets_empty: "Tiergesundheitsinhalte kommen bald.",
    pets_pro_h2: "Veterinärstudenten & Fachkräfte",
    pets_pro_desc: "Vollständige klinische Module, artspezifische Medikamentendosierungen, MCQs, klinische Fälle und Lernkarten.",
    pets_pro_btn: "Veterinärmodule durchsuchen →",
    pets_back: "← Zurück zu allen Tiergesundheitsratgebern",
    pets_key_points: "Wesentliche Punkte",
    pets_glossary_section: "Glossar für diesen Abschnitt",
    pets_glossary_full: "Vollständiges Glossar",
    pets_vet_h2: "Sind Sie Tierarzt oder Veterinärstudent?",
    pets_vet_desc: "Vollständige klinische Module mit Medikamentendosierungen, klinischen Fällen und Lernkarten.",
    pets_vet_btn: "Veterinärmodule erkunden →",
    pets_footer_note: "Die Informationen auf dieser Seite dienen ausschließlich zu allgemeinen Bildungszwecken und stellen keine tierärztliche Beratung dar. Wenden Sie sich bei Gesundheitsproblemen Ihres Tieres immer an einen qualifizierten Tierarzt.",
    vet_h1: "Veterinärmedizin",
    vet_badge: "Für Veterinärstudenten & Fachkräfte",
    vet_subtitle: "Klinische Module zu Kleintieren, Großtieren, Exoten, Pharmakologie, Chirurgie und mehr — für Veterinärstudenten und Praktiker.",
    vet_disclaimer: "Klinische Bildungsinhalte für Veterinärfachkräfte. Kein Ersatz für klinisches Urteilsvermögen.",
    vet_specs_title: "Abgedeckte Fachgebiete",
    vet_modules_label: "Module",
    vet_cta_h2: "Vollzugriff für Veterinärfachkräfte",
    vet_cta_desc: "Artspezifische Medikamentendosierungen, klinische Fälle, MCQs, Lernkarten und CME-Tracking — alles auf einer Plattform.",
    vet_cta_login: "Einloggen",
    vet_cta_signup: "Kostenloses Konto erstellen →",
    vet_pet_owners: "Suchen Sie Ratgeber für Tierbesitzer?",
    vet_pet_owners_link: "Tiergesundheitsratgeber →",
    card_vet_title: "Veterinärmedizin",
    card_vet_subtitle: "Für Studenten & Fachkräfte",
    card_vet_desc: "Klinische Module zu Kleintieren, Großtieren, Pharmakologie, Chirurgie und exotischen Arten — mit artspezifischen Dosierungen und klinischen Fällen.",
    card_vet_cta: "Vet-Module erkunden →",
  },

  // ── French ────────────────────────────────────────────────────────────────────
  fr: {
    nav_glossary: "Glossaire",
    nav_topics: "Sujets",
    nav_drugs: "Médicaments",
    nav_get_started: "Commencer gratuitement",
    disclaimer:
      "Contenu éducatif uniquement. Ces informations ne remplacent pas l'avis médical professionnel. Consultez toujours un professionnel de santé qualifié pour le diagnostic et le traitement.",
    footer_tagline:
      "Plateforme éducative pour les étudiants en médecine, les médecins et tous ceux qui s'intéressent à la médecine",
    hub_badge: "Gratuit · Sans compte requis",
    hub_h1: "Comprendre la médecine,",
    hub_h1_accent: "sans diplôme médical",
    hub_subtitle:
      "Guides en langage clair sur les sujets médicaux, les médicaments et les maladies — pour les patients, les étudiants et tous ceux qui s'intéressent à la santé.",
    hub_stat_topics: "sujets médicaux",
    hub_stat_drugs: "guides médicaments",
    hub_stat_glossary: "termes du glossaire",
    hub_btn_browse: "Voir tous les sujets",
    hub_btn_signup: "Accès complet — Inscription gratuite",
    hub_by_specialty: "Parcourir par spécialité",
    spec_cardiology: "Cardiologie",
    spec_neurology: "Neurologie",
    spec_internal: "Médecine interne",
    spec_pharmacology: "Pharmacologie",
    spec_pediatrics: "Pédiatrie",
    spec_surgery: "Chirurgie",
    spec_obstetrics: "Obstétrique & Gynécologie",
    spec_psychiatry: "Psychiatrie",
    card_topics_title: "Sujets médicaux",
    card_topics_subtitle: "Parcourir par spécialité",
    card_topics_desc:
      "Cardiologie, neurologie, pharmacologie, chirurgie et plus — chaque sujet décomposé en leçons claires sans jargon. Comprenez ce que dit votre médecin.",
    card_topics_cta: "Explorer les sujets →",
    card_drugs_title: "Guide des médicaments",
    card_drugs_subtitle: "Ce que font les médicaments",
    card_drugs_desc:
      "Comprenez le but, le mécanisme et la sécurité des médicaments courants. Explications simples sans dosage — consultez toujours votre médecin.",
    card_drugs_cta: "Parcourir les médicaments →",
    card_glossary_title: "Glossaire médical",
    card_glossary_subtitle: "Termes expliqués simplement",
    card_glossary_desc:
      "Glossaire A-Z des termes médicaux traduits en langage quotidien. Ne soyez plus jamais perdu face à un diagnostic ou un bilan de laboratoire.",
    card_glossary_cta: "Ouvrir le glossaire →",
    card_pets_title: "Santé animale",
    card_pets_subtitle: "Guides vétérinaires pour propriétaires",
    card_pets_desc:
      "Apprenez les maladies courantes, les médicaments et quand consulter un vétérinaire. Écrit pour les propriétaires d'animaux, pas les vétérinaires.",
    card_pets_cta: "Guide santé animale →",
    pro_h2: "Êtes-vous un professionnel de santé ?",
    pro_desc:
      "Accédez aux leçons cliniques complètes, au tuteur IA, aux simulations de cas, aux flashcards, aux dosages et au suivi CME.",
    pro_start: "Commencer gratuitement →",
    pro_how: "Comment ça marche",
    topics_h1: "Sujets médicaux",
    topics_count: "{count} sujets dans {specs} spécialités — expliqués en langage clair.",
    topics_empty_desc:
      "Guides de santé en langage clair pour les patients, les étudiants et les esprits curieux.",
    topics_coming_soon: "Sujets bientôt disponibles",
    topics_coming_desc:
      "Nous créons des résumés en langage clair pour tout notre contenu médical.",
    topics_notify: "Me notifier quand c'est prêt",
    topics_cta_h2: "Prêt à aller plus loin ?",
    topics_cta_desc:
      "Leçons complètes, tuteur IA, flashcards et cas cliniques — pour les étudiants, médecins et esprits curieux.",
    topics_cta_btn: "Apprendre gratuitement →",
    drugs_h1: "Guide des médicaments",
    drugs_count: "{count} médicaments expliqués en langage clair.",
    drugs_empty_desc: "Guides médicaments en langage clair pour les patients et les curieux.",
    drugs_disclaimer:
      "Information éducative uniquement — sans recommandations de dosage. Consultez toujours votre médecin ou pharmacien.",
    drugs_search_placeholder: "Rechercher un médicament…",
    drugs_search_btn: "Rechercher",
    drugs_no_results: "Aucun résultat",
    drugs_no_results_hint: 'Aucun médicament correspondant à "{search}". Essayez un terme différent.',
    drugs_coming_soon: "Guides médicaments bientôt disponibles",
    drugs_coming_desc: "Nous construisons des guides en langage clair pour tous les médicaments principaux.",
    drugs_clear_search: "Effacer la recherche",
    drugs_cta_h2: "Vous avez besoin de détails cliniques complets ?",
    drugs_cta_desc:
      "Dosage, interactions, effets indésirables et perles cliniques — disponibles pour les professionnels de santé.",
    drugs_cta_btn: "Créer un compte gratuit →",
    pets_h1: "Guides de santé animale",
    pets_subtitle: "Informations de santé fiables pour les propriétaires de chiens et chats — rédigées en langage clair par des professionnels vétérinaires. Sans jargon, sans conseils de dosage.",
    pets_disclaimer: "Ce contenu est à titre éducatif uniquement et ne constitue pas un avis vétérinaire. Si votre animal est malade, contactez immédiatement un vétérinaire.",
    pets_lesson_singular: "leçon",
    pets_lesson_plural: "leçons",
    pets_empty: "Contenu santé animale bientôt disponible.",
    pets_pro_h2: "Étudiants et professionnels vétérinaires",
    pets_pro_desc: "Modules cliniques complets, dosages par espèce, QCM, cas cliniques et flashcards de révision espacée.",
    pets_pro_btn: "Parcourir les modules vétérinaires →",
    pets_back: "← Retour à tous les guides de santé animale",
    pets_key_points: "Points clés",
    pets_glossary_section: "Glossaire de cette section",
    pets_glossary_full: "Glossaire complet",
    pets_vet_h2: "Êtes-vous vétérinaire ou étudiant vétérinaire ?",
    pets_vet_desc: "Modules cliniques complets avec dosages, cas cliniques et révision espacée.",
    pets_vet_btn: "Explorer les modules vétérinaires →",
    pets_footer_note: "Les informations sur cette page sont à titre éducatif général uniquement et ne constituent pas un conseil médical vétérinaire. Consultez toujours un vétérinaire qualifié pour les problèmes de santé de votre animal.",
    vet_h1: "Médecine vétérinaire",
    vet_badge: "Pour étudiants et professionnels vétérinaires",
    vet_subtitle: "Modules cliniques couvrant les petits animaux, grands animaux, exotiques, pharmacologie, chirurgie et plus — pour étudiants et praticiens vétérinaires.",
    vet_disclaimer: "Contenu éducatif clinique pour les professionnels vétérinaires. Ne remplace pas le jugement clinique.",
    vet_specs_title: "Spécialités couvertes",
    vet_modules_label: "modules",
    vet_cta_h2: "Accès complet pour les professionnels vétérinaires",
    vet_cta_desc: "Dosages par espèce, cas cliniques, QCM, révision espacée et suivi CME — tout sur une seule plateforme.",
    vet_cta_login: "Se connecter",
    vet_cta_signup: "Créer un compte gratuit →",
    vet_pet_owners: "Vous cherchez des guides pour propriétaires ?",
    vet_pet_owners_link: "Guides de santé animale →",
    card_vet_title: "Médecine vétérinaire",
    card_vet_subtitle: "Pour étudiants et professionnels",
    card_vet_desc: "Modules cliniques sur les petits animaux, grands animaux, pharmacologie, chirurgie et espèces exotiques — avec dosages par espèce et cas cliniques.",
    card_vet_cta: "Explorer les modules vétérinaires →",
  },

  // ── Spanish ───────────────────────────────────────────────────────────────────
  es: {
    nav_glossary: "Glosario",
    nav_topics: "Temas",
    nav_drugs: "Medicamentos",
    nav_get_started: "Comenzar gratis",
    disclaimer:
      "Solo contenido educativo. Esta información no reemplaza el consejo médico profesional. Consulte siempre a un profesional de salud cualificado para el diagnóstico y tratamiento.",
    footer_tagline:
      "Plataforma educativa para estudiantes de medicina, médicos y todos los curiosos de la medicina",
    hub_badge: "Gratis · Sin cuenta requerida",
    hub_h1: "Entiende la medicina,",
    hub_h1_accent: "sin título médico",
    hub_subtitle:
      "Guías en lenguaje sencillo sobre temas médicos, medicamentos y enfermedades — para pacientes, estudiantes y cualquier persona curiosa sobre la salud.",
    hub_stat_topics: "temas médicos",
    hub_stat_drugs: "guías de medicamentos",
    hub_stat_glossary: "términos del glosario",
    hub_btn_browse: "Ver todos los temas",
    hub_btn_signup: "Acceso completo — Registro gratuito",
    hub_by_specialty: "Explorar por especialidad",
    spec_cardiology: "Cardiología",
    spec_neurology: "Neurología",
    spec_internal: "Medicina Interna",
    spec_pharmacology: "Farmacología",
    spec_pediatrics: "Pediatría",
    spec_surgery: "Cirugía",
    spec_obstetrics: "Obstetricia y Ginecología",
    spec_psychiatry: "Psiquiatría",
    card_topics_title: "Temas Médicos",
    card_topics_subtitle: "Explorar por especialidad",
    card_topics_desc:
      "Cardiología, neurología, farmacología, cirugía y más — cada tema desglosado en lecciones claras y sin jerga. Entiende lo que te dice tu médico.",
    card_topics_cta: "Explorar Temas →",
    card_drugs_title: "Guía de Medicamentos",
    card_drugs_subtitle: "Qué hacen los medicamentos",
    card_drugs_desc:
      "Comprende el propósito, mecanismo y seguridad de los medicamentos comunes. Explicaciones sencillas sin dosis — consulta siempre a tu médico.",
    card_drugs_cta: "Ver Medicamentos →",
    card_glossary_title: "Glosario Médico",
    card_glossary_subtitle: "Términos explicados simplemente",
    card_glossary_desc:
      "Glosario A-Z de términos médicos traducidos al lenguaje cotidiano. Nunca más confundido por un diagnóstico o informe de laboratorio.",
    card_glossary_cta: "Abrir Glosario →",
    card_pets_title: "Salud de Mascotas",
    card_pets_subtitle: "Guías veterinarias para dueños",
    card_pets_desc:
      "Aprende sobre enfermedades comunes, medicamentos y cuándo visitar al veterinario. Escrito para dueños de mascotas, no para veterinarios.",
    card_pets_cta: "Guía de Salud Animal →",
    pro_h2: "¿Eres profesional de la salud?",
    pro_desc:
      "Obtén acceso a lecciones clínicas completas, tutor IA, simulaciones de casos, tarjetas de estudio, dosificación de medicamentos y seguimiento CME.",
    pro_start: "Empezar gratis →",
    pro_how: "Cómo funciona",
    topics_h1: "Temas Médicos",
    topics_count: "{count} temas en {specs} especialidades — explicados en lenguaje sencillo.",
    topics_empty_desc:
      "Guías de salud en lenguaje sencillo para pacientes, estudiantes y mentes curiosas.",
    topics_coming_soon: "Temas próximamente",
    topics_coming_desc:
      "Estamos generando resúmenes en lenguaje sencillo para todo nuestro contenido médico.",
    topics_notify: "Avisarme cuando esté listo",
    topics_cta_h2: "¿Listo para profundizar?",
    topics_cta_desc:
      "Lecciones completas, tutor IA, tarjetas de estudio y casos clínicos — para estudiantes, médicos y mentes curiosas.",
    topics_cta_btn: "Aprender Gratis →",
    drugs_h1: "Guía de Medicamentos",
    drugs_count: "{count} medicamentos explicados en lenguaje sencillo.",
    drugs_empty_desc:
      "Guías de medicamentos en lenguaje sencillo para pacientes y curiosos.",
    drugs_disclaimer:
      "Esta es información educativa únicamente — sin consejos de dosificación. Consulta siempre a tu médico o farmacéutico.",
    drugs_search_placeholder: "Buscar medicamentos…",
    drugs_search_btn: "Buscar",
    drugs_no_results: "Sin resultados",
    drugs_no_results_hint: 'Ningún medicamento coincide con "{search}". Prueba con un término diferente.',
    drugs_coming_soon: "Guías de medicamentos próximamente",
    drugs_coming_desc:
      "Estamos creando guías en lenguaje sencillo para todos los medicamentos principales.",
    drugs_clear_search: "Borrar búsqueda",
    drugs_cta_h2: "¿Necesitas detalles clínicos completos?",
    drugs_cta_desc:
      "Dosificación, interacciones, efectos adversos y perlas clínicas — disponibles para profesionales de la salud.",
    drugs_cta_btn: "Crear Cuenta Gratis →",
    pets_h1: "Guías de Salud Animal",
    pets_subtitle: "Información de salud basada en evidencia para dueños de perros y gatos — escrita en lenguaje sencillo por profesionales veterinarios. Sin jerga, sin consejos de dosis.",
    pets_disclaimer: "Este contenido es solo educativo y no constituye asesoramiento veterinario. Si tu mascota está enferma, contacta a un veterinario de inmediato.",
    pets_lesson_singular: "lección",
    pets_lesson_plural: "lecciones",
    pets_empty: "Contenido de salud animal próximamente.",
    pets_pro_h2: "Estudiantes y profesionales veterinarios",
    pets_pro_desc: "Módulos clínicos completos, dosificación por especie, preguntas tipo test, casos clínicos y tarjetas de repaso espaciado.",
    pets_pro_btn: "Ver módulos veterinarios →",
    pets_back: "← Volver a todas las guías de salud animal",
    pets_key_points: "Puntos clave",
    pets_glossary_section: "Glosario de esta sección",
    pets_glossary_full: "Glosario completo",
    pets_vet_h2: "¿Eres veterinario o estudiante de veterinaria?",
    pets_vet_desc: "Módulos clínicos completos con dosificación de medicamentos, casos clínicos y repaso espaciado.",
    pets_vet_btn: "Explorar módulos veterinarios →",
    pets_footer_note: "La información en esta página es solo para fines educativos generales y no constituye asesoramiento médico veterinario. Consulta siempre a un veterinario cualificado para los problemas de salud de tu mascota.",
    vet_h1: "Medicina Veterinaria",
    vet_badge: "Para estudiantes y profesionales veterinarios",
    vet_subtitle: "Módulos clínicos que cubren animales pequeños, grandes, exóticos, farmacología, cirugía y más — para estudiantes y practicantes veterinarios.",
    vet_disclaimer: "Contenido educativo clínico para profesionales veterinarios. No sustituye el juicio clínico.",
    vet_specs_title: "Especialidades cubiertas",
    vet_modules_label: "módulos",
    vet_cta_h2: "Acceso completo para profesionales veterinarios",
    vet_cta_desc: "Dosificación por especie, casos clínicos, preguntas tipo test, repaso espaciado y seguimiento CME — todo en una plataforma.",
    vet_cta_login: "Iniciar sesión",
    vet_cta_signup: "Crear cuenta gratis →",
    vet_pet_owners: "¿Buscas guías para dueños de mascotas?",
    vet_pet_owners_link: "Guías de Salud Animal →",
    card_vet_title: "Medicina Veterinaria",
    card_vet_subtitle: "Para estudiantes y profesionales",
    card_vet_desc: "Módulos clínicos de animales pequeños, grandes, farmacología, cirugía y especies exóticas — con dosificación por especie y casos clínicos.",
    card_vet_cta: "Explorar módulos veterinarios →",
  },
};

export function getLearnT(lang: string | null | undefined): LearnStrings {
  const locale = (lang && lang in translations ? lang : "en") as LearnLocale;
  return translations[locale];
}

export function interpolate(template: string, vars: Record<string, string | number>): string {
  return Object.entries(vars).reduce(
    (s, [k, v]) => s.replace(`{${k}}`, String(v)),
    template
  );
}
