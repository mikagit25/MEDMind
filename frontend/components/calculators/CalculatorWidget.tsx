"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { useI18n } from "@/lib/i18n";
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

// ── AI CTA ───────────────────────────────────────────────────────────────────

function AiCta({ lang }: { lang: string }) {
  return (
    <div className="bg-surface border border-border rounded-xl p-5 flex flex-col sm:flex-row gap-4 items-start sm:items-center">
      <div className="flex-1 min-w-0">
        <p className="font-syne font-bold text-sm text-ink mb-1">{t(UI.ai_cta_title, lang)}</p>
        <p className="text-ink-3 text-xs leading-relaxed">{t(UI.ai_cta_desc, lang)}</p>
      </div>
      <Link
        href="/register"
        className="flex-shrink-0 font-syne font-semibold text-sm bg-ink text-white px-4 py-2 rounded hover:bg-red transition-colors whitespace-nowrap"
      >
        {t(UI.ai_cta_btn, lang)}
      </Link>
    </div>
  );
}

// ── Checkbox-based calculator ─────────────────────────────────────────────────

function CheckboxCalc({ calc, lang }: { calc: CalcMeta; lang: string }) {
  const initState = useMemo(() => {
    const s: Record<string, number> = {};
    calc.fields.forEach((f, i) => {
      if (f.type === "checkbox") s[`cb_${i}`] = 0;
      else if (f.type === "select") s[f.id] = 0;
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

        <AiCta lang={lang} />

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

        <AiCta lang={lang} />

        <div className="text-ink-3 text-xs leading-relaxed">
          <span className="font-syne font-semibold">{tl("reference")}: </span>
          {tl("ref_text")}
        </div>
      </div>
    </div>
  );
}

// ── Main widget exported ─────────────────────────────────────────────────────

export function CalculatorWidget({ slug }: { slug: string }) {
  const { locale } = useI18n();
  const lang = locale as string;

  if (slug === "egfr-ckd-epi") {
    return <EgfrCalc lang={lang} />;
  }

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

  const allCalcs = [
    ...CALCULATORS.map(c => ({
      slug: c.slug,
      name: t(c.nameI18n, lang),
      subtitle: t(c.subtitle, lang),
      category: t(c.categoryI18n, lang),
      icon: c.icon,
    })),
    {
      slug: "egfr-ckd-epi",
      name: tIdx("egfr_name"),
      subtitle: tIdx("egfr_sub"),
      category: tIdx("nephrology"),
      icon: "🫘",
    },
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
