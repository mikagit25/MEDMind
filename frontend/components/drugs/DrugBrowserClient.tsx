"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { drugsApi } from "@/lib/api";
import { InteractionChecker } from "@/components/drugs/InteractionChecker";
import { useI18n } from "@/lib/i18n";
import { translateDrugClass } from "@/lib/learn-i18n";

type Drug = {
  id: string; name: string; generic_name?: string; drug_class?: string;
  mechanism?: string; indications?: string[]; contraindications?: string[];
  adverse_effects?: Record<string, string[]>; dosing?: Record<string, string>;
  is_high_yield?: boolean; is_nti?: boolean; is_veterinary?: boolean; image_url?: string;
};

type BrowseResult = { items: Drug[]; total: number; page: number; pages: number; limit: number };
type Tab = "browse" | "interactions" | "dose" | "vet";

function DrugCard({ drug, lang }: { drug: Drug; lang: string }) {
  const [imgOk, setImgOk] = useState(true);
  return (
    <Link
      href={`/drugs/${drug.id}`}
      className="group flex flex-col bg-surface border border-border rounded-xl p-3 hover:border-ink hover:shadow-md transition-all"
    >
      <div className="h-20 w-full rounded-lg overflow-hidden bg-bg flex items-center justify-center mb-2.5 flex-shrink-0">
        {drug.image_url && imgOk ? (
          <img src={drug.image_url} alt={drug.name} className="w-full h-full object-contain p-1" loading="lazy" onError={() => setImgOk(false)} />
        ) : (
          <span className="text-3xl">💊</span>
        )}
      </div>
      <div className="font-syne font-bold text-xs text-ink leading-tight group-hover:text-accent line-clamp-2">{drug.name}</div>
      {drug.generic_name && drug.generic_name !== drug.name && (
        <div className="font-serif text-ink-3 text-xs mt-0.5 line-clamp-1">{drug.generic_name}</div>
      )}
      {drug.drug_class && (
        <div className="font-serif text-ink-3 text-xs mt-1 line-clamp-1 leading-tight">{translateDrugClass(drug.drug_class, lang)}</div>
      )}
      <div className="flex gap-1 mt-1.5 flex-wrap">
        {drug.is_high_yield && <span className="px-1.5 py-0.5 rounded-full bg-amber-light text-amber font-syne font-bold text-xs">⭐ HY</span>}
        {drug.is_nti && <span className="px-1.5 py-0.5 rounded-full bg-red-light text-red font-syne font-bold text-xs">NTI</span>}
        {drug.is_veterinary && <span className="px-1.5 py-0.5 rounded-full bg-green-light text-green font-syne font-bold text-xs">🐾</span>}
      </div>
    </Link>
  );
}

const BROWSE_UI: Record<string, Record<string, string>> = {
  en: { search_placeholder: "Search by name, class, generic name…", all_classes: "All classes", no_results: "No results for", no_drugs: "No drugs found", adjust_filters: "Try adjusting filters", drugs: "drugs", page: "Page", of: "of", clear: "✕ Clear filters", high_yield: "⭐ High Yield", veterinary: "🐾 Veterinary" },
  ru: { search_placeholder: "Поиск по названию, классу, МНН…", all_classes: "Все классы", no_results: "Ничего не найдено по запросу", no_drugs: "Препараты не найдены", adjust_filters: "Попробуйте изменить фильтры", drugs: "препаратов", page: "Стр.", of: "из", clear: "✕ Сбросить", high_yield: "⭐ Высокий приоритет", veterinary: "🐾 Ветеринария" },
  ar: { search_placeholder: "البحث بالاسم أو الفئة…", all_classes: "جميع الفئات", no_results: "لا نتائج لـ", no_drugs: "لم يتم العثور على أدوية", adjust_filters: "حاول تعديل الفلاتر", drugs: "دواء", page: "صفحة", of: "من", clear: "✕ مسح", high_yield: "⭐ ذو أولوية", veterinary: "🐾 بيطري" },
  de: { search_placeholder: "Nach Name, Klasse, Wirkstoff suchen…", all_classes: "Alle Klassen", no_results: "Keine Ergebnisse für", no_drugs: "Keine Medikamente gefunden", adjust_filters: "Filter anpassen", drugs: "Medikamente", page: "Seite", of: "von", clear: "✕ Filter löschen", high_yield: "⭐ Hohe Priorität", veterinary: "🐾 Veterinär" },
  fr: { search_placeholder: "Rechercher par nom, classe, générique…", all_classes: "Toutes les classes", no_results: "Aucun résultat pour", no_drugs: "Aucun médicament trouvé", adjust_filters: "Ajuster les filtres", drugs: "médicaments", page: "Page", of: "sur", clear: "✕ Effacer", high_yield: "⭐ Haute priorité", veterinary: "🐾 Vétérinaire" },
  es: { search_placeholder: "Buscar por nombre, clase, genérico…", all_classes: "Todas las clases", no_results: "Sin resultados para", no_drugs: "No se encontraron medicamentos", adjust_filters: "Ajustar filtros", drugs: "medicamentos", page: "Pág.", of: "de", clear: "✕ Limpiar", high_yield: "⭐ Alta prioridad", veterinary: "🐾 Veterinaria" },
  tr: { search_placeholder: "Ad, sınıf, jenerik ile ara…", all_classes: "Tüm sınıflar", no_results: "Sonuç yok:", no_drugs: "İlaç bulunamadı", adjust_filters: "Filtreleri ayarlayın", drugs: "ilaç", page: "Sayfa", of: "/ toplam", clear: "✕ Temizle", high_yield: "⭐ Yüksek öncelik", veterinary: "🐾 Veteriner" },
};

function BrowseTab({ initial, classes, lang }: { initial: BrowseResult; classes: { drug_class: string; count: number }[]; lang: string }) {
  const [result, setResult]       = useState<BrowseResult>(initial);
  const [page, setPage]           = useState(1);
  const [search, setSearch]       = useState("");
  const [searchResults, setSearchResults] = useState<Drug[]>([]);
  const [selectedClass, setSelectedClass] = useState("");
  const [filterVet, setFilterVet] = useState<boolean | undefined>();
  const [filterHY, setFilterHY]   = useState<boolean | undefined>();
  const [loading, setLoading]     = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout>>();
  const ui = BROWSE_UI[lang] ?? BROWSE_UI.en;

  const loadBrowse = useCallback(async (p = 1) => {
    setLoading(true);
    try {
      const data = await drugsApi.browse(p, 24, selectedClass || undefined, filterVet, filterHY, lang);
      setResult(data); setPage(p);
    } catch { /* keep current */ }
    finally { setLoading(false); }
  }, [selectedClass, filterVet, filterHY, lang]);

  useEffect(() => {
    if (!search) loadBrowse(1);
  }, [loadBrowse, search]);

  useEffect(() => {
    clearTimeout(timer.current);
    if (!search.trim()) { setSearchResults([]); return; }
    timer.current = setTimeout(async () => {
      setLoading(true);
      try { const d = await drugsApi.search(search, lang); setSearchResults(d ?? []); }
      catch { setSearchResults([]); }
      finally { setLoading(false); }
    }, 350);
  }, [search, lang]);

  const displayDrugs = search.trim() ? searchResults : result?.items ?? [];
  const isSearch = !!search.trim();

  return (
    <div>
      <div className="flex flex-col sm:flex-row gap-3 mb-5">
        <div className="relative flex-1">
          <input type="text" value={search} onChange={e => setSearch(e.target.value)}
            placeholder={ui.search_placeholder}
            className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-border bg-surface text-ink font-serif text-sm focus:outline-none focus:border-ink transition-colors" />
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-3 pointer-events-none">🔍</span>
          {search && (
            <button onClick={() => setSearch("")} className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-3 hover:text-ink text-lg leading-none">×</button>
          )}
        </div>
        <select value={selectedClass} onChange={e => { setSelectedClass(e.target.value); setPage(1); }}
          className="px-3 py-2.5 rounded-xl border border-border bg-surface text-ink font-serif text-sm focus:outline-none focus:border-ink min-w-[180px]">
          <option value="">{ui.all_classes}</option>
          {classes.slice(0, 20).map(c => <option key={c.drug_class} value={c.drug_class}>{translateDrugClass(c.drug_class, lang)} ({c.count})</option>)}
        </select>
      </div>

      <div className="flex gap-2 mb-5 flex-wrap">
        <button onClick={() => { setFilterHY(filterHY ? undefined : true); setPage(1); }}
          className={`px-3 py-1 rounded-full font-syne font-semibold text-xs border transition-all ${filterHY ? "bg-amber-light border-amber text-amber" : "border-border text-ink-3 hover:border-ink-3"}`}>
          {ui.high_yield}
        </button>
        <button onClick={() => { setFilterVet(filterVet ? undefined : true); setPage(1); }}
          className={`px-3 py-1 rounded-full font-syne font-semibold text-xs border transition-all ${filterVet ? "bg-green-light border-green text-green" : "border-border text-ink-3 hover:border-ink-3"}`}>
          {ui.veterinary}
        </button>
        {(selectedClass || filterHY || filterVet) && (
          <button onClick={() => { setSelectedClass(""); setFilterHY(undefined); setFilterVet(undefined); setPage(1); }}
            className="px-3 py-1 rounded-full font-syne font-semibold text-xs border border-red/30 text-red hover:bg-red-light transition-all">
            {ui.clear}
          </button>
        )}
        {!isSearch && result && (
          <span className="ml-auto font-serif text-ink-3 text-xs self-center">{result.total} {ui.drugs}</span>
        )}
      </div>

      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
          {Array.from({ length: 24 }).map((_, i) => (
            <div key={i} className="bg-surface border border-border rounded-xl p-3 animate-pulse">
              <div className="h-20 bg-bg rounded-lg mb-3" />
              <div className="h-3 bg-bg rounded mb-1.5 w-3/4" />
              <div className="h-2.5 bg-bg rounded w-1/2" />
            </div>
          ))}
        </div>
      ) : displayDrugs.length === 0 ? (
        <div className="text-center py-16">
          <div className="text-4xl mb-3">💊</div>
          <p className="font-syne font-bold text-ink text-sm">{isSearch ? `${ui.no_results} "${search}"` : ui.no_drugs}</p>
          <p className="font-serif text-ink-3 text-xs mt-1">{ui.adjust_filters}</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-3">
          {displayDrugs.map(drug => <DrugCard key={drug.id} drug={drug} lang={lang} />)}
        </div>
      )}

      {!isSearch && result && result.pages > 1 && (
        <div className="flex items-center justify-center gap-2 mt-8">
          <button onClick={() => loadBrowse(page - 1)} disabled={page <= 1 || loading}
            className="px-3 py-1.5 rounded-lg border border-border font-syne font-semibold text-sm text-ink-2 hover:border-ink disabled:opacity-40 transition-all">←</button>
          {Array.from({ length: Math.min(result.pages, 7) }, (_, i) => {
            let p: number;
            if (result.pages <= 7) p = i + 1;
            else if (page <= 4) p = i + 1;
            else if (page >= result.pages - 3) p = result.pages - 6 + i;
            else p = page - 3 + i;
            return (
              <button key={p} onClick={() => loadBrowse(p)} disabled={loading}
                className={`w-8 h-8 rounded-lg font-syne font-semibold text-sm transition-all ${p === page ? "bg-ink text-white" : "border border-border text-ink-2 hover:border-ink disabled:opacity-40"}`}>
                {p}
              </button>
            );
          })}
          <button onClick={() => loadBrowse(page + 1)} disabled={page >= result.pages || loading}
            className="px-3 py-1.5 rounded-lg border border-border font-syne font-semibold text-sm text-ink-2 hover:border-ink disabled:opacity-40 transition-all">→</button>
          <span className="font-serif text-ink-3 text-xs ml-2">{ui.page} {page} {ui.of} {result.pages}</span>
        </div>
      )}
    </div>
  );
}

function DoseCalculator() {
  const [form, setForm] = useState({ drug_name: "", weight_kg: "", age_years: "", renal_gfr: "", dose_per_kg: "", unit: "mg", max_dose: "" });
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const set = (key: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setForm(p => ({ ...p, [key]: e.target.value }));

  const calculate = async (e: React.FormEvent) => {
    e.preventDefault(); setLoading(true); setError(""); setResult(null);
    try {
      const res = await drugsApi.calculateDose({ drug_name: form.drug_name, weight_kg: parseFloat(form.weight_kg), age_years: form.age_years ? parseFloat(form.age_years) : undefined, renal_gfr: form.renal_gfr ? parseFloat(form.renal_gfr) : undefined, dose_per_kg: form.dose_per_kg ? parseFloat(form.dose_per_kg) : undefined, unit: form.unit, max_dose: form.max_dose ? parseFloat(form.max_dose) : undefined } as any);
      setResult(res);
    } catch (err: any) { setError(err.response?.data?.detail ?? "Calculation failed"); }
    finally { setLoading(false); }
  };

  return (
    <div className="max-w-lg">
      <form onSubmit={calculate} className="bg-surface border border-border rounded-xl p-6 space-y-4">
        <h2 className="font-syne font-bold text-base text-ink">Dose Calculator</h2>
        <div><label className="block font-syne font-semibold text-xs text-ink-2 mb-1">Drug name *</label><input required type="text" value={form.drug_name} onChange={set("drug_name")} placeholder="e.g. Amoxicillin" className="w-full border border-border rounded-lg px-3 py-2 text-sm font-serif bg-bg text-ink focus:outline-none focus:border-ink" /></div>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="block font-syne font-semibold text-xs text-ink-2 mb-1">Weight (kg) *</label><input required type="number" min="0.5" max="300" step="0.1" value={form.weight_kg} onChange={set("weight_kg")} placeholder="70" className="w-full border border-border rounded-lg px-3 py-2 text-sm font-serif bg-bg text-ink focus:outline-none focus:border-ink" /></div>
          <div><label className="block font-syne font-semibold text-xs text-ink-2 mb-1">Age (years)</label><input type="number" min="0" max="120" value={form.age_years} onChange={set("age_years")} placeholder="optional" className="w-full border border-border rounded-lg px-3 py-2 text-sm font-serif bg-bg text-ink focus:outline-none focus:border-ink" /></div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="block font-syne font-semibold text-xs text-ink-2 mb-1">Dose per kg</label><input type="number" min="0" step="0.01" value={form.dose_per_kg} onChange={set("dose_per_kg")} placeholder="e.g. 25" className="w-full border border-border rounded-lg px-3 py-2 text-sm font-serif bg-bg text-ink focus:outline-none focus:border-ink" /></div>
          <div><label className="block font-syne font-semibold text-xs text-ink-2 mb-1">Unit</label><select value={form.unit} onChange={set("unit")} className="w-full border border-border rounded-lg px-3 py-2 text-sm font-serif bg-bg text-ink focus:outline-none focus:border-ink">{["mg","mcg","g","mg/kg","mcg/kg"].map(u => <option key={u} value={u}>{u}</option>)}</select></div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="block font-syne font-semibold text-xs text-ink-2 mb-1">Max single dose</label><input type="number" min="0" step="0.1" value={form.max_dose} onChange={set("max_dose")} placeholder="optional" className="w-full border border-border rounded-lg px-3 py-2 text-sm font-serif bg-bg text-ink focus:outline-none focus:border-ink" /></div>
          <div><label className="block font-syne font-semibold text-xs text-ink-2 mb-1">Renal GFR (mL/min)</label><input type="number" min="0" max="120" value={form.renal_gfr} onChange={set("renal_gfr")} placeholder="optional" className="w-full border border-border rounded-lg px-3 py-2 text-sm font-serif bg-bg text-ink focus:outline-none focus:border-ink" /></div>
        </div>
        {error && <p className="font-serif text-red text-xs">{error}</p>}
        <button type="submit" disabled={loading} className="w-full bg-ink text-white font-syne font-bold text-sm py-2.5 rounded-xl hover:bg-ink/80 transition-colors disabled:opacity-40">{loading ? "Calculating…" : "Calculate dose"}</button>
      </form>
      {result && (
        <div className="bg-surface border border-border rounded-xl p-5 mt-4">
          <h3 className="font-syne font-bold text-sm text-ink mb-3">Result — {result.drug_name}</h3>
          <div className="space-y-2">
            <div className="flex items-center justify-between py-1.5 border-b border-border">
              <span className="font-serif text-xs text-ink-3">Calculated dose</span>
              <span className="font-syne font-bold text-base text-ink">{result.calculated_dose} {result.unit}</span>
            </div>
            {result.renal_adjustment && result.renal_adjustment !== "none" && (
              <div className="flex items-center justify-between py-1.5 border-b border-border">
                <span className="font-serif text-xs text-ink-3">Renal adjustment</span>
                <span className="font-syne font-bold text-sm text-amber">{result.renal_adjustment}</span>
              </div>
            )}
          </div>
          <p className="font-serif text-ink-3 text-xs mt-3">⚕️ Educational estimate only.</p>
        </div>
      )}
    </div>
  );
}

const TAB_LABELS: Record<string, string[]> = {
  en: ["💊 Browse", "⚡ Interactions", "⚖️ Dose Calc", "🐾 Veterinary"],
  ru: ["💊 Препараты", "⚡ Взаимодействия", "⚖️ Дозировка", "🐾 Ветеринария"],
  ar: ["💊 تصفح", "⚡ التفاعلات", "⚖️ جرعة", "🐾 بيطري"],
  de: ["💊 Suchen", "⚡ Wechselwirkungen", "⚖️ Dosierung", "🐾 Veterinär"],
  fr: ["💊 Parcourir", "⚡ Interactions", "⚖️ Posologie", "🐾 Vétérinaire"],
  es: ["💊 Explorar", "⚡ Interacciones", "⚖️ Dosis", "🐾 Veterinaria"],
  tr: ["💊 Gözat", "⚡ Etkileşimler", "⚖️ Doz Hesapla", "🐾 Veteriner"],
};

export function DrugBrowserClient({
  initial,
  classes,
  initialLang = "en",
}: {
  initial: BrowseResult;
  classes: { drug_class: string; count: number }[];
  initialLang?: string;
}) {
  const [tab, setTab] = useState<Tab>("browse");
  const { locale } = useI18n();
  // Use initialLang (from server cookie) until useI18n hydrates to the real locale.
  // locale starts as "en" on SSR — we only switch once it differs from the default.
  const [lang, setLang] = useState(initialLang || "en");
  useEffect(() => { if (locale) setLang(locale); }, [locale]);
  const tabLabels = TAB_LABELS[lang] ?? TAB_LABELS.en;

  const tabs: { key: Tab; label: string }[] = [
    { key: "browse",       label: tabLabels[0] },
    { key: "interactions", label: tabLabels[1] },
    { key: "dose",         label: tabLabels[2] },
    { key: "vet",          label: tabLabels[3] },
  ];

  return (
    <>
      <div className="flex gap-1 mb-6 bg-surface border border-border p-1 rounded-xl w-fit flex-wrap">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-4 py-1.5 rounded-lg font-syne font-semibold text-sm transition-all ${tab === t.key ? "bg-ink text-white shadow" : "text-ink-3 hover:text-ink"}`}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === "browse"       && <BrowseTab initial={initial} classes={classes} lang={lang} />}
      {tab === "interactions" && <InteractionChecker />}
      {tab === "dose"         && <DoseCalculator />}
      {tab === "vet"          && <VetDosing />}
    </>
  );
}

function VetDosing() {
  const [species, setSpecies] = useState<any[]>([]);
  const [selectedSpecies, setSelectedSpecies] = useState("");
  const [drugQuery, setDrugQuery] = useState("");
  const [drugResults, setDrugResults] = useState<Drug[]>([]);
  const [selectedDrug, setSelectedDrug] = useState<Drug | null>(null);
  const [dosing, setDosing] = useState<any[]>([]);
  const [safety, setSafety] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [showSugg, setShowSugg] = useState(false);

  useEffect(() => {
    import("@/lib/api").then(({ veterinaryApi }) =>
      veterinaryApi.getSpecies().then((s: any) => setSpecies(s ?? [])).catch(() => {})
    );
  }, []);

  useEffect(() => {
    if (!drugQuery.trim()) { setDrugResults([]); return; }
    const t = setTimeout(async () => {
      try { const res = await drugsApi.search(drugQuery, "en"); setDrugResults((res ?? []).slice(0, 6)); setShowSugg(true); }
      catch { setDrugResults([]); }
    }, 300);
    return () => clearTimeout(t);
  }, [drugQuery]);

  const selectDrug = async (drug: Drug) => {
    setSelectedDrug(drug); setDrugQuery(drug.name); setShowSugg(false);
    if (selectedSpecies) {
      setLoading(true);
      try {
        const { veterinaryApi } = await import("@/lib/api");
        const [d, s] = await Promise.all([
          veterinaryApi.getDrugDosing(drug.id, selectedSpecies).catch(() => []),
          veterinaryApi.checkSafety(drug.id, selectedSpecies).catch(() => null),
        ]);
        setDosing(d ?? []); setSafety(s);
      } finally { setLoading(false); }
    }
  };

  return (
    <div className="space-y-5 max-w-2xl">
      <div className="bg-surface border border-border rounded-xl p-5">
        <h2 className="font-syne font-bold text-sm text-ink mb-4">Veterinary Drug Dosing</h2>
        <label className="block font-syne font-semibold text-xs text-ink-2 mb-2">Species</label>
        <div className="flex flex-wrap gap-2 mb-4">
          {species.length > 0 ? species.map((s: any) => (
            <button key={s.id} onClick={() => setSelectedSpecies(s.id)}
              className={`px-3 py-1.5 rounded-lg border font-syne font-semibold text-xs transition-all ${selectedSpecies === s.id ? "border-ink bg-ink text-white" : "border-border text-ink-2 hover:border-ink-3"}`}>
              {s.icon && <span className="mr-1">{s.icon}</span>}{s.name}
            </button>
          )) : ["🐕 Dog", "🐈 Cat", "🐎 Horse", "🐄 Cattle"].map(s => (
            <span key={s} className="px-3 py-1.5 rounded-lg border border-border font-syne font-semibold text-xs text-ink-3">{s}</span>
          ))}
        </div>
        <div className="relative">
          <input type="text" value={drugQuery} onChange={e => { setDrugQuery(e.target.value); setSelectedDrug(null); }} onFocus={() => setShowSugg(true)}
            placeholder="Search drug…" className="w-full px-3 py-2 rounded-lg border border-border bg-bg text-ink font-serif text-sm focus:outline-none focus:border-ink" />
          {showSugg && drugResults.length > 0 && (
            <div className="absolute top-full left-0 right-0 z-10 bg-surface border border-border rounded-xl shadow-lg mt-1">
              {drugResults.map(d => (
                <button key={d.id} onClick={() => selectDrug(d)}
                  className="w-full text-left px-3 py-2 font-serif text-sm text-ink hover:bg-bg transition-colors first:rounded-t-xl last:rounded-b-xl">
                  <span className="font-syne font-semibold">{d.name}</span>
                  <span className="text-ink-3 ml-2 text-xs">{d.drug_class}</span>{/* VetDosing always searches in EN, class shown as-is */}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
      {safety && (
        <div className={`rounded-xl p-4 border flex gap-3 ${safety.is_toxic ? "border-red/30 bg-red-light" : "border-green/20 bg-green-light"}`}>
          <span className="text-xl">{safety.is_toxic ? "⚠️" : "✅"}</span>
          <div>
            <div className={`font-syne font-bold text-sm ${safety.is_toxic ? "text-red" : "text-green"}`}>{safety.is_toxic ? "Caution: Potential toxicity" : "Generally safe"}</div>
            {safety.toxicity_note && <div className="font-serif text-xs mt-0.5 text-ink-2">{safety.toxicity_note}</div>}
          </div>
        </div>
      )}
      {loading && <div className="text-center py-6 font-serif text-ink-3 text-sm">Loading dosing data…</div>}
      {!loading && dosing.length > 0 && (
        <div className="bg-surface border border-border rounded-xl p-5">
          <h3 className="font-syne font-bold text-sm text-ink mb-3">Dosing: {selectedDrug?.name}</h3>
          <div className="space-y-3">
            {dosing.map((d: any, i: number) => (
              <div key={i} className="p-3 rounded-lg bg-bg space-y-1">
                <div className="flex items-center gap-3 flex-wrap">
                  {d.route && <span className="px-2 py-0.5 rounded bg-ink text-white font-syne font-bold text-xs">{d.route}</span>}
                  {d.dose && <span className="font-syne font-bold text-sm text-ink">{d.dose}</span>}
                  {d.frequency && <span className="font-serif text-ink-3 text-xs">{d.frequency}</span>}
                </div>
                {d.notes && <div className="font-serif text-xs text-ink-3 italic">{d.notes}</div>}
              </div>
            ))}
          </div>
        </div>
      )}
      <p className="font-serif text-ink-3 text-xs text-center">🐾 For educational use only.</p>
    </div>
  );
}
