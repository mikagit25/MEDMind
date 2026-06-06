"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { useI18n } from "@/lib/i18n";
import { useAuthStore } from "@/lib/store";
import { api, aiApi } from "@/lib/api";
import {
  type Lang, type CalcMeta, type FieldDef, type RiskBand,
  CALCULATORS, getCalc, getRiskBand, UI, CALC_SLUGS,
} from "./data";

// ── Colour helpers ───────────────────────────────────────────────────────────

const RISK_COLORS: Record<RiskBand["color"], { bg: string; text: string; border: string; badge: string }> = {
  green:    { bg: "bg-green-light", text: "text-green",    border: "border-green/30",    badge: "bg-green text-white" },
  amber:    { bg: "bg-amber-light", text: "text-amber",    border: "border-amber/30",    badge: "bg-amber text-white" },
  red:      { bg: "bg-red-light",   text: "text-red",      border: "border-red/30",      badge: "bg-red text-white" },
  "red-dark": { bg: "bg-red-light", text: "text-red",      border: "border-red/30",      badge: "bg-red text-white" },
};

type T = Record<Lang, string>;

// ── t() helper for inline translations ──────────────────────────────────────

function t(obj: Record<Lang, string> | undefined, lang: string): string {
  if (!obj) return "";
  return (obj as Record<string, string>)[lang] ?? obj.en ?? "";
}

// ── Checkbox field ───────────────────────────────────────────────────────────

function CheckboxField({
  field, checked, lang, onChange,
}: {
  field: Extract<FieldDef, { type: "checkbox" }>;
  checked: boolean;
  lang: string;
  onChange: (v: boolean) => void;
}) {
  const pts = field.points;
  const ptsLabel = pts > 0 ? `+${pts}` : `${pts}`;
  return (
    <label className={`flex items-start gap-3 p-3 sm:p-4 rounded-lg border cursor-pointer transition-all ${
      checked ? "bg-surface-2 border-border-2" : "bg-surface border-border hover:border-border-2"
    }`}>
      <div className={`mt-0.5 w-5 h-5 flex-shrink-0 rounded border-2 flex items-center justify-center transition-colors ${
        checked ? "bg-ink border-ink" : "border-border-2"
      }`}>
        {checked && (
          <svg className="w-3 h-3 text-white" viewBox="0 0 12 12" fill="none">
            <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        )}
      </div>
      <input type="checkbox" className="sr-only" checked={checked} onChange={e => onChange(e.target.checked)} />
      <div className="flex-1 min-w-0">
        <span className="font-syne font-semibold text-sm text-ink leading-snug">{t(field.label, lang)}</span>
        {field.hint && <p className="text-ink-3 text-xs mt-0.5">{t(field.hint, lang)}</p>}
      </div>
      <span className={`flex-shrink-0 font-syne font-bold text-sm px-2 py-0.5 rounded ${
        pts < 0 ? "bg-blue/10 text-blue" : "bg-surface-2 text-ink-2"
      }`}>{ptsLabel}</span>
    </label>
  );
}

// ── Select field ─────────────────────────────────────────────────────────────

function SelectField({
  field, value, lang, onChange,
}: {
  field: Extract<FieldDef, { type: "select" }>;
  value: number;
  lang: string;
  onChange: (v: number) => void;
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="font-syne font-semibold text-sm text-ink">{t(field.label, lang)}</span>
        {field.hint && <span className="text-ink-3 text-xs">{t(field.hint, lang)}</span>}
      </div>
      <div className="space-y-1.5">
        {field.options.map(opt => (
          <label key={opt.value} className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
            value === opt.value ? "bg-surface-2 border-border-2" : "bg-surface border-border hover:border-border-2"
          }`}>
            <div className={`w-4 h-4 flex-shrink-0 rounded-full border-2 flex items-center justify-center transition-colors ${
              value === opt.value ? "border-ink" : "border-border-2"
            }`}>
              {value === opt.value && <div className="w-2 h-2 rounded-full bg-ink" />}
            </div>
            <input type="radio" className="sr-only" checked={value === opt.value} onChange={() => onChange(opt.value)} />
            <span className="font-syne text-sm text-ink flex-1">{t(opt.label, lang)}</span>
            <span className="font-syne font-bold text-sm text-ink-3 flex-shrink-0">+{opt.value}</span>
          </label>
        ))}
      </div>
    </div>
  );
}

// ── Result panel ─────────────────────────────────────────────────────────────

function ResultPanel({ calc, score, band, lang }: {
  calc: CalcMeta; score: number; band: RiskBand | null; lang: string;
}) {
  const colors = band ? RISK_COLORS[band.color] : RISK_COLORS.green;
  return (
    <div className={`rounded-xl border p-5 sm:p-6 space-y-4 transition-all ${colors.bg} ${colors.border}`}>
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <p className="text-ink-3 text-xs font-syne uppercase tracking-widest mb-1">{t(UI.score, lang)}</p>
          <p className={`font-syne font-extrabold text-4xl ${colors.text}`}>{score}</p>
          <p className="text-ink-3 text-xs mt-0.5">/ {calc.maxScore}</p>
        </div>
        {band && (
          <span className={`font-syne font-bold text-sm px-4 py-1.5 rounded-full ${colors.badge}`}>
            {t(UI[band.labelKey], lang)}
          </span>
        )}
      </div>
      {band && (
        <>
          <p className={`text-sm leading-relaxed ${colors.text} font-medium`}>{t(band.description, lang)}</p>
          <div className="border-t border-current/20 pt-4">
            <p className="text-xs font-syne uppercase tracking-widest text-ink-3 mb-1">{t(UI.recommendation, lang)}</p>
            <p className="text-sm text-ink leading-relaxed">{t(band.recommendation, lang)}</p>
          </div>
        </>
      )}
    </div>
  );
}

// ── AI Panel: CTA for guests, live interpretation for auth users ─────────────

const AI_INTERPRET_PROMPT: Record<Lang, (calcName: string, score: number, risk: string) => string> = {
  en: (c, s, r) => `I just calculated a ${c} score of ${s}, which indicates ${r}. Please provide a concise clinical interpretation: what does this score mean in practice, what are the key management implications, and what should I monitor or consider next? Keep it practical and evidence-based.`,
  ru: (c, s, r) => `Я рассчитал шкалу ${c}: результат ${s} баллов, что соответствует ${r}. Пожалуйста, дай краткую клиническую интерпретацию: что означает этот результат на практике, какова тактика ведения, что необходимо мониторировать?`,
  ar: (c, s, r) => `قمت بحساب نتيجة ${c}: ${s} نقطة، مما يشير إلى ${r}. أعطني تفسيراً سريرياً موجزاً: ماذا تعني هذه النتيجة عملياً، وما هي الخطوات الإدارية الرئيسية، وما الذي يجب مراقبته؟`,
  tr: (c, s, r) => `${c} skorunu hesapladım: ${s} puan, bu ${r} gösteriyor. Pratik klinik yorum ver: bu skor ne anlama geliyor, temel yönetim seçenekleri neler ve neleri takip etmeliyim?`,
  de: (c, s, r) => `Ich habe einen ${c}-Score von ${s} berechnet, was auf ${r} hinweist. Bitte gib eine kurze klinische Interpretation: Was bedeutet dieser Score in der Praxis, welche therapeutischen Konsequenzen ergeben sich und was sollte überwacht werden?`,
  fr: (c, s, r) => `J'ai calculé un score ${c} de ${s}, indiquant ${r}. Donne une interprétation clinique concise : que signifie ce résultat en pratique, quelles sont les implications thérapeutiques et que faut-il surveiller?`,
  es: (c, s, r) => `He calculado una puntuación ${c} de ${s}, que indica ${r}. Por favor, proporciona una interpretación clínica concisa: qué significa este resultado en la práctica, cuáles son las implicaciones de manejo y qué se debe monitorizar?`,
};

function AiPanel({ lang, calcName, score, riskLabel }: {
  lang: string; calcName: string; score: number; riskLabel: string;
}) {
  const { isAuthenticated } = useAuthStore();
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<string | null>(null);
  const [error, setError] = useState(false);

  async function fetchInterpretation() {
    setLoading(true);
    setError(false);
    try {
      const prompt = AI_INTERPRET_PROMPT[lang as Lang]?.(calcName, score, riskLabel)
        ?? AI_INTERPRET_PROMPT.en(calcName, score, riskLabel);
      const res = await aiApi.ask({ message: prompt, specialty: "general", search_pubmed: false });
      setResponse(res.response ?? res.content ?? res.message ?? JSON.stringify(res));
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="bg-surface border border-border rounded-xl p-5 flex flex-col sm:flex-row gap-4 items-start sm:items-center">
        <div className="flex-1 min-w-0">
          <p className="font-syne font-bold text-sm text-ink mb-1">{t(UI.ai_cta_title, lang)}</p>
          <p className="text-ink-3 text-xs leading-relaxed">{t(UI.ai_cta_desc, lang)}</p>
        </div>
        <Link href="/register"
          className="flex-shrink-0 font-syne font-semibold text-sm bg-ink text-white px-4 py-2 rounded hover:bg-red transition-colors whitespace-nowrap">
          {t(UI.ai_cta_btn, lang)}
        </Link>
      </div>
    );
  }

  return (
    <div className="bg-surface border border-border rounded-xl p-5 space-y-3">
      <div className="flex items-center gap-2">
        <div className="w-6 h-6 rounded bg-red flex items-center justify-center text-white text-[10px] font-bold font-syne flex-shrink-0">AI</div>
        <p className="font-syne font-bold text-sm text-ink">{t(UI.ai_cta_title, lang)}</p>
      </div>

      {response ? (
        <div className="text-sm text-ink leading-relaxed whitespace-pre-wrap">{response}</div>
      ) : (
        <p className="text-ink-3 text-xs leading-relaxed">{t(UI.ai_cta_desc, lang)}</p>
      )}

      {error && (
        <p className="text-red text-xs">{lang === "ru" ? "Ошибка. Попробуйте ещё раз." : "Error. Please try again."}</p>
      )}

      {!response && (
        <button onClick={fetchInterpretation} disabled={loading}
          className="w-full font-syne font-bold text-sm bg-red text-white py-2.5 rounded hover:bg-ink transition-colors disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2">
          {loading ? (
            <>
              <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              {lang === "ru" ? "Claude думает…" : lang === "ar" ? "كلود يفكر…" : lang === "de" ? "Claude denkt…" : lang === "fr" ? "Claude réfléchit…" : lang === "es" ? "Claude piensa…" : lang === "tr" ? "Claude düşünüyor…" : "Claude is thinking…"}
            </>
          ) : (
            lang === "ru" ? "AI-интерпретация этого результата" : lang === "ar" ? "تفسير ذكاء اصطناعي لهذه النتيجة" : lang === "de" ? "KI-Interpretation dieses Ergebnisses" : lang === "fr" ? "Interprétation IA de ce résultat" : lang === "es" ? "Interpretación IA de este resultado" : lang === "tr" ? "Bu sonucun yapay zeka yorumu" : "AI interpretation of this result"
          )}
        </button>
      )}

      {response && (
        <button onClick={() => setResponse(null)}
          className="text-ink-3 text-xs font-syne hover:text-ink transition-colors">
          {lang === "ru" ? "Новый запрос" : "New query"}
        </button>
      )}
    </div>
  );
}

// ── Checkbox-based calculator ─────────────────────────────────────────────────

function CheckboxCalc({ calc, lang }: { calc: CalcMeta; lang: string }) {
  const initState = useMemo(() => {
    const s: Record<string, number> = {};
    calc.fields.forEach((f, i) => {
      if (f.type === "checkbox") s[`cb_${i}`] = 0;
      else if (f.type === "select") s[f.id] = Math.min(...f.options.map(o => o.value));
    });
    return s;
  }, [calc]);

  const [vals, setVals] = useState<Record<string, number>>(initState);
  const score = useMemo(() => Object.values(vals).reduce((a, b) => a + b, 0), [vals]);
  const band = getRiskBand(calc, score);

  function setField(key: string, v: number) {
    setVals(prev => ({ ...prev, [key]: v }));
  }
  function reset() { setVals(initState); }

  return (
    <div className="grid lg:grid-cols-[1fr_360px] gap-6">
      {/* Left: inputs */}
      <div className="space-y-3">
        {calc.fields.map((f, i) => {
          if (f.type === "checkbox") {
            const key = `cb_${i}`;
            return (
              <CheckboxField
                key={key}
                field={f}
                checked={vals[key] !== 0}
                lang={lang}
                onChange={v => setField(key, v ? f.points : 0)}
              />
            );
          }
          if (f.type === "select") {
            return (
              <SelectField
                key={f.id}
                field={f}
                value={vals[f.id] ?? 0}
                lang={lang}
                onChange={v => setField(f.id, v)}
              />
            );
          }
          return null;
        })}
      </div>

      {/* Right: result + meta */}
      <div className="space-y-4">
        <ResultPanel calc={calc} score={score} band={band} lang={lang} />

        {calc.note && (
          <div className="bg-blue-light border border-blue/20 rounded-lg p-3">
            <p className="text-blue text-xs leading-relaxed">{t(calc.note, lang)}</p>
          </div>
        )}

        <button
          onClick={reset}
          className="w-full font-syne font-semibold text-sm border border-border text-ink-2 py-2 rounded hover:border-border-2 hover:text-ink transition-colors"
        >
          {t(UI.reset, lang)}
        </button>

        {calc.relatedSlug && calc.relatedLabelI18n && (
          <Link
            href={`/modules`}
            className="flex items-center justify-between w-full bg-surface border border-border rounded-lg px-4 py-3 hover:border-border-2 transition-colors group"
          >
            <span className="font-syne text-sm text-ink-2 group-hover:text-ink transition-colors">{t(UI.study_topic, lang)}</span>
            <span className="text-ink-3 text-xs">{t(calc.relatedLabelI18n, lang)}</span>
          </Link>
        )}

        <AiPanel
          lang={lang}
          calcName={calc.nameI18n.en}
          score={score}
          riskLabel={band ? t(UI[band.labelKey], "en") : ""}
        />

        <div className="text-ink-3 text-xs leading-relaxed">
          <span className="font-syne font-semibold">{t(UI.reference, lang)}: </span>
          {calc.reference}
        </div>
      </div>
    </div>
  );
}

// ── eGFR Calculator (CKD-EPI 2021) ──────────────────────────────────────────

const eGFR_T: Record<string, Record<Lang, string>> = {
  name:        { en: "eGFR (CKD-EPI 2021)", ru: "рСКФ (CKD-EPI 2021)", ar: "معدل الترشيح الكبيبي التقديري (CKD-EPI 2021)", tr: "eGFR (CKD-EPI 2021)", de: "eGFR (CKD-EPI 2021)", fr: "DFGe (CKD-EPI 2021)", es: "TFGe (CKD-EPI 2021)" },
  subtitle:    { en: "Kidney function and CKD staging", ru: "Функция почек и стадия ХБП", ar: "وظائف الكلى وتصنيف مرض الكلى المزمن", tr: "Böbrek fonksiyonu ve KBH evrelemesi", de: "Nierenfunktion und CKD-Stadienbestimmung", fr: "Fonction rénale et stadification de l'IRC", es: "Función renal y estadificación de ERC" },
  unit_mg:     { en: "mg/dL", ru: "мг/дл", ar: "ملغ/ديسيلتر", tr: "mg/dL", de: "mg/dl", fr: "mg/dL", es: "mg/dL" },
  unit_umol:   { en: "μmol/L", ru: "мкмоль/л", ar: "ميكرومول/لتر", tr: "μmol/L", de: "μmol/l", fr: "μmol/L", es: "μmol/L" },
  calculate:   { en: "Calculate eGFR", ru: "Вычислить рСКФ", ar: "احسب معدل الترشيح الكبيبي التقديري", tr: "eGFR'yi hesapla", de: "eGFR berechnen", fr: "Calculer le DFGe", es: "Calcular TFGe" },
  reference:   { en: "Clinical reference", ru: "Клинический источник", ar: "المرجع السريري", tr: "Klinik referans", de: "Klinische Referenz", fr: "Référence clinique", es: "Referencia clínica" },
  ref_text:    { en: "Inker LA et al. NEJM 2021;385:1737–1749 · KDIGO CKD Guidelines 2024", ru: "Inker LA et al. NEJM 2021;385:1737–1749 · Рекомендации KDIGO по ХБП 2024", ar: "Inker LA et al. NEJM 2021;385:1737–1749 · إرشادات KDIGO لمرض الكلى المزمن 2024", tr: "Inker LA et al. NEJM 2021;385:1737–1749 · KDIGO KBH Kılavuzları 2024", de: "Inker LA et al. NEJM 2021;385:1737–1749 · KDIGO CKD-Leitlinien 2024", fr: "Inker LA et al. NEJM 2021;385:1737–1749 · Recommandations KDIGO IRC 2024", es: "Inker LA et al. NEJM 2021;385:1737–1749 · Guías KDIGO ERC 2024" },
  g1: { en: "G1 — Normal or high (≥90)", ru: "G1 — Норма или высокая (≥90)", ar: "G1 — طبيعي أو مرتفع (≥90)", tr: "G1 — Normal veya yüksek (≥90)", de: "G1 — Normal oder erhöht (≥90)", fr: "G1 — Normal ou élevé (≥90)", es: "G1 — Normal o alta (≥90)" },
  g2: { en: "G2 — Mildly decreased (60–89)", ru: "G2 — Незначительно снижена (60–89)", ar: "G2 — منخفض بشكل خفيف (60–89)", tr: "G2 — Hafif azalmış (60–89)", de: "G2 — Leicht vermindert (60–89)", fr: "G2 — Légèrement diminué (60–89)", es: "G2 — Levemente disminuida (60–89)" },
  g3a: { en: "G3a — Mild-moderately decreased (45–59)", ru: "G3a — Умеренно снижена (45–59)", ar: "G3a — منخفض من خفيف إلى معتدل (45–59)", tr: "G3a — Hafif-orta azalmış (45–59)", de: "G3a — Mäßig vermindert (45–59)", fr: "G3a — Légèrement à modérément diminué (45–59)", es: "G3a — Leve a moderadamente disminuida (45–59)" },
  g3b: { en: "G3b — Moderately-severely decreased (30–44)", ru: "G3b — Значительно снижена (30–44)", ar: "G3b — منخفض من متوسط إلى شديد (30–44)", tr: "G3b — Orta-ciddi azalmış (30–44)", de: "G3b — Mäßig bis stark vermindert (30–44)", fr: "G3b — Modérément à sévèrement diminué (30–44)", es: "G3b — Moderada a gravemente disminuida (30–44)" },
  g4: { en: "G4 — Severely decreased (15–29)", ru: "G4 — Резко снижена (15–29)", ar: "G4 — منخفض بشدة (15–29)", tr: "G4 — Ciddi azalmış (15–29)", de: "G4 — Stark vermindert (15–29)", fr: "G4 — Sévèrement diminué (15–29)", es: "G4 — Gravemente disminuida (15–29)" },
  g5: { en: "G5 — Kidney failure (<15)", ru: "G5 — Почечная недостаточность (<15)", ar: "G5 — فشل كلوي (<15)", tr: "G5 — Böbrek yetmezliği (<15)", de: "G5 — Nierenversagen (<15)", fr: "G5 — Insuffisance rénale (<15)", es: "G5 — Insuficiencia renal (<15)" },
  rec_g1: { en: "Normal kidney function. Monitor if at-risk (DM, HTN, family history).", ru: "Нормальная функция почек. Мониторинг при факторах риска.", ar: "وظائف الكلى طبيعية. المراقبة إذا كان هناك خطر (السكري، ارتفاع ضغط الدم، التاريخ العائلي).", tr: "Normal böbrek fonksiyonu. Risk varsa takip (DM, HTN, aile öyküsü).", de: "Normale Nierenfunktion. Monitoring bei Risikofaktoren (DM, HTN, Familienanamnese).", fr: "Fonction rénale normale. Surveillance si à risque (DM, HTN, ATCD familiaux).", es: "Función renal normal. Monitorizar si hay factores de riesgo (DM, HTA, antecedentes familiares)." },
  rec_g2: { en: "Mildly reduced. Monitor annually. Address cardiovascular risk.", ru: "Незначительно снижена. Ежегодный мониторинг. Коррекция сердечно-сосудистых рисков.", ar: "منخفض بشكل خفيف. المراقبة سنوياً. معالجة خطر القلب والأوعية.", tr: "Hafif azalmış. Yıllık takip. Kardiyovasküler riski ele alın.", de: "Leicht vermindert. Jährliche Überwachung. Kardiovaskuläre Risikofaktoren behandeln.", fr: "Légèrement réduit. Surveillance annuelle. Traiter les facteurs de risque cardiovasculaire.", es: "Levemente reducida. Control anual. Tratar riesgo cardiovascular." },
  rec_g3a: { en: "CKD stage G3a. Nephrology referral if progression. Avoid nephrotoxins. Monitor BP, HbA1c.", ru: "ХБП G3a. Направление к нефрологу при прогрессировании. Избегать нефротоксинов.", ar: "مرض الكلى المزمن G3a. إحالة لطب الكلى إذا تفاقمت الحالة. تجنب السموم الكلوية.", tr: "KBH G3a. İlerleme varsa nefroloji yönlendirmesi. Nefrotoksik ilaçlardan kaçının.", de: "CKD G3a. Nephrologische Überweisung bei Progression. Nephrotoxine meiden. RR, HbA1c überwachen.", fr: "IRC G3a. Adresser en néphrologie si progression. Éviter les néphrotoxiques.", es: "ERC G3a. Derivar a nefrología si hay progresión. Evitar nefrotóxicos. Control PA, HbA1c." },
  rec_g3b: { en: "CKD stage G3b. Nephrology referral. Dietary restriction (sodium, phosphate, protein). Anaemia workup.", ru: "ХБП G3b. Консультация нефролога. Диетические ограничения. Оценка анемии.", ar: "مرض الكلى المزمن G3b. إحالة لطب الكلى. قيود غذائية. تقييم فقر الدم.", tr: "KBH G3b. Nefroloji yönlendirmesi. Diyet kısıtlaması. Anemi değerlendirmesi.", de: "CKD G3b. Nephrologische Vorstellung. Diätrestriktion. Anämie-Abklärung.", fr: "IRC G3b. Consultation néphrologiste. Restriction diététique. Bilan d'anémie.", es: "ERC G3b. Remisión a nefrología. Restricción dietética. Evaluación de anemia." },
  rec_g4: { en: "CKD stage G4. Nephrologist follow-up. Prepare for renal replacement therapy planning.", ru: "ХБП G4. Наблюдение нефролога. Подготовка к заместительной почечной терапии.", ar: "مرض الكلى المزمن G4. متابعة طبيب الكلى. التخطيط للعلاج ببديل الكلى.", tr: "KBH G4. Nefrolog takibi. Renal replasman tedavisi planlaması.", de: "CKD G4. Nephrologische Betreuung. Planung der Nierenersatztherapie.", fr: "IRC G4. Suivi néphrologue. Préparation à la thérapie de remplacement rénal.", es: "ERC G4. Seguimiento nefrológico. Planificación de terapia renal sustitutiva." },
  rec_g5: { en: "Kidney failure. Immediate nephrology follow-up. Initiate or evaluate renal replacement therapy (dialysis, transplantation).", ru: "Почечная недостаточность. Немедленно к нефрологу. Диализ или трансплантация.", ar: "فشل كلوي. متابعة فورية مع طبيب الكلى. الغسيل الكلوي أو زرع الكلى.", tr: "Böbrek yetmezliği. Acil nefroloji takibi. Diyaliz veya nakil değerlendirmesi.", de: "Nierenversagen. Sofortige Nephrologievorststellung. Nierenersatztherapie einleiten.", fr: "Insuffisance rénale. Suivi néphrologue immédiat. Thérapie de remplacement rénal.", es: "Insuficiencia renal. Seguimiento nefrológico inmediato. Terapia renal sustitutiva." },
};

function calcEGFR(creatMgdl: number, age: number, isFemale: boolean): number {
  const k = isFemale ? 0.7 : 0.9;
  const a = isFemale ? -0.241 : -0.302;
  const ratio = creatMgdl / k;
  return 142 * Math.pow(Math.min(ratio, 1), a) * Math.pow(Math.max(ratio, 1), -1.200)
    * Math.pow(0.9938, age) * (isFemale ? 1.012 : 1);
}

interface CkdStage {
  stage: string; labelKey: keyof typeof eGFR_T; recKey: keyof typeof eGFR_T;
  color: "green" | "amber" | "red"; min: number; max: number;
}
const CKD_STAGES: CkdStage[] = [
  { stage: "G1",  labelKey: "g1",  recKey: "rec_g1",  color: "green",  min: 90,  max: Infinity },
  { stage: "G2",  labelKey: "g2",  recKey: "rec_g2",  color: "green",  min: 60,  max: 89 },
  { stage: "G3a", labelKey: "g3a", recKey: "rec_g3a", color: "amber",  min: 45,  max: 59 },
  { stage: "G3b", labelKey: "g3b", recKey: "rec_g3b", color: "amber",  min: 30,  max: 44 },
  { stage: "G4",  labelKey: "g4",  recKey: "rec_g4",  color: "red",    min: 15,  max: 29 },
  { stage: "G5",  labelKey: "g5",  recKey: "rec_g5",  color: "red",    min: 0,   max: 14 },
];

function EgfrCalc({ lang }: { lang: string }) {
  const [creat, setCreat] = useState("");
  const [unit, setUnit] = useState<"mg" | "umol">("mg");
  const [age, setAge] = useState("");
  const [sex, setSex] = useState<"male" | "female">("male");
  const [result, setResult] = useState<null | { egfr: number; stage: CkdStage }>(null);

  function calculate() {
    const cr = parseFloat(creat);
    const ag = parseInt(age);
    if (!cr || !ag || cr <= 0 || ag <= 0 || ag > 120) return;
    const mgdl = unit === "umol" ? cr / 88.42 : cr;
    const egfr = Math.round(calcEGFR(mgdl, ag, sex === "female") * 10) / 10;
    const stage = CKD_STAGES.find(s => egfr >= s.min && egfr <= s.max) ?? CKD_STAGES[CKD_STAGES.length - 1];
    setResult({ egfr, stage });
  }

  const colors = result ? RISK_COLORS[result.stage.color] : RISK_COLORS.green;
  const tl = (key: string) => t(eGFR_T[key], lang);

  return (
    <div className="grid lg:grid-cols-[1fr_360px] gap-6">
      {/* Inputs */}
      <div className="space-y-4">
        <div className="space-y-1.5">
          <label className="font-syne font-semibold text-sm text-ink">{t(UI.creatinine, lang)}</label>
          <div className="flex gap-2">
            <input
              type="number" min="0" step="0.01" placeholder={unit === "mg" ? "e.g. 1.2" : "e.g. 106"}
              value={creat} onChange={e => setCreat(e.target.value)}
              className="flex-1 border border-border rounded-lg px-3 py-2.5 text-sm font-syne bg-surface text-ink placeholder-ink-3 focus:outline-none focus:border-border-2"
            />
            <select
              value={unit} onChange={e => setUnit(e.target.value as "mg" | "umol")}
              className="border border-border rounded-lg px-3 py-2.5 text-sm font-syne bg-surface text-ink focus:outline-none focus:border-border-2"
            >
              <option value="mg">{tl("unit_mg")}</option>
              <option value="umol">{tl("unit_umol")}</option>
            </select>
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="font-syne font-semibold text-sm text-ink">{t(UI.age, lang)}</label>
          <input
            type="number" min="18" max="120" placeholder="e.g. 65"
            value={age} onChange={e => setAge(e.target.value)}
            className="w-full border border-border rounded-lg px-3 py-2.5 text-sm font-syne bg-surface text-ink placeholder-ink-3 focus:outline-none focus:border-border-2"
          />
        </div>

        <div className="space-y-1.5">
          <label className="font-syne font-semibold text-sm text-ink">{t(UI.sex, lang)}</label>
          <div className="flex gap-2">
            {(["male", "female"] as const).map(s => (
              <button key={s} onClick={() => setSex(s)}
                className={`flex-1 font-syne font-semibold text-sm py-2.5 rounded-lg border transition-colors ${
                  sex === s ? "bg-ink text-white border-ink" : "bg-surface text-ink-2 border-border hover:border-border-2"
                }`}>
                {t(UI[s], lang)}
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={calculate}
          className="w-full font-syne font-bold text-sm bg-ink text-white py-3 rounded-lg hover:bg-red transition-colors"
        >
          {tl("calculate")}
        </button>
      </div>

      {/* Result */}
      <div className="space-y-4">
        {result ? (
          <div className={`rounded-xl border p-5 space-y-4 ${colors.bg} ${colors.border}`}>
            <div className="flex items-center justify-between gap-4 flex-wrap">
              <div>
                <p className="text-ink-3 text-xs font-syne uppercase tracking-widest mb-1">{t(UI.egfr_result, lang)}</p>
                <p className={`font-syne font-extrabold text-4xl ${colors.text}`}>{result.egfr}</p>
                <p className="text-ink-3 text-xs mt-0.5">mL/min/1.73m²</p>
              </div>
              <div className="text-right">
                <p className="text-ink-3 text-xs font-syne uppercase tracking-widest mb-1">{t(UI.ckd_stage, lang)}</p>
                <span className={`font-syne font-bold text-lg px-3 py-1 rounded-full ${colors.badge}`}>{result.stage.stage}</span>
              </div>
            </div>
            <p className={`text-sm font-medium ${colors.text}`}>{tl(result.stage.labelKey)}</p>
            <div className="border-t border-current/20 pt-4">
              <p className="text-xs font-syne uppercase tracking-widest text-ink-3 mb-1">{t(UI.recommendation, lang)}</p>
              <p className="text-sm text-ink leading-relaxed">{tl(result.stage.recKey)}</p>
            </div>
          </div>
        ) : (
          <div className="rounded-xl border border-border bg-surface p-8 flex flex-col items-center justify-center text-center min-h-[200px]">
            <p className="text-ink-3 text-sm font-syne">
              {lang === "ru" ? "Введите данные и нажмите «Вычислить»" :
               lang === "ar" ? "أدخل القيم واضغط على احسب" :
               lang === "de" ? "Werte eingeben und berechnen" :
               lang === "fr" ? "Entrez les valeurs et calculez" :
               lang === "es" ? "Ingrese los valores y calcule" :
               lang === "tr" ? "Değerleri girin ve hesaplayın" :
               "Enter values and press Calculate"}
            </p>
          </div>
        )}

        <AiPanel
          lang={lang}
          calcName="eGFR (CKD-EPI 2021)"
          score={result?.egfr ?? 0}
          riskLabel={result ? `CKD stage ${result.stage.stage}` : ""}
        />

        <div className="text-ink-3 text-xs leading-relaxed">
          <span className="font-syne font-semibold">{tl("reference")}: </span>
          {tl("ref_text")}
        </div>
      </div>
    </div>
  );
}

// ── Shared numeric input helpers ──────────────────────────────────────────────

function NumInput({ label, value, onChange, placeholder, unit, min = 0, max, step = "any" }: {
  label: string; value: string; onChange: (v: string) => void;
  placeholder?: string; unit?: string; min?: number; max?: number; step?: string;
}) {
  return (
    <div className="space-y-1.5">
      <label className="font-syne font-semibold text-sm text-ink">{label}</label>
      <div className="flex gap-2">
        <input
          type="number" min={min} max={max} step={step} placeholder={placeholder}
          value={value} onChange={e => onChange(e.target.value)}
          className="flex-1 border border-border rounded-lg px-3 py-2.5 text-sm font-syne bg-surface text-ink placeholder-ink-3 focus:outline-none focus:border-border-2"
        />
        {unit && <span className="flex items-center px-3 text-sm text-ink-3 font-syne border border-border rounded-lg bg-bg">{unit}</span>}
      </div>
    </div>
  );
}

function NumResult({ label, value, unit, description, recommendation, color }: {
  label: string; value: string | null; unit: string; description?: string; recommendation?: string;
  color: "green" | "amber" | "red";
}) {
  const colors = RISK_COLORS[color];
  if (!value) {
    return (
      <div className="rounded-xl border border-border bg-surface p-8 flex items-center justify-center min-h-[160px]">
        <p className="text-ink-3 text-sm font-syne text-center">Enter values and press Calculate</p>
      </div>
    );
  }
  return (
    <div className={`rounded-xl border p-5 space-y-3 ${colors.bg} ${colors.border}`}>
      <div>
        <p className="text-ink-3 text-xs font-syne uppercase tracking-widest mb-1">{label}</p>
        <p className={`font-syne font-extrabold text-4xl ${colors.text}`}>{value}</p>
        <p className="text-ink-3 text-xs mt-0.5">{unit}</p>
      </div>
      {description && <p className={`text-sm font-medium leading-relaxed ${colors.text}`}>{description}</p>}
      {recommendation && (
        <div className="border-t border-current/20 pt-3">
          <p className="text-xs font-syne uppercase tracking-widest text-ink-3 mb-1">Recommendation</p>
          <p className="text-sm text-ink leading-relaxed">{recommendation}</p>
        </div>
      )}
    </div>
  );
}

// ── BMI Calculator ────────────────────────────────────────────────────────────

function BmiCalc({ lang }: { lang: string }) {
  const L: Record<string, Record<Lang, string>> = {
    weight:  { en: "Weight", ru: "Масса тела", ar: "الوزن", tr: "Ağırlık", de: "Gewicht", fr: "Poids", es: "Peso" },
    height:  { en: "Height", ru: "Рост", ar: "الطول", tr: "Boy", de: "Größe", fr: "Taille", es: "Talla" },
    calc:    { en: "Calculate BMI", ru: "Вычислить ИМТ", ar: "احسب مؤشر كتلة الجسم", tr: "VKİ hesapla", de: "BMI berechnen", fr: "Calculer l'IMC", es: "Calcular IMC" },
    result:  { en: "BMI", ru: "ИМТ", ar: "مؤشر كتلة الجسم", tr: "VKİ", de: "BMI", fr: "IMC", es: "IMC" },
    ref:     { en: "WHO BMI Classification 2024", ru: "Классификация ВОЗ 2024", ar: "تصنيف منظمة الصحة العالمية 2024", tr: "WHO BMI Sınıflaması 2024", de: "WHO BMI-Klassifikation 2024", fr: "Classification IMC OMS 2024", es: "Clasificación IMC OMS 2024" },
  };
  const [weight, setWeight] = useState("");
  const [height, setHeight] = useState("");
  const [result, setResult] = useState<null | { bmi: number; label: string; rec: string; color: "green" | "amber" | "red" }>(null);

  function getBmiCategory(bmi: number): { label: string; rec: string; color: "green" | "amber" | "red" } {
    if (bmi < 18.5) return {
      label: lang === "ru" ? "Дефицит массы тела" : lang === "ar" ? "نقص الوزن" : lang === "de" ? "Untergewicht" : lang === "fr" ? "Insuffisance pondérale" : lang === "es" ? "Bajo peso" : lang === "tr" ? "Düşük kilo" : "Underweight",
      rec: lang === "ru" ? "Нутритивная поддержка. Исключить недоедание, эндокринопатии." : "Nutritional support. Exclude malnutrition, endocrinopathies.",
      color: "amber",
    };
    if (bmi < 25) return {
      label: lang === "ru" ? "Нормальная масса тела" : lang === "ar" ? "وزن طبيعي" : lang === "de" ? "Normalgewicht" : lang === "fr" ? "Poids normal" : lang === "es" ? "Peso normal" : lang === "tr" ? "Normal kilo" : "Normal weight",
      rec: lang === "ru" ? "Поддерживайте здоровый образ жизни и регулярную физическую активность." : "Maintain healthy lifestyle and regular physical activity.",
      color: "green",
    };
    if (bmi < 30) return {
      label: lang === "ru" ? "Избыточная масса тела" : lang === "ar" ? "زيادة الوزن" : lang === "de" ? "Übergewicht" : lang === "fr" ? "Surpoids" : lang === "es" ? "Sobrepeso" : lang === "tr" ? "Fazla kilo" : "Overweight",
      rec: lang === "ru" ? "Изменение образа жизни. Оценка метаболических рисков (АД, гликемия, липиды)." : "Lifestyle modification. Assess metabolic risk factors (BP, glucose, lipids).",
      color: "amber",
    };
    return {
      label: lang === "ru" ? "Ожирение" : lang === "ar" ? "السمنة" : lang === "de" ? "Adipositas" : lang === "fr" ? "Obésité" : lang === "es" ? "Obesidad" : lang === "tr" ? "Obezite" : "Obesity",
      rec: lang === "ru" ? "Вмешательство: диета, ФА, медикаменты или бариатрическая хирургия (≥40). Скрининг осложнений." : "Intervention: diet, exercise, medications, or bariatric surgery (≥40). Screen for complications.",
      color: "red",
    };
  }

  function calculate() {
    const w = parseFloat(weight), h = parseFloat(height) / 100;
    if (!w || !h || w <= 0 || h <= 0) return;
    const bmi = Math.round((w / (h * h)) * 10) / 10;
    setResult({ bmi, ...getBmiCategory(bmi) });
  }

  return (
    <div className="grid lg:grid-cols-[1fr_360px] gap-6">
      <div className="space-y-4">
        <NumInput label={t(L.weight, lang)} value={weight} onChange={setWeight} placeholder="e.g. 80" unit="kg" />
        <NumInput label={t(L.height, lang)} value={height} onChange={setHeight} placeholder="e.g. 175" unit="cm" />
        <button onClick={calculate} className="w-full font-syne font-bold text-sm bg-ink text-white py-3 rounded-lg hover:bg-red transition-colors">{t(L.calc, lang)}</button>
      </div>
      <div className="space-y-4">
        <NumResult label={t(L.result, lang)} value={result ? String(result.bmi) : null} unit="kg/m²" description={result?.label} recommendation={result?.rec} color={result?.color ?? "green"} />
        <AiPanel lang={lang} calcName="BMI" score={result?.bmi ?? 0} riskLabel={result?.label ?? ""} />
        <div className="text-ink-3 text-xs"><span className="font-syne font-semibold">{t({ en: "Reference", ru: "Источник", ar: "المرجع", tr: "Kaynak", de: "Referenz", fr: "Référence", es: "Referencia" }, lang)}: </span>{t(L.ref, lang)}</div>
      </div>
    </div>
  );
}

// ── Corrected Calcium Calculator ──────────────────────────────────────────────

function CorrectedCalciumCalc({ lang }: { lang: string }) {
  const L: Record<string, Record<Lang, string>> = {
    calcium:   { en: "Total Calcium", ru: "Общий кальций", ar: "الكالسيوم الكلي", tr: "Total Kalsiyum", de: "Gesamtkalzium", fr: "Calcium total", es: "Calcio total" },
    albumin:   { en: "Serum Albumin", ru: "Сывороточный альбумин", ar: "ألبومين المصل", tr: "Serum Albumini", de: "Serumalbumin", fr: "Albumine sérique", es: "Albúmina sérica" },
    calc:      { en: "Calculate", ru: "Вычислить", ar: "احسب", tr: "Hesapla", de: "Berechnen", fr: "Calculer", es: "Calcular" },
    result:    { en: "Corrected Calcium", ru: "Скорр. кальций", ar: "الكالسيوم المصحح", tr: "Düzeltilmiş Kalsiyum", de: "Korrigiertes Kalzium", fr: "Calcium corrigé", es: "Calcio corregido" },
    ref:       { en: "Payne RB et al. BMJ 1973;4:643–644", ru: "Payne RB et al. BMJ 1973;4:643–644", ar: "Payne RB et al. BMJ 1973;4:643–644", tr: "Payne RB et al. BMJ 1973;4:643–644", de: "Payne RB et al. BMJ 1973;4:643–644", fr: "Payne RB et al. BMJ 1973;4:643–644", es: "Payne RB et al. BMJ 1973;4:643–644" },
  };
  const [calcium, setCalcium] = useState("");
  const [albumin, setAlbumin] = useState("");
  const [unit, setUnit] = useState<"mmol" | "mg">("mmol");
  const [result, setResult] = useState<null | { value: number; label: string; rec: string; color: "green" | "amber" | "red" }>(null);

  function getCalciumCategory(val: number, unitType: "mmol" | "mg"): { label: string; rec: string; color: "green" | "amber" | "red" } {
    const mmol = unitType === "mg" ? val / 4 : val;
    if (mmol < 2.1) return {
      label: lang === "ru" ? "Гипокальциемия" : "Hypocalcemia",
      rec: lang === "ru" ? "Исключить гипопаратиреоз, дефицит витамина D. Мониторинг ЭКГ. Коррекция кальция." : "Exclude hypoparathyroidism, vitamin D deficiency. ECG monitoring. Calcium supplementation.",
      color: "red",
    };
    if (mmol <= 2.6) return {
      label: lang === "ru" ? "Нормокальциемия" : "Normocalcemia",
      rec: lang === "ru" ? "Уровень кальция в норме с поправкой на гипоальбуминемию." : "Calcium level normal after correcting for hypoalbuminaemia.",
      color: "green",
    };
    return {
      label: lang === "ru" ? "Гиперкальциемия" : "Hypercalcemia",
      rec: lang === "ru" ? "Исключить первичный гиперпаратиреоз, злокачественные образования. Гидратация. Биофосфонаты." : "Exclude primary hyperparathyroidism, malignancy. Hydration. Consider bisphosphonates.",
      color: "red",
    };
  }

  function calculate() {
    const ca = parseFloat(calcium), alb = parseFloat(albumin);
    if (!ca || !alb || ca <= 0 || alb <= 0) return;
    const normalAlb = 4.0;
    let corrected: number;
    if (unit === "mg") {
      corrected = ca + 0.8 * (normalAlb - alb);
    } else {
      corrected = ca + 0.02 * (40 - alb * 10);
    }
    corrected = Math.round(corrected * 100) / 100;
    setResult({ value: corrected, ...getCalciumCategory(corrected, unit) });
  }

  const unitLabel = unit === "mmol" ? "mmol/L" : "mg/dL";
  const albUnit = unit === "mmol" ? "g/L" : "g/dL";

  return (
    <div className="grid lg:grid-cols-[1fr_360px] gap-6">
      <div className="space-y-4">
        <div className="space-y-1.5">
          <label className="font-syne font-semibold text-sm text-ink">{t(L.calcium, lang)}</label>
          <div className="flex gap-2">
            <input type="number" step="0.01" min="0" placeholder={unit === "mmol" ? "e.g. 2.1" : "e.g. 8.5"} value={calcium} onChange={e => setCalcium(e.target.value)}
              className="flex-1 border border-border rounded-lg px-3 py-2.5 text-sm font-syne bg-surface text-ink placeholder-ink-3 focus:outline-none focus:border-border-2" />
            <select value={unit} onChange={e => { setUnit(e.target.value as "mmol" | "mg"); setResult(null); }}
              className="border border-border rounded-lg px-3 py-2.5 text-sm font-syne bg-surface text-ink focus:outline-none focus:border-border-2">
              <option value="mmol">mmol/L</option>
              <option value="mg">mg/dL</option>
            </select>
          </div>
        </div>
        <NumInput label={`${t(L.albumin, lang)} (${albUnit})`} value={albumin} onChange={setAlbumin} placeholder={unit === "mmol" ? "e.g. 35" : "e.g. 3.5"} unit={albUnit} />
        <button onClick={calculate} className="w-full font-syne font-bold text-sm bg-ink text-white py-3 rounded-lg hover:bg-red transition-colors">{t(L.calc, lang)}</button>
      </div>
      <div className="space-y-4">
        <NumResult label={t(L.result, lang)} value={result ? String(result.value) : null} unit={unitLabel} description={result?.label} recommendation={result?.rec} color={result?.color ?? "green"} />
        <AiPanel lang={lang} calcName="Corrected Calcium" score={result?.value ?? 0} riskLabel={result?.label ?? ""} />
        <div className="text-ink-3 text-xs"><span className="font-syne font-semibold">{t({ en: "Reference", ru: "Источник", ar: "المرجع", tr: "Kaynak", de: "Referenz", fr: "Référence", es: "Referencia" }, lang)}: </span>{t(L.ref, lang)}</div>
      </div>
    </div>
  );
}

// ── Anion Gap Calculator ──────────────────────────────────────────────────────

function AnionGapCalc({ lang }: { lang: string }) {
  const L: Record<string, Record<Lang, string>> = {
    sodium:    { en: "Sodium (Na⁺)", ru: "Натрий (Na⁺)", ar: "الصوديوم (Na⁺)", tr: "Sodyum (Na⁺)", de: "Natrium (Na⁺)", fr: "Sodium (Na⁺)", es: "Sodio (Na⁺)" },
    chloride:  { en: "Chloride (Cl⁻)", ru: "Хлорид (Cl⁻)", ar: "الكلوريد (Cl⁻)", tr: "Klorür (Cl⁻)", de: "Chlorid (Cl⁻)", fr: "Chlorure (Cl⁻)", es: "Cloruro (Cl⁻)" },
    bicarb:    { en: "Bicarbonate (HCO₃⁻)", ru: "Бикарбонат (HCO₃⁻)", ar: "البيكربونات (HCO₃⁻)", tr: "Bikarbonat (HCO₃⁻)", de: "Bikarbonat (HCO₃⁻)", fr: "Bicarbonate (HCO₃⁻)", es: "Bicarbonato (HCO₃⁻)" },
    albumin:   { en: "Albumin (for correction)", ru: "Альбумин (для поправки)", ar: "ألبومين (للتصحيح)", tr: "Albumin (düzeltme için)", de: "Albumin (für Korrektur)", fr: "Albumine (pour correction)", es: "Albúmina (para corrección)" },
    calc:      { en: "Calculate Anion Gap", ru: "Вычислить анионный разрыв", ar: "احسب الفجوة الأيونية", tr: "Anyon Açığı Hesapla", de: "Anionenlücke berechnen", fr: "Calculer le trou anionique", es: "Calcular brecha aniónica" },
    result:    { en: "Anion Gap", ru: "Анионный разрыв", ar: "الفجوة الأيونية", tr: "Anyon Açığı", de: "Anionenlücke", fr: "Trou anionique", es: "Brecha aniónica" },
    corrected: { en: "Albumin-corrected AG", ru: "Скорр. анионный разрыв", ar: "الفجوة المصحح للألبومين", tr: "Albumin düzeltmeli AG", de: "Albumin-korrigierte AL", fr: "TA corrigé albumine", es: "BA corregido por albúmina" },
    ref:       { en: "Emmett M, Narins RG. Medicine 1977;56:38–54", ru: "Emmett M, Narins RG. Medicine 1977;56:38–54", ar: "Emmett M, Narins RG. Medicine 1977;56:38–54", tr: "Emmett M, Narins RG. Medicine 1977;56:38–54", de: "Emmett M, Narins RG. Medicine 1977;56:38–54", fr: "Emmett M, Narins RG. Medicine 1977;56:38–54", es: "Emmett M, Narins RG. Medicine 1977;56:38–54" },
  };
  const [na, setNa] = useState("");
  const [cl, setCl] = useState("");
  const [hco3, setHco3] = useState("");
  const [alb, setAlb] = useState("");
  const [result, setResult] = useState<null | { ag: number; agCorr: number | null; label: string; rec: string; color: "green" | "amber" | "red" }>(null);

  function getAgCategory(ag: number): { label: string; rec: string; color: "green" | "amber" | "red" } {
    if (ag <= 12) return {
      label: lang === "ru" ? "Нормальный анионный разрыв (≤12)" : "Normal anion gap (≤12)",
      rec: lang === "ru" ? "Нормальный АР. Рассмотреть неАР метаболический ацидоз (гиперхлоремический). Причины: диарея, RTA, введение хлоридов." : "Normal AG. Consider non-AG metabolic acidosis (hyperchloraemic). Causes: diarrhoea, RTA, chloride infusion.",
      color: "green",
    };
    return {
      label: lang === "ru" ? "Высокий анионный разрыв (>12)" : "Elevated anion gap (>12)",
      rec: lang === "ru" ? "Высокий АР. Причины: лактат-ацидоз, ДКА, уремия, интоксикации (MULEPAK). Дополнительное обследование." : "Elevated AG. Causes: lactic acidosis, DKA, uraemia, toxins (MULEPAK mnemonic). Further workup needed.",
      color: "red",
    };
  }

  function calculate() {
    const sodium = parseFloat(na), chloride = parseFloat(cl), bicarb = parseFloat(hco3);
    if (!sodium || !chloride || !bicarb) return;
    const ag = Math.round((sodium - chloride - bicarb) * 10) / 10;
    const albumin = parseFloat(alb);
    const agCorr = albumin > 0 ? Math.round((ag + 2.5 * (4.0 - albumin)) * 10) / 10 : null;
    const effectiveAg = agCorr ?? ag;
    setResult({ ag, agCorr, ...getAgCategory(effectiveAg) });
  }

  return (
    <div className="grid lg:grid-cols-[1fr_360px] gap-6">
      <div className="space-y-4">
        <NumInput label={t(L.sodium, lang)} value={na} onChange={setNa} placeholder="e.g. 140" unit="mEq/L" />
        <NumInput label={t(L.chloride, lang)} value={cl} onChange={setCl} placeholder="e.g. 104" unit="mEq/L" />
        <NumInput label={t(L.bicarb, lang)} value={hco3} onChange={setHco3} placeholder="e.g. 24" unit="mEq/L" />
        <NumInput label={`${t(L.albumin, lang)} (optional)`} value={alb} onChange={setAlb} placeholder="e.g. 4.0" unit="g/dL" />
        <button onClick={calculate} className="w-full font-syne font-bold text-sm bg-ink text-white py-3 rounded-lg hover:bg-red transition-colors">{t(L.calc, lang)}</button>
      </div>
      <div className="space-y-4">
        {result ? (
          <div className={`rounded-xl border p-5 space-y-3 ${RISK_COLORS[result.color].bg} ${RISK_COLORS[result.color].border}`}>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-ink-3 text-xs font-syne uppercase tracking-widest mb-1">{t(L.result, lang)}</p>
                <p className={`font-syne font-extrabold text-3xl ${RISK_COLORS[result.color].text}`}>{result.ag}</p>
                <p className="text-ink-3 text-xs">mEq/L</p>
              </div>
              {result.agCorr !== null && (
                <div>
                  <p className="text-ink-3 text-xs font-syne uppercase tracking-widest mb-1">{t(L.corrected, lang)}</p>
                  <p className={`font-syne font-extrabold text-3xl ${RISK_COLORS[result.color].text}`}>{result.agCorr}</p>
                  <p className="text-ink-3 text-xs">mEq/L</p>
                </div>
              )}
            </div>
            <p className={`text-sm font-medium ${RISK_COLORS[result.color].text}`}>{result.label}</p>
            <div className="border-t border-current/20 pt-3">
              <p className="text-xs font-syne uppercase tracking-widest text-ink-3 mb-1">{t(UI.recommendation, lang)}</p>
              <p className="text-sm text-ink leading-relaxed">{result.rec}</p>
            </div>
          </div>
        ) : (
          <div className="rounded-xl border border-border bg-surface p-8 flex items-center justify-center min-h-[160px]">
            <p className="text-ink-3 text-sm font-syne text-center">{lang === "ru" ? "Введите данные" : "Enter values above"}</p>
          </div>
        )}
        <AiPanel lang={lang} calcName="Anion Gap" score={result?.ag ?? 0} riskLabel={result?.label ?? ""} />
        <div className="text-ink-3 text-xs"><span className="font-syne font-semibold">{t({ en: "Reference", ru: "Источник", ar: "المرجع", tr: "Kaynak", de: "Referenz", fr: "Référence", es: "Referencia" }, lang)}: </span>{t(L.ref, lang)}</div>
      </div>
    </div>
  );
}

// ── MELD Score Calculator ─────────────────────────────────────────────────────

function MeldCalc({ lang }: { lang: string }) {
  const L: Record<string, Record<Lang, string>> = {
    inr:     { en: "INR", ru: "МНО", ar: "النسبة الدولية المعيارية", tr: "INR", de: "INR", fr: "INR", es: "INR" },
    bili:    { en: "Total Bilirubin", ru: "Общий билирубин", ar: "البيليروبين الكلي", tr: "Total Bilirubin", de: "Gesamtbilirubin", fr: "Bilirubine totale", es: "Bilirrubina total" },
    creat:   { en: "Creatinine", ru: "Креатинин", ar: "الكرياتينين", tr: "Kreatinin", de: "Kreatinin", fr: "Créatinine", es: "Creatinina" },
    sodium:  { en: "Sodium (for MELD-Na)", ru: "Натрий (для MELD-Na)", ar: "الصوديوم (لـ MELD-Na)", tr: "Sodyum (MELD-Na için)", de: "Natrium (für MELD-Na)", fr: "Sodium (pour MELD-Na)", es: "Sodio (para MELD-Na)" },
    calc:    { en: "Calculate MELD", ru: "Вычислить MELD", ar: "احسب MELD", tr: "MELD hesapla", de: "MELD berechnen", fr: "Calculer MELD", es: "Calcular MELD" },
    result:  { en: "MELD Score", ru: "Шкала MELD", ar: "نتيجة MELD", tr: "MELD Skoru", de: "MELD-Score", fr: "Score MELD", es: "Puntuación MELD" },
    meldna:  { en: "MELD-Na Score", ru: "Шкала MELD-Na", ar: "نتيجة MELD-Na", tr: "MELD-Na Skoru", de: "MELD-Na-Score", fr: "Score MELD-Na", es: "Puntuación MELD-Na" },
    ref:     { en: "Kamath PS et al. Hepatology 2001;33:464–470 · UNOS MELD-Na policy", ru: "Kamath PS et al. Hepatology 2001;33:464–470 · UNOS MELD-Na", ar: "Kamath PS et al. Hepatology 2001;33:464–470 · سياسة UNOS MELD-Na", tr: "Kamath PS et al. Hepatology 2001;33:464–470 · UNOS MELD-Na", de: "Kamath PS et al. Hepatology 2001;33:464–470 · UNOS MELD-Na", fr: "Kamath PS et al. Hepatology 2001;33:464–470 · UNOS MELD-Na", es: "Kamath PS et al. Hepatology 2001;33:464–470 · UNOS MELD-Na" },
  };
  const [inr, setInr] = useState("");
  const [bili, setBili] = useState("");
  const [creat, setCreat] = useState("");
  const [sodium, setSodium] = useState("");
  const [result, setResult] = useState<null | { meld: number; meldNa: number | null; label: string; mortality: string; color: "green" | "amber" | "red" }>(null);

  function getMeldCategory(meld: number): { label: string; mortality: string; color: "green" | "amber" | "red" } {
    if (meld < 10) return { label: lang === "ru" ? "Лёгкая степень" : "Mild", mortality: lang === "ru" ? "90-дневная летальность <5%. Плановое наблюдение." : "90-day mortality <5%. Routine follow-up.", color: "green" };
    if (meld < 20) return { label: lang === "ru" ? "Средняя степень" : "Moderate", mortality: lang === "ru" ? "90-дневная летальность ~20%. Наблюдение каждые 3 мес." : "90-day mortality ~20%. Follow-up every 3 months.", color: "amber" };
    if (meld < 30) return { label: lang === "ru" ? "Тяжёлая степень" : "Severe", mortality: lang === "ru" ? "90-дневная летальность ~40–50%. Приоритет трансплантации." : "90-day mortality ~40–50%. High priority for transplantation.", color: "red" };
    return { label: lang === "ru" ? "Критическая степень" : "Critical", mortality: lang === "ru" ? "90-дневная летальность >70%. Экстренная оценка трансплантации." : "90-day mortality >70%. Urgent transplantation evaluation.", color: "red" };
  }

  function calculate() {
    const i = Math.max(parseFloat(inr), 1.0);
    const b = Math.max(parseFloat(bili), 1.0);
    const c = Math.min(Math.max(parseFloat(creat), 1.0), 4.0);
    if (!i || !b || !c) return;
    const meld = Math.round(3.78 * Math.log(b) + 11.2 * Math.log(i) + 9.57 * Math.log(c) + 6.43);
    const na = parseFloat(sodium);
    let meldNa: number | null = null;
    if (na > 0) {
      const clampedNa = Math.min(Math.max(na, 125), 137);
      meldNa = Math.round(meld + 1.32 * (137 - clampedNa) - 0.033 * meld * (137 - clampedNa));
    }
    setResult({ meld, meldNa, ...getMeldCategory(meldNa ?? meld) });
  }

  return (
    <div className="grid lg:grid-cols-[1fr_360px] gap-6">
      <div className="space-y-4">
        <NumInput label={t(L.inr, lang)} value={inr} onChange={setInr} placeholder="e.g. 1.5" step="0.01" />
        <NumInput label={`${t(L.bili, lang)} (mg/dL)`} value={bili} onChange={setBili} placeholder="e.g. 2.0" step="0.01" unit="mg/dL" />
        <NumInput label={`${t(L.creat, lang)} (mg/dL)`} value={creat} onChange={setCreat} placeholder="e.g. 1.2" step="0.01" unit="mg/dL" />
        <NumInput label={`${t(L.sodium, lang)} (optional)`} value={sodium} onChange={setSodium} placeholder="e.g. 135" unit="mEq/L" />
        <button onClick={calculate} className="w-full font-syne font-bold text-sm bg-ink text-white py-3 rounded-lg hover:bg-red transition-colors">{t(L.calc, lang)}</button>
      </div>
      <div className="space-y-4">
        {result ? (
          <div className={`rounded-xl border p-5 space-y-3 ${RISK_COLORS[result.color].bg} ${RISK_COLORS[result.color].border}`}>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-ink-3 text-xs font-syne uppercase tracking-widest mb-1">{t(L.result, lang)}</p>
                <p className={`font-syne font-extrabold text-3xl ${RISK_COLORS[result.color].text}`}>{result.meld}</p>
              </div>
              {result.meldNa !== null && (
                <div>
                  <p className="text-ink-3 text-xs font-syne uppercase tracking-widest mb-1">{t(L.meldna, lang)}</p>
                  <p className={`font-syne font-extrabold text-3xl ${RISK_COLORS[result.color].text}`}>{result.meldNa}</p>
                </div>
              )}
            </div>
            <span className={`inline-block font-syne font-bold text-sm px-3 py-1 rounded-full ${RISK_COLORS[result.color].badge}`}>{result.label}</span>
            <p className="text-sm text-ink leading-relaxed">{result.mortality}</p>
          </div>
        ) : (
          <div className="rounded-xl border border-border bg-surface p-8 flex items-center justify-center min-h-[160px]">
            <p className="text-ink-3 text-sm font-syne text-center">{lang === "ru" ? "Введите данные" : "Enter values above"}</p>
          </div>
        )}
        <AiPanel lang={lang} calcName="MELD Score" score={result?.meld ?? 0} riskLabel={result?.label ?? ""} />
        <div className="text-ink-3 text-xs"><span className="font-syne font-semibold">{t({ en: "Reference", ru: "Источник", ar: "المرجع", tr: "Kaynak", de: "Referenz", fr: "Référence", es: "Referencia" }, lang)}: </span>{t(L.ref, lang)}</div>
      </div>
    </div>
  );
}

// ── Cockcroft-Gault Calculator ────────────────────────────────────────────────

function CockcroftGaultCalc({ lang }: { lang: string }) {
  const L: Record<string, Record<Lang, string>> = {
    age:     { en: "Age", ru: "Возраст", ar: "العمر", tr: "Yaş", de: "Alter", fr: "Âge", es: "Edad" },
    weight:  { en: "Weight (actual body weight)", ru: "Масса тела (фактическая)", ar: "الوزن (الوزن الفعلي)", tr: "Ağırlık (gerçek vücut ağırlığı)", de: "Gewicht (tatsächlich)", fr: "Poids (poids corporel réel)", es: "Peso (peso corporal real)" },
    creat:   { en: "Serum Creatinine", ru: "Сывороточный креатинин", ar: "كرياتينين المصل", tr: "Serum Kreatinini", de: "Serumkreatinin", fr: "Créatinine sérique", es: "Creatinina sérica" },
    sex:     { en: "Sex", ru: "Пол", ar: "الجنس", tr: "Cinsiyet", de: "Geschlecht", fr: "Sexe", es: "Sexo" },
    calc:    { en: "Calculate CrCl", ru: "Вычислить КлКр", ar: "احسب تصفية الكرياتينين", tr: "CrCl Hesapla", de: "KrCl berechnen", fr: "Calculer la ClCr", es: "Calcular ClCr" },
    result:  { en: "Creatinine Clearance", ru: "Клиренс креатинина", ar: "تصفية الكرياتينين", tr: "Kreatinin Klerensi", de: "Kreatinin-Clearance", fr: "Clairance de la créatinine", es: "Aclaramiento de creatinina" },
    ref:     { en: "Cockcroft DW & Gault MH. Nephron 1976;16:31–41", ru: "Cockcroft DW & Gault MH. Nephron 1976;16:31–41", ar: "Cockcroft DW & Gault MH. Nephron 1976;16:31–41", tr: "Cockcroft DW & Gault MH. Nephron 1976;16:31–41", de: "Cockcroft DW & Gault MH. Nephron 1976;16:31–41", fr: "Cockcroft DW & Gault MH. Nephron 1976;16:31–41", es: "Cockcroft DW & Gault MH. Nephron 1976;16:31–41" },
  };
  const [age, setAge] = useState("");
  const [weight, setWeight] = useState("");
  const [creat, setCreat] = useState("");
  const [sex, setSex] = useState<"male" | "female">("male");
  const [unit, setUnit] = useState<"mg" | "umol">("mg");
  const [result, setResult] = useState<null | { crcl: number; label: string; rec: string; color: "green" | "amber" | "red" }>(null);

  function getCategory(crcl: number): { label: string; rec: string; color: "green" | "amber" | "red" } {
    if (crcl >= 90) return {
      label: lang === "ru" ? "Нормальная функция почек (≥90)" : "Normal kidney function (≥90)",
      rec: lang === "ru" ? "Стандартные дозы препаратов. Мониторинг при применении нефротоксинов." : "Standard drug dosing. Monitor if using nephrotoxic agents.",
      color: "green",
    };
    if (crcl >= 60) return {
      label: lang === "ru" ? "Лёгкое снижение (60–89)" : "Mild reduction (60–89)",
      rec: lang === "ru" ? "Большинство препаратов — стандартные дозы. Осторожность с НПВП, метформином." : "Most drugs at standard doses. Caution with NSAIDs, metformin.",
      color: "green",
    };
    if (crcl >= 30) return {
      label: lang === "ru" ? "Умеренное снижение (30–59)" : "Moderate reduction (30–59)",
      rec: lang === "ru" ? "Коррекция доз многих препаратов. Избегать НПВП. Осторожность с метформином (<45)." : "Dose adjustment required for many drugs. Avoid NSAIDs. Caution with metformin (<45).",
      color: "amber",
    };
    if (crcl >= 15) return {
      label: lang === "ru" ? "Тяжёлое снижение (15–29)" : "Severe reduction (15–29)",
      rec: lang === "ru" ? "Значительная коррекция доз. Консультация нефролога. Отмена метформина." : "Significant dose adjustments. Nephrology consultation. Discontinue metformin.",
      color: "red",
    };
    return {
      label: lang === "ru" ? "Почечная недостаточность (<15)" : "Kidney failure (<15)",
      rec: lang === "ru" ? "Диализная дозировка или отмена ренально выводимых препаратов. Диализ или трансплантация." : "Dialysis dosing or discontinuation of renally cleared drugs. Dialysis or transplantation.",
      color: "red",
    };
  }

  function calculate() {
    const a = parseFloat(age), w = parseFloat(weight), cr = parseFloat(creat);
    if (!a || !w || !cr || a <= 0 || w <= 0 || cr <= 0) return;
    const crMgdl = unit === "umol" ? cr / 88.42 : cr;
    let crcl = ((140 - a) * w) / (72 * crMgdl);
    if (sex === "female") crcl *= 0.85;
    crcl = Math.round(crcl * 10) / 10;
    setResult({ crcl, ...getCategory(crcl) });
  }

  return (
    <div className="grid lg:grid-cols-[1fr_360px] gap-6">
      <div className="space-y-4">
        <NumInput label={t(L.age, lang)} value={age} onChange={setAge} placeholder="e.g. 65" unit={lang === "ru" ? "лет" : "years"} />
        <NumInput label={t(L.weight, lang)} value={weight} onChange={setWeight} placeholder="e.g. 70" unit="kg" />
        <div className="space-y-1.5">
          <label className="font-syne font-semibold text-sm text-ink">{t(L.creat, lang)}</label>
          <div className="flex gap-2">
            <input type="number" step="0.01" min="0" placeholder={unit === "mg" ? "e.g. 1.2" : "e.g. 106"} value={creat} onChange={e => setCreat(e.target.value)}
              className="flex-1 border border-border rounded-lg px-3 py-2.5 text-sm font-syne bg-surface text-ink placeholder-ink-3 focus:outline-none focus:border-border-2" />
            <select value={unit} onChange={e => { setUnit(e.target.value as "mg" | "umol"); setResult(null); }}
              className="border border-border rounded-lg px-3 py-2.5 text-sm font-syne bg-surface text-ink focus:outline-none focus:border-border-2">
              <option value="mg">mg/dL</option>
              <option value="umol">μmol/L</option>
            </select>
          </div>
        </div>
        <div className="space-y-1.5">
          <label className="font-syne font-semibold text-sm text-ink">{t(L.sex, lang)}</label>
          <div className="flex gap-2">
            {(["male", "female"] as const).map(s => (
              <button key={s} onClick={() => setSex(s)}
                className={`flex-1 font-syne font-semibold text-sm py-2.5 rounded-lg border transition-colors ${sex === s ? "bg-ink text-white border-ink" : "bg-surface text-ink-2 border-border hover:border-border-2"}`}>
                {t(UI[s], lang)}
              </button>
            ))}
          </div>
        </div>
        <button onClick={calculate} className="w-full font-syne font-bold text-sm bg-ink text-white py-3 rounded-lg hover:bg-red transition-colors">{t(L.calc, lang)}</button>
      </div>
      <div className="space-y-4">
        <NumResult label={t(L.result, lang)} value={result ? String(result.crcl) : null} unit="mL/min" description={result?.label} recommendation={result?.rec} color={result?.color ?? "green"} />
        <AiPanel lang={lang} calcName="Cockcroft-Gault" score={result?.crcl ?? 0} riskLabel={result?.label ?? ""} />
        <div className="text-ink-3 text-xs"><span className="font-syne font-semibold">{t({ en: "Reference", ru: "Источник", ar: "المرجع", tr: "Kaynak", de: "Referenz", fr: "Référence", es: "Referencia" }, lang)}: </span>{t(L.ref, lang)}</div>
      </div>
    </div>
  );
}

// ── AKI Staging Calculator (KDIGO 2012) ──────────────────────────────────────

function AkiCalc({ lang }: { lang: string }) {
  const L: Record<string, Record<Lang, string>> = {
    baseline_cr:  { en: "Baseline Creatinine", ru: "Базовый креатинин", ar: "الكرياتينين الأساسي", tr: "Bazal Kreatinin", de: "Ausgangskreatinin", fr: "Créatinine de base", es: "Creatinina basal" },
    current_cr:   { en: "Current Creatinine", ru: "Текущий креатинин", ar: "الكرياتينين الحالي", tr: "Mevcut Kreatinin", de: "Aktuelles Kreatinin", fr: "Créatinine actuelle", es: "Creatinina actual" },
    uo:           { en: "Urine Output (optional)", ru: "Диурез (необязательно)", ar: "إنتاج البول (اختياري)", tr: "İdrar Çıkışı (isteğe bağlı)", de: "Urinausscheidung (optional)", fr: "Diurèse (optionnel)", es: "Diuresis (opcional)" },
    uo_duration:  { en: "Duration of low UO", ru: "Длительность олигурии", ar: "مدة انخفاض البول", tr: "Düşük idrar çıkışı süresi", de: "Dauer der Oligurie", fr: "Durée de la faible diurèse", es: "Duración de oliguria" },
    weight:       { en: "Patient weight (for UO/kg)", ru: "Масса пациента (для диуреза/кг)", ar: "وزن المريض (لإنتاج البول/كغ)", tr: "Hasta ağırlığı (idrar çıkışı/kg için)", de: "Patientengewicht (für UO/kg)", fr: "Poids patient (pour diurèse/kg)", es: "Peso paciente (para diuresis/kg)" },
    calc:         { en: "Stage AKI", ru: "Определить стадию ОПП", ar: "تحديد مرحلة الإصابة الكلوية", tr: "AKI Evresini Belirle", de: "AKI-Stufe bestimmen", fr: "Stadifier l'IRA", es: "Estadificar IRA" },
    ref:          { en: "KDIGO AKI Guidelines 2012 · Kidney International Supplements 2012;2:1–138", ru: "KDIGO AKI Guidelines 2012 · Kidney International Supplements 2012;2:1–138", ar: "إرشادات KDIGO للإصابة الكلوية الحادة 2012", tr: "KDIGO AKI Kılavuzları 2012 · Kidney International Supplements 2012;2:1–138", de: "KDIGO AKI-Leitlinien 2012 · Kidney International Supplements 2012;2:1–138", fr: "Recommandations KDIGO IRA 2012 · Kidney International Supplements 2012;2:1–138", es: "Guías KDIGO IRA 2012 · Kidney International Supplements 2012;2:1–138" },
    no_aki:       { en: "No AKI criteria met", ru: "Критерии ОПП не выполнены", ar: "لا تتحقق معايير الإصابة الكلوية الحادة", tr: "AKI kriterleri karşılanmadı", de: "Keine AKI-Kriterien erfüllt", fr: "Aucun critère d'IRA atteint", es: "No se cumplen criterios de IRA" },
    cr_criterion: { en: "Creatinine criterion", ru: "Критерий по креатинину", ar: "معيار الكرياتينين", tr: "Kreatinin kriteri", de: "Kreatinin-Kriterium", fr: "Critère créatinine", es: "Criterio creatinina" },
    uo_criterion: { en: "Urine output criterion", ru: "Критерий по диурезу", ar: "معيار إنتاج البول", tr: "İdrar çıkışı kriteri", de: "Diurese-Kriterium", fr: "Critère diurèse", es: "Criterio diuresis" },
    highest_stage:{ en: "Final stage (highest criterion)", ru: "Итоговая стадия (наивысший критерий)", ar: "المرحلة النهائية (أعلى معيار)", tr: "Son evre (en yüksek kriter)", de: "Endstadium (höchstes Kriterium)", fr: "Stade final (critère le plus élevé)", es: "Estadio final (criterio más alto)" },
  };

  const [baseCr, setBaseCr] = useState("");
  const [currCr, setCurrCr] = useState("");
  const [unit, setUnit] = useState<"mg" | "umol">("mg");
  const [uo, setUo] = useState("");
  const [uoDuration, setUoDuration] = useState("");
  const [weight, setWeight] = useState("");
  const [result, setResult] = useState<null | {
    crStage: number; uoStage: number; finalStage: number;
    ratio: number; absDiff: number;
    uoPerKg: number | null;
  }>(null);

  const STAGE_INFO: Record<number, { label: Record<Lang, string>; rec: Record<Lang, string>; color: "green" | "amber" | "red" }> = {
    0: {
      label: { en: "No AKI", ru: "ОПП отсутствует", ar: "لا توجد إصابة كلوية حادة", tr: "AKI yok", de: "Kein AKI", fr: "Pas d'IRA", es: "Sin IRA" },
      rec: { en: "No AKI criteria met. Monitor renal function if clinically at risk.", ru: "Критерии ОПП не выполнены. Мониторинг функции почек при наличии факторов риска.", ar: "لا تتحقق معايير الإصابة الكلوية الحادة. راقب وظائف الكلى إذا كان هناك خطر سريري.", tr: "AKI kriterleri karşılanmadı. Klinik risk varsa böbrek fonksiyonunu izleyin.", de: "Keine AKI-Kriterien erfüllt. Nierenfunktion bei klinischem Risiko überwachen.", fr: "Aucun critère d'IRA atteint. Surveiller la fonction rénale si risque clinique.", es: "No se cumplen criterios de IRA. Monitorizar función renal si hay riesgo clínico." },
      color: "green",
    },
    1: {
      label: { en: "AKI Stage 1", ru: "ОПП 1 стадия", ar: "إصابة كلوية حادة المرحلة 1", tr: "AKI Evre 1", de: "AKI Stadium 1", fr: "IRA Stade 1", es: "IRA Estadio 1" },
      rec: { en: "Stage 1 AKI: Identify and remove precipitants (nephrotoxins, hypovolaemia). Optimise haemodynamics. Avoid contrast. Monitor creatinine q6–12h and urine output.", ru: "ОПП 1 ст.: Выявить и устранить причины (нефротоксины, гиповолемия). Гемодинамическая оптимизация. Отмена НПВП, ИАПФ/БРА. Мониторинг креатинина каждые 6–12 ч и диуреза.", ar: "IRA المرحلة 1: تحديد الأسباب وإزالتها (مواد سُمية للكلى، نقص حجم الدم). تحسين الديناميكا الدموية. تجنب التباين. مراقبة الكرياتينين كل 6–12 ساعة.", tr: "AKI Evre 1: Presipitan faktörleri tanımlayın ve kaldırın (nefrotoksinler, hipovolemi). Hemodinamiyi optimize edin. Kontrasttan kaçının. Kreatinini q6-12h izleyin.", de: "AKI Stadium 1: Auslöser identifizieren und entfernen (Nephrotoxine, Hypovolämie). Hämodynamik optimieren. Kontrastmittel vermeiden. Kreatinin q6–12h und Diurese überwachen.", fr: "IRA Stade 1 : Identifier et supprimer les facteurs précipitants (néphrotoxiques, hypovolémie). Optimiser l'hémodynamique. Éviter le contraste. Surveiller créatinine q6–12h et diurèse.", es: "IRA Estadio 1: Identificar y eliminar precipitantes (nefrotóxicos, hipovolemia). Optimizar hemodinámica. Evitar contraste. Monitorizar creatinina q6-12h y diuresis." },
      color: "amber",
    },
    2: {
      label: { en: "AKI Stage 2", ru: "ОПП 2 стадия", ar: "إصابة كلوية حادة المرحلة 2", tr: "AKI Evre 2", de: "AKI Stadium 2", fr: "IRA Stade 2", es: "IRA Estadio 2" },
      rec: { en: "Stage 2 AKI: Nephrology consult. Strict fluid balance. Stop all nephrotoxic agents (NSAIDs, ACEi/ARB, aminoglycosides, contrast). Adjust drug doses. Consider renal replacement therapy indications.", ru: "ОПП 2 ст.: Консультация нефролога. Строгий контроль баланса жидкости. Отмена всех нефротоксинов (НПВП, ИАПФ/БРА, аминогликозиды, контраст). Коррекция доз. Оценка показаний к ЗПТ.", ar: "IRA المرحلة 2: استشارة طب الكلى. موازنة صارمة للسوائل. إيقاف جميع العوامل السامة للكلى. تعديل جرعات الأدوية. النظر في العلاج ببديل الكلى.", tr: "AKI Evre 2: Nefroloji konsültasyonu. Sıkı sıvı dengesi. Tüm nefrotoksik ajanları kesin. İlaç dozlarını ayarlayın. Renal replasman tedavisini değerlendirin.", de: "AKI Stadium 2: Nephrologische Konsultation. Strenge Flüssigkeitsbilanz. Alle nephrotoxischen Substanzen absetzen. Dosisanpassung. Nierenersatztherapie-Indikationen prüfen.", fr: "IRA Stade 2 : Consultation néphrologie. Bilan hydrique strict. Arrêter tous les néphrotoxiques. Adapter les doses médicamenteuses. Évaluer les indications de EER.", es: "IRA Estadio 2: Consulta nefrología. Balance hídrico estricto. Suspender todos los nefrotóxicos. Ajustar dosis. Evaluar indicaciones de terapia renal sustitutiva." },
      color: "red",
    },
    3: {
      label: { en: "AKI Stage 3", ru: "ОПП 3 стадия", ar: "إصابة كلوية حادة المرحلة 3", tr: "AKI Evre 3", de: "AKI Stadium 3", fr: "IRA Stade 3", es: "IRA Estadio 3" },
      rec: { en: "Stage 3 AKI (severe): Urgent nephrology input. Consider immediate RRT if: refractory fluid overload, hyperkalaemia >6.5 mEq/L, metabolic acidosis pH <7.1, uraemic symptoms. ICU-level monitoring.", ru: "ОПП 3 ст. (тяжёлое): Экстренная консультация нефролога. Рассмотреть срочную ЗПТ при: рефрактерной перегрузке жидкостью, гиперкалиемии >6,5 мэкв/л, метаболическом ацидозе pH <7,1, уремических симптомах. Мониторинг в ОРИТ.", ar: "IRA المرحلة 3 (شديد): استشارة عاجلة لطب الكلى. فكر في العلاج الفوري ببديل الكلى في حالات: الحمل الزائد للسوائل، فرط بوتاسيوم الدم >6.5 ملي مكافئ/لتر، الحماض الأيضي pH <7.1، أعراض اليوريميا.", tr: "AKI Evre 3 (şiddetli): Acil nefroloji konsültasyonu. Refraktör sıvı yüklenmesi, hiperkalaemi >6.5 mEq/L, metabolik asidoz pH <7.1, üremik semptomlar varsa acil RRT düşünün. YBÜ düzeyinde izleme.", de: "AKI Stadium 3 (schwer): Dringende nephrologische Beurteilung. Sofortige Nierenersatztherapie erwägen bei: refraktärer Flüssigkeitsüberladung, Hyperkaliämie >6,5 mEq/L, metabolischer Azidose pH <7,1, urämischen Symptomen. Intensivüberwachung.", fr: "IRA Stade 3 (sévère) : Avis néphrologue urgent. Envisager EER immédiate si : surcharge hydrique réfractaire, hyperkaliémie >6,5 mEq/L, acidose métabolique pH <7,1, symptômes urémiques. Surveillance niveau réanimation.", es: "IRA Estadio 3 (grave): Consulta urgente nefrología. Considerar TRS inmediata si: sobrecarga hídrica refractaria, hiperpotasemia >6.5 mEq/L, acidosis metabólica pH <7.1, síntomas urémicos. Monitorización nivel UCI." },
      color: "red",
    },
  };

  function getStageCr(baseline: number, current: number): number {
    const ratio = current / baseline;
    const diff = current - baseline;
    if (ratio >= 3.0 || current >= 4.0) return 3;
    if (ratio >= 2.0) return 2;
    if (ratio >= 1.5 || diff >= 0.3) return 1;
    return 0;
  }

  function getStageUo(uoPerKg: number, hours: number): number {
    if (uoPerKg < 0.3 && hours >= 24) return 3;
    if (uoPerKg < 0.5 && hours >= 12) return 2;
    if (uoPerKg < 0.5 && hours >= 6) return 1;
    return 0;
  }

  function calculate() {
    const base = parseFloat(baseCr), curr = parseFloat(currCr);
    if (!base || !curr || base <= 0 || curr <= 0) return;

    const baseConv = unit === "umol" ? base / 88.42 : base;
    const currConv = unit === "umol" ? curr / 88.42 : curr;

    const crStage = getStageCr(baseConv, currConv);
    const ratio = Math.round((currConv / baseConv) * 100) / 100;
    const absDiff = Math.round((currConv - baseConv) * 100) / 100;

    let uoStage = 0;
    let uoPerKg: number | null = null;
    const uoVal = parseFloat(uo), wt = parseFloat(weight), hrs = parseFloat(uoDuration);
    if (uoVal > 0 && wt > 0 && hrs > 0) {
      uoPerKg = Math.round((uoVal / wt / hrs) * 1000) / 1000;
      uoStage = getStageUo(uoPerKg, hrs);
    }

    const finalStage = Math.max(crStage, uoStage);
    setResult({ crStage, uoStage, finalStage, ratio, absDiff, uoPerKg });
  }

  const stageColors: Record<number, "green" | "amber" | "red"> = { 0: "green", 1: "amber", 2: "red", 3: "red" };
  const stageBadge: Record<number, string> = { 0: "—", 1: "1", 2: "2", 3: "3" };

  return (
    <div className="grid lg:grid-cols-[1fr_380px] gap-6">
      {/* Inputs */}
      <div className="space-y-5">
        {/* Creatinine section */}
        <div className="bg-surface border border-border rounded-xl p-4 space-y-4">
          <div className="flex items-center justify-between">
            <p className="font-syne font-bold text-sm text-ink">
              {lang === "ru" ? "Критерий 1 — Креатинин" : lang === "ar" ? "المعيار 1 — الكرياتينين" : lang === "de" ? "Kriterium 1 — Kreatinin" : lang === "fr" ? "Critère 1 — Créatinine" : lang === "es" ? "Criterio 1 — Creatinina" : lang === "tr" ? "Kriter 1 — Kreatinin" : "Criterion 1 — Creatinine"}
            </p>
            <select value={unit} onChange={e => { setUnit(e.target.value as "mg" | "umol"); setResult(null); }}
              className="text-xs font-syne border border-border rounded px-2 py-1 bg-bg text-ink focus:outline-none">
              <option value="mg">mg/dL</option>
              <option value="umol">μmol/L</option>
            </select>
          </div>
          <div className="grid sm:grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="font-syne font-semibold text-sm text-ink">{t(L.baseline_cr, lang)}</label>
              <input type="number" step="0.01" min="0" placeholder={unit === "mg" ? "e.g. 0.9" : "e.g. 80"}
                value={baseCr} onChange={e => setBaseCr(e.target.value)}
                className="w-full border border-border rounded-lg px-3 py-2.5 text-sm font-syne bg-surface text-ink placeholder-ink-3 focus:outline-none focus:border-border-2" />
            </div>
            <div className="space-y-1.5">
              <label className="font-syne font-semibold text-sm text-ink">{t(L.current_cr, lang)}</label>
              <input type="number" step="0.01" min="0" placeholder={unit === "mg" ? "e.g. 1.8" : "e.g. 159"}
                value={currCr} onChange={e => setCurrCr(e.target.value)}
                className="w-full border border-border rounded-lg px-3 py-2.5 text-sm font-syne bg-surface text-ink placeholder-ink-3 focus:outline-none focus:border-border-2" />
            </div>
          </div>
          <p className="text-ink-3 text-xs leading-relaxed">
            {lang === "ru" ? "Базовый — исходный или минимальный за последние 7 дней. При недоступности — используйте обратный расчёт по eGFR=75." : lang === "ar" ? "الأساسي = الكرياتينين في الحالة الطبيعية أو أدنى قيمة خلال 7 أيام." : lang === "de" ? "Ausgangskreatinin = Normalwert oder niedrigster Wert innerhalb von 7 Tagen." : lang === "fr" ? "Baseline = créatinine habituelle ou valeur la plus basse dans les 7 jours." : lang === "es" ? "Basal = creatinina habitual o valor mínimo en los últimos 7 días." : lang === "tr" ? "Bazal = son 7 günde minimum veya olağan değer." : "Baseline = usual or lowest value within 7 days. If unknown, back-calculate assuming eGFR=75."}
          </p>
        </div>

        {/* Urine output section */}
        <div className="bg-surface border border-border rounded-xl p-4 space-y-4">
          <p className="font-syne font-bold text-sm text-ink">
            {lang === "ru" ? "Критерий 2 — Диурез (необязательно)" : lang === "ar" ? "المعيار 2 — إنتاج البول (اختياري)" : lang === "de" ? "Kriterium 2 — Urinausscheidung (optional)" : lang === "fr" ? "Critère 2 — Diurèse (optionnel)" : lang === "es" ? "Criterio 2 — Diuresis (opcional)" : lang === "tr" ? "Kriter 2 — İdrar Çıkışı (isteğe bağlı)" : "Criterion 2 — Urine Output (optional)"}
          </p>
          <div className="grid sm:grid-cols-3 gap-3">
            <div className="space-y-1.5">
              <label className="font-syne font-semibold text-sm text-ink">{lang === "ru" ? "Диурез (мл)" : lang === "ar" ? "البول (مل)" : lang === "de" ? "Urin (ml)" : lang === "fr" ? "Diurèse (ml)" : lang === "es" ? "Diuresis (ml)" : lang === "tr" ? "İdrar (ml)" : "Total UO (mL)"}</label>
              <input type="number" min="0" placeholder="e.g. 480" value={uo} onChange={e => setUo(e.target.value)}
                className="w-full border border-border rounded-lg px-3 py-2.5 text-sm font-syne bg-surface text-ink placeholder-ink-3 focus:outline-none focus:border-border-2" />
            </div>
            <div className="space-y-1.5">
              <label className="font-syne font-semibold text-sm text-ink">{t(L.uo_duration, lang)} (h)</label>
              <input type="number" min="0" max="72" placeholder="e.g. 8" value={uoDuration} onChange={e => setUoDuration(e.target.value)}
                className="w-full border border-border rounded-lg px-3 py-2.5 text-sm font-syne bg-surface text-ink placeholder-ink-3 focus:outline-none focus:border-border-2" />
            </div>
            <div className="space-y-1.5">
              <label className="font-syne font-semibold text-sm text-ink">{t(L.weight, lang)} (kg)</label>
              <input type="number" min="0" placeholder="e.g. 70" value={weight} onChange={e => setWeight(e.target.value)}
                className="w-full border border-border rounded-lg px-3 py-2.5 text-sm font-syne bg-surface text-ink placeholder-ink-3 focus:outline-none focus:border-border-2" />
            </div>
          </div>
          <p className="text-ink-3 text-xs">
            {lang === "ru" ? "Порог олигурии: <0,5 мл/кг/ч ≥6 ч (ст. 1), ≥12 ч (ст. 2); <0,3 мл/кг/ч ≥24 ч или анурия ≥12 ч (ст. 3)" : lang === "ar" ? "عتبة قلة البول: <0.5 مل/كغ/ساعة ≥6 ساعات (مرحلة 1)، ≥12 ساعة (مرحلة 2)؛ <0.3 مل/كغ/ساعة ≥24 ساعة أو انقطاع البول ≥12 ساعة (مرحلة 3)" : lang === "de" ? "Oligurie-Schwelle: <0,5 ml/kg/h ≥6 h (St. 1), ≥12 h (St. 2); <0,3 ml/kg/h ≥24 h oder Anurie ≥12 h (St. 3)" : lang === "fr" ? "Seuil d'oligurie : <0,5 ml/kg/h ≥6h (St 1), ≥12h (St 2) ; <0,3 ml/kg/h ≥24h ou anurie ≥12h (St 3)" : lang === "es" ? "Umbral oliguria: <0,5 ml/kg/h ≥6h (Est. 1), ≥12h (Est. 2); <0,3 ml/kg/h ≥24h o anuria ≥12h (Est. 3)" : lang === "tr" ? "Oligüri eşiği: <0,5 ml/kg/sa ≥6sa (Evre 1), ≥12sa (Evre 2); <0,3 ml/kg/sa ≥24sa veya anüri ≥12sa (Evre 3)" : "Oliguria threshold: <0.5 mL/kg/h ≥6h (St.1), ≥12h (St.2); <0.3 mL/kg/h ≥24h or anuria ≥12h (St.3)"}
          </p>
        </div>

        <button onClick={calculate}
          className="w-full font-syne font-bold text-sm bg-ink text-white py-3 rounded-lg hover:bg-red transition-colors">
          {t(L.calc, lang)}
        </button>
      </div>

      {/* Result */}
      <div className="space-y-4">
        {result ? (() => {
          const info = STAGE_INFO[result.finalStage];
          const colors = RISK_COLORS[info.color];
          return (
            <>
              {/* Main result */}
              <div className={`rounded-xl border p-5 space-y-4 ${colors.bg} ${colors.border}`}>
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-ink-3 text-xs font-syne uppercase tracking-widest mb-1">{t(L.highest_stage, lang)}</p>
                    <div className="flex items-center gap-3">
                      <span className={`font-syne font-extrabold text-5xl ${colors.text}`}>
                        {result.finalStage === 0 ? "—" : result.finalStage}
                      </span>
                      {result.finalStage > 0 && (
                        <span className={`font-syne font-bold text-xs px-3 py-1 rounded-full ${colors.badge}`}>
                          {t(info.label, lang)}
                        </span>
                      )}
                    </div>
                  </div>
                  {result.finalStage === 0 && (
                    <span className="font-syne font-bold text-sm px-4 py-2 rounded-full bg-green text-white">
                      {t(L.no_aki, lang)}
                    </span>
                  )}
                </div>
                <p className={`text-sm leading-relaxed ${colors.text} font-medium`}>{t(info.rec, lang)}</p>
              </div>

              {/* Criteria breakdown */}
              <div className="bg-surface border border-border rounded-xl p-4 space-y-3">
                <p className="font-syne font-bold text-xs text-ink-3 uppercase tracking-widest">
                  {lang === "ru" ? "Разбивка по критериям" : lang === "ar" ? "تفصيل المعايير" : lang === "de" ? "Kriterien-Auswertung" : lang === "fr" ? "Détail des critères" : lang === "es" ? "Desglose de criterios" : lang === "tr" ? "Kriter dökümü" : "Criteria breakdown"}
                </p>

                {/* Creatinine criterion */}
                <div className="flex items-center gap-3 p-3 rounded-lg bg-bg border border-border">
                  <div className={`w-8 h-8 flex-shrink-0 rounded-full flex items-center justify-center font-syne font-bold text-sm ${result.crStage > 0 ? `${RISK_COLORS[stageColors[result.crStage]].badge}` : "bg-surface-2 text-ink-3"}`}>
                    {stageBadge[result.crStage]}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-syne font-semibold text-sm text-ink">{t(L.cr_criterion, lang)}</p>
                    <p className="text-ink-3 text-xs">
                      {lang === "ru"
                        ? `×${result.ratio} от базового (+${result.absDiff} ${unit === "umol" ? "мкмоль/л" : "мг/дл"})`
                        : `×${result.ratio} from baseline (+${result.absDiff} ${unit === "umol" ? "μmol/L" : "mg/dL"})`}
                    </p>
                  </div>
                  <span className="text-xs font-syne font-bold text-ink-2">
                    {result.crStage === 0
                      ? (lang === "ru" ? "Нет ОПП" : "No AKI")
                      : `${lang === "ru" ? "Ст." : lang === "de" ? "Std." : lang === "fr" ? "St." : lang === "es" ? "Est." : lang === "tr" ? "Evre" : lang === "ar" ? "مرحلة" : "Stage"} ${result.crStage}`}
                  </span>
                </div>

                {/* UO criterion */}
                {result.uoPerKg !== null && (
                  <div className="flex items-center gap-3 p-3 rounded-lg bg-bg border border-border">
                    <div className={`w-8 h-8 flex-shrink-0 rounded-full flex items-center justify-center font-syne font-bold text-sm ${result.uoStage > 0 ? `${RISK_COLORS[stageColors[result.uoStage]].badge}` : "bg-surface-2 text-ink-3"}`}>
                      {stageBadge[result.uoStage]}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-syne font-semibold text-sm text-ink">{t(L.uo_criterion, lang)}</p>
                      <p className="text-ink-3 text-xs">{result.uoPerKg} mL/kg/h</p>
                    </div>
                    <span className="text-xs font-syne font-bold text-ink-2">
                      {result.uoStage === 0
                        ? (lang === "ru" ? "Нет ОПП" : "No AKI")
                        : `${lang === "ru" ? "Ст." : lang === "de" ? "Std." : lang === "fr" ? "St." : lang === "es" ? "Est." : lang === "tr" ? "Evre" : lang === "ar" ? "مرحلة" : "Stage"} ${result.uoStage}`}
                    </span>
                  </div>
                )}

                {/* KDIGO stage table */}
                <div className="mt-2 overflow-x-auto">
                  <table className="w-full text-xs font-syne border-collapse">
                    <thead>
                      <tr className="border-b border-border">
                        <th className="text-left py-1.5 pr-3 text-ink-3 font-semibold">{lang === "ru" ? "Стадия" : "Stage"}</th>
                        <th className="text-left py-1.5 pr-3 text-ink-3 font-semibold">{lang === "ru" ? "Креатинин" : "Creatinine"}</th>
                        <th className="text-left py-1.5 text-ink-3 font-semibold">{lang === "ru" ? "Диурез" : "Urine Output"}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border">
                      {[
                        { s: 1, cr: "×1.5–1.9 or +0.3 mg/dL", uo: "<0.5 mL/kg/h ≥6h" },
                        { s: 2, cr: "×2.0–2.9", uo: "<0.5 mL/kg/h ≥12h" },
                        { s: 3, cr: "×3.0 or ≥4.0 mg/dL or RRT", uo: "<0.3 mL/kg/h ≥24h or anuria ≥12h" },
                      ].map(row => (
                        <tr key={row.s} className={result.finalStage === row.s ? "bg-amber-light/40" : ""}>
                          <td className="py-1.5 pr-3 font-bold text-ink">{row.s}</td>
                          <td className="py-1.5 pr-3 text-ink-2">{row.cr}</td>
                          <td className="py-1.5 text-ink-2">{row.uo}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              <AiPanel lang={lang} calcName="AKI (KDIGO)" score={result.finalStage} riskLabel={t(info.label, lang)} />

              <div className="text-ink-3 text-xs leading-relaxed">
                <span className="font-syne font-semibold">{t({ en: "Reference", ru: "Источник", ar: "المرجع", tr: "Kaynak", de: "Referenz", fr: "Référence", es: "Referencia" }, lang)}: </span>
                {t(L.ref, lang)}
              </div>
            </>
          );
        })() : (
          <div className="rounded-xl border border-border bg-surface p-8 flex flex-col items-center justify-center text-center min-h-[300px] space-y-3">
            <div className="text-4xl">🫘</div>
            <p className="text-ink font-syne font-semibold text-sm">
              {lang === "ru" ? "Введите данные и нажмите «Определить стадию ОПП»" : lang === "ar" ? "أدخل القيم وانقر على تحديد مرحلة الإصابة" : lang === "de" ? "Werte eingeben und AKI-Stufe bestimmen" : lang === "fr" ? "Entrez les valeurs et stadifiez l'IRA" : lang === "es" ? "Ingrese los valores y estadifique la IRA" : lang === "tr" ? "Değerleri girin ve AKI evresini belirleyin" : "Enter values and press Stage AKI"}
            </p>
            <p className="text-ink-3 text-xs max-w-xs">
              {lang === "ru" ? "Использует критерии KDIGO 2012. Диурез необязателен — итоговая стадия определяется наивысшим из двух критериев." : "Uses KDIGO 2012 criteria. Urine output is optional — final stage is the highest met criterion."}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Pregnancy Due Date ───────────────────────────────────────────────────────

const PL = {
  lmp:        { en: "Last menstrual period (LMP)", ru: "Первый день последней менструации", ar: "أول يوم في آخر دورة شهرية", tr: "Son adet tarihi (SAT)", de: "Erster Tag der letzten Periode", fr: "Premier jour des dernières règles", es: "Primer día de la última menstruación" },
  edd:        { en: "Estimated due date (EDD)", ru: "Предполагаемая дата родов (ПДР)", ar: "التاريخ المتوقع للولادة", tr: "Tahmini doğum tarihi", de: "Voraussichtlicher Geburtstermin", fr: "Date prévue d'accouchement", es: "Fecha probable de parto" },
  ga:         { en: "Gestational age today", ru: "Гестационный возраст сегодня", ar: "عمر الحمل اليوم", tr: "Bugünkü gestasyonel yaş", de: "Gestationsalter heute", fr: "Âge gestationnel aujourd'hui", es: "Edad gestacional hoy" },
  weeks:      { en: "weeks", ru: "нед.", ar: "أسابيع", tr: "hafta", de: "Wo.", fr: "sem.", es: "sem." },
  days_short: { en: "days", ru: "дн.", ar: "أيام", tr: "gün", de: "Tage", fr: "j", es: "días" },
  trimester:  { en: "Trimester", ru: "Триместр", ar: "الثلاثي", tr: "Trimester", de: "Trimester", fr: "Trimestre", es: "Trimestre" },
  first:      { en: "1st trimester (0–13 weeks)", ru: "I триместр (0–13 нед.)", ar: "الثلاثي الأول (0–13 أسبوعاً)", tr: "1. trimester (0–13 hafta)", de: "1. Trimester (0–13 Wo.)", fr: "1ᵉʳ trimestre (0–13 sem.)", es: "1.er trimestre (0–13 sem.)" },
  second:     { en: "2nd trimester (14–27 weeks)", ru: "II триместр (14–27 нед.)", ar: "الثلاثي الثاني (14–27 أسبوعاً)", tr: "2. trimester (14–27 hafta)", de: "2. Trimester (14–27 Wo.)", fr: "2ᵉ trimestre (14–27 sem.)", es: "2.º trimestre (14–27 sem.)" },
  third:      { en: "3rd trimester (28–40 weeks)", ru: "III триместр (28–40 нед.)", ar: "الثلاثي الثالث (28–40 أسبوعاً)", tr: "3. trimester (28–40 hafta)", de: "3. Trimester (28–40 Wo.)", fr: "3ᵉ trimestre (28–40 sem.)", es: "3.er trimestre (28–40 sem.)" },
  postterm:   { en: "Post-term (> 40 weeks)", ru: "Переношенная (> 40 нед.)", ar: "ما بعد الموعد (> 40 أسبوعاً)", tr: "Miat geçmiş (> 40 hafta)", de: "Übertragen (> 40 Wo.)", fr: "Post-terme (> 40 sem.)", es: "Post-término (> 40 sem.)" },
  note_preg:  { en: "Based on Naegele's rule (LMP + 280 days). Confirm with first-trimester ultrasound.", ru: "По правилу Негеле (ПМ + 280 дней). Уточните по УЗИ 1-го триместра.", ar: "استناداً لقاعدة نيغيل (آخر دورة + 280 يوماً). تأكّد بالموجات فوق الصوتية للثلاثي الأول.", tr: "Naegele kuralına göre (SAT + 280 gün). Birinci trimester ultrasonu ile doğrulayın.", de: "Nach Naegele-Regel (LMP + 280 Tage). Durch Ersttrimester-Ultraschall bestätigen.", fr: "Règle de Naegele (DDR + 280 j). Confirmer par échographie du 1ᵉʳ trimestre.", es: "Regla de Naegele (FUR + 280 días). Confirmar con ecografía del primer trimestre." },
} as const satisfies Record<string, T>;

function PregnancyCalc({ lang }: { lang: string }) {
  const [lmp, setLmp] = useState("");
  const [result, setResult] = useState<{ edd: string; gaWeeks: number; gaDays: number; trimester: string } | null>(null);

  function calculate() {
    if (!lmp) return;
    const lmpDate = new Date(lmp);
    if (isNaN(lmpDate.getTime())) return;
    const eddDate = new Date(lmpDate.getTime() + 280 * 86400000);
    const today = new Date();
    const diffMs = today.getTime() - lmpDate.getTime();
    const totalDays = Math.floor(diffMs / 86400000);
    const gaWeeks = Math.floor(totalDays / 7);
    const gaDays = totalDays % 7;
    let tri = "";
    if (gaWeeks > 40) tri = t(PL.postterm, lang);
    else if (gaWeeks >= 28) tri = t(PL.third, lang);
    else if (gaWeeks >= 14) tri = t(PL.second, lang);
    else tri = t(PL.first, lang);
    setResult({ edd: eddDate.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" }), gaWeeks, gaDays, trimester: tri });
  }

  return (
    <div className="bg-surface border border-border rounded-2xl p-6 space-y-5">
      <div>
        <label className="block font-syne font-semibold text-sm text-ink mb-1">{t(PL.lmp, lang)}</label>
        <input type="date" value={lmp} onChange={e => setLmp(e.target.value)} max={new Date().toISOString().split("T")[0]}
          className="w-full border border-border rounded-lg px-3 py-2 text-sm font-syne text-ink bg-bg focus:outline-none focus:border-ink-2" />
      </div>
      <button onClick={calculate} className="w-full font-syne font-bold text-sm bg-ink text-white py-2.5 rounded-lg hover:bg-red transition-colors">{t(UI.calculate, lang)}</button>
      {result && (
        <div className="space-y-3 pt-2">
          <div className="bg-bg border border-border rounded-xl p-4 text-center">
            <p className="text-ink-3 text-xs font-syne uppercase tracking-widest mb-1">{t(PL.edd, lang)}</p>
            <p className="font-syne font-extrabold text-2xl text-red">{result.edd}</p>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-bg border border-border rounded-xl p-4 text-center">
              <p className="text-ink-3 text-xs font-syne uppercase tracking-widest mb-1">{t(PL.ga, lang)}</p>
              <p className="font-syne font-extrabold text-xl text-ink">{result.gaWeeks}<span className="text-sm font-normal ml-1">{t(PL.weeks, lang)}</span> {result.gaDays}<span className="text-sm font-normal ml-0.5">{t(PL.days_short, lang)}</span></p>
            </div>
            <div className="bg-bg border border-border rounded-xl p-4 text-center">
              <p className="text-ink-3 text-xs font-syne uppercase tracking-widest mb-1">{t(PL.trimester, lang)}</p>
              <p className="font-syne font-bold text-sm text-ink leading-snug mt-1">{result.trimester}</p>
            </div>
          </div>
          <p className="text-ink-3 text-xs leading-relaxed border border-border rounded-lg p-3">{t(PL.note_preg, lang)}</p>
        </div>
      )}
    </div>
  );
}

// ── Ideal Body Weight ────────────────────────────────────────────────────────

const IL = {
  height:    { en: "Height (cm)", ru: "Рост (см)", ar: "الطول (سم)", tr: "Boy (cm)", de: "Größe (cm)", fr: "Taille (cm)", es: "Talla (cm)" },
  weight:    { en: "Actual weight (kg)", ru: "Фактический вес (кг)", ar: "الوزن الفعلي (كغ)", tr: "Gerçek ağırlık (kg)", de: "Tatsächliches Gewicht (kg)", fr: "Poids réel (kg)", es: "Peso actual (kg)" },
  ibw:       { en: "Ideal body weight (IBW)", ru: "Идеальный вес (ИВТ)", ar: "الوزن المثالي للجسم", tr: "İdeal vücut ağırlığı (IBW)", de: "Idealgewicht (IBW)", fr: "Poids idéal (IBW)", es: "Peso corporal ideal (IBW)" },
  abw:       { en: "Adjusted body weight (ABW)", ru: "Скорректированный вес (СВТ)", ar: "الوزن الجسمي المعدّل", tr: "Düzeltilmiş vücut ağırlığı (ABW)", de: "Angepasstes Körpergewicht (ABW)", fr: "Poids ajusté (ABW)", es: "Peso ajustado (ABW)" },
  abw_note:  { en: "Used for dosing in obesity (actual > 120% IBW). ABW = IBW + 0.4 × (actual − IBW)", ru: "Применяется при ожирении (факт. > 120% ИВТ). СВТ = ИВТ + 0,4 × (факт. − ИВТ)", ar: "يُستخدم للجرعة في السمنة (الفعلي > 120% من المثالي). ABW = IBW + 0.4 × (الفعلي − IBW)", tr: "Obezitede dozaj için kullanılır (gerçek > %120 IBW). ABW = IBW + 0.4 × (gerçek − IBW)", de: "Dosierung bei Adipositas (Ist > 120 % IBW). ABW = IBW + 0,4 × (Ist − IBW)", fr: "Dosage en cas d'obésité (réel > 120 % IBW). ABW = IBW + 0,4 × (réel − IBW)", es: "Dosificación en obesidad (real > 120% IBW). ABW = IBW + 0,4 × (real − IBW)" },
  devine:    { en: "Devine formula (1974) — standard for drug dosing in renal/pulmonary medicine.", ru: "Формула Девина (1974) — стандарт дозирования в нефрологии и пульмонологии.", ar: "معادلة ديفين (1974) — معيار لجرعات الأدوية في طب الكلى والرئة.", tr: "Devine formülü (1974) — renal/pulmoner tıpta ilaç dozajı için standart.", de: "Devine-Formel (1974) — Standard für Medikamentendosierung in Nephrologie/Pneumologie.", fr: "Formule de Devine (1974) — standard pour le dosage médicamenteux en néphrologie/pneumologie.", es: "Fórmula de Devine (1974) — estándar para dosificación farmacológica en nefrología/neumología." },
} as const satisfies Record<string, T>;

function IBWCalc({ lang }: { lang: string }) {
  const [height, setHeight] = useState("");
  const [weight, setWeight] = useState("");
  const [sex, setSex] = useState<"male" | "female">("male");
  const [result, setResult] = useState<{ ibw: number; abw: number | null } | null>(null);

  function calculate() {
    const h = parseFloat(height), w = parseFloat(weight);
    if (!h || h < 100 || h > 250) return;
    const inches = h / 2.54;
    const base = sex === "male" ? 50 : 45.5;
    const ibw = Math.max(base + 2.3 * (inches - 60), 0);
    const abw = w && w > ibw * 1.2 ? ibw + 0.4 * (w - ibw) : null;
    setResult({ ibw: Math.round(ibw * 10) / 10, abw: abw ? Math.round(abw * 10) / 10 : null });
  }

  return (
    <div className="bg-surface border border-border rounded-2xl p-6 space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <button onClick={() => setSex("male")} className={`font-syne font-semibold text-sm py-2 rounded-lg border transition-colors ${sex === "male" ? "bg-ink text-white border-ink" : "border-border text-ink-2 hover:border-ink-2"}`}>{t(UI.male, lang)}</button>
        <button onClick={() => setSex("female")} className={`font-syne font-semibold text-sm py-2 rounded-lg border transition-colors ${sex === "female" ? "bg-ink text-white border-ink" : "border-border text-ink-2 hover:border-ink-2"}`}>{t(UI.female, lang)}</button>
      </div>
      <NumInput label={t(IL.height, lang)} value={height} onChange={setHeight} unit="cm" min={100} max={250} />
      <NumInput label={t(IL.weight, lang)} value={weight} onChange={setWeight} unit="kg" min={20} max={300} />
      <button onClick={calculate} className="w-full font-syne font-bold text-sm bg-ink text-white py-2.5 rounded-lg hover:bg-red transition-colors">{t(UI.calculate, lang)}</button>
      {result && (
        <div className="space-y-3 pt-2">
          <div className="bg-bg border border-border rounded-xl p-4 text-center">
            <p className="text-ink-3 text-xs font-syne uppercase tracking-widest mb-1">{t(IL.ibw, lang)}</p>
            <p className="font-syne font-extrabold text-3xl text-red">{result.ibw} <span className="text-base font-normal">kg</span></p>
          </div>
          {result.abw && (
            <div className="bg-bg border border-border rounded-xl p-4 text-center">
              <p className="text-ink-3 text-xs font-syne uppercase tracking-widest mb-1">{t(IL.abw, lang)}</p>
              <p className="font-syne font-extrabold text-2xl text-blue">{result.abw} <span className="text-base font-normal">kg</span></p>
              <p className="text-ink-3 text-xs mt-1">{t(IL.abw_note, lang)}</p>
            </div>
          )}
          <p className="text-ink-3 text-xs leading-relaxed border border-border rounded-lg p-3">{t(IL.devine, lang)}</p>
        </div>
      )}
    </div>
  );
}

// ── Target Heart Rate ────────────────────────────────────────────────────────

const HRL = {
  resting_hr:  { en: "Resting heart rate (bpm)", ru: "ЧСС в покое (уд/мин)", ar: "معدل ضربات القلب أثناء الراحة (نبضة/دقيقة)", tr: "Dinlenme kalp hızı (atım/dak)", de: "Ruheherzfrequenz (S/min)", fr: "Fréquence cardiaque au repos (bpm)", es: "Frecuencia cardíaca en reposo (lpm)" },
  hrmax:       { en: "Max heart rate (220 − age)", ru: "Макс. ЧСС (220 − возраст)", ar: "أقصى معدل لضربات القلب (220 ناقص العمر)", tr: "Maks. kalp hızı (220 − yaş)", de: "Maximale HF (220 − Alter)", fr: "FC maximale (220 − âge)", es: "FC máxima (220 − edad)" },
  zones:       { en: "Training zones (Karvonen method)", ru: "Зоны нагрузки (метод Карвонена)", ar: "مناطق التدريب (طريقة كارفونن)", tr: "Antrenman bölgeleri (Karvonen yöntemi)", de: "Trainingszonen (Karvonen-Methode)", fr: "Zones d'entraînement (méthode Karvonen)", es: "Zonas de entrenamiento (método Karvonen)" },
  zone1: { en: "50–60% — Warm-up / Recovery", ru: "50–60% — Разминка / Восстановление", ar: "50–60% — الإحماء / التعافي", tr: "50–60% — Isınma / Toparlanma", de: "50–60 % — Aufwärmen / Erholung", fr: "50–60 % — Échauffement / Récupération", es: "50–60 % — Calentamiento / Recuperación" },
  zone2: { en: "60–70% — Fat burning / Aerobic base", ru: "60–70% — Сжигание жира / Аэробная база", ar: "60–70% — حرق الدهون / القاعدة الهوائية", tr: "60–70% — Yağ yakma / Aerobik taban", de: "60–70 % — Fettverbrennung / Aerobe Basis", fr: "60–70 % — Combustion graisses / Base aérobie", es: "60–70 % — Quema de grasa / Base aeróbica" },
  zone3: { en: "70–80% — Aerobic / Cardiovascular fitness", ru: "70–80% — Аэробная / Кардиотренировка", ar: "70–80% — اللياقة الهوائية / القلبية الوعائية", tr: "70–80% — Aerobik / Kardiyovasküler kondisyon", de: "70–80 % — Aerob / Kardiovaskuläre Fitness", fr: "70–80 % — Aérobie / Forme cardiovasculaire", es: "70–80 % — Aeróbico / Forma cardiovascular" },
  zone4: { en: "80–90% — Anaerobic threshold / Performance", ru: "80–90% — Анаэробный порог / Производительность", ar: "80–90% — الحد اللاهوائي / الأداء", tr: "80–90% — Anaerobik eşik / Performans", de: "80–90 % — Anaerobe Schwelle / Leistung", fr: "80–90 % — Seuil anaérobie / Performance", es: "80–90 % — Umbral anaeróbico / Rendimiento" },
  bpm: { en: "bpm", ru: "уд/мин", ar: "نبضة/دقيقة", tr: "atım/dak", de: "S/min", fr: "bpm", es: "lpm" },
} as const satisfies Record<string, T>;

function TargetHeartRateCalc({ lang }: { lang: string }) {
  const [age, setAge] = useState("");
  const [rhr, setRhr] = useState("");
  const [result, setResult] = useState<{ hrmax: number; zones: [number, number][] } | null>(null);

  function calculate() {
    const a = parseInt(age), r = parseInt(rhr);
    if (!a || a < 10 || a > 100) return;
    if (!r || r < 30 || r > 120) return;
    const hrmax = 220 - a;
    const hrr = hrmax - r;
    const zones: [number, number][] = [
      [Math.round(hrr * 0.50 + r), Math.round(hrr * 0.60 + r)],
      [Math.round(hrr * 0.60 + r), Math.round(hrr * 0.70 + r)],
      [Math.round(hrr * 0.70 + r), Math.round(hrr * 0.80 + r)],
      [Math.round(hrr * 0.80 + r), Math.round(hrr * 0.90 + r)],
    ];
    setResult({ hrmax, zones });
  }

  const zoneLabels = [HRL.zone1, HRL.zone2, HRL.zone3, HRL.zone4] as const;
  const zoneColors = ["text-green-2", "text-blue", "text-amber-2", "text-red"];

  return (
    <div className="bg-surface border border-border rounded-2xl p-6 space-y-4">
      <NumInput label={t(UI.age, lang)} value={age} onChange={setAge} unit="" min={10} max={100} />
      <NumInput label={t(HRL.resting_hr, lang)} value={rhr} onChange={setRhr} unit="bpm" min={30} max={120} />
      <button onClick={calculate} className="w-full font-syne font-bold text-sm bg-ink text-white py-2.5 rounded-lg hover:bg-red transition-colors">{t(UI.calculate, lang)}</button>
      {result && (
        <div className="space-y-3 pt-2">
          <div className="bg-bg border border-border rounded-xl p-4 text-center">
            <p className="text-ink-3 text-xs font-syne uppercase tracking-widest mb-1">{t(HRL.hrmax, lang)}</p>
            <p className="font-syne font-extrabold text-3xl text-ink">{result.hrmax} <span className="text-base font-normal">{t(HRL.bpm, lang)}</span></p>
          </div>
          <p className="font-syne font-semibold text-sm text-ink">{t(HRL.zones, lang)}</p>
          <div className="space-y-2">
            {result.zones.map(([lo, hi], i) => (
              <div key={i} className="flex items-center justify-between bg-bg border border-border rounded-lg px-4 py-2.5">
                <span className="text-ink-3 text-xs font-syne">{t(zoneLabels[i], lang)}</span>
                <span className={`font-syne font-bold text-sm ${zoneColors[i]}`}>{lo}–{hi} <span className="font-normal text-xs">{t(HRL.bpm, lang)}</span></span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Daily Calorie Needs (TDEE) ───────────────────────────────────────────────

const CL = {
  weight_kg:   { en: "Weight (kg)", ru: "Вес (кг)", ar: "الوزن (كغ)", tr: "Ağırlık (kg)", de: "Gewicht (kg)", fr: "Poids (kg)", es: "Peso (kg)" },
  height_cm:   { en: "Height (cm)", ru: "Рост (см)", ar: "الطول (سم)", tr: "Boy (cm)", de: "Größe (cm)", fr: "Taille (cm)", es: "Talla (cm)" },
  activity:    { en: "Activity level", ru: "Уровень активности", ar: "مستوى النشاط", tr: "Aktivite düzeyi", de: "Aktivitätsniveau", fr: "Niveau d'activité", es: "Nivel de actividad" },
  bmr:         { en: "Basal metabolic rate (BMR)", ru: "Базальный метаболизм (BMR)", ar: "معدل الأيض الأساسي (BMR)", tr: "Bazal metabolizma hızı (BMR)", de: "Grundumsatz (BMR)", fr: "Métabolisme basal (BMR)", es: "Tasa metabólica basal (TMB)" },
  tdee:        { en: "Daily calorie needs (TDEE)", ru: "Суточная потребность в калориях", ar: "احتياجات السعرات الحرارية اليومية", tr: "Günlük kalori ihtiyacı (TDEE)", de: "Täglicher Kalorienbedarf (TDEE)", fr: "Besoins caloriques quotidiens", es: "Necesidades calóricas diarias (TDEE)" },
  lose:        { en: "For weight loss (−500 kcal)", ru: "Для похудения (−500 ккал)", ar: "لفقدان الوزن (−500 سعرة)", tr: "Kilo vermek için (−500 kcal)", de: "Zur Gewichtsabnahme (−500 kcal)", fr: "Pour perdre du poids (−500 kcal)", es: "Para perder peso (−500 kcal)" },
  gain:        { en: "For weight gain (+500 kcal)", ru: "Для набора веса (+500 ккал)", ar: "لزيادة الوزن (+500 سعرة)", tr: "Kilo almak için (+500 kcal)", de: "Zur Gewichtszunahme (+500 kcal)", fr: "Pour prendre du poids (+500 kcal)", es: "Para ganar peso (+500 kcal)" },
  kcal:        { en: "kcal/day", ru: "ккал/сут", ar: "سعرة/يوم", tr: "kcal/gün", de: "kcal/Tag", fr: "kcal/j", es: "kcal/día" },
  mifflin:     { en: "Mifflin-St Jeor equation (1990). Most accurate BMR formula for general population.", ru: "Формула Миффлина-Сент-Жора (1990). Наиболее точная для расчёта BMR у населения.", ar: "معادلة ميفلين-سانت جيور (1990). أكثر معادلات BMR دقةً للسكان العاميين.", tr: "Mifflin-St Jeor denklemi (1990). Genel popülasyon için en doğru BMR formülü.", de: "Mifflin-St-Jeor-Gleichung (1990). Genaueste BMR-Formel für die allgemeine Bevölkerung.", fr: "Équation de Mifflin-St Jeor (1990). Formule BMR la plus précise pour la population générale.", es: "Ecuación de Mifflin-St Jeor (1990). Fórmula de TMB más precisa para la población general." },
  act_sed:     { en: "Sedentary (desk job, little exercise)", ru: "Малоактивный (сидячая работа)", ar: "خامل (عمل مكتبي، قليل من الرياضة)", tr: "Hareketsiz (ofis işi, az egzersiz)", de: "Sitzend (Bürojob, wenig Sport)", fr: "Sédentaire (bureau, peu d'exercice)", es: "Sedentario (trabajo de escritorio, poco ejercicio)" },
  act_light:   { en: "Lightly active (1–3 days/week exercise)", ru: "Слабоактивный (1–3 дня/нед. упражнений)", ar: "نشيط بشكل خفيف (1–3 أيام/الأسبوع)", tr: "Hafif aktif (haftada 1–3 gün egzersiz)", de: "Leicht aktiv (1–3 Tage/Wo. Sport)", fr: "Légèrement actif (1–3 j/sem. exercice)", es: "Ligeramente activo (1–3 días/semana)" },
  act_mod:     { en: "Moderately active (3–5 days/week)", ru: "Умеренно активный (3–5 дней/нед.)", ar: "نشيط باعتدال (3–5 أيام/الأسبوع)", tr: "Orta aktif (haftada 3–5 gün)", de: "Mäßig aktiv (3–5 Tage/Wo.)", fr: "Modérément actif (3–5 j/sem.)", es: "Moderadamente activo (3–5 días/semana)" },
  act_very:    { en: "Very active (6–7 days/week)", ru: "Очень активный (6–7 дней/нед.)", ar: "نشيط جداً (6–7 أيام/الأسبوع)", tr: "Çok aktif (haftada 6–7 gün)", de: "Sehr aktiv (6–7 Tage/Wo.)", fr: "Très actif (6–7 j/sem.)", es: "Muy activo (6–7 días/semana)" },
  act_extra:   { en: "Extra active (athlete / physical job)", ru: "Экстра активный (спортсмен / физ. труд)", ar: "نشاط فائق (رياضي / عمل جسدي)", tr: "Ekstra aktif (atlet / fiziksel iş)", de: "Extra aktiv (Sportler / körperl. Arbeit)", fr: "Très très actif (athlète / travail physique)", es: "Extra activo (atleta / trabajo físico)" },
} as const satisfies Record<string, T>;

const ACTIVITY_OPTS = [
  { key: "act_sed",   mult: 1.2 },
  { key: "act_light", mult: 1.375 },
  { key: "act_mod",   mult: 1.55 },
  { key: "act_very",  mult: 1.725 },
  { key: "act_extra", mult: 1.9 },
] as const;

function CalorieCalc({ lang }: { lang: string }) {
  const [weight, setWeight] = useState("");
  const [height, setHeight] = useState("");
  const [age, setAge] = useState("");
  const [sex, setSex] = useState<"male" | "female">("male");
  const [activity, setActivity] = useState(1.55);
  const [result, setResult] = useState<{ bmr: number; tdee: number } | null>(null);

  function calculate() {
    const w = parseFloat(weight), h = parseFloat(height), a = parseInt(age);
    if (!w || !h || !a) return;
    const bmr = sex === "male"
      ? 10 * w + 6.25 * h - 5 * a + 5
      : 10 * w + 6.25 * h - 5 * a - 161;
    setResult({ bmr: Math.round(bmr), tdee: Math.round(bmr * activity) });
  }

  return (
    <div className="bg-surface border border-border rounded-2xl p-6 space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <button onClick={() => setSex("male")} className={`font-syne font-semibold text-sm py-2 rounded-lg border transition-colors ${sex === "male" ? "bg-ink text-white border-ink" : "border-border text-ink-2"}`}>{t(UI.male, lang)}</button>
        <button onClick={() => setSex("female")} className={`font-syne font-semibold text-sm py-2 rounded-lg border transition-colors ${sex === "female" ? "bg-ink text-white border-ink" : "border-border text-ink-2"}`}>{t(UI.female, lang)}</button>
      </div>
      <NumInput label={t(UI.age, lang)} value={age} onChange={setAge} unit="" min={10} max={100} />
      <NumInput label={t(CL.weight_kg, lang)} value={weight} onChange={setWeight} unit="kg" min={20} max={300} />
      <NumInput label={t(CL.height_cm, lang)} value={height} onChange={setHeight} unit="cm" min={100} max={250} />
      <div>
        <label className="block font-syne font-semibold text-sm text-ink mb-1">{t(CL.activity, lang)}</label>
        <select value={activity} onChange={e => setActivity(parseFloat(e.target.value))}
          className="w-full border border-border rounded-lg px-3 py-2 text-sm font-syne text-ink bg-bg focus:outline-none focus:border-ink-2">
          {ACTIVITY_OPTS.map(o => (
            <option key={o.mult} value={o.mult}>{t(CL[o.key as keyof typeof CL] as T, lang)}</option>
          ))}
        </select>
      </div>
      <button onClick={calculate} className="w-full font-syne font-bold text-sm bg-ink text-white py-2.5 rounded-lg hover:bg-red transition-colors">{t(UI.calculate, lang)}</button>
      {result && (
        <div className="space-y-3 pt-2">
          <div className="bg-bg border border-border rounded-xl p-4 text-center">
            <p className="text-ink-3 text-xs font-syne uppercase tracking-widest mb-1">{t(CL.tdee, lang)}</p>
            <p className="font-syne font-extrabold text-3xl text-red">{result.tdee} <span className="text-base font-normal">{t(CL.kcal, lang)}</span></p>
          </div>
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-bg border border-border rounded-lg p-3 text-center">
              <p className="text-ink-3 text-xs font-syne mb-0.5">{t(CL.bmr, lang)}</p>
              <p className="font-syne font-bold text-sm text-ink">{result.bmr}</p>
            </div>
            <div className="bg-bg border border-blue/30 rounded-lg p-3 text-center">
              <p className="text-ink-3 text-xs font-syne mb-0.5">{t(CL.lose, lang)}</p>
              <p className="font-syne font-bold text-sm text-blue">{result.tdee - 500}</p>
            </div>
            <div className="bg-bg border border-green-2/30 rounded-lg p-3 text-center">
              <p className="text-ink-3 text-xs font-syne mb-0.5">{t(CL.gain, lang)}</p>
              <p className="font-syne font-bold text-sm text-green-2">{result.tdee + 500}</p>
            </div>
          </div>
          <p className="text-ink-3 text-xs leading-relaxed border border-border rounded-lg p-3">{t(CL.mifflin, lang)}</p>
        </div>
      )}
    </div>
  );
}

// ── Main widget exported ─────────────────────────────────────────────────────

export function CalculatorWidget({ slug }: { slug: string }) {
  const { locale } = useI18n();
  const lang = locale as string;

  if (slug === "egfr-ckd-epi") return <EgfrCalc lang={lang} />;
  if (slug === "aki") return <AkiCalc lang={lang} />;
  if (slug === "bmi") return <BmiCalc lang={lang} />;
  if (slug === "corrected-calcium") return <CorrectedCalciumCalc lang={lang} />;
  if (slug === "anion-gap") return <AnionGapCalc lang={lang} />;
  if (slug === "meld") return <MeldCalc lang={lang} />;
  if (slug === "cockcroft-gault") return <CockcroftGaultCalc lang={lang} />;
  if (slug === "pregnancy-due-date") return <PregnancyCalc lang={lang} />;
  if (slug === "ideal-body-weight") return <IBWCalc lang={lang} />;
  if (slug === "target-heart-rate") return <TargetHeartRateCalc lang={lang} />;
  if (slug === "daily-calories") return <CalorieCalc lang={lang} />;

  const calc = getCalc(slug);
  if (!calc) return (
    <div className="text-ink-3 text-sm py-12 text-center font-syne">
      {lang === "ru" ? "Калькулятор не найден" : "Calculator not found"}
    </div>
  );

  return <CheckboxCalc calc={calc} lang={lang} />;
}

// ── Index widget: grid of all calculators ─────────────────────────────────────

import { INDEX_T } from "./data";

export function CalculatorsIndex() {
  const { locale } = useI18n();
  const lang = locale as string;
  const tIdx = (key: string) => t(INDEX_T[key], lang);

  const numericCalcs = [
    { slug: "egfr-ckd-epi",         name: tIdx("egfr_name"),     subtitle: tIdx("egfr_sub"),       category: tIdx("nephrology"),    icon: "🫘" },
    { slug: "aki",                   name: tIdx("aki_name"),      subtitle: tIdx("aki_sub"),        category: tIdx("critical_care"), icon: "🚨" },
    { slug: "bmi",                   name: tIdx("bmi_name"),      subtitle: tIdx("bmi_sub"),        category: tIdx("general"),       icon: "⚖️" },
    { slug: "corrected-calcium",     name: tIdx("calcium_name"),  subtitle: tIdx("calcium_sub"),    category: tIdx("biochemistry"),  icon: "🧪" },
    { slug: "anion-gap",             name: tIdx("aniongap_name"), subtitle: tIdx("aniongap_sub"),   category: tIdx("biochemistry"),  icon: "⚗️" },
    { slug: "meld",                  name: tIdx("meld_name"),     subtitle: tIdx("meld_sub"),       category: tIdx("hepatology"),    icon: "🫀" },
    { slug: "cockcroft-gault",       name: tIdx("cg_name"),       subtitle: tIdx("cg_sub"),         category: tIdx("nephrology"),    icon: "💊" },
    { slug: "pregnancy-due-date",    name: tIdx("preg_name"),     subtitle: tIdx("preg_sub"),       category: tIdx("obstetrics"),    icon: "🤰" },
    { slug: "ideal-body-weight",     name: tIdx("ibw_name"),      subtitle: tIdx("ibw_sub"),        category: tIdx("general"),       icon: "⚖️" },
    { slug: "target-heart-rate",     name: tIdx("thr_name"),      subtitle: tIdx("thr_sub"),        category: tIdx("cardiology"),    icon: "💓" },
    { slug: "daily-calories",        name: tIdx("cal_name"),      subtitle: tIdx("cal_sub"),        category: tIdx("general"),       icon: "🍎" },
  ];

  const allCalcs = [
    ...CALCULATORS.map(c => ({
      slug: c.slug,
      name: t(c.nameI18n, lang),
      subtitle: t(c.subtitle, lang),
      category: t(c.categoryI18n, lang),
      icon: c.icon,
    })),
    ...numericCalcs,
  ];

  return (
    <div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-10">
        {allCalcs.map(c => (
          <Link
            key={c.slug}
            href={`/calculators/${c.slug}`}
            className="group bg-surface border border-border rounded-xl p-5 hover:border-border-2 hover:shadow-sm transition-all flex flex-col gap-3"
          >
            <div className="flex items-start justify-between gap-2">
              <span className="text-2xl">{c.icon}</span>
              <span className="text-xs font-syne font-semibold text-ink-3 bg-bg px-2 py-0.5 rounded-full border border-border">
                {c.category}
              </span>
            </div>
            <div>
              <h3 className="font-syne font-bold text-base text-ink group-hover:text-red transition-colors leading-tight mb-1">
                {c.name}
              </h3>
              <p className="text-ink-3 text-sm leading-snug">{c.subtitle}</p>
            </div>
            <span className="text-red font-syne font-semibold text-sm mt-auto">{tIdx("open_calculator")}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
