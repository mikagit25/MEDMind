/**
 * Server-safe translations for trust pages: /about, /editorial-policy,
 * /medical-disclaimer, /contact.
 * Used by server components that cannot access useI18n() hooks.
 */

export type TrustLocale = "en" | "ru" | "ar" | "tr" | "de" | "fr" | "es";

export interface TrustT {
  dir: "ltr" | "rtl";
  // Shared footer labels
  footer_tagline: string;
  footer_editorial: string;
  footer_about: string;
  footer_disclaimer: string;
  footer_contact: string;
  // Shared disclaimer line used in every footer
  disclaimer_short: string;
}

export interface AboutT extends TrustT {
  meta_title: string;
  meta_desc: string;
  hero_title: string;
  hero_sub: string;
  mission_title: string;
  mission_body: string;
  for_whom_title: string;
  for_whom_doctors: string;
  for_whom_students: string;
  for_whom_patients: string;
  for_whom_vet: string;
  how_title: string;
  how_1_title: string;
  how_1_body: string;
  how_2_title: string;
  how_2_body: string;
  how_3_title: string;
  how_3_body: string;
  how_4_title: string;
  how_4_body: string;
  team_title: string;
  team_body: string;
  cta_title: string;
  cta_btn: string;
}

export interface EditorialT extends TrustT {
  meta_title: string;
  meta_desc: string;
  hero_title: string;
  hero_sub: string;
  sources_title: string;
  sources_body: string;
  sources_tier1: string;
  sources_tier2: string;
  sources_tier3: string;
  generation_title: string;
  generation_body: string;
  verification_title: string;
  verification_body: string;
  verification_steps: string[];
  human_review_title: string;
  human_review_body: string;
  updates_title: string;
  updates_body: string;
  feedback_title: string;
  feedback_body: string;
}

export interface DisclaimerT extends TrustT {
  meta_title: string;
  meta_desc: string;
  hero_title: string;
  hero_sub: string;
  not_advice_title: string;
  not_advice_body: string;
  emergency_title: string;
  emergency_body: string;
  accuracy_title: string;
  accuracy_body: string;
  professional_title: string;
  professional_body: string;
  dosing_title: string;
  dosing_body: string;
  liability_title: string;
  liability_body: string;
  contact_note: string;
}

export interface ContactT extends TrustT {
  meta_title: string;
  meta_desc: string;
  hero_title: string;
  hero_sub: string;
  general_title: string;
  general_email: string;
  press_title: string;
  press_email: string;
  partnership_title: string;
  partnership_email: string;
  feedback_title: string;
  feedback_body: string;
  response_note: string;
}

// ── Translations ──────────────────────────────────────────────────────────────

const SHARED: Record<TrustLocale, TrustT> = {
  en: {
    dir: "ltr",
    footer_tagline: "Medicine, understood by everyone",
    footer_editorial: "Editorial Policy",
    footer_about: "About",
    footer_disclaimer: "Medical Disclaimer",
    footer_contact: "Contact",
    disclaimer_short: "For educational purposes only. Not a substitute for professional medical advice.",
  },
  ru: {
    dir: "ltr",
    footer_tagline: "Медицина, понятная каждому",
    footer_editorial: "Редакционная политика",
    footer_about: "О проекте",
    footer_disclaimer: "Медицинский дисклеймер",
    footer_contact: "Контакты",
    disclaimer_short: "Только в образовательных целях. Не заменяет консультацию врача.",
  },
  de: {
    dir: "ltr",
    footer_tagline: "Medizin, die jeder versteht",
    footer_editorial: "Redaktionelle Richtlinien",
    footer_about: "Über uns",
    footer_disclaimer: "Medizinischer Haftungsausschluss",
    footer_contact: "Kontakt",
    disclaimer_short: "Nur zu Bildungszwecken. Kein Ersatz für professionellen medizinischen Rat.",
  },
  fr: {
    dir: "ltr",
    footer_tagline: "La médecine comprise de tous",
    footer_editorial: "Politique éditoriale",
    footer_about: "À propos",
    footer_disclaimer: "Avertissement médical",
    footer_contact: "Contact",
    disclaimer_short: "À des fins éducatives uniquement. Ne remplace pas les conseils médicaux professionnels.",
  },
  es: {
    dir: "ltr",
    footer_tagline: "Medicina al alcance de todos",
    footer_editorial: "Política editorial",
    footer_about: "Acerca de",
    footer_disclaimer: "Aviso médico",
    footer_contact: "Contacto",
    disclaimer_short: "Solo con fines educativos. No sustituye el consejo médico profesional.",
  },
  tr: {
    dir: "ltr",
    footer_tagline: "Herkesin anlayacağı tıp",
    footer_editorial: "Editoryal Politika",
    footer_about: "Hakkında",
    footer_disclaimer: "Tıbbi Sorumluluk Reddi",
    footer_contact: "İletişim",
    disclaimer_short: "Yalnızca eğitim amaçlıdır. Profesyonel tıbbi tavsiyenin yerini tutmaz.",
  },
  ar: {
    dir: "rtl",
    footer_tagline: "الطب بلغة الجميع",
    footer_editorial: "السياسة التحريرية",
    footer_about: "حول المشروع",
    footer_disclaimer: "إخلاء المسؤولية الطبية",
    footer_contact: "تواصل معنا",
    disclaimer_short: "لأغراض تعليمية فقط. لا يغني عن استشارة الطبيب.",
  },
};

const ABOUT: Record<TrustLocale, Omit<AboutT, keyof TrustT>> = {
  en: {
    meta_title: "About MedMind AI — Medical Education Platform",
    meta_desc: "Learn about MedMind AI: our mission to make evidence-based medicine accessible to everyone, our team, and our technology.",
    hero_title: "Medicine, understood by everyone, in their language",
    hero_sub: "MedMind AI is an evidence-based medical education platform powered by AI — for doctors, students, patients, and veterinarians.",
    mission_title: "Our Mission",
    mission_body: "We believe that access to reliable medical knowledge should not depend on language, geography, or professional credentials. MedMind AI combines the rigor of evidence-based medicine with the accessibility of AI — delivering verified medical content in 7 languages, interactive learning tools for healthcare professionals, and plain-language explanations for patients.",
    for_whom_title: "Who We Serve",
    for_whom_doctors: "Physicians & Residents — clinical modules, drug interactions, CME-ready content",
    for_whom_students: "Medical & Nursing Students — structured curriculum, spaced-repetition flashcards, MCQs",
    for_whom_patients: "Patients & Caregivers — plain-language articles, symptom guides, no medical jargon",
    for_whom_vet: "Veterinary Professionals — species-specific drug dosing, veterinary clinical cases",
    how_title: "How Our Content Is Created",
    how_1_title: "1. Evidence-Based Sources",
    how_1_body: "Every article starts with peer-reviewed sources: clinical guidelines (WHO, NICE, AHA, ESC), systematic reviews, and indexed PubMed research.",
    how_2_title: "2. AI Generation",
    how_2_body: "Content is drafted by Claude AI with explicit source citations and structured medical formatting.",
    how_3_title: "3. Automated Verification",
    how_3_body: "Our claim-checking pipeline extracts every factual assertion and verifies it against its cited sources — automatically, before publication.",
    how_4_title: "4. Human Review",
    how_4_body: "Selected articles are reviewed and approved by licensed healthcare professionals, marked with a verified badge.",
    team_title: "The Team",
    team_body: "MedMind AI was founded in 2025 by a team of physicians, software engineers, and AI researchers. We are building the infrastructure for trustworthy AI-assisted medical education.",
    cta_title: "Start Learning for Free",
    cta_btn: "Create Free Account",
  },
  ru: {
    meta_title: "О проекте MedMind AI — платформа медицинского образования",
    meta_desc: "Узнайте о MedMind AI: наша миссия — сделать доказательную медицину доступной для всех.",
    hero_title: "Медицина, понятная каждому, на его языке",
    hero_sub: "MedMind AI — это AI-платформа для медицинского образования на основе доказательной медицины для врачей, студентов, пациентов и ветеринаров.",
    mission_title: "Наша миссия",
    mission_body: "Мы убеждены, что доступ к надёжным медицинским знаниям не должен зависеть от языка, географии или профессионального статуса. MedMind AI объединяет строгость доказательной медицины с доступностью ИИ — верифицированный медицинский контент на 7 языках, интерактивные инструменты обучения для специалистов и понятные объяснения для пациентов.",
    for_whom_title: "Для кого мы работаем",
    for_whom_doctors: "Врачи и ординаторы — клинические модули, взаимодействия препаратов, контент для НМО",
    for_whom_students: "Студенты медицинских и сестринских специальностей — структурированная программа, карточки с интервальным повторением, тесты",
    for_whom_patients: "Пациенты и их родственники — статьи на понятном языке, руководства по симптомам без медицинского жаргона",
    for_whom_vet: "Ветеринарные специалисты — дозирование препаратов по видам животных, клинические случаи",
    how_title: "Как создаётся наш контент",
    how_1_title: "1. Доказательная база",
    how_1_body: "Каждая статья начинается с рецензируемых источников: клинических руководств (ВОЗ, NICE, AHA, ESC), систематических обзоров и индексированных исследований PubMed.",
    how_2_title: "2. Генерация ИИ",
    how_2_body: "Контент создаётся Claude AI с явными ссылками на источники и структурированным медицинским форматированием.",
    how_3_title: "3. Автоматическая верификация",
    how_3_body: "Наш конвейер проверки утверждений извлекает каждое фактическое утверждение и автоматически проверяет его по цитируемым источникам до публикации.",
    how_4_title: "4. Человеческая рецензия",
    how_4_body: "Отдельные статьи проверяются и одобряются лицензированными медицинскими специалистами и отмечаются значком верификации.",
    team_title: "Команда",
    team_body: "MedMind AI основана в 2025 году командой врачей, разработчиков и исследователей ИИ. Мы строим инфраструктуру для надёжного медицинского образования с помощью ИИ.",
    cta_title: "Начните учиться бесплатно",
    cta_btn: "Создать бесплатный аккаунт",
  },
  de: {
    meta_title: "Über MedMind AI — Medizinische Bildungsplattform",
    meta_desc: "Erfahren Sie mehr über MedMind AI: unsere Mission, evidenzbasierte Medizin für alle zugänglich zu machen.",
    hero_title: "Medizin, die jeder in seiner Sprache versteht",
    hero_sub: "MedMind AI ist eine KI-gestützte Plattform für medizinische Bildung — für Ärzte, Studierende, Patienten und Tierärzte.",
    mission_title: "Unsere Mission",
    mission_body: "Wir glauben, dass der Zugang zu zuverlässigem medizinischem Wissen nicht von Sprache, Geografie oder beruflichem Status abhängen sollte.",
    for_whom_title: "Für wen wir arbeiten",
    for_whom_doctors: "Ärzte & Assistenzärzte — klinische Module, Arzneimittelinteraktionen, CME-Inhalte",
    for_whom_students: "Medizin- und Pflegestudierende — strukturierter Lehrplan, Lernkarten, Multiple-Choice-Fragen",
    for_whom_patients: "Patienten & Pflegende — Artikel in verständlicher Sprache, Symptomführer",
    for_whom_vet: "Tierärztliche Fachkräfte — Dosierung nach Tierart, veterinärmedizinische Fälle",
    how_title: "Wie unsere Inhalte erstellt werden",
    how_1_title: "1. Evidenzbasierte Quellen",
    how_1_body: "Jeder Artikel basiert auf begutachteten Quellen: Klinische Leitlinien (WHO, NICE, AHA, ESC), systematische Übersichtsarbeiten und PubMed-Studien.",
    how_2_title: "2. KI-Generierung",
    how_2_body: "Inhalte werden von Claude KI mit expliziten Quellenangaben und strukturierter medizinischer Formatierung erstellt.",
    how_3_title: "3. Automatisierte Überprüfung",
    how_3_body: "Unsere Claim-Checking-Pipeline extrahiert jede Behauptung und überprüft sie automatisch anhand der zitierten Quellen.",
    how_4_title: "4. Menschliche Überprüfung",
    how_4_body: "Ausgewählte Artikel werden von lizenzierten Gesundheitsfachkräften geprüft und mit einem Verifizierungs-Badge versehen.",
    team_title: "Das Team",
    team_body: "MedMind AI wurde 2025 von einem Team aus Ärzten, Softwareentwicklern und KI-Forschern gegründet.",
    cta_title: "Kostenlos lernen starten",
    cta_btn: "Kostenloses Konto erstellen",
  },
  fr: {
    meta_title: "À propos de MedMind AI — Plateforme d'éducation médicale",
    meta_desc: "Découvrez MedMind AI: notre mission de rendre la médecine fondée sur les preuves accessible à tous.",
    hero_title: "La médecine, comprise de tous, dans leur langue",
    hero_sub: "MedMind AI est une plateforme d'éducation médicale propulsée par l'IA — pour les médecins, étudiants, patients et vétérinaires.",
    mission_title: "Notre mission",
    mission_body: "Nous croyons que l'accès à des connaissances médicales fiables ne devrait pas dépendre de la langue, de la géographie ou des diplômes professionnels.",
    for_whom_title: "Pour qui nous travaillons",
    for_whom_doctors: "Médecins et internes — modules cliniques, interactions médicamenteuses, contenu DPC",
    for_whom_students: "Étudiants en médecine et soins infirmiers — programme structuré, fiches de révision, QCM",
    for_whom_patients: "Patients et aidants — articles en langage simple, guides des symptômes",
    for_whom_vet: "Professionnels vétérinaires — posologie par espèce, cas cliniques vétérinaires",
    how_title: "Comment notre contenu est créé",
    how_1_title: "1. Sources fondées sur les preuves",
    how_1_body: "Chaque article commence par des sources évaluées par des pairs: recommandations cliniques (OMS, NICE, AHA, ESC), revues systématiques et recherches PubMed.",
    how_2_title: "2. Génération par IA",
    how_2_body: "Le contenu est rédigé par Claude IA avec des citations explicites et un formatage médical structuré.",
    how_3_title: "3. Vérification automatisée",
    how_3_body: "Notre pipeline extrait chaque affirmation factuelle et la vérifie automatiquement par rapport aux sources citées.",
    how_4_title: "4. Révision humaine",
    how_4_body: "Des articles sélectionnés sont examinés et approuvés par des professionnels de santé agréés.",
    team_title: "L'équipe",
    team_body: "MedMind AI a été fondée en 2025 par une équipe de médecins, ingénieurs et chercheurs en IA.",
    cta_title: "Commencer à apprendre gratuitement",
    cta_btn: "Créer un compte gratuit",
  },
  es: {
    meta_title: "Acerca de MedMind AI — Plataforma de educación médica",
    meta_desc: "Conozca MedMind AI: nuestra misión de hacer accesible la medicina basada en la evidencia para todos.",
    hero_title: "Medicina al alcance de todos, en su idioma",
    hero_sub: "MedMind AI es una plataforma de educación médica impulsada por IA — para médicos, estudiantes, pacientes y veterinarios.",
    mission_title: "Nuestra misión",
    mission_body: "Creemos que el acceso al conocimiento médico confiable no debe depender del idioma, la geografía o las credenciales profesionales.",
    for_whom_title: "A quién servimos",
    for_whom_doctors: "Médicos y residentes — módulos clínicos, interacciones farmacológicas, contenido para formación continua",
    for_whom_students: "Estudiantes de medicina y enfermería — plan de estudios estructurado, tarjetas de memoria, preguntas tipo test",
    for_whom_patients: "Pacientes y cuidadores — artículos en lenguaje sencillo, guías de síntomas",
    for_whom_vet: "Profesionales veterinarios — dosificación por especie, casos clínicos veterinarios",
    how_title: "Cómo se crea nuestro contenido",
    how_1_title: "1. Fuentes basadas en evidencia",
    how_1_body: "Cada artículo comienza con fuentes revisadas por pares: guías clínicas (OMS, NICE, AHA, ESC), revisiones sistemáticas e investigaciones indexadas en PubMed.",
    how_2_title: "2. Generación por IA",
    how_2_body: "El contenido es redactado por Claude IA con citas explícitas y formato médico estructurado.",
    how_3_title: "3. Verificación automatizada",
    how_3_body: "Nuestra canalización extrae cada afirmación factual y la verifica automáticamente frente a las fuentes citadas.",
    how_4_title: "4. Revisión humana",
    how_4_body: "Artículos seleccionados son revisados y aprobados por profesionales sanitarios con licencia.",
    team_title: "El equipo",
    team_body: "MedMind AI fue fundada en 2025 por un equipo de médicos, ingenieros de software e investigadores de IA.",
    cta_title: "Empiece a aprender gratis",
    cta_btn: "Crear cuenta gratuita",
  },
  tr: {
    meta_title: "MedMind AI Hakkında — Tıp Eğitim Platformu",
    meta_desc: "MedMind AI hakkında bilgi edinin: kanıta dayalı tıbbı herkes için erişilebilir kılma misyonumuz.",
    hero_title: "Tıp, herkesin kendi dilinde anlayabileceği şekilde",
    hero_sub: "MedMind AI, doktorlar, öğrenciler, hastalar ve veterinerler için yapay zeka destekli tıp eğitim platformudur.",
    mission_title: "Misyonumuz",
    mission_body: "Güvenilir tıbbi bilgiye erişimin dil, coğrafya veya mesleki kimlik bilgilerine bağlı olmaması gerektiğine inanıyoruz.",
    for_whom_title: "Kime hizmet veriyoruz",
    for_whom_doctors: "Hekimler ve asistan doktorlar — klinik modüller, ilaç etkileşimleri, STE içerikleri",
    for_whom_students: "Tıp ve hemşirelik öğrencileri — yapılandırılmış müfredat, aralıklı tekrar kartları, çoktan seçmeli sorular",
    for_whom_patients: "Hastalar ve bakıcılar — sade dilde makaleler, belirti rehberleri",
    for_whom_vet: "Veteriner profesyoneller — türe göre ilaç dozajı, veteriner klinik vakalar",
    how_title: "İçeriklerimiz nasıl oluşturulur",
    how_1_title: "1. Kanıta Dayalı Kaynaklar",
    how_1_body: "Her makale hakemli kaynaklarla başlar: klinik kılavuzlar (WHO, NICE, AHA, ESC), sistematik derlemeler ve PubMed araştırmaları.",
    how_2_title: "2. Yapay Zeka Üretimi",
    how_2_body: "İçerik, açık kaynak atıfları ve yapılandırılmış tıbbi biçimlendirme ile Claude yapay zeka tarafından hazırlanır.",
    how_3_title: "3. Otomatik Doğrulama",
    how_3_body: "İddia kontrol hattımız her gerçeksel beyanı çıkarır ve yayımdan önce otomatik olarak atıfta bulunulan kaynaklara göre doğrular.",
    how_4_title: "4. Uzman İncelemesi",
    how_4_body: "Seçilmiş makaleler lisanslı sağlık profesyonelleri tarafından incelenir ve onaylanır.",
    team_title: "Ekip",
    team_body: "MedMind AI, 2025 yılında hekimler, yazılım mühendisleri ve yapay zeka araştırmacılarından oluşan bir ekip tarafından kurulmuştur.",
    cta_title: "Ücretsiz öğrenmeye başlayın",
    cta_btn: "Ücretsiz hesap oluştur",
  },
  ar: {
    meta_title: "حول MedMind AI — منصة التعليم الطبي",
    meta_desc: "تعرّف على MedMind AI: مهمتنا لجعل الطب المبني على الأدلة متاحاً للجميع.",
    hero_title: "الطب، مفهوم للجميع، بلغتهم",
    hero_sub: "MedMind AI منصة تعليم طبي مدعومة بالذكاء الاصطناعي — للأطباء والطلاب والمرضى والبيطريين.",
    mission_title: "مهمتنا",
    mission_body: "نؤمن بأن الوصول إلى المعرفة الطبية الموثوقة لا ينبغي أن يعتمد على اللغة أو الموقع الجغرافي أو المؤهلات المهنية.",
    for_whom_title: "من نخدم",
    for_whom_doctors: "الأطباء والمقيمون — وحدات سريرية، تفاعلات الأدوية، محتوى التعليم الطبي المستمر",
    for_whom_students: "طلاب الطب والتمريض — مناهج منظمة، بطاقات مراجعة، أسئلة اختيار من متعدد",
    for_whom_patients: "المرضى ومقدمو الرعاية — مقالات بلغة بسيطة، أدلة الأعراض",
    for_whom_vet: "الأطباء البيطريون — جرعات الدواء حسب النوع، الحالات السريرية البيطرية",
    how_title: "كيف يُنشأ محتوانا",
    how_1_title: "١. مصادر مبنية على الأدلة",
    how_1_body: "يبدأ كل مقال بمصادر محكّمة: الإرشادات السريرية (WHO، NICE، AHA، ESC)، المراجعات المنهجية وأبحاث PubMed.",
    how_2_title: "٢. توليد الذكاء الاصطناعي",
    how_2_body: "يُصاغ المحتوى بواسطة Claude AI مع استشهادات صريحة بالمصادر وتنسيق طبي منظم.",
    how_3_title: "٣. التحقق التلقائي",
    how_3_body: "تستخرج خطوط معالجة التحقق كل ادعاء حقيقي وتتحقق منه تلقائياً مقابل المصادر المستشهد بها قبل النشر.",
    how_4_title: "٤. المراجعة البشرية",
    how_4_body: "تُراجَع مقالات مختارة وتُعتمَد من قبل متخصصين في الرعاية الصحية مرخصين.",
    team_title: "الفريق",
    team_body: "تأسست MedMind AI عام 2025 من قبل فريق من الأطباء ومهندسي البرمجيات وباحثي الذكاء الاصطناعي.",
    cta_title: "ابدأ التعلم مجاناً",
    cta_btn: "إنشاء حساب مجاني",
  },
};

const EDITORIAL: Record<TrustLocale, Omit<EditorialT, keyof TrustT>> = {
  en: {
    meta_title: "Editorial Policy — MedMind AI",
    meta_desc: "How MedMind AI creates, verifies, and updates medical content: source hierarchy, AI generation, automated verification, and human review.",
    hero_title: "Editorial Policy",
    hero_sub: "How we create, verify, and maintain every piece of medical content on MedMind AI.",
    sources_title: "Source Hierarchy",
    sources_body: "All content on MedMind AI is grounded in a strict hierarchy of evidence:",
    sources_tier1: "Tier 1 — Clinical guidelines and official recommendations (WHO, NICE, AHA, ACC, ESC, CDC, EMA, national health authorities). These are the primary source for clinical recommendations.",
    sources_tier2: "Tier 2 — Systematic reviews and meta-analyses from peer-reviewed journals (NEJM, The Lancet, BMJ, JAMA, Cochrane). Used to validate statistical claims.",
    sources_tier3: "Tier 3 — Individual randomized controlled trials and observational studies. Referenced only when Tier 1–2 sources are unavailable, and explicitly labeled as such. We never present a single study as established consensus.",
    generation_title: "AI-Assisted Generation",
    generation_body: "Articles are drafted by Claude AI (Anthropic) with a strict system prompt requiring source citations for every factual claim. The AI is instructed to use hedged language for single-study claims ('a study showed…' not 'it is proven that…'), to state dosages only from official prescribing information, and to flag areas of active clinical debate.",
    verification_title: "Automated Verification (V4 Pipeline)",
    verification_body: "Every article goes through our automated claim-checking pipeline before publication:",
    verification_steps: [
      "Claim extraction: Claude Haiku extracts all verifiable factual assertions (statistics, dosages, causal claims, clinical recommendations)",
      "Source matching: each claim is checked against the article's declared sources by fetching the source and asking Haiku: 'does this source support the claim?'",
      "Verdict: 'yes/partial' for all claims → status = passed; any 'no' → status = failed, article hidden from public endpoints",
      "Only articles with status 'passed' or 'human_reviewed' are served on public routes and included in sitemaps",
    ],
    human_review_title: "Human Expert Review",
    human_review_body: "Articles selected for high-traffic topics or complex clinical decisions are reviewed by licensed healthcare professionals. A reviewed article receives the 'human_reviewed' verification status and displays the reviewer's credentials on the article page. Reviewer profiles are published at /reviewers/[slug].",
    updates_title: "Content Updates",
    updates_body: "Medical knowledge evolves. Articles are flagged for re-review when: (1) a guideline update is detected via our news pipeline, (2) users report an error via the feedback button, (3) a scheduled re-verification fails. Updated content goes back through the full verification pipeline before republication.",
    feedback_title: "Reporting Errors",
    feedback_body: "Every public article has a 'Report an error' button. Reports are reviewed by our editorial team within 5 business days. If an error is confirmed, the article is hidden from public access until corrected and re-verified.",
  },
  ru: {
    meta_title: "Редакционная политика — MedMind AI",
    meta_desc: "Как MedMind AI создаёт, проверяет и обновляет медицинский контент: иерархия источников, генерация ИИ, автоматическая верификация и человеческая рецензия.",
    hero_title: "Редакционная политика",
    hero_sub: "Как мы создаём, проверяем и поддерживаем каждую единицу медицинского контента на MedMind AI.",
    sources_title: "Иерархия источников",
    sources_body: "Весь контент на MedMind AI основан на строгой иерархии доказательств:",
    sources_tier1: "Уровень 1 — Клинические руководства и официальные рекомендации (ВОЗ, NICE, AHA, ACC, ESC, CDC, EMA, национальные органы здравоохранения). Это основной источник клинических рекомендаций.",
    sources_tier2: "Уровень 2 — Систематические обзоры и метаанализы из рецензируемых журналов (NEJM, The Lancet, BMJ, JAMA, Cochrane). Используются для проверки статистических утверждений.",
    sources_tier3: "Уровень 3 — Отдельные рандомизированные контролируемые исследования и обсервационные исследования. Упоминаются только при отсутствии источников 1–2 уровней и явно маркируются как таковые. Мы никогда не представляем единственное исследование как устоявшийся консенсус.",
    generation_title: "Генерация с помощью ИИ",
    generation_body: "Статьи создаются Claude AI (Anthropic) с помощью строгого системного промпта, требующего ссылок на источники для каждого фактического утверждения.",
    verification_title: "Автоматическая верификация (конвейер V4)",
    verification_body: "Каждая статья проходит через наш конвейер проверки утверждений перед публикацией:",
    verification_steps: [
      "Извлечение утверждений: Claude Haiku извлекает все проверяемые фактические утверждения (статистика, дозировки, причинно-следственные связи, клинические рекомендации)",
      "Сопоставление с источниками: каждое утверждение проверяется по заявленным источникам статьи",
      "Вердикт: «да/частично» для всех утверждений → статус = passed; любое «нет» → статус = failed, статья скрывается из публичного доступа",
      "Только статьи со статусом 'passed' или 'human_reviewed' публикуются и включаются в sitemap",
    ],
    human_review_title: "Человеческая рецензия",
    human_review_body: "Статьи по популярным темам или сложным клиническим вопросам проверяются лицензированными медицинскими специалистами. Рецензированная статья получает статус 'human_reviewed' и отображает учётные данные рецензента.",
    updates_title: "Обновление контента",
    updates_body: "Медицинские знания развиваются. Статьи помечаются для повторной проверки когда: (1) обнаружено обновление руководства, (2) пользователи сообщают об ошибке, (3) плановая верификация не проходит.",
    feedback_title: "Сообщение об ошибках",
    feedback_body: "На каждой публичной статье есть кнопка «Сообщить об ошибке». Жалобы рассматриваются редакцией в течение 5 рабочих дней.",
  },
  de: {
    meta_title: "Redaktionelle Richtlinien — MedMind AI",
    meta_desc: "Wie MedMind AI medizinische Inhalte erstellt, verifiziert und aktualisiert.",
    hero_title: "Redaktionelle Richtlinien",
    hero_sub: "Wie wir jeden medizinischen Inhalt auf MedMind AI erstellen, verifizieren und pflegen.",
    sources_title: "Quellhierarchie",
    sources_body: "Alle Inhalte auf MedMind AI basieren auf einer strikten Beweishierarchie:",
    sources_tier1: "Stufe 1 — Klinische Leitlinien und offizielle Empfehlungen (WHO, NICE, AHA, ACC, ESC, CDC, EMA, nationale Gesundheitsbehörden).",
    sources_tier2: "Stufe 2 — Systematische Übersichtsarbeiten und Metaanalysen aus begutachteten Fachzeitschriften (NEJM, The Lancet, BMJ, JAMA, Cochrane).",
    sources_tier3: "Stufe 3 — Einzelne randomisierte kontrollierte Studien und Beobachtungsstudien. Nur bei fehlenden Quellen der Stufen 1–2 und explizit als solche gekennzeichnet.",
    generation_title: "KI-gestützte Erstellung",
    generation_body: "Artikel werden von Claude KI mit striktem System-Prompt erstellt, der Quellenangaben für jede Sachaussage verlangt.",
    verification_title: "Automatisierte Verifizierung (V4-Pipeline)",
    verification_body: "Jeder Artikel durchläuft unsere automatisierte Claim-Checking-Pipeline vor der Veröffentlichung:",
    verification_steps: [
      "Claim-Extraktion: Faktische Behauptungen werden automatisch extrahiert",
      "Quellenabgleich: Jede Behauptung wird anhand der deklarierten Quellen überprüft",
      "Urteil: Alle bestätigt → Status passed; jedes 'Nein' → Status failed, Artikel versteckt",
      "Nur Artikel mit Status 'passed' oder 'human_reviewed' werden veröffentlicht",
    ],
    human_review_title: "Menschliche Überprüfung",
    human_review_body: "Ausgewählte Artikel werden von lizenzierten Gesundheitsfachkräften geprüft und erhalten den Status 'human_reviewed'.",
    updates_title: "Inhaltsaktualisierungen",
    updates_body: "Medizinisches Wissen entwickelt sich weiter. Artikel werden zur Überprüfung markiert bei Leitlinienänderungen, Nutzer-Fehlermeldungen oder fehlgeschlagener Re-Verifizierung.",
    feedback_title: "Fehler melden",
    feedback_body: "Jeder öffentliche Artikel hat eine 'Fehler melden'-Schaltfläche. Berichte werden innerhalb von 5 Werktagen überprüft.",
  },
  fr: {
    meta_title: "Politique éditoriale — MedMind AI",
    meta_desc: "Comment MedMind AI crée, vérifie et met à jour les contenus médicaux.",
    hero_title: "Politique éditoriale",
    hero_sub: "Comment nous créons, vérifions et maintenons chaque contenu médical sur MedMind AI.",
    sources_title: "Hiérarchie des sources",
    sources_body: "Tous les contenus de MedMind AI reposent sur une hiérarchie stricte de preuves:",
    sources_tier1: "Niveau 1 — Recommandations cliniques officielles (OMS, NICE, AHA, ACC, ESC, CDC, EMA, autorités nationales de santé).",
    sources_tier2: "Niveau 2 — Revues systématiques et méta-analyses de revues à comité de lecture (NEJM, The Lancet, BMJ, JAMA, Cochrane).",
    sources_tier3: "Niveau 3 — Études individuelles randomisées ou observationnelles. Référencées uniquement en l'absence de sources de niveaux 1–2, et explicitement étiquetées comme telles.",
    generation_title: "Génération assistée par IA",
    generation_body: "Les articles sont rédigés par Claude IA avec un prompt système strict exigeant des citations pour chaque affirmation factuelle.",
    verification_title: "Vérification automatisée (Pipeline V4)",
    verification_body: "Chaque article passe par notre pipeline de vérification avant publication:",
    verification_steps: [
      "Extraction des affirmations: toutes les assertions factuelles sont extraites automatiquement",
      "Correspondance des sources: chaque affirmation est vérifiée par rapport aux sources déclarées",
      "Verdict: tout confirmé → statut passed; un seul 'non' → statut failed, article masqué",
      "Seuls les articles au statut 'passed' ou 'human_reviewed' sont publiés",
    ],
    human_review_title: "Révision humaine",
    human_review_body: "Des articles sélectionnés sont examinés par des professionnels de santé agréés et obtiennent le statut 'human_reviewed'.",
    updates_title: "Mises à jour du contenu",
    updates_body: "Le savoir médical évolue. Les articles sont signalés pour re-révision lors de mises à jour de recommandations, de signalements d'erreurs ou d'échec de re-vérification.",
    feedback_title: "Signaler une erreur",
    feedback_body: "Chaque article public dispose d'un bouton 'Signaler une erreur'. Les signalements sont traités sous 5 jours ouvrables.",
  },
  es: {
    meta_title: "Política editorial — MedMind AI",
    meta_desc: "Cómo MedMind AI crea, verifica y actualiza el contenido médico.",
    hero_title: "Política editorial",
    hero_sub: "Cómo creamos, verificamos y mantenemos cada pieza de contenido médico en MedMind AI.",
    sources_title: "Jerarquía de fuentes",
    sources_body: "Todo el contenido en MedMind AI se basa en una jerarquía estricta de evidencia:",
    sources_tier1: "Nivel 1 — Guías clínicas y recomendaciones oficiales (OMS, NICE, AHA, ACC, ESC, CDC, EMA, autoridades sanitarias nacionales).",
    sources_tier2: "Nivel 2 — Revisiones sistemáticas y metaanálisis de revistas revisadas por pares (NEJM, The Lancet, BMJ, JAMA, Cochrane).",
    sources_tier3: "Nivel 3 — Ensayos controlados aleatorios individuales y estudios observacionales. Solo se referencian cuando no hay fuentes de niveles 1–2 disponibles.",
    generation_title: "Generación asistida por IA",
    generation_body: "Los artículos son redactados por Claude IA con un prompt de sistema estricto que requiere citas para cada afirmación factual.",
    verification_title: "Verificación automatizada (Pipeline V4)",
    verification_body: "Cada artículo pasa por nuestro pipeline de verificación antes de la publicación:",
    verification_steps: [
      "Extracción de afirmaciones: se extraen automáticamente todas las afirmaciones factuales verificables",
      "Correspondencia de fuentes: cada afirmación se verifica frente a las fuentes declaradas",
      "Veredicto: todo confirmado → estado passed; cualquier 'no' → estado failed, artículo oculto",
      "Solo los artículos con estado 'passed' o 'human_reviewed' se publican e incluyen en sitemaps",
    ],
    human_review_title: "Revisión humana",
    human_review_body: "Artículos seleccionados son revisados y aprobados por profesionales sanitarios con licencia.",
    updates_title: "Actualizaciones de contenido",
    updates_body: "El conocimiento médico evoluciona. Los artículos se marcan para re-revisión ante actualizaciones de guías, errores reportados o fallos de re-verificación.",
    feedback_title: "Reportar errores",
    feedback_body: "Cada artículo público tiene un botón 'Reportar un error'. Los informes se revisan en 5 días hábiles.",
  },
  tr: {
    meta_title: "Editoryal Politika — MedMind AI",
    meta_desc: "MedMind AI tıbbi içerikleri nasıl oluşturur, doğrular ve günceller.",
    hero_title: "Editoryal Politika",
    hero_sub: "MedMind AI'daki her tıbbi içeriği nasıl oluşturduğumuzu, doğruladığımızı ve sürdürdüğümüzü açıklıyoruz.",
    sources_title: "Kaynak Hiyerarşisi",
    sources_body: "MedMind AI'daki tüm içerikler katı bir kanıt hiyerarşisine dayanmaktadır:",
    sources_tier1: "Seviye 1 — Klinik kılavuzlar ve resmi öneriler (WHO, NICE, AHA, ACC, ESC, CDC, EMA, ulusal sağlık otoriteleri).",
    sources_tier2: "Seviye 2 — Hakemli dergilerden sistematik derlemeler ve meta-analizler (NEJM, The Lancet, BMJ, JAMA, Cochrane).",
    sources_tier3: "Seviye 3 — Bireysel randomize kontrollü çalışmalar ve gözlemsel çalışmalar. Yalnızca 1–2. seviye kaynaklar mevcut olmadığında referans gösterilir.",
    generation_title: "Yapay Zeka Destekli Üretim",
    generation_body: "Makaleler, her olgusal iddia için kaynak alıntısı gerektiren katı sistem komutuyla Claude AI tarafından hazırlanır.",
    verification_title: "Otomatik Doğrulama (V4 Hattı)",
    verification_body: "Her makale yayımdan önce otomatik iddia kontrol hattından geçer:",
    verification_steps: [
      "İddia çıkarımı: tüm doğrulanabilir olgusal iddialar otomatik olarak çıkarılır",
      "Kaynak eşleştirmesi: her iddia beyan edilen kaynaklara göre doğrulanır",
      "Karar: tümü onaylandı → durum passed; herhangi bir 'hayır' → durum failed, makale gizlendi",
      "Yalnızca 'passed' veya 'human_reviewed' durumundaki makaleler yayımlanır",
    ],
    human_review_title: "Uzman İncelemesi",
    human_review_body: "Seçilmiş makaleler lisanslı sağlık profesyonelleri tarafından incelenerek 'human_reviewed' durumu alır.",
    updates_title: "İçerik Güncellemeleri",
    updates_body: "Tıbbi bilgi gelişir. Makaleler; kılavuz güncellemeleri, hata bildirimleri veya yeniden doğrulama başarısızlığı durumunda yeniden inceleme için işaretlenir.",
    feedback_title: "Hata Bildirme",
    feedback_body: "Her genel makale 'Hata bildir' düğmesine sahiptir. Raporlar 5 iş günü içinde incelenir.",
  },
  ar: {
    meta_title: "السياسة التحريرية — MedMind AI",
    meta_desc: "كيف تنشئ MedMind AI المحتوى الطبي وتتحقق منه وتحدّثه.",
    hero_title: "السياسة التحريرية",
    hero_sub: "كيف ننشئ كل محتوى طبي على MedMind AI ونتحقق منه ونحافظ عليه.",
    sources_title: "التسلسل الهرمي للمصادر",
    sources_body: "يستند جميع المحتوى على MedMind AI إلى تسلسل هرمي صارم من الأدلة:",
    sources_tier1: "المستوى الأول — الإرشادات السريرية والتوصيات الرسمية (WHO، NICE، AHA، ACC، ESC، CDC، EMA، السلطات الصحية الوطنية).",
    sources_tier2: "المستوى الثاني — المراجعات المنهجية والتحليلات التلوية من مجلات محكّمة (NEJM، The Lancet، BMJ، JAMA، Cochrane).",
    sources_tier3: "المستوى الثالث — التجارب المعشاة الفردية والدراسات الرصدية. تُستشهد بها فقط عند غياب مصادر المستوى الأول والثاني.",
    generation_title: "التوليد بالذكاء الاصطناعي",
    generation_body: "تُصاغ المقالات بواسطة Claude AI بموجب نظام موجّه صارم يتطلب استشهادات بالمصادر لكل ادعاء حقيقي.",
    verification_title: "التحقق التلقائي (خط أنابيب V4)",
    verification_body: "تمر كل مقالة عبر خط أنابيب التحقق من الادعاءات قبل النشر:",
    verification_steps: [
      "استخراج الادعاءات: تُستخرج جميع الادعاءات الحقيقية القابلة للتحقق تلقائياً",
      "مطابقة المصادر: يُتحقق من كل ادعاء مقابل المصادر المُعلنة",
      "الحكم: جميعها مؤكدة → الحالة passed؛ أي 'لا' → الحالة failed، المقالة مخفية",
      "تُنشر فقط المقالات ذات الحالة 'passed' أو 'human_reviewed'",
    ],
    human_review_title: "المراجعة البشرية",
    human_review_body: "تُراجَع مقالات مختارة من قبل متخصصين في الرعاية الصحية مرخصين وتحصل على حالة 'human_reviewed'.",
    updates_title: "تحديثات المحتوى",
    updates_body: "تتطور المعرفة الطبية. تُوضع المقالات في قائمة إعادة المراجعة عند تحديث الإرشادات أو الإبلاغ عن أخطاء أو فشل إعادة التحقق.",
    feedback_title: "الإبلاغ عن الأخطاء",
    feedback_body: "كل مقالة عامة تحتوي على زر 'الإبلاغ عن خطأ'. تُراجَع التقارير خلال 5 أيام عمل.",
  },
};

const DISCLAIMER_DATA: Record<TrustLocale, Omit<DisclaimerT, keyof TrustT>> = {
  en: {
    meta_title: "Medical Disclaimer — MedMind AI",
    meta_desc: "MedMind AI is an educational platform. Read our full medical disclaimer regarding the use of content on this site.",
    hero_title: "Medical Disclaimer",
    hero_sub: "Please read this disclaimer carefully before using any medical information on MedMind AI.",
    not_advice_title: "Not Medical Advice",
    not_advice_body: "All content on MedMind AI — including articles, drug information, clinical cases, educational modules, and AI-generated responses — is provided for educational and informational purposes only. It does not constitute medical advice, professional diagnosis, or a treatment plan. It is not a substitute for consultation with a qualified, licensed healthcare professional.",
    emergency_title: "Medical Emergencies",
    emergency_body: "If you are experiencing a medical emergency, call emergency services (911 in the US, 112 in the EU, or your local equivalent) immediately. Do not rely on this platform in emergency situations.",
    accuracy_title: "Accuracy and Currency",
    accuracy_body: "While we strive to provide accurate, evidence-based information, medical knowledge evolves continuously. Content may not reflect the most recent guidelines, drug approvals, or research findings. Always verify clinical information against current official guidelines and prescribing information.",
    professional_title: "For Healthcare Professionals",
    professional_body: "Content on MedMind AI is primarily designed for educational use by healthcare professionals. Even for qualified clinicians, the information presented should not replace clinical judgment, patient-specific assessment, or consultation with specialists.",
    dosing_title: "Drug Dosages and Protocols",
    dosing_body: "Drug dosages, contraindications, interactions, and clinical protocols listed on this platform are for educational reference only. Always verify dosages and protocols against current prescribing information, local formularies, and institutional guidelines before making any clinical decision.",
    liability_title: "Limitation of Liability",
    liability_body: "MedMind AI and its operators, authors, and contributors accept no liability for any harm, loss, or damages arising from reliance on information provided on this platform. Use of this platform is entirely at the user's own risk.",
    contact_note: "Questions about this disclaimer? Contact us at legal@medmind.pro",
  },
  ru: {
    meta_title: "Медицинский дисклеймер — MedMind AI",
    meta_desc: "MedMind AI — образовательная платформа. Прочитайте наш полный медицинский дисклеймер.",
    hero_title: "Медицинский дисклеймер",
    hero_sub: "Пожалуйста, внимательно прочитайте этот дисклеймер перед использованием медицинской информации на MedMind AI.",
    not_advice_title: "Не является медицинским советом",
    not_advice_body: "Весь контент на MedMind AI — включая статьи, информацию о препаратах, клинические случаи, учебные модули и ответы ИИ — предоставляется исключительно в образовательных и информационных целях. Он не является медицинским советом, профессиональным диагнозом или планом лечения и не заменяет консультацию квалифицированного лицензированного медицинского специалиста.",
    emergency_title: "Медицинские экстренные ситуации",
    emergency_body: "При медицинской экстренной ситуации немедленно вызовите службы экстренной помощи. Не полагайтесь на эту платформу в экстренных случаях.",
    accuracy_title: "Точность и актуальность",
    accuracy_body: "Несмотря на то что мы стремимся предоставлять точную информацию, основанную на доказательствах, медицинские знания постоянно развиваются. Всегда проверяйте клиническую информацию по текущим официальным руководствам.",
    professional_title: "Для медицинских работников",
    professional_body: "Контент на MedMind AI предназначен прежде всего для образовательного использования медицинскими работниками. Даже для квалифицированных клиницистов представленная информация не должна заменять клиническое суждение.",
    dosing_title: "Дозировки препаратов и протоколы",
    dosing_body: "Дозировки препаратов, противопоказания, взаимодействия и клинические протоколы представлены только в образовательных целях. Всегда проверяйте по текущим инструкциям по применению и институциональным руководствам.",
    liability_title: "Ограничение ответственности",
    liability_body: "MedMind AI и её операторы, авторы и участники не несут ответственности за любой ущерб, возникший в результате использования информации на этой платформе.",
    contact_note: "Вопросы по дисклеймеру? Свяжитесь с нами: legal@medmind.pro",
  },
  de: {
    meta_title: "Medizinischer Haftungsausschluss — MedMind AI",
    meta_desc: "MedMind AI ist eine Bildungsplattform. Lesen Sie unseren vollständigen medizinischen Haftungsausschluss.",
    hero_title: "Medizinischer Haftungsausschluss",
    hero_sub: "Bitte lesen Sie diesen Haftungsausschluss sorgfältig, bevor Sie medizinische Informationen auf MedMind AI verwenden.",
    not_advice_title: "Kein medizinischer Rat",
    not_advice_body: "Alle Inhalte auf MedMind AI dienen ausschließlich Bildungs- und Informationszwecken. Sie stellen keine medizinische Beratung, professionelle Diagnose oder einen Behandlungsplan dar.",
    emergency_title: "Medizinische Notfälle",
    emergency_body: "Bei einem medizinischen Notfall rufen Sie sofort den Notruf (112 in der EU). Verlassen Sie sich nicht auf diese Plattform in Notfallsituationen.",
    accuracy_title: "Genauigkeit und Aktualität",
    accuracy_body: "Medizinisches Wissen entwickelt sich ständig weiter. Überprüfen Sie klinische Informationen stets anhand aktueller offizieller Leitlinien.",
    professional_title: "Für Gesundheitsfachkräfte",
    professional_body: "Inhalte auf MedMind AI sind hauptsächlich für die Bildung von Gesundheitsfachkräften konzipiert und sollten das klinische Urteil nicht ersetzen.",
    dosing_title: "Arzneimitteldosierungen und Protokolle",
    dosing_body: "Dosierungen, Kontraindikationen, Wechselwirkungen und klinische Protokolle dienen nur als Bildungsreferenz. Überprüfen Sie stets anhand aktueller Fachinformationen.",
    liability_title: "Haftungsbeschränkung",
    liability_body: "MedMind AI übernimmt keine Haftung für Schäden, die aus der Nutzung der auf dieser Plattform bereitgestellten Informationen entstehen.",
    contact_note: "Fragen zu diesem Haftungsausschluss? Kontakt: legal@medmind.pro",
  },
  fr: {
    meta_title: "Avertissement médical — MedMind AI",
    meta_desc: "MedMind AI est une plateforme éducative. Lisez notre avertissement médical complet.",
    hero_title: "Avertissement médical",
    hero_sub: "Veuillez lire attentivement cet avertissement avant d'utiliser les informations médicales sur MedMind AI.",
    not_advice_title: "Pas un avis médical",
    not_advice_body: "Tous les contenus de MedMind AI sont fournis à des fins éducatives et informatives uniquement. Ils ne constituent pas un avis médical, un diagnostic professionnel ou un plan de traitement.",
    emergency_title: "Urgences médicales",
    emergency_body: "En cas d'urgence médicale, appelez immédiatement les services d'urgence (15, 18 ou 112). Ne vous fiez pas à cette plateforme dans les situations d'urgence.",
    accuracy_title: "Exactitude et actualité",
    accuracy_body: "Les connaissances médicales évoluent continuellement. Vérifiez toujours les informations cliniques auprès des recommandations officielles en vigueur.",
    professional_title: "Pour les professionnels de santé",
    professional_body: "Le contenu est principalement conçu pour la formation des professionnels de santé et ne doit pas remplacer le jugement clinique.",
    dosing_title: "Posologies et protocoles médicamenteux",
    dosing_body: "Les posologies, contre-indications, interactions et protocoles sont donnés à titre éducatif uniquement. Vérifiez toujours auprès des notices actuelles.",
    liability_title: "Limitation de responsabilité",
    liability_body: "MedMind AI n'accepte aucune responsabilité pour tout préjudice découlant de l'utilisation des informations fournies sur cette plateforme.",
    contact_note: "Questions sur cet avertissement ? Contactez-nous : legal@medmind.pro",
  },
  es: {
    meta_title: "Aviso médico — MedMind AI",
    meta_desc: "MedMind AI es una plataforma educativa. Lea nuestro aviso médico completo.",
    hero_title: "Aviso médico",
    hero_sub: "Por favor, lea este aviso detenidamente antes de utilizar cualquier información médica en MedMind AI.",
    not_advice_title: "No es consejo médico",
    not_advice_body: "Todo el contenido de MedMind AI se proporciona únicamente con fines educativos e informativos. No constituye consejo médico, diagnóstico profesional ni plan de tratamiento.",
    emergency_title: "Emergencias médicas",
    emergency_body: "Si está experimentando una emergencia médica, llame inmediatamente a los servicios de emergencia (112 en la UE). No confíe en esta plataforma en situaciones de emergencia.",
    accuracy_title: "Exactitud y vigencia",
    accuracy_body: "El conocimiento médico evoluciona continuamente. Verifique siempre la información clínica con las guías oficiales actuales.",
    professional_title: "Para profesionales de la salud",
    professional_body: "El contenido está diseñado principalmente para uso educativo por profesionales de la salud y no debe reemplazar el juicio clínico.",
    dosing_title: "Dosis de medicamentos y protocolos",
    dosing_body: "Las dosis, contraindicaciones, interacciones y protocolos son solo para referencia educativa. Verifique siempre con la información de prescripción actual.",
    liability_title: "Limitación de responsabilidad",
    liability_body: "MedMind AI no acepta responsabilidad alguna por daños derivados del uso de la información proporcionada en esta plataforma.",
    contact_note: "¿Preguntas sobre este aviso? Contacte: legal@medmind.pro",
  },
  tr: {
    meta_title: "Tıbbi Sorumluluk Reddi — MedMind AI",
    meta_desc: "MedMind AI bir eğitim platformudur. Tam tıbbi sorumluluk reddimizi okuyun.",
    hero_title: "Tıbbi Sorumluluk Reddi",
    hero_sub: "MedMind AI'daki tıbbi bilgileri kullanmadan önce lütfen bu sorumluluk reddini dikkatlice okuyun.",
    not_advice_title: "Tıbbi Tavsiye Değildir",
    not_advice_body: "MedMind AI'daki tüm içerikler yalnızca eğitim ve bilgilendirme amaçlıdır. Tıbbi tavsiye, profesyonel tanı veya tedavi planı oluşturmaz.",
    emergency_title: "Tıbbi Acil Durumlar",
    emergency_body: "Tıbbi acil durumda hemen acil servisleri arayın (112). Acil durumlarda bu platforma güvenmeyin.",
    accuracy_title: "Doğruluk ve Güncellik",
    accuracy_body: "Tıbbi bilgi sürekli gelişmektedir. Klinik bilgileri daima güncel resmi kılavuzlar doğrultusunda doğrulayın.",
    professional_title: "Sağlık Profesyonelleri İçin",
    professional_body: "İçerik, öncelikle sağlık profesyonellerinin eğitimi için tasarlanmıştır ve klinik yargının yerini tutmamalıdır.",
    dosing_title: "İlaç Dozajları ve Protokoller",
    dosing_body: "Dozajlar, kontrendikasyonlar, etkileşimler ve protokoller yalnızca eğitim referansı amaçlıdır. Her zaman güncel reçete bilgileriyle doğrulayın.",
    liability_title: "Sorumluluk Sınırlaması",
    liability_body: "MedMind AI, bu platformdaki bilgilere dayanılması sonucu doğabilecek zararlardan sorumlu değildir.",
    contact_note: "Bu sorumluluk reddi hakkında sorularınız mı var? İletişim: legal@medmind.pro",
  },
  ar: {
    meta_title: "إخلاء المسؤولية الطبية — MedMind AI",
    meta_desc: "MedMind AI منصة تعليمية. اقرأ إخلاء مسؤوليتنا الطبية الكاملة.",
    hero_title: "إخلاء المسؤولية الطبية",
    hero_sub: "يرجى قراءة إخلاء المسؤولية هذا بعناية قبل استخدام أي معلومات طبية على MedMind AI.",
    not_advice_title: "ليس نصيحة طبية",
    not_advice_body: "جميع المحتوى على MedMind AI — بما في ذلك المقالات ومعلومات الأدوية والحالات السريرية والوحدات التعليمية وردود الذكاء الاصطناعي — مقدَّم لأغراض تعليمية وإعلامية فقط. لا يشكّل نصيحة طبية أو تشخيصاً مهنياً أو خطة علاج.",
    emergency_title: "حالات الطوارئ الطبية",
    emergency_body: "في حالة الطوارئ الطبية، اتصل فوراً بخدمات الطوارئ. لا تعتمد على هذه المنصة في حالات الطوارئ.",
    accuracy_title: "الدقة والحداثة",
    accuracy_body: "تتطور المعرفة الطبية باستمرار. تحقق دائماً من المعلومات السريرية مع الإرشادات الرسمية الحالية.",
    professional_title: "لمتخصصي الرعاية الصحية",
    professional_body: "المحتوى مخصص أساساً للاستخدام التعليمي من قبل متخصصي الرعاية الصحية ولا ينبغي أن يحل محل الحكم السريري.",
    dosing_title: "جرعات الأدوية والبروتوكولات",
    dosing_body: "الجرعات والموانع والتفاعلات والبروتوكولات مقدَّمة للمرجعية التعليمية فقط. تحقق دائماً من معلومات الوصفة الحالية.",
    liability_title: "تحديد المسؤولية",
    liability_body: "لا تتحمل MedMind AI أي مسؤولية عن أي ضرر ناتج عن الاعتماد على المعلومات المقدَّمة على هذه المنصة.",
    contact_note: "أسئلة حول إخلاء المسؤولية؟ تواصل معنا: legal@medmind.pro",
  },
};

const CONTACT_DATA: Record<TrustLocale, Omit<ContactT, keyof TrustT>> = {
  en: {
    meta_title: "Contact MedMind AI",
    meta_desc: "Contact the MedMind AI team for general inquiries, press, partnerships, or content feedback.",
    hero_title: "Contact Us",
    hero_sub: "We are a small, focused team. We read every message.",
    general_title: "General Inquiries",
    general_email: "hello@medmind.pro",
    press_title: "Press & Media",
    press_email: "press@medmind.pro",
    partnership_title: "Partnerships & Integrations",
    partnership_email: "partners@medmind.pro",
    feedback_title: "Content Feedback",
    feedback_body: "Found an error in a medical article? Use the 'Report an error' button on the article page for the fastest response.",
    response_note: "We aim to respond within 2–3 business days.",
  },
  ru: {
    meta_title: "Контакты MedMind AI",
    meta_desc: "Свяжитесь с командой MedMind AI по общим вопросам, для прессы, партнёрства или обратной связи по контенту.",
    hero_title: "Связаться с нами",
    hero_sub: "Мы небольшая команда. Читаем каждое сообщение.",
    general_title: "Общие вопросы",
    general_email: "hello@medmind.pro",
    press_title: "Пресса и СМИ",
    press_email: "press@medmind.pro",
    partnership_title: "Партнёрство и интеграции",
    partnership_email: "partners@medmind.pro",
    feedback_title: "Обратная связь по контенту",
    feedback_body: "Нашли ошибку в статье? Используйте кнопку «Сообщить об ошибке» на странице статьи для самого быстрого ответа.",
    response_note: "Мы стараемся отвечать в течение 2–3 рабочих дней.",
  },
  de: {
    meta_title: "Kontakt — MedMind AI",
    meta_desc: "Kontaktieren Sie das MedMind AI-Team für allgemeine Anfragen, Presse, Partnerschaften oder Inhaltsfeedback.",
    hero_title: "Kontakt",
    hero_sub: "Wir sind ein kleines, fokussiertes Team. Wir lesen jede Nachricht.",
    general_title: "Allgemeine Anfragen",
    general_email: "hello@medmind.pro",
    press_title: "Presse & Medien",
    press_email: "press@medmind.pro",
    partnership_title: "Partnerschaften & Integrationen",
    partnership_email: "partners@medmind.pro",
    feedback_title: "Inhaltsfeedback",
    feedback_body: "Fehler in einem Artikel gefunden? Verwenden Sie die 'Fehler melden'-Schaltfläche auf der Artikelseite.",
    response_note: "Wir antworten in der Regel innerhalb von 2–3 Werktagen.",
  },
  fr: {
    meta_title: "Contactez MedMind AI",
    meta_desc: "Contactez l'équipe MedMind AI pour des questions générales, la presse, les partenariats ou les retours sur le contenu.",
    hero_title: "Nous contacter",
    hero_sub: "Nous sommes une petite équipe concentrée. Nous lisons chaque message.",
    general_title: "Questions générales",
    general_email: "hello@medmind.pro",
    press_title: "Presse & Médias",
    press_email: "press@medmind.pro",
    partnership_title: "Partenariats & Intégrations",
    partnership_email: "partners@medmind.pro",
    feedback_title: "Retours sur le contenu",
    feedback_body: "Vous avez trouvé une erreur dans un article ? Utilisez le bouton 'Signaler une erreur' sur la page de l'article.",
    response_note: "Nous répondons généralement sous 2 à 3 jours ouvrables.",
  },
  es: {
    meta_title: "Contacto — MedMind AI",
    meta_desc: "Contacte al equipo de MedMind AI para consultas generales, prensa, asociaciones o comentarios sobre el contenido.",
    hero_title: "Contáctenos",
    hero_sub: "Somos un equipo pequeño y enfocado. Leemos cada mensaje.",
    general_title: "Consultas generales",
    general_email: "hello@medmind.pro",
    press_title: "Prensa y medios",
    press_email: "press@medmind.pro",
    partnership_title: "Asociaciones e integraciones",
    partnership_email: "partners@medmind.pro",
    feedback_title: "Comentarios sobre el contenido",
    feedback_body: "¿Encontró un error en un artículo? Use el botón 'Reportar un error' en la página del artículo.",
    response_note: "Intentamos responder en 2–3 días hábiles.",
  },
  tr: {
    meta_title: "İletişim — MedMind AI",
    meta_desc: "Genel sorular, basın, ortaklıklar veya içerik geri bildirimi için MedMind AI ekibiyle iletişime geçin.",
    hero_title: "Bize Ulaşın",
    hero_sub: "Küçük ve odaklı bir ekibiz. Her mesajı okuyoruz.",
    general_title: "Genel Sorular",
    general_email: "hello@medmind.pro",
    press_title: "Basın & Medya",
    press_email: "press@medmind.pro",
    partnership_title: "Ortaklıklar & Entegrasyonlar",
    partnership_email: "partners@medmind.pro",
    feedback_title: "İçerik Geri Bildirimi",
    feedback_body: "Bir makalede hata mı buldunuz? En hızlı yanıt için makale sayfasındaki 'Hata bildir' düğmesini kullanın.",
    response_note: "2–3 iş günü içinde yanıt vermeye çalışıyoruz.",
  },
  ar: {
    meta_title: "تواصل مع MedMind AI",
    meta_desc: "تواصل مع فريق MedMind AI للاستفسارات العامة أو الصحافة أو الشراكات أو التغذية الراجعة حول المحتوى.",
    hero_title: "تواصل معنا",
    hero_sub: "نحن فريق صغير ومركّز. نقرأ كل رسالة.",
    general_title: "استفسارات عامة",
    general_email: "hello@medmind.pro",
    press_title: "الصحافة والإعلام",
    press_email: "press@medmind.pro",
    partnership_title: "الشراكات والتكاملات",
    partnership_email: "partners@medmind.pro",
    feedback_title: "التغذية الراجعة حول المحتوى",
    feedback_body: "وجدت خطأً في مقالة؟ استخدم زر 'الإبلاغ عن خطأ' في صفحة المقالة للحصول على أسرع استجابة.",
    response_note: "نهدف إلى الرد خلال 2–3 أيام عمل.",
  },
};

// ── Public accessors ──────────────────────────────────────────────────────────

function locale(raw: string | undefined): TrustLocale {
  const SUPPORTED: TrustLocale[] = ["en", "ru", "ar", "tr", "de", "fr", "es"];
  return (SUPPORTED.includes(raw as TrustLocale) ? raw : "en") as TrustLocale;
}

export function getAboutT(rawLocale?: string): AboutT {
  const l = locale(rawLocale);
  return { ...SHARED[l], ...ABOUT[l] };
}

export function getEditorialT(rawLocale?: string): EditorialT {
  const l = locale(rawLocale);
  return { ...SHARED[l], ...EDITORIAL[l] };
}

export function getDisclaimerT(rawLocale?: string): DisclaimerT {
  const l = locale(rawLocale);
  return { ...SHARED[l], ...DISCLAIMER_DATA[l] };
}

export function getContactT(rawLocale?: string): ContactT {
  const l = locale(rawLocale);
  return { ...SHARED[l], ...CONTACT_DATA[l] };
}

export function getTrustShared(rawLocale?: string): TrustT {
  return SHARED[locale(rawLocale)];
}
