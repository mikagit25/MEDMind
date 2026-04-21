"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { veterinaryApi, drugsApi, contentApi, authApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import Link from "next/link";

type Tab = "overview" | "dosing" | "toxicity" | "zoonoses" | "modules";

// Static species for fallback + dose calculator mapping
const SPECIES_LIST = [
  { key: "canine",  label: "Dog",    icon: "🐕", factor: "1.0×" },
  { key: "feline",  label: "Cat",    icon: "🐈", factor: "0.6×" },
  { key: "equine",  label: "Horse",  icon: "🐎", factor: "10×" },
  { key: "bovine",  label: "Cattle", icon: "🐄", factor: "12×" },
  { key: "porcine", label: "Pig",    icon: "🐖", factor: "1.2×" },
  { key: "avian",   label: "Bird",   icon: "🦜", factor: "0.05×" },
  { key: "exotic",  label: "Exotic", icon: "🦎", factor: "0.3×" },
];

export default function VeterinaryPage() {
  const [tab, setTab] = useState<Tab>("overview");
  const { user } = useAuthStore();
  const vetMode = (user?.preferences?.vet_mode as boolean) ?? false;

  const tabs: { key: Tab; label: string }[] = [
    { key: "overview",  label: "🐾 Overview" },
    { key: "dosing",    label: "⚖️ Dose Calc" },
    { key: "toxicity",  label: "⚠️ Toxicity" },
    { key: "zoonoses",  label: "🦠 Zoonoses" },
    { key: "modules",   label: "📚 Modules" },
  ];

  return (
    <div className="flex-1 overflow-y-auto p-6 max-w-4xl mx-auto w-full">
      <div className="flex items-start justify-between mb-4 flex-wrap gap-3">
        <div>
          <h1 className="font-syne font-black text-2xl text-ink">Veterinary Medicine</h1>
          <p className="font-serif text-ink-3 text-sm mt-0.5">
            Species-specific pharmacology, dosing, and clinical resources
          </p>
        </div>
        {!vetMode && (
          <Link
            href="/settings"
            className="text-xs font-syne font-semibold px-3 py-1.5 rounded-lg bg-green-light text-green border border-green/20 hover:bg-green/10 transition-colors"
          >
            Enable Vet Mode in Settings →
          </Link>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-bg-2 p-1 rounded-lg overflow-x-auto flex-nowrap">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-1.5 rounded font-syne font-semibold text-sm transition-all whitespace-nowrap ${
              tab === t.key ? "bg-white shadow text-ink" : "text-ink-3 hover:text-ink"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "overview"  && <OverviewTab setTab={setTab} />}
      {tab === "dosing"    && <DoseCalcTab />}
      {tab === "toxicity"  && <ToxicityTab />}
      {tab === "zoonoses"  && <ZoonosesTab />}
      {tab === "modules"   && <ModulesTab />}
    </div>
  );
}

// ── Overview ──────────────────────────────────────────────────────────────────

function OverviewTab({ setTab }: { setTab: (t: Tab) => void }) {
  // alias so quick-link buttons can switch tabs
  const setCurrentTab = setTab;
  return (
    <div className="space-y-5">
      {/* Quick links */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { icon: "⚖️", label: "Dose Calculator",  desc: "Weight-adjusted species dosing", tab: "dosing"   as Tab },
          { icon: "⚠️", label: "Toxicity Checker", desc: "Drug safety per species",         tab: "toxicity" as Tab },
          { icon: "🦠", label: "Zoonoses",          desc: "Diseases from animals",          tab: "zoonoses" as Tab },
          { icon: "📚", label: "Vet Modules",       desc: "Species-specific courses",       tab: "modules"  as Tab },
        ].map((item) => (
          <button
            key={item.tab}
            onClick={() => setCurrentTab(item.tab)}
            className="card p-4 text-left hover:border-ink transition-colors group"
          >
            <div className="text-2xl mb-2">{item.icon}</div>
            <div className="font-syne font-bold text-sm text-ink group-hover:text-ink">{item.label}</div>
            <div className="font-serif text-ink-3 text-xs mt-0.5">{item.desc}</div>
          </button>
        ))}
      </div>

      {/* Species cards */}
      <div className="card p-5">
        <h2 className="font-syne font-bold text-sm text-ink mb-4">Species Reference — Dose Scaling Factors</h2>
        <p className="font-serif text-ink-3 text-xs mb-4">
          Scaling factors vs adult human dose. Used only as initial estimate — always verify with formulary.
        </p>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {SPECIES_LIST.map((sp) => (
            <div key={sp.key} className="p-3 rounded-lg bg-bg-2 text-center">
              <div className="text-2xl mb-1">{sp.icon}</div>
              <div className="font-syne font-bold text-xs text-ink">{sp.label}</div>
              <div className="font-serif text-ink-3 text-xs mt-0.5">Factor: {sp.factor}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Key principles */}
      <div className="card p-5">
        <h2 className="font-syne font-bold text-sm text-ink mb-3">Key Principles of Veterinary Pharmacology</h2>
        <div className="space-y-3">
          {[
            {
              title: "Species differences in drug metabolism",
              body: "Cats lack glucuronyl transferase — many NSAIDs and paracetamol are toxic. Dogs lack certain CYP450 isoforms. Always check species compatibility before prescribing.",
            },
            {
              title: "Weight-based dosing is species-specific",
              body: "Unlike humans, metabolic rate in animals scales allometrically. Smaller animals need relatively higher mg/kg doses (birds ~0.05× of human dose/kg; horses ~10×).",
            },
            {
              title: "Route bioavailability varies widely",
              body: "Oral bioavailability in horses is very low for many antibiotics (e.g., amoxicillin). IV/IM routes are often preferred in large animals.",
            },
            {
              title: "Breed-specific genetics matter",
              body: "MDR1 (ABCB1) mutation in Collies and related breeds causes extreme sensitivity to ivermectin, loperamide, and other P-gp substrates.",
            },
          ].map((p, i) => (
            <div key={i} className="p-3 rounded-lg bg-bg-2">
              <div className="font-syne font-bold text-xs text-ink mb-1">{p.title}</div>
              <div className="font-serif text-xs text-ink-2 leading-relaxed">{p.body}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Dose Calculator ───────────────────────────────────────────────────────────

function DoseCalcTab() {
  const [drugQuery, setDrugQuery] = useState("");
  const [drugResults, setDrugResults] = useState<any[]>([]);
  const [selectedDrug, setSelectedDrug] = useState<any>(null);
  const [selectedSpecies, setSelectedSpecies] = useState<string>("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [showSugg, setShowSugg] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!drugQuery.trim()) { setDrugResults([]); return; }
    const t = setTimeout(async () => {
      const res = await drugsApi.search(drugQuery).catch(() => ({ data: [] }));
      setDrugResults((res.data ?? []).slice(0, 6));
      setShowSugg(true);
    }, 300);
    return () => clearTimeout(t);
  }, [drugQuery]);

  const calculate = async () => {
    if (!selectedDrug || !selectedSpecies) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const data = await veterinaryApi.getScaledDosing(selectedDrug.name, selectedSpecies);
      setResult(data);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "No dosing data found for this combination");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-5">
      <div className="card p-5 space-y-4">
        <h2 className="font-syne font-bold text-base text-ink">Species-Adjusted Dose Lookup</h2>
        <p className="font-serif text-ink-3 text-xs -mt-2">
          Scales human drug doses using species-specific pharmacokinetic factors
        </p>

        {/* Drug search */}
        <div>
          <label className="block font-syne font-semibold text-xs text-ink-2 mb-1">Drug</label>
          <div className="relative">
            <input
              type="text"
              value={drugQuery}
              onChange={(e) => { setDrugQuery(e.target.value); setSelectedDrug(null); setResult(null); }}
              onFocus={() => setShowSugg(true)}
              placeholder="Search drug name…"
              className="w-full px-3 py-2 rounded border border-border bg-surface text-ink font-serif text-sm focus:outline-none focus:border-ink"
            />
            {selectedDrug && (
              <span className="absolute right-3 top-2 text-green text-xs font-syne font-semibold">✓ {selectedDrug.name}</span>
            )}
            {showSugg && drugResults.length > 0 && !selectedDrug && (
              <div className="absolute top-full left-0 right-0 z-10 bg-surface border border-border rounded-lg shadow-lg mt-1">
                {drugResults.map((d: any) => (
                  <button
                    key={d.id}
                    onClick={() => { setSelectedDrug(d); setDrugQuery(d.name); setShowSugg(false); }}
                    className="w-full text-left px-3 py-2 font-serif text-sm text-ink hover:bg-bg-2 transition-colors first:rounded-t-lg last:rounded-b-lg"
                  >
                    <span className="font-syne font-semibold">{d.name}</span>
                    <span className="text-ink-3 ml-2 text-xs">{d.drug_class}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Species */}
        <div>
          <label className="block font-syne font-semibold text-xs text-ink-2 mb-2">Species</label>
          <div className="flex flex-wrap gap-2">
            {SPECIES_LIST.map((sp) => (
              <button
                key={sp.key}
                onClick={() => { setSelectedSpecies(sp.key); setResult(null); }}
                className={`px-3 py-1.5 rounded-lg border font-syne font-semibold text-xs transition-all ${
                  selectedSpecies === sp.key
                    ? "border-ink bg-ink text-white"
                    : "border-border text-ink-2 hover:border-ink-3"
                }`}
              >
                {sp.icon} {sp.label}
              </button>
            ))}
          </div>
        </div>

        {error && <p className="font-serif text-red text-xs">{error}</p>}

        <button
          onClick={calculate}
          disabled={!selectedDrug || !selectedSpecies || loading}
          className="btn-primary disabled:opacity-40"
        >
          {loading ? "Looking up…" : "Get Veterinary Dosing"}
        </button>
      </div>

      {/* Result */}
      {result && (
        <div className="card p-5">
          <h3 className="font-syne font-bold text-base text-ink mb-1">
            {result.drug_name} — {selectedSpecies.charAt(0).toUpperCase() + selectedSpecies.slice(1)}
          </h3>
          {result.note && (
            <p className="font-serif text-xs text-amber mb-4 p-2 rounded bg-amber-light">{result.note}</p>
          )}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {/* Human dosing */}
            {result.human_dosing && Object.keys(result.human_dosing).length > 0 && (
              <div>
                <div className="font-syne font-bold text-xs text-ink-2 uppercase mb-2">Human Dose (reference)</div>
                <div className="space-y-1">
                  {Object.entries(result.human_dosing).map(([route, info]: [string, any]) => (
                    <div key={route} className="flex gap-3 py-1">
                      <span className="font-syne font-bold text-xs text-ink-3 uppercase w-20 shrink-0">{route}</span>
                      <span className="font-serif text-xs text-ink-2">
                        {typeof info === "object" ? (info.dose ?? "-") : String(info)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Species dosing */}
            {result.species_dosing && Object.keys(result.species_dosing).length > 0 && (
              <div>
                <div className="font-syne font-bold text-xs text-ink uppercase mb-2">
                  {selectedSpecies.charAt(0).toUpperCase() + selectedSpecies.slice(1)} Estimate
                </div>
                <div className="space-y-1">
                  {Object.entries(result.species_dosing).map(([route, info]: [string, any]) => (
                    <div key={route} className="flex gap-3 py-1">
                      <span className="font-syne font-bold text-xs text-ink-3 uppercase w-20 shrink-0">{route}</span>
                      <span className="font-syne font-bold text-sm text-ink">
                        {typeof info === "object" ? (info.dose ?? "-") : String(info)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <p className="font-serif text-ink-3 text-xs text-center">
        ⚕️ Estimates only. Verify with current veterinary formulary (e.g. Plumb's) before clinical use.
      </p>
    </div>
  );
}

// ── Toxicity Checker ──────────────────────────────────────────────────────────

const TOXICITY_DB: Record<string, Record<string, { level: "fatal" | "toxic" | "caution"; note: string }>> = {
  "paracetamol / acetaminophen": {
    "Cat":   { level: "fatal",  note: "FATAL — causes methaemoglobinaemia and acute hepatic necrosis. Absolutely contraindicated." },
    "Dog":   { level: "toxic",  note: "Toxic in overdose (hepatotoxicity). Use only under strict supervision." },
  },
  "ibuprofen": {
    "Cat":   { level: "fatal",  note: "Highly toxic: GI ulceration + acute renal failure. Contraindicated." },
    "Dog":   { level: "toxic",  note: "Toxic even at low doses: GI ulceration, renal failure. Contraindicated." },
  },
  "aspirin": {
    "Cat":   { level: "caution", note: "High risk — cats lack glucuronyl transferase. Only q72h maximum if absolutely needed." },
  },
  "xylitol": {
    "Dog":   { level: "fatal",  note: "FATAL — causes severe hypoglycaemia and acute liver failure even in small amounts." },
  },
  "permethrin": {
    "Cat":   { level: "fatal",  note: "FATAL — severe neurotoxicity from pyrethroid toxicosis. Never use dog flea products on cats." },
  },
  "ivermectin": {
    "Dog":   { level: "caution", note: "Toxic in Collie breeds and MDR1 (ABCB1)-mutant dogs. Safe for other breeds at standard doses." },
  },
  "enrofloxacin": {
    "Cat":   { level: "caution", note: "Doses >5 mg/kg can cause irreversible retinal degeneration and blindness." },
    "Dog":   { level: "caution", note: "Avoid in growing puppies (<12 months) — cartilage toxicity." },
  },
  "amoxicillin": {
    "Rabbit": { level: "fatal", note: "FATAL in rabbits and guinea pigs — disrupts GI flora, causing fatal enterotoxaemia." },
    "Hamster": { level: "fatal", note: "FATAL — same mechanism as rabbits." },
  },
  "metronidazole (high dose)": {
    "Bird":   { level: "caution", note: "Neurotoxicity at high doses. Use minimum effective dose." },
    "Dog":    { level: "caution", note: "Neurotoxicity (ataxia, vestibular signs) at high doses or prolonged use." },
  },
  "xylazine": {
    "Cattle": { level: "caution", note: "Cattle are extremely sensitive — require ~10× lower doses than horses." },
  },
};

function ToxicityTab() {
  const levelColors: Record<string, string> = {
    fatal:   "bg-red-light border-red/30 text-red",
    toxic:   "bg-red-light border-red/20 text-red",
    caution: "bg-amber-light border-amber/30 text-amber",
  };
  const levelLabels: Record<string, string> = {
    fatal: "FATAL", toxic: "TOXIC", caution: "CAUTION",
  };

  const [filter, setFilter] = useState<string>("all");

  const allSpecies = ["all", "Cat", "Dog", "Rabbit", "Bird", "Cattle", "Hamster"];

  const filtered = Object.entries(TOXICITY_DB).flatMap(([drug, speciesMap]) =>
    Object.entries(speciesMap)
      .filter(([species]) => filter === "all" || species === filter)
      .map(([species, info]) => ({ drug, species, ...info }))
  );

  return (
    <div className="space-y-4">
      {/* Filter */}
      <div className="flex gap-2 flex-wrap">
        {allSpecies.map((sp) => (
          <button
            key={sp}
            onClick={() => setFilter(sp)}
            className={`px-3 py-1 rounded-full font-syne font-semibold text-xs border transition-colors ${
              filter === sp ? "bg-ink text-white border-ink" : "border-border text-ink-2 hover:border-ink-3"
            }`}
          >
            {sp === "all" ? "All species" : sp}
          </button>
        ))}
      </div>

      <div className="space-y-3">
        {filtered.map((item, i) => (
          <div key={i} className={`p-4 rounded-lg border ${levelColors[item.level]}`}>
            <div className="flex items-start justify-between gap-2 mb-1">
              <div>
                <span className="font-syne font-bold text-sm capitalize">{item.drug}</span>
                <span className="font-serif text-xs ml-2">in {item.species}</span>
              </div>
              <span className={`px-2 py-0.5 rounded-full font-syne font-bold text-xs border ${levelColors[item.level]}`}>
                {levelLabels[item.level]}
              </span>
            </div>
            <p className="font-serif text-xs leading-relaxed">{item.note}</p>
          </div>
        ))}
        {filtered.length === 0 && (
          <div className="card p-6 text-center font-serif text-ink-3 text-sm">
            No toxicity data for selected species.
          </div>
        )}
      </div>

      <p className="font-serif text-ink-3 text-xs text-center mt-2">
        This is a curated educational list. Always check a current formulary for complete safety information.
      </p>
    </div>
  );
}

// ── Zoonoses ──────────────────────────────────────────────────────────────────

function ZoonosesTab() {
  const [zoonoses, setZoonoses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    veterinaryApi.getZoonoses()
      .then((d: any) => setZoonoses(d.zoonoses ?? []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-center py-10 font-serif text-ink-3 text-sm">Loading…</div>;

  return (
    <div className="space-y-4">
      <p className="font-serif text-ink-2 text-sm">
        Zoonotic diseases are infections transmissible between animals and humans.
        Understanding them is essential for both veterinary and human medicine.
      </p>
      <div className="grid gap-4">
        {zoonoses.map((z: any, i: number) => (
          <div key={i} className="card p-5">
            <div className="flex items-start justify-between gap-3 mb-3">
              <div>
                <h3 className="font-syne font-bold text-base text-ink">{z.name}</h3>
                {z.name_ru && <div className="font-serif text-ink-3 text-sm">{z.name_ru}</div>}
              </div>
              <span className="px-2 py-0.5 rounded-full bg-bg-2 border border-border font-syne font-semibold text-xs text-ink-3 shrink-0">
                {z.pathogen}
              </span>
            </div>
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
              <InfoBlock label="Transmission" value={z.transmission} />
              <InfoBlock label="Animal sources" value={z.species?.join(", ")} />
              <InfoBlock label="Prevention" value={z.prevention} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function InfoBlock({ label, value }: { label: string; value?: string }) {
  return (
    <div>
      <div className="font-syne font-bold text-xs text-ink-3 uppercase mb-1">{label}</div>
      <div className="font-serif text-xs text-ink-2 leading-relaxed">{value ?? "—"}</div>
    </div>
  );
}

// ── Veterinary Modules ────────────────────────────────────────────────────────

function ModulesTab() {
  const router = useRouter();
  const [specialties, setSpecialties] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    contentApi.getSpecialties(true)  // vet=true
      .then((data: any) => setSpecialties(data ?? []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-center py-10 font-serif text-ink-3 text-sm">Loading…</div>;

  if (specialties.length === 0) {
    return (
      <div className="card p-8 text-center">
        <div className="text-4xl mb-3">🐾</div>
        <p className="font-syne font-bold text-sm text-ink">No veterinary modules yet</p>
        <p className="font-serif text-ink-3 text-xs mt-1">
          Veterinary-specific modules will appear here as they are published.
        </p>
        <p className="font-serif text-ink-3 text-xs mt-3">
          In the meantime, use the{" "}
          <Link href="/simulation" className="underline">Clinical Simulation</Link>{" "}
          with veterinary patient types to practice.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {specialties.map((sp: any) => (
        <div key={sp.id} className="card p-4">
          <div
            className="flex items-center justify-between cursor-pointer"
            onClick={() => router.push(`/modules?specialty=${sp.id}`)}
          >
            <div>
              <div className="font-syne font-bold text-sm text-ink">{sp.name}</div>
              {sp.description && (
                <div className="font-serif text-ink-3 text-xs mt-0.5">{sp.description}</div>
              )}
            </div>
            <span className="text-ink-3 text-sm">→</span>
          </div>
        </div>
      ))}
    </div>
  );
}
