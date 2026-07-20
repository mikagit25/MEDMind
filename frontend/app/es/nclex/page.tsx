import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "NCLEX en Español — Preparación para el Examen de Enfermería | MedMind AI",
  description:
    "Prepárate para el NCLEX en español. Preguntas de práctica con explicaciones detalladas en español médico latinoamericano. Rationales bilingües, flashcards y tutorías con IA.",
  alternates: { canonical: "https://medmind.ai/es/nclex" },
  openGraph: {
    title: "NCLEX en Español — MedMind AI",
    description:
      "Preguntas NCLEX con explicaciones completas en español médico. Ideal para enfermeras hispanohablantes que se preparan para el examen NCLEX-RN o NCLEX-PN.",
    url: "https://medmind.ai/es/nclex",
  },
};

const FEATURES = [
  {
    icon: "🇪🇸",
    title: "Explicaciones en español",
    body: "Cada pregunta incluye rationales completos en español médico latinoamericano. Activa el toggle de idioma durante la práctica para leer las explicaciones en tu idioma.",
  },
  {
    icon: "🧠",
    title: "Más de 3 000 preguntas NCLEX",
    body: "Banco de preguntas que cubre todos los dominios del plan de estudios NCLEX-RN: cuidado seguro y efectivo, promoción de la salud, integridad psicosocial y fisiológica.",
  },
  {
    icon: "🤖",
    title: "Tutor de IA en español",
    body: "Haz preguntas en español sobre cualquier tema de enfermería. Nuestro tutor responde con precisión clínica adaptada al nivel NCLEX.",
  },
  {
    icon: "📊",
    title: "Modo adaptativo (CAT)",
    body: "Simula el formato computerizado del NCLEX real con preguntas que se ajustan a tu nivel de dominio en tiempo real.",
  },
];

const CATEGORIES = [
  "Cuidado Seguro y Efectivo",
  "Promoción de la Salud",
  "Integridad Psicosocial",
  "Integridad Fisiológica Básica",
  "Farmacología y Terapias Parenterales",
  "Reducción del Riesgo",
  "Adaptación Fisiológica",
  "Manejo y Cuidado",
];

const FAQ = [
  {
    q: "¿Puedo practicar el NCLEX completamente en español?",
    a: "Las preguntas y opciones están en inglés (el examen real es en inglés), pero todas las explicaciones, rationales, puntos clave y consejos de examen están disponibles en español. Esto te permite entender los conceptos en tu idioma mientras te familiarizas con el vocabulario inglés necesario para el examen.",
  },
  {
    q: "¿Las explicaciones en español son traducciones automáticas?",
    a: "No. Las explicaciones son generadas y revisadas con un glosario médico especializado que preserva términos técnicos como NCLEX, SBAR, NPO, PRN, IV, entre otros. Usamos español médico latinoamericano, no castellano de España.",
  },
  {
    q: "¿MedMind AI está afiliado al NCSBN o al NCLEX?",
    a: "No. MedMind AI es una plataforma de preparación independiente y no tiene afiliación, respaldo ni conexión con el National Council of State Boards of Nursing (NCSBN) ni con el programa NCLEX.",
  },
  {
    q: "¿Qué planes incluyen las explicaciones en español?",
    a: "Las explicaciones en español están disponibles en los planes Student, Pro y Clinic. El plan Free incluye 5 preguntas de práctica por día en inglés.",
  },
];

export default function NclexEsPage() {
  return (
    <main className="min-h-screen bg-canvas">
      {/* Hero */}
      <section className="bg-ink text-white py-20 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-white/10 rounded-full px-4 py-1.5 text-sm font-syne mb-6">
            <span>🇪🇸</span>
            <span>NCLEX en Español</span>
          </div>
          <h1 className="font-syne font-extrabold text-4xl md:text-5xl leading-tight mb-5">
            Prepárate para el NCLEX<br />
            <span className="text-green">en tu idioma</span>
          </h1>
          <p className="font-serif text-lg text-white/80 mb-8 max-w-2xl mx-auto">
            Más de 3 000 preguntas NCLEX con explicaciones completas en español médico latinoamericano.
            Entiende los conceptos en español, practica en el formato del examen real.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Link
              href="/register"
              className="font-syne font-bold text-sm bg-green text-white px-8 py-3 rounded-xl hover:bg-green/90 transition-colors"
            >
              Comenzar gratis
            </Link>
            <Link
              href="/nurses/nclex"
              className="font-syne font-bold text-sm bg-white/10 text-white px-8 py-3 rounded-xl hover:bg-white/20 transition-colors"
            >
              Ver en inglés →
            </Link>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-16 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="font-syne font-bold text-2xl text-ink text-center mb-10">
            Diseñado para enfermeras hispanohablantes
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {FEATURES.map((f) => (
              <div key={f.title} className="bg-surface rounded-xl border border-border p-6">
                <div className="text-3xl mb-3">{f.icon}</div>
                <h3 className="font-syne font-bold text-base text-ink mb-2">{f.title}</h3>
                <p className="font-serif text-sm text-ink-2 leading-relaxed">{f.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Categories */}
      <section className="py-14 px-6 bg-surface border-y border-border">
        <div className="max-w-4xl mx-auto">
          <h2 className="font-syne font-bold text-xl text-ink mb-2 text-center">
            Dominios del NCLEX cubiertos
          </h2>
          <p className="font-serif text-sm text-ink-3 text-center mb-8">
            Preguntas en todos los dominios del plan de estudios NCLEX-RN y NCLEX-PN
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {CATEGORIES.map((cat) => (
              <div
                key={cat}
                className="bg-white rounded-lg border border-border px-3 py-3 text-center"
              >
                <span className="font-serif text-xs text-ink-2 leading-snug">{cat}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Language toggle explainer */}
      <section className="py-16 px-6">
        <div className="max-w-2xl mx-auto text-center">
          <div className="inline-flex items-center gap-3 bg-ink text-white rounded-xl px-5 py-3 text-sm font-syne mb-6 shadow-sm">
            <span className="opacity-60">🇺🇸 English</span>
            <span className="opacity-40 text-lg">↔</span>
            <span>🇪🇸 Español</span>
          </div>
          <h2 className="font-syne font-bold text-2xl text-ink mb-4">
            Cambia el idioma de las explicaciones con un clic
          </h2>
          <p className="font-serif text-sm text-ink-2 leading-relaxed">
            Durante la práctica, después de confirmar tu respuesta, verás un toggle que te permite cambiar
            entre explicaciones en inglés y español. El sistema recuerda tu preferencia entre sesiones.
          </p>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-14 px-6 bg-surface border-t border-border">
        <div className="max-w-2xl mx-auto">
          <h2 className="font-syne font-bold text-xl text-ink mb-8 text-center">
            Preguntas frecuentes
          </h2>
          <div className="space-y-5">
            {FAQ.map((item) => (
              <div key={item.q} className="bg-white rounded-xl border border-border p-5">
                <h3 className="font-syne font-semibold text-sm text-ink mb-2">{item.q}</h3>
                <p className="font-serif text-xs text-ink-2 leading-relaxed">{item.a}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-6">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="font-syne font-bold text-2xl text-ink mb-4">
            Empieza a practicar hoy
          </h2>
          <p className="font-serif text-sm text-ink-2 mb-8">
            Crea una cuenta gratuita y accede a 5 preguntas diarias sin costo.
            Los planes de pago desbloquean el banco completo y las explicaciones en español.
          </p>
          <Link
            href="/register"
            className="inline-block font-syne font-bold text-sm bg-ink text-white px-10 py-3 rounded-xl hover:bg-red transition-colors"
          >
            Registrarse gratis →
          </Link>
          <p className="mt-4 text-xs font-serif text-ink-3">
            MedMind AI no está afiliado, respaldado ni conectado con el NCSBN o el programa NCLEX.
          </p>
        </div>
      </section>
    </main>
  );
}
