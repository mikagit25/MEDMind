// SYNC-GROUP: nclex-landing
// /nclex (EN) · /ar/nclex (AR) · /es/nclex (ES) · /ru/nclex (RU) · /de/nclex (DE) · /fr/nclex (FR) · /tr/nclex (TR) ← you are here: RU
// TODO: replace with next-intl server routing when the project migrates to SSR i18n.

import type { Metadata } from "next";
import Link from "next/link";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { PublicFooter } from "@/components/layout/PublicFooter";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";

export const metadata: Metadata = {
  title: "Подготовка к NCLEX-RN 2025 — Адаптивные симуляции CAT и объяснения ИИ | MedMind AI",
  description:
    "Готовьтесь к NCLEX-RN с адаптивными симуляциями CAT (75–145 вопросов), SATA, NGN и объяснениями ИИ для каждого вопроса. Отслеживайте результаты по всем 7 категориям NCLEX. Начните бесплатно.",
  alternates: {
    canonical: `${SITE_URL}/ru/nclex`,
    languages: {
      "en":        `${SITE_URL}/nclex`,
      "ar":        `${SITE_URL}/ar/nclex`,
      "es":        `${SITE_URL}/es/nclex`,
      "ru":        `${SITE_URL}/ru/nclex`,
      "de":        `${SITE_URL}/de/nclex`,
      "fr":        `${SITE_URL}/fr/nclex`,
      "tr":        `${SITE_URL}/tr/nclex`,
      "x-default": `${SITE_URL}/nclex`,
    },
  },
  openGraph: {
    title: "Подготовка к NCLEX-RN — MedMind AI",
    description: "Адаптивная симуляция CAT · объяснения ИИ · аналитика по категориям · 600+ вопросов",
    url: `${SITE_URL}/ru/nclex`,
    siteName: "MedMind AI",
    type: "website",
  },
};

const MODES = [
  { id: "Демо",        questions: "10",    tag: "Бесплатно — без регистрации", desc: "Попробуйте без обязательств. 10 вопросов из всех категорий с полными объяснениями ИИ.", free: true },
  { id: "NCLEX-RN 75", questions: "75",   tag: "Минимальная длина",           desc: "Стандартная адаптивная симуляция. Экзамен завершается здесь при явном прохождении или провале.", free: false },
  { id: "NCLEX-RN 85", questions: "85",   tag: "Расширенная симуляция",       desc: "Пройдите пограничную зону. Более сложные вопросы — точнее оценивается готовность.", free: false },
  { id: "NCLEX-RN 145", questions: "145", tag: "Максимальная длина",          desc: "Полная симуляция. Все категории в глубину. Лучший вариант за последнюю неделю перед экзаменом.", free: false },
  { id: "По категории", questions: "10–30", tag: "Целевая практика",          desc: "Выберите одну из 7 категорий Client Needs и отрабатывайте её отдельно.", free: false },
];

const FEATURES = [
  { title: "Адаптивная симуляция CAT",        desc: "Реальная логика NCLEX-RN: сложность подстраивается под каждый ответ. Выберите 75, 85 или 145 вопросов — тот же формат, что у Pearson VUE." },
  { title: "ИИ-объяснение для каждого вопроса", desc: "После каждого ответа — полный клинический разбор: почему правильный ответ верен, почему остальные неверны, и какой концепт нужно запомнить." },
  { title: "7 категорий Client Needs",         desc: "Каждый вопрос привязан к одной из 7 категорий NCLEX. После экзамена видите точный балл по каждой категории." },
  { title: "Отслеживание навыков CJMM",        desc: "Следите за прогрессом по 6 навыкам клинического суждения: распознавание улик, анализ, приоритизация гипотез, генерация решений, действия, оценка результатов." },
  { title: "Повтор ошибочных вопросов",        desc: "После каждой сессии — целевая повторная сессия только с вопросами, на которые вы ответили неверно." },
  { title: "SATA, расчёты и NGN",              desc: "Не только стандартные MCQ. Тренируйте Выберите все подходящие, расчёты инфузий, упорядочивание и вопросы Next Generation NCLEX." },
];

const FAQ = [
  {
    q: "Демо действительно бесплатное?",
    a: "Да. 10-вопросный демо-тест не требует аккаунта. Вы получаете полные объяснения ИИ и разбивку баллов — без кредитной карты и без email.",
  },
  {
    q: "Вопросы на русском языке?",
    a: "Тренировочные вопросы — на английском (реальный экзамен тоже на английском), но объяснения ИИ и ключевые концепты доступны на русском. Это помогает понимать материал на родном языке, одновременно усваивая английскую терминологию.",
  },
  {
    q: "Вопросы актуальны для NCLEX 2024/2025?",
    a: "Да. Банк вопросов включает типы Next Generation NCLEX (NGN), введённые в 2023 году — SATA, упорядочивание и расчёты. Адаптивный алгоритм воспроизводит логику CAT Pearson VUE.",
  },
  {
    q: "MedMind AI аффилирован с NCSBN или NCLEX?",
    a: "Нет. MedMind AI — независимая платформа для подготовки и не имеет никакой связи с NCSBN или программой NCLEX.",
  },
];

export default function RussianNclexPage() {
  return (
    <>
      <ArticleNav />

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 pt-16 sm:pt-24 pb-12 sm:pb-16">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div>
            <div className="inline-flex items-center gap-2 bg-red/10 border border-red/20 px-3 py-1 rounded-full font-syne font-semibold text-xs text-red mb-5">
              <span className="w-1.5 h-1.5 rounded-full bg-red inline-block" />
              NCLEX-RN 2025
            </div>
            <h1 className="font-syne font-extrabold text-3xl sm:text-4xl lg:text-5xl text-ink mb-4 leading-tight">
              Сдайте NCLEX-RN<br />с первой попытки.
            </h1>
            <p className="text-ink-2 text-base sm:text-lg leading-relaxed mb-8 max-w-lg">
              Адаптивные симуляции CAT, разбор клинического мышления с помощью ИИ, аналитика по всем категориям NCLEX Client Needs — создано для того, как медсёстры учатся на самом деле.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link href="/register"
                className="inline-block font-syne font-bold text-base bg-red text-white px-8 py-4 rounded-xl hover:bg-ink transition-colors">
                Начать бесплатно →
              </Link>
              <Link href="/login"
                className="inline-block font-syne font-semibold text-base border border-border text-ink-2 px-8 py-4 rounded-xl hover:border-ink hover:text-ink transition-colors">
                Войти
              </Link>
            </div>
            <p className="text-xs text-ink-3 mt-4 font-syne">Бесплатный аккаунт · 5 ИИ-вопросов/день · Без кредитной карты</p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {[
              { value: "600+", label: "вопросов NCLEX", sub: "SATA · CAT · NGN · расчёты" },
              { value: "12",   label: "модулей по уходу", sub: "доказательная база" },
              { value: "7",    label: "категорий Client Needs", sub: "полное покрытие" },
              { value: "6",    label: "навыков CJMM", sub: "клиническое суждение" },
            ].map((s) => (
              <div key={s.label} className="bg-surface border border-border rounded-xl p-5 flex flex-col gap-1">
                <span className="font-syne font-extrabold text-3xl sm:text-4xl text-ink">{s.value}</span>
                <span className="font-syne font-semibold text-sm text-ink leading-tight">{s.label}</span>
                <span className="text-xs text-ink-3">{s.sub}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Exam modes */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-12 sm:py-16">
          <div className="mb-8">
            <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink mb-2">Пять режимов тренировки</h2>
            <p className="text-ink-3 text-sm">От 10-вопросного демо до полной симуляции из 145 вопросов.</p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {MODES.map((m) => (
              <div key={m.id} className={`rounded-xl border p-5 flex flex-col gap-3 ${m.free ? "border-red/30 bg-red/5" : "border-border bg-bg"}`}>
                <div className="flex items-start justify-between gap-2">
                  <span className="font-syne font-extrabold text-xl text-ink">{m.questions}</span>
                  <span className={`text-xs font-syne font-semibold px-2 py-0.5 rounded-full border ${m.free ? "bg-red/10 border-red/20 text-red" : "bg-surface border-border text-ink-3"}`}>
                    {m.tag}
                  </span>
                </div>
                <div>
                  <h3 className="font-syne font-bold text-base text-ink mb-1">{m.id}</h3>
                  <p className="text-ink-3 text-sm leading-snug">{m.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
        <div className="mb-10">
          <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink mb-2">Всё, что нужно для сдачи</h2>
          <p className="text-ink-3 text-sm max-w-xl">Каждая функция создана с одной целью: сдать NCLEX-RN уверенно, а не случайно.</p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {FEATURES.map((f) => (
            <div key={f.title} className="flex flex-col gap-3">
              <div>
                <h3 className="font-syne font-bold text-base text-ink mb-1">{f.title}</h3>
                <p className="text-ink-3 text-sm leading-relaxed">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
          <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink mb-10 text-center">Как это работает</h2>
          <div className="grid sm:grid-cols-3 gap-8">
            {[
              { step: "01", title: "Выберите режим", desc: "Начните с бесплатного демо (10 вопросов), выберите полную CAT-симуляцию (75/85/145) или тренировку по конкретной категории." },
              { step: "02", title: "Отвечайте и изучайте", desc: "После каждого вопроса нажмите «Объяснить с ИИ» и получите полный клинический разбор — почему ответ верен или неверен и что запомнить." },
              { step: "03", title: "Следите и улучшайте", desc: "Вкладка аналитики показывает ваш результат по каждой категории Client Needs и навыку CJMM. Повторите неверные ответы в один клик." },
            ].map((s) => (
              <div key={s.step} className="flex flex-col gap-3">
                <span className="font-syne font-extrabold text-5xl text-ink/10 leading-none">{s.step}</span>
                <h3 className="font-syne font-bold text-base text-ink">{s.title}</h3>
                <p className="text-ink-3 text-sm leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
          <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink mb-8 text-center">Часто задаваемые вопросы</h2>
          <div className="space-y-6">
            {FAQ.map((item) => (
              <div key={item.q} className="border-b border-border pb-6 last:border-0 last:pb-0">
                <h3 className="font-syne font-bold text-base text-ink mb-2">{item.q}</h3>
                <p className="text-ink-3 text-sm leading-relaxed">{item.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="bg-ink text-white">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 py-16 sm:py-20 text-center">
          <h2 className="font-syne font-extrabold text-3xl sm:text-4xl mb-4">Готовы начать?</h2>
          <p className="text-white/60 mb-8 text-base leading-relaxed">
            Попробуйте бесплатное демо прямо сейчас — 10 вопросов, полные объяснения ИИ, без аккаунта. Создайте аккаунт для доступа к полным CAT-симуляциям и персональной аналитике.
          </p>
          <Link href="/register"
            className="inline-block font-syne font-bold text-base bg-white text-ink px-8 py-4 rounded-xl hover:bg-red hover:text-white transition-colors">
            Начать бесплатно →
          </Link>
          <p className="text-white/30 text-xs mt-5 font-syne">Без кредитной карты · Бесплатный план: 5 ИИ-вопросов/день</p>
        </div>
      </section>

      <PublicFooter />
    </>
  );
}
