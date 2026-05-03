"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { drugsApi, veterinaryApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { useT } from "@/lib/i18n";

type Drug = {
  id: string;
  name: string;
  generic_name?: string;
  drug_class?: string;
  mechanism?: string;
  indications?: string[];
  contraindications?: string[];
  adverse_effects?: Record<string, string[]>;
  dosing?: Record<string, string>;
  monitoring?: string[];
  black_box_warning?: string;
  interactions?: string[];
  is_high_yield?: boolean;
  is_nti?: boolean;
  is_veterinary?: boolean;
};

type Alternative = {
  id: string;
  name: string;
  generic_name?: string;
  drug_class?: string;
  is_high_yield?: boolean;
  reason: string;
};

type Tab = "overview" | "dosing" | "adverse" | "alternatives" | "vet";

export default function DrugDetailPage() {
  const t = useT();
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { user } = useAuthStore();

  const [drug, setDrug] = useState<Drug | null>(null);
  const [alternatives, setAlternatives] = useState<Alternative[]>([]);
  const [images, setImages] = useState<string[]>([]);
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
    Promise.all([
      drugsApi.get(id),
      drugsApi.getAlternatives(id).catch(() => ({ alternatives: [] })),
    ])
      .then(([drugData, altData]) => {
        setDrug(drugData);
        setAlternatives(altData.alternatives ?? []);
        // Fetch images in background
        if (drugData.name) {
          drugsApi.fetchImages(drugData.name).then((imgRes: any) => {
            const urls = (imgRes?.replyList ?? [])
              .slice(0, 4)
              .map((r: any) => r.imageUrl)
              .filter(Boolean);
            setImages(urls);
          });
        }
      })
      .catch((e) => {
        setError(e?.response?.data?.detail ?? "Failed to load drug");
      })
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="font-serif text-ink-3 text-sm">{t("common.loading")}</p>
      </div>
    );
  }

  if (error || !drug) {
    return (
      <div className="flex-1 p-6 max-w-4xl mx-auto w-full">
        <button onClick={() => router.back()} className="font-syne text-xs text-ink-3 hover:text-ink mb-4">
          ← {t("common.back")}
        </button>
        <div className="card p-8 text-center">
          <div className="text-3xl mb-3">💊</div>
          <p className="font-syne font-bold text-sm text-ink">{error || "Drug not found"}</p>
          <p className="font-serif text-ink-3 text-xs mt-1">This drug may require a Pro subscription to view.</p>
        </div>
      </div>
    );
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: "overview", label: "Overview" },
    { key: "dosing", label: t("drugs.dosing") },
    { key: "adverse", label: t("drugs.side_effects") },
    { key: "alternatives", label: `Alternatives${alternatives.length ? ` (${alternatives.length})` : ""}` },
    { key: "vet", label: "🐾 Vet Dosing" },
  ];

  return (
    <div className="flex-1 overflow-y-auto p-6 max-w-4xl mx-auto w-full">
      {/* Back */}
      <button onClick={() => router.back()} className="font-syne text-xs text-ink-3 hover:text-ink mb-5 flex items-center gap-1">
        ← Drug Database
      </button>

      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-4 flex-wrap">
        <div>
          <h1 className="font-syne font-black text-2xl text-ink">{drug.name}</h1>
          {drug.generic_name && (
            <p className="font-serif text-ink-3 text-sm mt-0.5">{drug.generic_name}</p>
          )}
        </div>
        {images.length > 0 && (
          <div className="flex gap-2">
            {images.map((url, i) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                key={i}
                src={url}
                alt={drug.name}
                className="w-16 h-16 object-contain rounded-lg border border-border bg-white"
              />
            ))}
          </div>
        )}
      </div>

      {/* Badges */}
      <div className="flex gap-2 flex-wrap mb-6">
        {drug.drug_class && (
          <Badge color="blue">{drug.drug_class}</Badge>
        )}
        {drug.is_high_yield && <Badge color="amber">⭐ High Yield</Badge>}
        {drug.is_nti && <Badge color="red">⚠ NTI Drug</Badge>}
        {drug.is_veterinary && <Badge color="green">🐾 Veterinary</Badge>}
      </div>

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
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-3 py-1.5 rounded font-syne font-semibold text-xs transition-all whitespace-nowrap ${
              tab === t.key ? "bg-white shadow text-ink" : "text-ink-3 hover:text-ink"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {tab === "overview" && <OverviewTab drug={drug} />}
      {tab === "dosing" && <DosingTab drug={drug} />}
      {tab === "adverse" && <AdverseTab drug={drug} />}
      {tab === "alternatives" && <AlternativesTab alternatives={alternatives} currentId={drug.id} />}
      {tab === "vet" && <VetDosingTab drug={drug} allSpecies={allSpecies} />}
    </div>
  );
}

// ── Overview Tab ─────────────────────────────────────────────────────────────

function OverviewTab({ drug }: { drug: Drug }) {
  const t = useT();
  return (
    <div className="space-y-5">
      {drug.mechanism && (
        <Section title={t("drugs.mechanism")}>
          <p className="font-serif text-sm text-ink leading-relaxed">{drug.mechanism}</p>
        </Section>
      )}

      {drug.indications && drug.indications.length > 0 && (
        <Section title={t("drugs.indications")}>
          <ul className="space-y-1">
            {drug.indications.map((item, i) => (
              <li key={i} className="font-serif text-sm text-green flex gap-2">
                <span>✓</span><span>{item}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {drug.contraindications && drug.contraindications.length > 0 && (
        <Section title={t("drugs.contraindications")}>
          <ul className="space-y-1">
            {drug.contraindications.map((item, i) => (
              <li key={i} className="font-serif text-sm text-red flex gap-2">
                <span>✗</span><span>{item}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {drug.interactions && drug.interactions.length > 0 && (
        <Section title={t("drugs.interactions")}>
          <ul className="space-y-1">
            {drug.interactions.map((item, i) => (
              <li key={i} className="font-serif text-sm text-amber flex gap-2">
                <span>⚡</span><span>{item}</span>
              </li>
            ))}
          </ul>
        </Section>
      )}
    </div>
  );
}

// ── Dosing Tab ────────────────────────────────────────────────────────────────

function DosingTab({ drug }: { drug: Drug }) {
  const t = useT();
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
        <Section title={t("drugs.dosing")}>
          <div className="divide-y divide-border">
            {Object.entries(drug.dosing!).map(([route, dose]) => (
              <div key={route} className="py-2.5 flex gap-4 items-start">
                <span className="font-syne font-bold text-xs text-ink-2 uppercase w-24 flex-shrink-0 pt-0.5">
                  {route}
                </span>
                <span className="font-serif text-sm text-ink">{dose as string}</span>
              </div>
            ))}
          </div>
        </Section>
      )}

      {hasMonitoring && (
        <Section title={t("drugs.monitoring")}>
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
          ⚠ This is a Narrow Therapeutic Index (NTI) drug. Close monitoring and precise dosing are critical.
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
    common: "text-amber",
    serious: "text-red",
    "life-threatening": "text-red",
    rare: "text-ink-3",
  };

  return (
    <div className="space-y-4">
      {entries.map(([category, effects]) => {
        const colorKey = Object.keys(categoryColor).find((k) =>
          category.toLowerCase().includes(k)
        );
        const color = colorKey ? categoryColor[colorKey] : "text-ink-2";
        return (
          <div key={category} className="card p-4">
            <div className={`font-syne font-bold text-xs uppercase mb-2 ${color}`}>{category}</div>
            <div className="flex flex-wrap gap-1.5">
              {(effects as string[]).map((effect, i) => (
                <span
                  key={i}
                  className="inline-block px-2 py-0.5 rounded-full bg-bg-2 font-serif text-xs text-ink"
                >
                  {effect}
                </span>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Alternatives Tab ──────────────────────────────────────────────────────────

function AlternativesTab({ alternatives, currentId }: { alternatives: Alternative[]; currentId: string }) {
  const router = useRouter();

  if (alternatives.length === 0) {
    return (
      <div className="card p-8 text-center">
        <p className="font-serif text-ink-3 text-sm">No alternatives found for this drug class.</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="font-serif text-ink-3 text-xs">Drugs in the same or related class:</p>
      {alternatives.map((alt) => (
        <div
          key={alt.id}
          onClick={() => router.push(`/drugs/${alt.id}`)}
          className="card p-4 cursor-pointer hover:border-ink transition-colors"
        >
          <div className="flex items-start justify-between gap-2">
            <div>
              <div className="font-syne font-bold text-sm text-ink">{alt.name}</div>
              {alt.generic_name && (
                <div className="font-serif text-ink-3 text-xs mt-0.5">{alt.generic_name}</div>
              )}
              {alt.drug_class && (
                <div className="font-serif text-ink-3 text-xs">{alt.drug_class}</div>
              )}
            </div>
            <div className="flex flex-col items-end gap-1 flex-shrink-0">
              {alt.is_high_yield && (
                <span className="inline-block px-2 py-0.5 rounded-full bg-amber-light text-amber font-syne font-semibold text-xs">
                  ⭐ HY
                </span>
              )}
              <span className="font-serif text-ink-3 text-xs">{alt.reason}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Vet Dosing Tab ────────────────────────────────────────────────────────────

const FALLBACK_SPECIES = [
  { id: "canine",  name: "Canine",  icon: "🐕" },
  { id: "feline",  name: "Feline",  icon: "🐈" },
  { id: "equine",  name: "Equine",  icon: "🐎" },
  { id: "bovine",  name: "Bovine",  icon: "🐄" },
  { id: "porcine", name: "Porcine", icon: "🐖" },
  { id: "avian",   name: "Avian",   icon: "🦜" },
  { id: "rabbit",  name: "Rabbit",  icon: "🐇" },
  { id: "exotic",  name: "Exotic",  icon: "🦎" },
];

function VetDosingTab({ drug, allSpecies }: { drug: Drug; allSpecies: any[] }) {
  const t = useT();
  // Use DB species or fallback to static list for scaled dosing
  const speciesList = allSpecies.length > 0 ? allSpecies : FALLBACK_SPECIES;

  const [selectedSpecies, setSelectedSpecies] = useState<any | null>(null);
  const [dbDosing, setDbDosing] = useState<any[]>([]);
  const [safety, setSafety] = useState<any>(null);
  const [scaledDosing, setScaledDosing] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const selectSpecies = async (sp: any) => {
    setSelectedSpecies(sp);
    setDbDosing([]);
    setSafety(null);
    setScaledDosing(null);
    setLoading(true);

    // Map display name → species factor key
    const nameToKey: Record<string, string> = {
      canine: "canine", feline: "feline", equine: "equine",
      bovine: "bovine", porcine: "porcine", avian: "avian",
      rabbit: "exotic", exotic: "exotic",
    };
    const speciesKey = nameToKey[sp.name?.toLowerCase()] ?? sp.name?.toLowerCase();

    const promises: Promise<any>[] = [];

    // DB dosing (only if we have a real UUID species id, not a short key)
    const isUUID = sp.id && sp.id.includes("-");
    if (isUUID) {
      promises.push(
        veterinaryApi.getDrugDosing(drug.id, sp.id).catch(() => []),
        veterinaryApi.checkSafety(drug.id, sp.id).catch(() => null),
      );
    } else {
      promises.push(Promise.resolve([]), Promise.resolve(null));
    }

    // Scaled dosing always available
    if (speciesKey) {
      promises.push(
        veterinaryApi.getScaledDosing(drug.name, speciesKey).catch(() => null),
      );
    } else {
      promises.push(Promise.resolve(null));
    }

    const [dosingRes, safetyRes, scaledRes] = await Promise.all(promises);
    setDbDosing(dosingRes ?? []);
    setSafety(safetyRes);
    setScaledDosing(scaledRes);
    setLoading(false);
  };

  return (
    <div className="space-y-5">
      {/* Species selector */}
      <Section title={t("simulation.select_species")}>
        <div className="flex flex-wrap gap-2">
          {speciesList.map((sp: any) => (
            <button
              key={sp.id}
              onClick={() => selectSpecies(sp)}
              className={`px-3 py-2 rounded-lg border font-syne font-semibold text-xs transition-all ${
                selectedSpecies?.id === sp.id
                  ? "border-ink bg-ink text-white"
                  : "border-border text-ink-2 hover:border-ink-3"
              }`}
            >
              {sp.icon && <span className="mr-1">{sp.icon}</span>}{sp.name}
            </button>
          ))}
        </div>
      </Section>

      {loading && <div className="text-center py-6 font-serif text-ink-3 text-sm">{t("common.loading")}</div>}

      {!loading && selectedSpecies && (
        <>
          {/* Safety Banner */}
          {safety && (
            <div className={`p-4 rounded-lg border flex gap-3 ${
              safety.is_toxic ? "bg-red-light border-red/30" : "bg-green-light border-green/20"
            }`}>
              <span className="text-xl flex-shrink-0">{safety.is_toxic ? "⚠️" : "✅"}</span>
              <div>
                <div className={`font-syne font-bold text-sm ${safety.is_toxic ? "text-red" : "text-green"}`}>
                  {safety.is_toxic ? `Caution: Risk for ${selectedSpecies.name}` : `Generally safe for ${selectedSpecies.name}`}
                </div>
                {safety.warnings?.map((w: string, i: number) => (
                  <div key={i} className="font-serif text-xs text-ink-2 mt-0.5">{w}</div>
                ))}
              </div>
            </div>
          )}

          {/* DB-specific dosing */}
          {dbDosing.length > 0 && (
            <Section title={`Verified Dosing — ${selectedSpecies.name}`}>
              <div className="space-y-3">
                {dbDosing.map((d: any, i: number) => (
                  <div key={i} className={`p-3 rounded-lg ${d.is_toxic ? "bg-red-light border border-red/30" : "bg-bg-2"}`}>
                    {d.is_toxic && (
                      <div className="font-syne font-bold text-xs text-red uppercase mb-1">⚠ Contraindicated</div>
                    )}
                    <div className="flex items-center gap-3 flex-wrap">
                      {d.route && <span className="px-2 py-0.5 rounded bg-ink text-white font-syne font-bold text-xs">{d.route}</span>}
                      {d.dose && !d.is_toxic && <span className="font-syne font-bold text-sm text-ink">{d.dose}</span>}
                      {d.frequency && !d.is_toxic && <span className="font-serif text-ink-3 text-xs">{d.frequency}</span>}
                    </div>
                    {d.max_dose && <div className="font-serif text-xs text-ink-2 mt-1">Max: {d.max_dose}</div>}
                    {d.toxicity_note && <div className="font-serif text-xs text-red mt-1">{d.toxicity_note}</div>}
                    {d.notes && <div className="font-serif text-xs text-ink-3 italic mt-1">{d.notes}</div>}
                    {d.source && <div className="font-serif text-xs text-ink-3 mt-1">📖 {d.source}</div>}
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Scaled dosing from human data */}
          {scaledDosing && (
            <Section title={`Scaled Dosing Estimate — ${selectedSpecies.name}`}>
              <div className="p-3 rounded-lg bg-amber-light border border-amber/20 mb-3">
                <p className="font-serif text-xs text-amber">
                  ⚠ Estimated by scaling human doses. Always verify with current veterinary formulary before clinical use.
                </p>
              </div>
              {scaledDosing.note && (
                <p className="font-serif text-xs text-ink-3 mb-3">{scaledDosing.note}</p>
              )}
              {scaledDosing.species_dosing && Object.keys(scaledDosing.species_dosing).length > 0 ? (
                <div className="divide-y divide-border">
                  {Object.entries(scaledDosing.species_dosing).map(([route, info]: [string, any]) => (
                    <div key={route} className="py-2.5 flex gap-4 items-start">
                      <span className="font-syne font-bold text-xs text-ink-2 uppercase w-24 flex-shrink-0 pt-0.5">
                        {route}
                      </span>
                      <span className="font-serif text-sm text-ink">
                        {typeof info === "object" ? (info.dose ?? JSON.stringify(info)) : String(info)}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="font-serif text-xs text-ink-3">No scaled dosing data available for this drug.</p>
              )}
            </Section>
          )}

          {dbDosing.length === 0 && !scaledDosing && !loading && (
            <div className="card p-6 text-center">
              <p className="font-serif text-ink-3 text-sm">
                No veterinary dosing data available for {drug.name} in {selectedSpecies.name}.
              </p>
              <p className="font-serif text-ink-3 text-xs mt-1">
                Consult Plumb's Veterinary Drug Handbook or a specialist.
              </p>
            </div>
          )}
        </>
      )}

      {!selectedSpecies && !loading && (
        <div className="card p-6 text-center">
          <p className="font-serif text-ink-3 text-sm">Select a species above to see veterinary dosing information.</p>
        </div>
      )}

      <p className="font-serif text-ink-3 text-xs text-center">
        🐾 For educational use only. Always consult a licensed veterinarian for clinical dosing decisions.
      </p>
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

function Badge({ color, children }: { color: "blue" | "amber" | "red" | "green"; children: React.ReactNode }) {
  const colors = {
    blue: "bg-blue-light text-blue",
    amber: "bg-amber-light text-amber",
    red: "bg-red-light text-red",
    green: "bg-green-light text-green",
  };
  return (
    <span className={`inline-flex items-center px-2.5 py-1 rounded-full font-syne font-semibold text-xs ${colors[color]}`}>
      {children}
    </span>
  );
}
