"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { drugsApi, veterinaryApi } from "@/lib/api";
import { useT } from "@/lib/i18n";

const LANG_FLAGS: Record<string, string> = {
  en: "🇺🇸", ru: "🇷🇺", ar: "🇸🇦", de: "🇩🇪", fr: "🇫🇷", es: "🇪🇸", tr: "🇹🇷",
};
const LANG_NAMES: Record<string, string> = {
  en: "English", ru: "Русский", ar: "العربية", de: "Deutsch", fr: "Français", es: "Español", tr: "Türkçe",
};

type Drug = {
  id: string;
  name: string;
  generic_name?: string;
  drug_class?: string;
  mechanism?: string;
  indications?: string[];
  contraindications?: string[];
  adverse_effects?: Record<string, any>;
  dosing?: Record<string, any>;
  monitoring?: string[];
  black_box_warning?: string;
  interactions?: string[];
  is_high_yield?: boolean;
  is_nti?: boolean;
  is_veterinary?: boolean;
  image_url?: string;
  available_langs?: string[];
};

type Alternative = {
  id: string;
  name: string;
  generic_name?: string;
  drug_class?: string;
  is_high_yield?: boolean;
  reason: string;
  image_url?: string;
};

type Tab = "overview" | "dosing" | "adverse" | "vet";

export default function DrugDetailPage() {
  const t = useT();
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const lang = searchParams.get("lang") || "en";

  const [drug, setDrug] = useState<Drug | null>(null);
  const [alternatives, setAlternatives] = useState<Alternative[]>([]);
  const [tab, setTab] = useState<Tab>("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [allSpecies, setAllSpecies] = useState<any[]>([]);

  useEffect(() => {
    veterinaryApi.getSpecies().then((s: any) => setAllSpecies(s ?? [])).catch(() => {});
  }, []);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setError("");

    Promise.all([
      drugsApi.get(id, lang),
      drugsApi.getAlternatives(id).catch(() => ({ alternatives: [] })),
    ])
      .then(([drugData, altData]) => {
        setDrug(drugData);
        setAlternatives(altData?.alternatives ?? []);
      })
      .catch((e) => {
        const detail = e?.response?.data?.detail;
        setError(detail || "Failed to load drug");
      })
      .finally(() => setLoading(false));
  }, [id, lang]);

  if (loading) {
    return (
      <div className="flex-1 p-6 max-w-4xl mx-auto w-full">
        <div className="animate-pulse space-y-4">
          <div className="h-4 w-24 bg-bg-2 rounded" />
          <div className="h-8 w-64 bg-bg-2 rounded" />
          <div className="h-4 w-40 bg-bg-2 rounded" />
          <div className="card p-6 space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-3 bg-bg-2 rounded" style={{ width: `${70 + i * 5}%` }} />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error || !drug) {
    return (
      <div className="flex-1 p-6 max-w-4xl mx-auto w-full">
        <button onClick={() => router.back()} className="font-syne text-xs text-ink-3 hover:text-ink mb-4">
          ← Drug Database
        </button>
        <div className="card p-10 text-center">
          <div className="text-4xl mb-4">💊</div>
          <p className="font-syne font-bold text-sm text-ink mb-1">{error || "Drug not found"}</p>
          <p className="font-serif text-ink-3 text-xs">Try searching from the drug database.</p>
          <button onClick={() => router.push("/drugs")} className="btn-primary mt-4 text-sm">
            Browse Drugs
          </button>
        </div>
      </div>
    );
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: "overview", label: "Overview" },
    { key: "dosing", label: "Dosing" },
    { key: "adverse", label: "Side Effects" },
    { key: "vet", label: "🐾 Vet Dosing" },
  ];

  const availableLangs = ["en", ...(drug.available_langs || [])];
  const SITE_URL = "https://medmind.pro";

  return (
    <div className="flex-1 overflow-y-auto p-4 sm:p-6 max-w-4xl mx-auto w-full">
      {/* hreflang links for SEO */}
      {availableLangs.length > 1 && (
        <head>
          <link rel="canonical" href={`${SITE_URL}/drugs/${id}${lang !== "en" ? `?lang=${lang}` : ""}`} />
          {availableLangs.map((l) => (
            <link key={l} rel="alternate" hrefLang={l} href={`${SITE_URL}/drugs/${id}${l !== "en" ? `?lang=${l}` : ""}`} />
          ))}
          <link rel="alternate" hrefLang="x-default" href={`${SITE_URL}/drugs/${id}`} />
        </head>
      )}

      {/* Back */}
      <button onClick={() => router.back()} className="font-syne text-xs text-ink-3 hover:text-ink mb-5 flex items-center gap-1">
        ← Drug Database
      </button>

      {/* Header */}
      <div className="flex items-start gap-4 mb-4 flex-wrap sm:flex-nowrap">
        {/* Drug image from DB (pre-fetched from Wikipedia) */}
        {drug.image_url ? (
          <div className="w-24 h-24 sm:w-32 sm:h-32 rounded-xl border border-border bg-white overflow-hidden flex-shrink-0">
            <img
              src={drug.image_url}
              alt={drug.name}
              className="w-full h-full object-contain p-1"
            />
          </div>
        ) : (
          <div className="w-24 h-24 sm:w-32 sm:h-32 rounded-xl border border-border bg-bg-2 flex items-center justify-center flex-shrink-0">
            <span className="text-4xl">💊</span>
          </div>
        )}

        <div className="flex-1 min-w-0">
          <h1 className="font-syne font-black text-xl sm:text-2xl text-ink leading-tight">{drug.name}</h1>
          {drug.generic_name && drug.generic_name !== drug.name && (
            <p className="font-serif text-ink-3 text-sm mt-0.5">{drug.generic_name}</p>
          )}
          {drug.drug_class && (
            <p className="font-serif text-ink-3 text-xs mt-1">{drug.drug_class}</p>
          )}

          {/* Badges */}
          <div className="flex gap-2 flex-wrap mt-2">
            {drug.is_high_yield && <Badge color="amber">⭐ High Yield</Badge>}
            {drug.is_nti && <Badge color="red">⚠ NTI Drug</Badge>}
            {drug.is_veterinary && <Badge color="green">🐾 Veterinary</Badge>}
          </div>
        </div>
      </div>

      {/* Language switcher */}
      {availableLangs.length > 1 && (
        <div className="flex items-center gap-2 mb-4 flex-wrap">
          <span className="font-syne font-semibold text-xs text-ink-3">Language:</span>
          {availableLangs.map((l) => (
            <button
              key={l}
              onClick={() => router.push(`/drugs/${id}${l !== "en" ? `?lang=${l}` : ""}`)}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-full font-syne font-semibold text-xs border transition-all ${
                l === lang
                  ? "bg-ink text-white border-ink"
                  : "border-border text-ink-2 hover:border-ink"
              }`}
            >
              <span>{LANG_FLAGS[l] || "🌐"}</span>
              <span>{LANG_NAMES[l] || l.toUpperCase()}</span>
            </button>
          ))}
        </div>
      )}

      {/* Black Box Warning */}
      {drug.black_box_warning && (
        <div className="mb-5 p-4 rounded-lg border border-red/40 bg-red-light flex gap-3">
          <span className="text-red text-lg flex-shrink-0">⬛</span>
          <div>
            <div className="font-syne font-bold text-xs text-red uppercase mb-1">Black Box Warning</div>
            <p className="font-serif text-sm text-ink leading-relaxed">{drug.black_box_warning}</p>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-bg-2 p-1 rounded-lg overflow-x-auto">
        {tabs.map((tabItem) => (
          <button
            key={tabItem.key}
            onClick={() => setTab(tabItem.key)}
            className={`px-3 py-1.5 rounded font-syne font-semibold text-xs transition-all whitespace-nowrap ${
              tab === tabItem.key ? "bg-white shadow text-ink" : "text-ink-3 hover:text-ink"
            }`}
          >
            {tabItem.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {tab === "overview" && <OverviewTab drug={drug} />}
      {tab === "dosing" && <DosingTab drug={drug} />}
      {tab === "adverse" && <AdverseTab drug={drug} />}
      {tab === "vet" && <VetDosingTab drug={drug} allSpecies={allSpecies} />}

      {/* ── Related Drugs Section (always visible at bottom) ───────────────── */}
      {alternatives.length > 0 && (
        <div className="mt-10">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-syne font-bold text-base text-ink">
              Similar Drugs — Same Class
            </h2>
            <span className="font-serif text-ink-3 text-xs">{alternatives.length} found</span>
          </div>

          {/* Horizontal scroll grid — same as articles related section */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {alternatives.map((alt) => (
              <RelatedDrugCard
                key={alt.id}
                drug={alt}
                onClick={() => router.push(`/drugs/${alt.id}`)}
              />
            ))}
          </div>

          <p className="font-serif text-ink-3 text-xs text-center mt-4">
            Same pharmacological class or related mechanism of action
          </p>
        </div>
      )}

      <div className="h-8" />
    </div>
  );
}

// ── Related Drug Card ─────────────────────────────────────────────────────────

function RelatedDrugCard({ drug, onClick }: { drug: Alternative; onClick: () => void }) {
  const [imgSrc, setImgSrc] = useState<string | null>(drug.image_url || null);
  const [tried, setTried] = useState(false);

  useEffect(() => {
    if (!imgSrc && !tried) {
      setTried(true);
      drugsApi.fetchRxImage(drug.generic_name || drug.name).then((url) => {
        if (url) setImgSrc(url);
      }).catch(() => {});
    }
  }, [drug.name, drug.generic_name, imgSrc, tried]);

  return (
    <div
      onClick={onClick}
      className="card p-3 cursor-pointer hover:border-ink transition-all hover:shadow-md group"
    >
      {/* Image */}
      <div className="h-16 w-full rounded-lg overflow-hidden bg-bg-2 flex items-center justify-center mb-2">
        {imgSrc ? (
          <img
            src={imgSrc}
            alt={drug.name}
            className="w-full h-full object-contain p-1"
            onError={() => setImgSrc(null)}
          />
        ) : (
          <span className="text-2xl">💊</span>
        )}
      </div>

      <div className="font-syne font-bold text-xs text-ink leading-tight line-clamp-2 group-hover:text-ink">
        {drug.name}
      </div>
      {drug.generic_name && drug.generic_name !== drug.name && (
        <div className="font-serif text-ink-3 text-xs mt-0.5 line-clamp-1">{drug.generic_name}</div>
      )}
      <div className="flex items-center justify-between mt-1.5">
        <span className="font-serif text-ink-3 text-xs">{drug.reason}</span>
        {drug.is_high_yield && (
          <span className="px-1.5 py-0.5 rounded-full bg-amber-light text-amber font-syne font-bold text-xs">⭐</span>
        )}
      </div>
    </div>
  );
}

// ── Overview Tab ──────────────────────────────────────────────────────────────

function OverviewTab({ drug }: { drug: Drug }) {
  return (
    <div className="space-y-5">
      {drug.mechanism && (
        <Section title="Mechanism of Action">
          <p className="font-serif text-sm text-ink leading-relaxed">{drug.mechanism}</p>
        </Section>
      )}

      {drug.indications && drug.indications.length > 0 && (
        <Section title="Indications">
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
        <Section title="Contraindications">
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
        <Section title="Drug Interactions">
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
        <div className="card p-8 text-center">
          <p className="font-serif text-ink-3 text-sm">Detailed information not yet available for this drug.</p>
        </div>
      )}
    </div>
  );
}

// ── Dosing Tab ────────────────────────────────────────────────────────────────

function DosingTab({ drug }: { drug: Drug }) {
  const hasDosingData = drug.dosing && Object.keys(drug.dosing).length > 0;
  const hasMonitoring = drug.monitoring && drug.monitoring.length > 0;

  if (!hasDosingData && !hasMonitoring) {
    return (
      <div className="card p-8 text-center">
        <p className="font-serif text-ink-3 text-sm">No dosing information available.</p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {hasDosingData && (
        <Section title="Dosing">
          <div className="divide-y divide-border">
            {Object.entries(drug.dosing!).map(([route, dose]) => (
              <div key={route} className="py-2.5 flex gap-4 items-start">
                <span className="font-syne font-bold text-xs text-ink-2 uppercase w-24 flex-shrink-0 pt-0.5">{route}</span>
                <span className="font-serif text-sm text-ink">{dose as string}</span>
              </div>
            ))}
          </div>
        </Section>
      )}

      {hasMonitoring && (
        <Section title="Monitoring Parameters">
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
          ⚠ Narrow Therapeutic Index (NTI) drug — close monitoring and precise dosing required.
        </div>
      )}
    </div>
  );
}

// ── Adverse Effects Tab ───────────────────────────────────────────────────────

function AdverseTab({ drug }: { drug: Drug }) {
  if (!drug.adverse_effects || Object.keys(drug.adverse_effects).length === 0) {
    return (
      <div className="card p-8 text-center">
        <p className="font-serif text-ink-3 text-sm">No adverse effects data available.</p>
      </div>
    );
  }

  const severityOrder = ["common", "serious", "rare", "life-threatening"];
  const entries = Object.entries(drug.adverse_effects);
  entries.sort(([a], [b]) => {
    const ai = severityOrder.findIndex((s) => a.toLowerCase().includes(s));
    const bi = severityOrder.findIndex((s) => b.toLowerCase().includes(s));
    return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
  });

  const categoryColor: Record<string, string> = {
    common: "text-amber", serious: "text-red", "life-threatening": "text-red", rare: "text-ink-3",
  };

  return (
    <div className="space-y-4">
      {entries.map(([category, effects]) => {
        const colorKey = Object.keys(categoryColor).find((k) => category.toLowerCase().includes(k));
        const color = colorKey ? categoryColor[colorKey] : "text-ink-2";
        return (
          <div key={category} className="card p-4">
            <div className={`font-syne font-bold text-xs uppercase mb-2 ${color}`}>{category}</div>
            <div className="flex flex-wrap gap-1.5">
              {(effects as string[]).map((effect, i) => (
                <span key={i} className="inline-block px-2 py-0.5 rounded-full bg-bg-2 font-serif text-xs text-ink">{effect}</span>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Vet Dosing Tab ────────────────────────────────────────────────────────────

const FALLBACK_SPECIES = [
  { id: "canine", name: "Canine", icon: "🐕" },
  { id: "feline", name: "Feline", icon: "🐈" },
  { id: "equine", name: "Equine", icon: "🐎" },
  { id: "bovine", name: "Bovine", icon: "🐄" },
  { id: "avian",  name: "Avian",  icon: "🦜" },
  { id: "rabbit", name: "Rabbit", icon: "🐇" },
];

function VetDosingTab({ drug, allSpecies }: { drug: Drug; allSpecies: any[] }) {
  const speciesList = allSpecies.length > 0 ? allSpecies : FALLBACK_SPECIES;
  const [selectedSpecies, setSelectedSpecies] = useState<any | null>(null);
  const [dbDosing, setDbDosing] = useState<any[]>([]);
  const [safety, setSafety] = useState<any>(null);
  const [scaledDosing, setScaledDosing] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const selectSpecies = async (sp: any) => {
    setSelectedSpecies(sp);
    setDbDosing([]); setSafety(null); setScaledDosing(null);
    setLoading(true);
    const isUUID = sp.id?.includes("-");
    const nameToKey: Record<string, string> = { canine: "canine", feline: "feline", equine: "equine", bovine: "bovine", avian: "avian", rabbit: "exotic", exotic: "exotic" };
    const speciesKey = nameToKey[sp.name?.toLowerCase()] ?? sp.name?.toLowerCase();
    const [dosingRes, safetyRes, scaledRes] = await Promise.all([
      isUUID ? veterinaryApi.getDrugDosing(drug.id, sp.id).catch(() => []) : Promise.resolve([]),
      isUUID ? veterinaryApi.checkSafety(drug.id, sp.id).catch(() => null) : Promise.resolve(null),
      speciesKey ? veterinaryApi.getScaledDosing(drug.name, speciesKey).catch(() => null) : Promise.resolve(null),
    ]);
    setDbDosing(dosingRes ?? []); setSafety(safetyRes); setScaledDosing(scaledRes);
    setLoading(false);
  };

  return (
    <div className="space-y-5">
      <Section title="Select Species">
        <div className="flex flex-wrap gap-2">
          {speciesList.map((sp: any) => (
            <button key={sp.id} onClick={() => selectSpecies(sp)}
              className={`px-3 py-2 rounded-lg border font-syne font-semibold text-xs transition-all ${selectedSpecies?.id === sp.id ? "border-ink bg-ink text-white" : "border-border text-ink-2 hover:border-ink-3"}`}>
              {sp.icon && <span className="mr-1">{sp.icon}</span>}{sp.name}
            </button>
          ))}
        </div>
      </Section>

      {loading && <div className="text-center py-6 font-serif text-ink-3 text-sm">Loading…</div>}
      {!loading && selectedSpecies && (
        <>
          {safety && (
            <div className={`p-4 rounded-lg border flex gap-3 ${safety.is_toxic ? "bg-red-light border-red/30" : "bg-green-light border-green/20"}`}>
              <span className="text-xl">{safety.is_toxic ? "⚠️" : "✅"}</span>
              <div className={`font-syne font-bold text-sm ${safety.is_toxic ? "text-red" : "text-green"}`}>
                {safety.is_toxic ? `Caution: Risk for ${selectedSpecies.name}` : `Generally safe for ${selectedSpecies.name}`}
                {safety.toxicity_note && <div className="font-serif font-normal text-xs text-ink-2 mt-0.5">{safety.toxicity_note}</div>}
              </div>
            </div>
          )}

          {dbDosing.length > 0 && (
            <Section title={`Dosing — ${selectedSpecies.name}`}>
              <div className="space-y-3">
                {dbDosing.map((d: any, i: number) => (
                  <div key={i} className="p-3 rounded-lg bg-bg-2 space-y-1">
                    <div className="flex items-center gap-3 flex-wrap">
                      {d.route && <span className="px-2 py-0.5 rounded bg-ink text-white font-syne font-bold text-xs">{d.route}</span>}
                      {d.dose && !d.is_toxic && <span className="font-syne font-bold text-sm text-ink">{d.dose}</span>}
                      {d.frequency && !d.is_toxic && <span className="font-serif text-ink-3 text-xs">{d.frequency}</span>}
                    </div>
                    {d.max_dose && <div className="font-serif text-xs text-ink-2">Max: {d.max_dose}</div>}
                    {d.notes && <div className="font-serif text-xs text-ink-3 italic">{d.notes}</div>}
                  </div>
                ))}
              </div>
            </Section>
          )}

          {scaledDosing && scaledDosing.species_dosing && Object.keys(scaledDosing.species_dosing).length > 0 && (
            <Section title={`Estimated Dosing — ${selectedSpecies.name}`}>
              <div className="p-3 rounded-lg bg-amber-light border border-amber/20 mb-3 font-serif text-xs text-amber">
                ⚠ Scaled from human doses — verify with current veterinary formulary before clinical use.
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
            <div className="card p-6 text-center">
              <p className="font-serif text-ink-3 text-sm">No veterinary dosing data for {drug.name} in {selectedSpecies.name}.</p>
              <p className="font-serif text-ink-3 text-xs mt-1">Consult Plumb's Veterinary Drug Handbook.</p>
            </div>
          )}
        </>
      )}

      {!selectedSpecies && <div className="card p-6 text-center"><p className="font-serif text-ink-3 text-sm">Select a species above.</p></div>}
      <p className="font-serif text-ink-3 text-xs text-center">🐾 For educational use only.</p>
    </div>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card p-5">
      <div className="font-syne font-bold text-xs text-ink-2 uppercase mb-3">{title}</div>
      {children}
    </div>
  );
}

function Badge({ color, children }: { color: "amber" | "red" | "green"; children: React.ReactNode }) {
  const colors = { amber: "bg-amber-light text-amber", red: "bg-red-light text-red", green: "bg-green-light text-green" };
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full font-syne font-semibold text-xs ${colors[color]}`}>
      {children}
    </span>
  );
}
