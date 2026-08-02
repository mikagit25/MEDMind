// SYNC-GROUP: nclex-landing
// /nclex (EN) · /ar/nclex (AR) · /es/nclex (ES) · /ru/nclex (RU) · /de/nclex (DE) · /fr/nclex (FR) · /tr/nclex (TR) ← you are here: TR
// TODO: replace with next-intl server routing when the project migrates to SSR i18n.

import type { Metadata } from "next";
import Link from "next/link";
import { ArticleNav } from "@/components/layout/ArticleNav";
import { PublicFooter } from "@/components/layout/PublicFooter";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";

export const metadata: Metadata = {
  title: "NCLEX-RN Hazırlık 2025 — Uyarlamalı CAT Simülasyonları ve YZ Açıklamaları | MedMind AI",
  description:
    "NCLEX-RN'e uyarlamalı CAT simülasyonları (75–145 soru), SATA, NGN ve her soru için YZ açıklamalarıyla hazırlanın. 7 NCLEX kategorisinde performansınızı takip edin. Ücretsiz başlayın.",
  alternates: {
    canonical: `${SITE_URL}/tr/nclex`,
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
    title: "NCLEX-RN Hazırlık — MedMind AI",
    description: "Uyarlamalı CAT simülasyonu · YZ açıklamaları · kategori analizi · 600+ soru",
    url: `${SITE_URL}/tr/nclex`,
    siteName: "MedMind AI",
    type: "website",
  },
};

const MODES = [
  { id: "Demo",            questions: "10",    tag: "Ücretsiz — giriş gerekmez", desc: "Tüm kategorilerden 10 soru ve tam YZ açıklamalarıyla kayıt olmadan deneyin.", free: true },
  { id: "NCLEX-RN 75",    questions: "75",    tag: "Minimum sınav uzunluğu",    desc: "Standart uyarlamalı simülasyon. Performans net biçimde geçme ya da başarısız olma durumunda sınav burada sona erer.", free: false },
  { id: "NCLEX-RN 85",    questions: "85",    tag: "Genişletilmiş simülasyon",  desc: "Sınır bölgesini geçin. Daha zor sorular — hazırlık durumunun daha doğru değerlendirmesi.", free: false },
  { id: "NCLEX-RN 145",   questions: "145",   tag: "Maksimum uzunluk",          desc: "Tam uzunluklu simülasyon. Tüm kategoriler derinlemesine. Sınavdan önceki son hafta için en iyisi.", free: false },
  { id: "Kategoriye göre", questions: "10–30", tag: "Hedefli pratik",           desc: "7 İstemci İhtiyaçları kategorisinden birini seçin ve spesifik olarak üzerinde çalışın.", free: false },
];

const FEATURES = [
  { title: "Uyarlamalı CAT Simülasyonu",       desc: "Gerçek NCLEX-RN mantığı: sınav her yanıta göre zorluğu ayarlar. 75, 85 veya 145 soru seçin — Pearson VUE ile aynı format." },
  { title: "Her Soru İçin YZ Açıklaması",      desc: "Her yanıtın ardından tam klinik gerekçe alın: doğru yanıtın neden doğru, her yanlışlayıcının neden yanlış olduğu." },
  { title: "7 İstemci İhtiyaçları Kategorisi", desc: "Her soru 7 NCLEX kategorisinden birine bağlıdır. Sınavdan sonra her kategorideki tam puanınızı görün." },
  { title: "CJMM Beceri Takibi",               desc: "6 klinik karar verme becerisindeki gelişiminizi takip edin: ipuçlarını tanıma, analiz etme, hipotezleri önceliklendirme, çözüm üretme, uygulama, sonuçları değerlendirme." },
  { title: "Yanlış Soruları Tekrarlama",        desc: "Her oturumdan sonra yalnızca yanlış yanıtladığınız sorularla hedefli tekrar oturumu başlatın." },
  { title: "SATA, Hesaplamalar ve NGN",         desc: "Sadece standart MCQ değil. Hepsini seçin, IV hesaplamaları, sıralı yanıt ve Next Generation NCLEX soru türlerini de çalışın." },
];

const FAQ = [
  {
    q: "Demo gerçekten ücretsiz mi?",
    a: "Evet. 10 soruluk demo hesap gerektirmez. Tam YZ açıklamaları ve puan dökümü alırsınız — kredi kartı ve e-posta gerekmez.",
  },
  {
    q: "Sorular Türkçe mi?",
    a: "Pratik sorular İngilizce (gerçek sınav da İngilizce), ancak YZ açıklamaları Türkçe olarak mevcuttur. Bu, ana dilinizde kavramları anlamanıza ve aynı zamanda sınav için gereken İngilizce terminolojiye alışmanıza yardımcı olur.",
  },
  {
    q: "Sorular NCLEX 2024/2025 değişikliklerine göre güncel mi?",
    a: "Evet. Soru bankası, 2023'te tanıtılan Next Generation NCLEX (NGN) soru türlerini içeriyor — SATA, sıralı yanıt ve hesaplama soruları. Uyarlamalı algoritma, Pearson VUE'nun CAT mantığını yansıtır.",
  },
  {
    q: "MedMind AI, NCSBN veya NCLEX ile bağlantılı mı?",
    a: "Hayır. MedMind AI bağımsız bir hazırlık platformudur ve NCSBN veya NCLEX programıyla herhangi bir bağlantısı yoktur.",
  },
];

export default function TurkishNclexPage() {
  return (
    <>
      <ArticleNav />

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 pt-16 sm:pt-24 pb-12 sm:pb-16">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div>
            <div className="inline-flex items-center gap-2 bg-red/10 border border-red/20 px-3 py-1 rounded-full font-syne font-semibold text-xs text-red mb-5">
              <span className="w-1.5 h-1.5 rounded-full bg-red inline-block" />
              NCLEX-RN 2025 Hazırlık
            </div>
            <h1 className="font-syne font-extrabold text-3xl sm:text-4xl lg:text-5xl text-ink mb-4 leading-tight">
              NCLEX-RN&apos;i ilk denemede<br />geçin.
            </h1>
            <p className="text-ink-2 text-base sm:text-lg leading-relaxed mb-8 max-w-lg">
              Uyarlamalı CAT simülasyonları, YZ destekli klinik akıl yürütme analizi ve tüm NCLEX İstemci İhtiyaçları kategorilerinde performans takibi.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link href="/register"
                className="inline-block font-syne font-bold text-base bg-red text-white px-8 py-4 rounded-xl hover:bg-ink transition-colors">
                Ücretsiz başla →
              </Link>
              <Link href="/login"
                className="inline-block font-syne font-semibold text-base border border-border text-ink-2 px-8 py-4 rounded-xl hover:border-ink hover:text-ink transition-colors">
                Giriş yap
              </Link>
            </div>
            <p className="text-xs text-ink-3 mt-4 font-syne">Ücretsiz hesap · Günde 5 YZ sorusu · Kredi kartı gerekmez</p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {[
              { value: "600+", label: "NCLEX sorusu", sub: "SATA · CAT · NGN · hesaplamalar" },
              { value: "12",   label: "hemşirelik modülü", sub: "kanıta dayalı içerik" },
              { value: "7",    label: "İstemci İhtiyaçları", sub: "tam kategori kapsamı" },
              { value: "6",    label: "CJMM becerisi", sub: "klinik karar verme takibi" },
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
            <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink mb-2">Beş çalışma modu</h2>
            <p className="text-ink-3 text-sm">Ücretsiz 10 soruluk demodan 145 soruluk tam simülasyona.</p>
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
          <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink mb-2">Geçmek için ihtiyacınız olan her şey</h2>
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

      {/* FAQ */}
      <section className="bg-surface border-y border-border">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
          <h2 className="font-syne font-extrabold text-2xl sm:text-3xl text-ink mb-8 text-center">Sıkça sorulan sorular</h2>
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
          <h2 className="font-syne font-extrabold text-3xl sm:text-4xl mb-4">Başlamaya hazır mısınız?</h2>
          <p className="text-white/60 mb-8 text-base leading-relaxed">
            Şimdi ücretsiz demoyu deneyin — 10 soru, tam YZ açıklamaları, hesap gerekmez. Tam CAT simülasyonları ve kişisel analizlere erişmek için hesap oluşturun.
          </p>
          <Link href="/register"
            className="inline-block font-syne font-bold text-base bg-white text-ink px-8 py-4 rounded-xl hover:bg-red hover:text-white transition-colors">
            Ücretsiz başla →
          </Link>
          <p className="text-white/30 text-xs mt-5 font-syne">Kredi kartı gerekmez · Ücretsiz plan: günde 5 YZ sorusu</p>
        </div>
      </section>

      <PublicFooter />
    </>
  );
}
