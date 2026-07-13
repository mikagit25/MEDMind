"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { veterinaryApi } from "@/lib/api";

type Drug = {
  id: string; name: string; generic_name?: string; drug_class?: string;
  mechanism?: string; indications?: string[]; contraindications?: string[];
  adverse_effects?: Record<string, any>; dosing?: Record<string, any>;
  monitoring?: string[]; black_box_warning?: string; interactions?: string[];
  is_high_yield?: boolean; is_nti?: boolean; is_veterinary?: boolean;
  image_url?: string; available_langs?: string[];
};

type Alternative = {
  id: string; name: string; generic_name?: string; drug_class?: string;
  is_high_yield?: boolean; reason: string; image_url?: string;
};

type Tab = "overview" | "dosing" | "adverse" | "vet";

const LANG_FLAGS: Record<string, string> = {
  en: "🇺🇸", ru: "🇷🇺", ar: "🇸🇦", de: "🇩🇪", fr: "🇫🇷", es: "🇪🇸", tr: "🇹🇷",
};
const LANG_NAMES: Record<string, string> = {
  en: "English", ru: "Русский", ar: "العربية", de: "Deutsch", fr: "Français", es: "Español", tr: "Türkçe",
};

const T: Record<string, Record<string, string>> = {
  language:      { en: "Language:", ru: "Язык:", ar: "اللغة:", de: "Sprache:", fr: "Langue:", es: "Idioma:", tr: "Dil:" },
  overview:      { en: "Overview", ru: "Обзор", ar: "نظرة عامة", de: "Übersicht", fr: "Aperçu", es: "Resumen", tr: "Genel Bakış" },
  dosing:        { en: "Dosing", ru: "Дозировка", ar: "الجرعات", de: "Dosierung", fr: "Posologie", es: "Dosificación", tr: "Dozaj" },
  adverse:       { en: "Side Effects", ru: "Побочные эффекты", ar: "الآثار الجانبية", de: "Nebenwirkungen", fr: "Effets secondaires", es: "Efectos secundarios", tr: "Yan Etkiler" },
  vet:           { en: "🐾 Vet Dosing", ru: "🐾 Вет. дозы", ar: "🐾 جرعات بيطرية", de: "🐾 Vet. Dosierung", fr: "🐾 Doses vét.", es: "🐾 Dosis vet.", tr: "🐾 Vet. Dozu" },
  selectSpecies: { en: "Select Species", ru: "Выберите вид", ar: "اختر النوع", de: "Tierart wählen", fr: "Choisir l'espèce", es: "Seleccionar especie", tr: "Tür seçin" },
  loading:       { en: "Loading…", ru: "Загрузка…", ar: "جارٍ التحميل…", de: "Lädt…", fr: "Chargement…", es: "Cargando…", tr: "Yükleniyor…" },
  estimatedDose: { en: "Estimated Dosing", ru: "Ориентировочная доза", ar: "الجرعة التقديرية", de: "Geschätzte Dosierung", fr: "Dosage estimé", es: "Dosificación estimada", tr: "Tahmini Dozaj" },
  vetDisclaimer: { en: "⚠ Scaled from human doses — verify with current veterinary formulary before clinical use.", ru: "⚠ Дозы масштабированы от человеческих — проверяйте по ветеринарному формуляру перед применением.", ar: "⚠ مُحتسبة من جرعات البشر — تحقق من الدستور البيطري قبل الاستخدام.", de: "⚠ Von menschlichen Dosen skaliert — vor klinischer Anwendung mit aktuellem Veterinärformular prüfen.", fr: "⚠ Extrapolé des doses humaines — vérifier avec le formulaire vétérinaire actuel avant usage clinique.", es: "⚠ Escalado desde dosis humanas — verificar con formulario veterinario vigente antes del uso clínico.", tr: "⚠ İnsan dozlarından ölçeklendirildi — klinik kullanım öncesi mevcut veteriner formüleri ile doğrulayın." },
  noVetData:     { en: "No veterinary dosing data", ru: "Нет ветеринарных данных по дозировке", ar: "لا توجد بيانات جرعات بيطرية", de: "Keine veterinären Dosierdaten", fr: "Aucune donnée de dosage vétérinaire", es: "Sin datos de dosificación veterinaria", tr: "Veteriner dozaj verisi yok" },
  vetEduOnly:    { en: "🐾 For educational use only.", ru: "🐾 Только в образовательных целях.", ar: "🐾 للاستخدام التعليمي فقط.", de: "🐾 Nur zu Bildungszwecken.", fr: "🐾 À des fins éducatives uniquement.", es: "🐾 Solo para uso educativo.", tr: "🐾 Yalnızca eğitim amaçlıdır." },
  similarDrugs:  { en: "Similar Drugs — Same Class", ru: "Похожие препараты — тот же класс", ar: "أدوية مماثلة — نفس الفئة", de: "Ähnliche Medikamente — gleiche Klasse", fr: "Médicaments similaires — même classe", es: "Medicamentos similares — misma clase", tr: "Benzer İlaçlar — Aynı Sınıf" },
  sameClass:     { en: "Same pharmacological class or related mechanism of action", ru: "Тот же фармакологический класс или схожий механизм действия", ar: "نفس الفئة الدوائية أو آلية عمل مماثلة", de: "Gleiche pharmakologische Klasse oder verwandter Wirkungsmechanismus", fr: "Même classe pharmacologique ou mécanisme d'action similaire", es: "Misma clase farmacológica o mecanismo de acción relacionado", tr: "Aynı farmakolojik sınıf veya ilgili etki mekanizması" },
  caution:       { en: "Caution: Risk for", ru: "Осторожно: риск для", ar: "تحذير: خطر على", de: "Vorsicht: Risiko für", fr: "Attention : risque pour", es: "Precaución: riesgo para", tr: "Dikkat: Risk var:" },
  safe:          { en: "Generally safe for", ru: "Как правило, безопасен для", ar: "آمن عمومًا لـ", de: "Im Allgemeinen sicher für", fr: "Généralement sûr pour", es: "Generalmente seguro para", tr: "Genellikle güvenli:" },
  mechanism:     { en: "Mechanism of Action", ru: "Механизм действия", ar: "آلية العمل", de: "Wirkmechanismus", fr: "Mécanisme d'action", es: "Mecanismo de acción", tr: "Etki Mekanizması" },
  indications:   { en: "Indications", ru: "Показания", ar: "المؤشرات", de: "Indikationen", fr: "Indications", es: "Indicaciones", tr: "Endikasyonlar" },
  contraindications: { en: "Contraindications", ru: "Противопоказания", ar: "موانع الاستخدام", de: "Kontraindikationen", fr: "Contre-indications", es: "Contraindicaciones", tr: "Kontrendikasyonlar" },
  drugInteractions:  { en: "Drug Interactions", ru: "Лекарственные взаимодействия", ar: "التفاعلات الدوائية", de: "Wechselwirkungen", fr: "Interactions médicamenteuses", es: "Interacciones farmacológicas", tr: "İlaç Etkileşimleri" },
  dosingSection: { en: "Dosing", ru: "Дозировка", ar: "الجرعات", de: "Dosierung", fr: "Posologie", es: "Dosificación", tr: "Dozaj" },
  monitoring:    { en: "Monitoring Parameters", ru: "Параметры мониторинга", ar: "معايير المراقبة", de: "Überwachungsparameter", fr: "Paramètres de surveillance", es: "Parámetros de monitoreo", tr: "İzleme Parametreleri" },
  ntiWarning:    { en: "⚠ Narrow Therapeutic Index (NTI) drug — close monitoring and precise dosing required.", ru: "⚠ Препарат с узким терапевтическим индексом (NTI) — необходим тщательный мониторинг.", ar: "⚠ دواء ذو نطاق علاجي ضيق — يتطلب مراقبة دقيقة وجرعات محددة.", de: "⚠ Arzneimittel mit engem therapeutischem Index (NTI) — genaue Überwachung erforderlich.", fr: "⚠ Médicament à index thérapeutique étroit (NTI) — surveillance étroite requise.", es: "⚠ Medicamento de índice terapéutico estrecho (NTI) — se requiere monitoreo cercano.", tr: "⚠ Dar Terapötik İndeksli (NTI) ilaç — yakın izleme gereklidir." },
  noDosingInfo:  { en: "No dosing information available.", ru: "Информация о дозировке отсутствует.", ar: "لا تتوفر معلومات عن الجرعة.", de: "Keine Dosierungsinformationen verfügbar.", fr: "Aucune information de dosage disponible.", es: "No hay información de dosificación disponible.", tr: "Dozaj bilgisi mevcut değil." },
  noAdverseInfo: { en: "No adverse effects data available.", ru: "Данные о побочных эффектах отсутствуют.", ar: "لا تتوفر بيانات عن الآثار الجانبية.", de: "Keine Daten zu Nebenwirkungen verfügbar.", fr: "Aucune donnée sur les effets indésirables.", es: "No hay datos de efectos adversos disponibles.", tr: "Advers etki verisi mevcut değil." },
  noDetailedInfo: { en: "Detailed information not yet available for this drug.", ru: "Подробная информация об этом препарате пока отсутствует.", ar: "التفاصيل غير متوفرة لهذا الدواء بعد.", de: "Detaillierte Informationen für dieses Medikament noch nicht verfügbar.", fr: "Informations détaillées pas encore disponibles pour ce médicament.", es: "Información detallada aún no disponible para este medicamento.", tr: "Bu ilaç için ayrıntılı bilgi henüz mevcut değil." },
  foundCount:    { en: "{n} found", ru: "Найдено: {n}", ar: "تم العثور على {n}", de: "{n} gefunden", fr: "{n} trouvé(s)", es: "{n} encontrado(s)", tr: "{n} bulundu" },
};
const t = (key: string, lang: string) => T[key]?.[lang] ?? T[key]?.["en"] ?? key;

const FALLBACK_SPECIES = [
  { id: "canine", name: "Canine", icon: "🐕" }, { id: "feline", name: "Feline", icon: "🐈" },
  { id: "equine", name: "Equine", icon: "🐎" }, { id: "bovine", name: "Bovine", icon: "🐄" },
  { id: "avian",  name: "Avian",  icon: "🦜" }, { id: "rabbit", name: "Rabbit", icon: "🐇" },
];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-surface border border-border rounded-xl p-5">
      <div className="font-syne font-bold text-xs text-ink-2 uppercase tracking-wider mb-3">{title}</div>
      {children}
    </div>
  );
}

function OverviewTab({ drug, lang }: { drug: Drug; lang: string }) {
  return (
    <div className="space-y-5">
      {drug.mechanism && (
        <Section title={t("mechanism", lang)}>
          <p className="font-serif text-sm text-ink leading-relaxed">{drug.mechanism}</p>
        </Section>
      )}
      {drug.indications && drug.indications.length > 0 && (
        <Section title={t("indications", lang)}>
          <ul className="space-y-1">
            {drug.indications.map((item, i) => (
              <li key={i} className="font-serif text-sm text-ink flex gap-2">
                <span className="text-green flex-shrink-0">✓</span><span>{item}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}
      {drug.contraindications && drug.contraindications.length > 0 && (
        <Section title={t("contraindications", lang)}>
          <ul className="space-y-1">
            {drug.contraindications.map((item, i) => (
              <li key={i} className="font-serif text-sm text-ink flex gap-2">
                <span className="text-red flex-shrink-0">✗</span><span>{item}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}
      {drug.interactions && drug.interactions.length > 0 && (
        <Section title={t("drugInteractions", lang)}>
          <ul className="space-y-1">
            {drug.interactions.map((item, i) => (
              <li key={i} className="font-serif text-sm text-ink flex gap-2">
                <span className="text-amber flex-shrink-0">⚡</span><span>{item}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}
      {!drug.mechanism && !drug.indications?.length && !drug.contraindications?.length && (
        <div className="bg-surface border border-border rounded-xl p-8 text-center">
          <p className="font-serif text-ink-3 text-sm">{t("noDetailedInfo", lang)}</p>
        </div>
      )}
    </div>
  );
}

function DosingTab({ drug, lang }: { drug: Drug; lang: string }) {
  const hasDosingData = drug.dosing && Object.keys(drug.dosing).length > 0;
  const hasMonitoring = drug.monitoring && drug.monitoring.length > 0;
  if (!hasDosingData && !hasMonitoring) {
    return (
      <div className="bg-surface border border-border rounded-xl p-8 text-center">
        <p className="font-serif text-ink-3 text-sm">{t("noDosingInfo", lang)}</p>
      </div>
    );
  }
  return (
    <div className="space-y-5">
      {hasDosingData && (
        <Section title={t("dosingSection", lang)}>
          <div className="divide-y divide-border">
            {Object.entries(drug.dosing!).map(([route, dose]) => (
              <div key={route} className="py-2.5 flex gap-4 items-start">
                <span className="font-syne font-bold text-xs text-ink-2 uppercase w-24 flex-shrink-0 pt-0.5">{route}</span>
                <span className="font-serif text-sm text-ink">{String(dose)}</span>
              </div>
            ))}
          </div>
        </Section>
      )}
      {hasMonitoring && (
        <Section title={t("monitoring", lang)}>
          <ul className="space-y-1.5">
            {drug.monitoring!.map((item, i) => (
              <li key={i} className="font-serif text-sm text-ink flex gap-2">
                <span className="text-blue">•</span><span>{item}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}
      {drug.is_nti && (
        <div className="p-3 rounded-lg bg-amber-light border border-amber/30 font-serif text-xs text-amber">
          {t("ntiWarning", lang)}
        </div>
      )}
    </div>
  );
}

function AdverseTab({ drug, lang }: { drug: Drug; lang: string }) {
  if (!drug.adverse_effects || Object.keys(drug.adverse_effects).length === 0) {
    return (
      <div className="bg-surface border border-border rounded-xl p-8 text-center">
        <p className="font-serif text-ink-3 text-sm">{t("noAdverseInfo", lang)}</p>
      </div>
    );
  }
  const severityOrder = ["common", "serious", "rare", "life-threatening"];
  const entries = Object.entries(drug.adverse_effects);
  entries.sort(([a], [b]) => {
    const ai = severityOrder.findIndex(s => a.toLowerCase().includes(s));
    const bi = severityOrder.findIndex(s => b.toLowerCase().includes(s));
    return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
  });
  const categoryColor: Record<string, string> = { common: "text-amber", serious: "text-red", "life-threatening": "text-red", rare: "text-ink-3" };
  return (
    <div className="space-y-4">
      {entries.map(([category, effects]) => {
        const colorKey = Object.keys(categoryColor).find(k => category.toLowerCase().includes(k));
        const color = colorKey ? categoryColor[colorKey] : "text-ink-2";
        return (
          <div key={category} className="bg-surface border border-border rounded-xl p-4">
            <div className={`font-syne font-bold text-xs uppercase mb-2 ${color}`}>{category}</div>
            <div className="flex flex-wrap gap-1.5">
              {(effects as string[]).map((effect, i) => (
                <span key={i} className="inline-block px-2 py-0.5 rounded-full bg-bg font-serif text-xs text-ink">{effect}</span>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function VetTab({ drug, allSpecies, lang }: { drug: Drug; allSpecies: any[]; lang: string }) {
  const speciesList = allSpecies.length > 0 ? allSpecies : FALLBACK_SPECIES;
  const [selectedSpecies, setSelectedSpecies] = useState<any | null>(null);
  const [dbDosing, setDbDosing] = useState<any[]>([]);
  const [safety, setSafety] = useState<any>(null);
  const [scaledDosing, setScaledDosing] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const selectSpecies = async (sp: any) => {
    setSelectedSpecies(sp); setDbDosing([]); setSafety(null); setScaledDosing(null); setLoading(true);
    const isUUID = sp.id?.includes("-");
    const nameToKey: Record<string, string> = { canine: "canine", feline: "feline", equine: "equine", bovine: "bovine", avian: "avian", rabbit: "exotic" };
    const speciesKey = nameToKey[sp.name?.toLowerCase()] ?? sp.name?.toLowerCase();
    const [dosingRes, safetyRes, scaledRes] = await Promise.all([
      isUUID ? veterinaryApi.getDrugDosing(drug.id, sp.id).catch(() => []) : Promise.resolve([]),
      isUUID ? veterinaryApi.checkSafety(drug.id, sp.id).catch(() => null) : Promise.resolve(null),
      speciesKey ? veterinaryApi.getScaledDosing(drug.name, speciesKey).catch(() => null) : Promise.resolve(null),
    ]);
    setDbDosing(dosingRes ?? []); setSafety(safetyRes); setScaledDosing(scaledRes); setLoading(false);
  };

  const speciesDisplayName = (sp: any) =>
    lang !== "en" && sp.name_ru ? sp.name_ru : sp.name;

  return (
    <div className="space-y-5">
      <Section title={t("selectSpecies", lang)}>
        <div className="flex flex-wrap gap-2">
          {speciesList.map((sp: any) => (
            <button key={sp.id} onClick={() => selectSpecies(sp)}
              className={`px-3 py-2 rounded-lg border font-syne font-semibold text-xs transition-all ${selectedSpecies?.id === sp.id ? "border-ink bg-ink text-white" : "border-border text-ink-2 hover:border-ink-3"}`}>
              {sp.icon && <span className="mr-1">{sp.icon}</span>}{speciesDisplayName(sp)}
            </button>
          ))}
        </div>
      </Section>
      {loading && <div className="text-center py-6 font-serif text-ink-3 text-sm">{t("loading", lang)}</div>}
      {!loading && selectedSpecies && (
        <>
          {safety && (
            <div className={`p-4 rounded-xl border flex gap-3 ${safety.is_toxic ? "bg-red-light border-red/30" : "bg-green-light border-green/20"}`}>
              <span className="text-xl">{safety.is_toxic ? "⚠️" : "✅"}</span>
              <div className={`font-syne font-bold text-sm ${safety.is_toxic ? "text-red" : "text-green"}`}>
                {safety.is_toxic
                  ? `${t("caution", lang)} ${speciesDisplayName(selectedSpecies)}`
                  : `${t("safe", lang)} ${speciesDisplayName(selectedSpecies)}`}
                {safety.toxicity_note && <div className="font-serif font-normal text-xs text-ink-2 mt-0.5">{safety.toxicity_note}</div>}
              </div>
            </div>
          )}
          {dbDosing.length > 0 && (
            <Section title={`${t("dosing", lang)} — ${speciesDisplayName(selectedSpecies)}`}>
              <div className="space-y-3">
                {dbDosing.map((d: any, i: number) => (
                  <div key={i} className="p-3 rounded-lg bg-bg space-y-1">
                    <div className="flex items-center gap-3 flex-wrap">
                      {d.route && <span className="px-2 py-0.5 rounded bg-ink text-white font-syne font-bold text-xs">{d.route}</span>}
                      {d.dose && !d.is_toxic && <span className="font-syne font-bold text-sm text-ink">{d.dose}</span>}
                      {d.frequency && !d.is_toxic && <span className="font-serif text-ink-3 text-xs">{d.frequency}</span>}
                    </div>
                    {d.notes && <div className="font-serif text-xs text-ink-3 italic">{d.notes}</div>}
                  </div>
                ))}
              </div>
            </Section>
          )}
          {scaledDosing?.species_dosing && Object.keys(scaledDosing.species_dosing).length > 0 && (
            <Section title={`${t("estimatedDose", lang)} — ${speciesDisplayName(selectedSpecies)}`}>
              <div className="p-3 rounded-lg bg-amber-light border border-amber/20 mb-3 font-serif text-xs text-amber">
                {t("vetDisclaimer", lang)}
              </div>
              <div className="divide-y divide-border">
                {Object.entries(scaledDosing.species_dosing).map(([route, info]: [string, any]) => (
                  <div key={route} className="py-2.5 flex gap-4 items-start">
                    <span className="font-syne font-bold text-xs text-ink-2 uppercase w-20 flex-shrink-0">{route}</span>
                    <span className="font-serif text-sm text-ink">{typeof info === "object" ? (info.dose ?? JSON.stringify(info)) : String(info)}</span>
                  </div>
                ))}
              </div>
            </Section>
          )}
          {dbDosing.length === 0 && !scaledDosing && (
            <div className="bg-surface border border-border rounded-xl p-6 text-center">
              <p className="font-serif text-ink-3 text-sm">{t("noVetData", lang)} — {drug.name} / {speciesDisplayName(selectedSpecies)}</p>
            </div>
          )}
        </>
      )}
      {!selectedSpecies && <div className="bg-surface border border-border rounded-xl p-6 text-center"><p className="font-serif text-ink-3 text-sm">{t("selectSpecies", lang)}</p></div>}
      <p className="font-serif text-ink-3 text-xs text-center">{t("vetEduOnly", lang)}</p>
    </div>
  );
}

function AltDrugImage({ url, name }: { url?: string; name: string }) {
  const [ok, setOk] = useState(true);
  if (url && ok) {
    return <img src={url} alt={name} className="w-full h-full object-contain p-1" loading="lazy" onError={() => setOk(false)} />;
  }
  return <span className="text-2xl">💊</span>;
}

export function DrugDetailTabs({
  drug,
  alternatives,
  allSpecies,
  lang,
}: {
  drug: Drug;
  alternatives: Alternative[];
  allSpecies: any[];
  lang: string;
}) {
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("overview");
  const availableLangs = ["en", ...(drug.available_langs ?? [])];

  const tabs: { key: Tab; label: string }[] = [
    { key: "overview", label: t("overview", lang) },
    { key: "dosing",   label: t("dosing", lang) },
    { key: "adverse",  label: t("adverse", lang) },
    { key: "vet",      label: t("vet", lang) },
  ];

  return (
    <>
      {/* Language switcher */}
      {availableLangs.length > 1 && (
        <div className="flex items-center gap-2 mb-6 flex-wrap">
          <span className="font-syne font-semibold text-xs text-ink-3">{t("language", lang)}</span>
          {availableLangs.map(l => (
            <button key={l}
              onClick={() => router.push(`/drugs/${drug.id}${l !== "en" ? `?lang=${l}` : ""}`)}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-full font-syne font-semibold text-xs border transition-all ${l === lang ? "bg-ink text-white border-ink" : "border-border text-ink-2 hover:border-ink"}`}>
              <span>{LANG_FLAGS[l] || "🌐"}</span>
              <span>{LANG_NAMES[l] || l.toUpperCase()}</span>
            </button>
          ))}
        </div>
      )}

      {/* Tabs — horizontal scroll on narrow screens, hidden scrollbar */}
      <div className="flex gap-1 mb-6 bg-surface border border-border p-1 rounded-xl overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`flex-1 min-w-fit px-2 sm:px-3 py-1.5 rounded-lg font-syne font-semibold text-xs transition-all whitespace-nowrap text-center ${tab === t.key ? "bg-ink text-white shadow" : "text-ink-3 hover:text-ink"}`}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === "overview" && <OverviewTab drug={drug} lang={lang} />}
      {tab === "dosing"   && <DosingTab drug={drug} lang={lang} />}
      {tab === "adverse"  && <AdverseTab drug={drug} lang={lang} />}
      {tab === "vet"      && <VetTab drug={drug} allSpecies={allSpecies} lang={lang} />}

      {/* Related drugs */}
      {alternatives.length > 0 && (
        <div className="mt-10">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-syne font-bold text-base text-ink">{t("similarDrugs", lang)}</h2>
            <span className="font-serif text-ink-3 text-xs">{t("foundCount", lang).replace("{n}", String(alternatives.length))}</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {alternatives.map(alt => (
              <Link key={alt.id} href={`/drugs/${alt.id}`}
                className="group flex flex-col bg-surface border border-border rounded-xl p-3 hover:border-ink hover:shadow-md transition-all cursor-pointer">
                <div className="h-16 w-full rounded-lg overflow-hidden bg-bg flex items-center justify-center mb-2">
                  <AltDrugImage url={alt.image_url} name={alt.name} />
                </div>
                <div className="font-syne font-bold text-xs text-ink leading-tight line-clamp-2 group-hover:text-accent">{alt.name}</div>
                {alt.generic_name && alt.generic_name !== alt.name && (
                  <div className="font-serif text-ink-3 text-xs mt-0.5 line-clamp-1">{alt.generic_name}</div>
                )}
                <div className="flex items-center justify-between mt-1.5">
                  <span className="font-serif text-ink-3 text-xs">{alt.reason}</span>
                  {alt.is_high_yield && <span className="px-1.5 py-0.5 rounded-full bg-amber-light text-amber font-syne font-bold text-xs">⭐</span>}
                </div>
              </Link>
            ))}
          </div>
          <p className="font-serif text-ink-3 text-xs text-center mt-4">{t("sameClass", lang)}</p>
        </div>
      )}
    </>
  );
}
