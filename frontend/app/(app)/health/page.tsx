"use client";

import { useEffect, useState, useCallback } from "react";
import { healthProfileApi } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────
interface HealthProfile {
  birth_year: number | null;
  sex: string | null;
  conditions: string[];
  medications: string[];
  allergies: string[];
  health_log: Array<{ date: string; complaint: string; category: string; symptoms: string[] }>;
  checkin_log: Array<{ date: string; mood: string }>;
  trackers: Record<string, Array<{ date: string; value: string }>>;
  telegram_chat_id: string | null;
  disease_configs: Array<{
    key: string;
    label: { en: string; ru: string };
    icon: string;
    metrics: string[];
    targets: Record<string, { min?: number; max?: number; unit: string; label: string }>;
    article_tags: string[];
    calculators: string[];
  }>;
  updated_at: string | null;
  created_at: string | null;
}

interface Disease {
  key: string;
  label: { en: string; ru: string };
  icon: string;
}

const TRACKER_UNITS: Record<string, string> = {
  glucose: "mmol/L", hba1c: "%", bp: "mmHg", pulse: "bpm",
  weight: "kg", temp: "°C", spo2: "%", cholesterol: "mmol/L",
};

const TRACKER_LABELS: Record<string, string> = {
  glucose: "Glucose", hba1c: "HbA1c", bp: "Blood Pressure", pulse: "Pulse",
  weight: "Weight", temp: "Temperature", spo2: "SpO₂", cholesterol: "Cholesterol",
};

const TRACKER_ICONS: Record<string, string> = {
  glucose: "🩸", hba1c: "🔬", bp: "❤️", pulse: "💓",
  weight: "⚖️", temp: "🌡️", spo2: "🫁", cholesterol: "📊",
};

const MOOD_EMOJI: Record<string, string> = {
  good: "🟢", ok: "🟡", bad: "🔴", symptoms: "🤒",
};

// ── Metric Add Modal ──────────────────────────────────────────
function AddMetricModal({
  metric, unit, onSave, onClose,
}: {
  metric: string; unit: string; onSave: (v: string, n: string) => void; onClose: () => void;
}) {
  const [value, setValue] = useState("");
  const [note, setNote] = useState("");
  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
      <div className="bg-surface rounded-2xl p-6 w-full max-w-sm shadow-2xl">
        <h3 className="font-syne font-bold text-lg text-ink mb-4">
          Add {TRACKER_LABELS[metric] || metric}
        </h3>
        <div className="mb-3">
          <label className="text-xs text-ink-3 font-syne mb-1 block">
            Value ({unit})
          </label>
          <input
            className="w-full border border-border rounded-lg px-3 py-2 text-ink bg-bg font-mono text-lg"
            placeholder={metric === "bp" ? "120/80" : "0.0"}
            value={value}
            onChange={e => setValue(e.target.value)}
            autoFocus
          />
        </div>
        <div className="mb-5">
          <label className="text-xs text-ink-3 font-syne mb-1 block">Note (optional)</label>
          <input
            className="w-full border border-border rounded-lg px-3 py-2 text-ink bg-bg"
            placeholder="After meal, morning, etc."
            value={note}
            onChange={e => setNote(e.target.value)}
          />
        </div>
        <div className="flex gap-3">
          <button
            className="flex-1 btn-secondary py-2 rounded-lg text-sm"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            className="flex-1 bg-amber text-white py-2 rounded-lg text-sm font-syne font-bold hover:bg-amber-2 transition-colors"
            onClick={() => { if (value.trim()) { onSave(value.trim(), note.trim()); onClose(); } }}
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Condition Card ────────────────────────────────────────────
function DiseaseCard({
  config, trackers, onAddMetric,
}: {
  config: HealthProfile["disease_configs"][0];
  trackers: Record<string, Array<{ date: string; value: string }>>;
  onAddMetric: (metric: string) => void;
}) {
  return (
    <div className="card p-4 mb-3">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-2xl">{config.icon}</span>
        <h3 className="font-syne font-bold text-ink">{config.label.en}</h3>
      </div>

      {config.metrics.length > 0 && (
        <div className="grid grid-cols-2 gap-2 mb-3">
          {config.metrics.map(metric => {
            const history = trackers[metric] || [];
            const latest = history[history.length - 1];
            const target = config.targets[metric];
            return (
              <button
                key={metric}
                onClick={() => onAddMetric(metric)}
                className="bg-bg-2 rounded-xl p-3 text-left hover:bg-amber-light transition-colors group"
              >
                <div className="text-xs text-ink-3 font-syne mb-1">{TRACKER_LABELS[metric] || metric}</div>
                {latest ? (
                  <div className="font-mono font-bold text-ink text-sm">
                    {latest.value}{" "}
                    <span className="text-ink-3 font-normal text-xs">{TRACKER_UNITS[metric]}</span>
                  </div>
                ) : (
                  <div className="text-xs text-amber group-hover:text-amber-2">+ Add reading</div>
                )}
                {target && latest && (
                  <div className="text-xs mt-1">
                    {target.max && parseFloat(latest.value) > target.max
                      ? <span className="text-red">↑ Above target</span>
                      : target.min && parseFloat(latest.value) < target.min
                      ? <span className="text-red">↓ Below target</span>
                      : <span className="text-green">✓ On target</span>}
                  </div>
                )}
                {!latest && (
                  <div className="text-xs text-ink-3 mt-1">{TRACKER_UNITS[metric]}</div>
                )}
              </button>
            );
          })}
        </div>
      )}

      {(config.calculators.length > 0 || config.article_tags.length > 0) && (
        <div className="flex flex-wrap gap-2">
          {config.calculators.slice(0, 2).map(slug => (
            <a
              key={slug}
              href="/calculators"
              className="text-xs bg-amber-light text-amber px-2 py-1 rounded-full font-syne hover:bg-amber hover:text-white transition-colors"
            >
              🧮 {slug.toUpperCase()}
            </a>
          ))}
          {config.article_tags.slice(0, 1).map(tag => (
            <a
              key={tag}
              href={`/articles?search=${encodeURIComponent(tag)}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs bg-bg-2 text-ink-3 px-2 py-1 rounded-full font-syne hover:bg-amber-light transition-colors"
            >
              📖 Articles
            </a>
          ))}
          <a
            href="/knowledge"
            className="text-xs bg-bg-2 text-ink-3 px-2 py-1 rounded-full font-syne hover:bg-amber-light transition-colors"
          >
            📚 More reading
          </a>
        </div>
      )}
    </div>
  );
}

// ── Add Condition Panel ───────────────────────────────────────
function AddConditionPanel({
  allDiseases, activeConditions, onAdd, onClose,
}: {
  allDiseases: Disease[];
  activeConditions: string[];
  onAdd: (key: string) => void;
  onClose: () => void;
}) {
  const available = allDiseases.filter(d => !activeConditions.includes(d.key));
  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end justify-center">
      <div className="bg-surface rounded-t-3xl p-6 w-full max-w-lg max-h-[70vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-syne font-bold text-lg text-ink">Add Condition</h3>
          <button onClick={onClose} className="text-ink-3 hover:text-ink text-xl">✕</button>
        </div>
        <div className="space-y-2">
          {available.map(d => (
            <button
              key={d.key}
              onClick={() => { onAdd(d.key); onClose(); }}
              className="w-full flex items-center gap-3 p-3 rounded-xl bg-bg-2 hover:bg-amber-light text-left transition-colors"
            >
              <span className="text-xl">{d.icon}</span>
              <span className="font-syne text-ink">{d.label.en}</span>
            </button>
          ))}
          {available.length === 0 && (
            <p className="text-ink-3 text-sm text-center py-4">All conditions already added</p>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Profile Edit Panel ────────────────────────────────────────
function ProfileEditPanel({
  profile, onSave, onClose,
}: {
  profile: HealthProfile;
  onSave: (data: { birth_year?: number; sex?: string; medications: string[]; allergies: string[] }) => void;
  onClose: () => void;
}) {
  const currentYear = new Date().getFullYear();
  const [birthYear, setBirthYear] = useState(profile.birth_year?.toString() || "");
  const [sex, setSex] = useState(profile.sex || "");
  const [medications, setMedications] = useState(profile.medications.join(", "));
  const [allergies, setAllergies] = useState(profile.allergies.join(", "));

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-end justify-center">
      <div className="bg-surface rounded-t-3xl p-6 w-full max-w-lg">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-syne font-bold text-lg text-ink">Edit Profile</h3>
          <button onClick={onClose} className="text-ink-3 hover:text-ink text-xl">✕</button>
        </div>
        <div className="space-y-4">
          <div>
            <label className="text-xs text-ink-3 font-syne mb-1 block">Birth year</label>
            <input
              type="number"
              className="input w-full"
              placeholder={`e.g. ${currentYear - 30}`}
              value={birthYear}
              onChange={e => setBirthYear(e.target.value)}
            />
          </div>
          <div>
            <label className="text-xs text-ink-3 font-syne mb-1 block">Sex</label>
            <div className="flex gap-2">
              {["male", "female", "other"].map(s => (
                <button
                  key={s}
                  onClick={() => setSex(s)}
                  className={`flex-1 py-2 rounded-lg text-sm font-syne capitalize transition-colors ${
                    sex === s ? "bg-amber text-white" : "bg-bg-2 text-ink hover:bg-amber-light"
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="text-xs text-ink-3 font-syne mb-1 block">
              Medications <span className="text-ink-3">(comma-separated)</span>
            </label>
            <textarea
              className="input w-full text-sm"
              rows={2}
              placeholder="Metformin 500mg, Lisinopril 10mg"
              value={medications}
              onChange={e => setMedications(e.target.value)}
            />
          </div>
          <div>
            <label className="text-xs text-ink-3 font-syne mb-1 block">
              Allergies <span className="text-ink-3">(comma-separated)</span>
            </label>
            <textarea
              className="input w-full text-sm"
              rows={2}
              placeholder="Penicillin, Ibuprofen"
              value={allergies}
              onChange={e => setAllergies(e.target.value)}
            />
          </div>
        </div>
        <div className="flex gap-3 mt-5">
          <button className="flex-1 btn-secondary py-2 rounded-lg text-sm" onClick={onClose}>
            Cancel
          </button>
          <button
            className="flex-1 bg-amber text-white py-2 rounded-lg text-sm font-syne font-bold hover:bg-amber-2 transition-colors"
            onClick={() => {
              onSave({
                birth_year: birthYear ? parseInt(birthYear) : undefined,
                sex: sex || undefined,
                medications: medications.split(",").map(s => s.trim()).filter(Boolean),
                allergies: allergies.split(",").map(s => s.trim()).filter(Boolean),
              });
              onClose();
            }}
          >
            Save
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────
export default function HealthHubPage() {
  const [profile, setProfile] = useState<HealthProfile | null>(null);
  const [allDiseases, setAllDiseases] = useState<Disease[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeMetric, setActiveMetric] = useState<string | null>(null);
  const [showAddCondition, setShowAddCondition] = useState(false);
  const [showEditProfile, setShowEditProfile] = useState(false);
  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");

  const load = useCallback(async () => {
    try {
      const [p, d] = await Promise.all([
        healthProfileApi.get(),
        healthProfileApi.getDiseases(),
      ]);
      setProfile(p);
      setAllDiseases(d);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const showSuccess = (msg: string) => {
    setSuccessMsg(msg);
    setTimeout(() => setSuccessMsg(""), 3000);
  };

  const handleSaveMetric = async (metric: string, value: string, note: string) => {
    try {
      await healthProfileApi.addMetric(metric, value, note || undefined);
      showSuccess(`${TRACKER_LABELS[metric] || metric}: ${value} ${TRACKER_UNITS[metric] || ""} saved`);
      await load();
    } catch (e) {
      console.error(e);
    }
  };

  const handleAddCondition = async (conditionKey: string) => {
    if (!profile) return;
    setSaving(true);
    try {
      const updated = await healthProfileApi.update({
        conditions: [...profile.conditions, conditionKey],
        medications: profile.medications,
        allergies: profile.allergies,
        birth_year: profile.birth_year ?? undefined,
        sex: profile.sex ?? undefined,
      });
      setProfile(updated);
      showSuccess("Condition added");
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  const handleRemoveCondition = async (conditionKey: string) => {
    if (!profile) return;
    setSaving(true);
    try {
      const updated = await healthProfileApi.update({
        conditions: profile.conditions.filter(c => c !== conditionKey),
        medications: profile.medications,
        allergies: profile.allergies,
        birth_year: profile.birth_year ?? undefined,
        sex: profile.sex ?? undefined,
      });
      setProfile(updated);
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  const handleSaveProfile = async (data: {
    birth_year?: number;
    sex?: string;
    medications: string[];
    allergies: string[];
  }) => {
    if (!profile) return;
    setSaving(true);
    try {
      const updated = await healthProfileApi.update({
        conditions: profile.conditions,
        medications: data.medications,
        allergies: data.allergies,
        birth_year: data.birth_year,
        sex: data.sex,
      });
      setProfile(updated);
      showSuccess("Profile saved");
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex-1 overflow-y-auto flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin w-8 h-8 border-2 border-amber border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!profile) return null;

  const currentYear = new Date().getFullYear();
  const age = profile.birth_year ? currentYear - profile.birth_year : null;
  const recentCheckins = [...(profile.checkin_log || [])].reverse().slice(0, 7);
  const recentLog = [...(profile.health_log || [])].reverse().slice(0, 5);

  return (
    <div className="flex-1 overflow-y-auto p-3 sm:p-6">
      {/* Success Toast */}
      {successMsg && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 z-50 bg-green text-white px-4 py-2 rounded-xl text-sm font-syne shadow-lg">
          ✓ {successMsg}
        </div>
      )}

      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div>
            <h1 className="font-syne font-black text-2xl text-ink">Health Hub</h1>
            <p className="text-ink-3 text-sm mt-0.5 font-serif">Your personal health dashboard</p>
          </div>
          <button
            onClick={() => setShowEditProfile(true)}
            className="btn-secondary px-3 py-2 rounded-lg text-sm"
          >
            ✏️ Edit
          </button>
        </div>

        {/* Demographics Card */}
        <div className="card p-4 mb-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-amber-light flex items-center justify-center text-2xl shrink-0">
              {profile.sex === "female" ? "👩" : profile.sex === "male" ? "👨" : "👤"}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                {age && (
                  <span className="text-sm font-syne text-ink font-bold">{age} years</span>
                )}
                {profile.sex && (
                  <span className="text-sm text-ink-3 capitalize">{profile.sex}</span>
                )}
                {profile.telegram_chat_id && (
                  <span className="text-xs bg-blue-light text-blue px-2 py-0.5 rounded-full font-syne">
                    📱 Telegram linked
                  </span>
                )}
              </div>
              {profile.medications.length > 0 && (
                <p className="text-xs text-ink-3 mt-1 truncate">
                  💊 {profile.medications.slice(0, 3).join(", ")}
                  {profile.medications.length > 3 && ` +${profile.medications.length - 3} more`}
                </p>
              )}
              {profile.allergies.length > 0 && (
                <p className="text-xs text-red mt-0.5 truncate">
                  ⚠️ {profile.allergies.join(", ")}
                </p>
              )}
              {!age && !profile.sex && !profile.medications.length && (
                <button
                  onClick={() => setShowEditProfile(true)}
                  className="text-xs text-amber hover:text-amber-2 font-syne mt-1"
                >
                  + Add your demographics →
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Medical Disclaimer */}
        <div className="bg-amber-light border border-amber/30 rounded-xl px-3 py-2 mb-5 text-xs text-amber font-syne">
          ⚕️ For informational purposes only. Always consult a qualified healthcare professional.
        </div>

        {/* Active Conditions */}
        <div className="mb-5">
          <h2 className="font-syne font-bold text-ink text-base mb-3">My Conditions</h2>

          {profile.disease_configs.length === 0 && (
            <div className="card p-5 text-center mb-3">
              <p className="text-ink-3 text-sm mb-2">No conditions added yet</p>
              <p className="text-xs text-ink-3">
                Add a chronic condition to get personalized metrics, targets, and article recommendations
              </p>
            </div>
          )}

          {profile.disease_configs.map(config => (
            <div key={config.key} className="relative">
              <DiseaseCard
                config={config}
                trackers={profile.trackers || {}}
                onAddMetric={setActiveMetric}
              />
              <button
                onClick={() => handleRemoveCondition(config.key)}
                className="absolute top-3 right-3 text-ink-3 hover:text-red text-xs transition-colors p-1"
                title="Remove condition"
              >
                ✕
              </button>
            </div>
          ))}

          <button
            onClick={() => setShowAddCondition(true)}
            disabled={saving}
            className="w-full border-2 border-dashed border-border-2 rounded-xl p-3 text-sm text-ink-3 font-syne hover:border-amber hover:text-amber transition-colors"
          >
            + Add condition
          </button>
        </div>

        {/* Quick Metric Log */}
        <div className="card p-4 mb-5">
          <h2 className="font-syne font-bold text-ink text-base mb-3">Quick Log</h2>
          <div className="grid grid-cols-4 gap-2">
            {Object.keys(TRACKER_LABELS).map(metric => {
              const history = profile.trackers?.[metric] || [];
              const latest = history[history.length - 1];
              return (
                <button
                  key={metric}
                  onClick={() => setActiveMetric(metric)}
                  className="bg-bg-2 rounded-xl p-2 text-center hover:bg-amber-light transition-colors group"
                >
                  <div className="text-lg mb-1">{TRACKER_ICONS[metric]}</div>
                  <div className="text-xs text-ink-3 font-syne group-hover:text-amber leading-tight">
                    {TRACKER_LABELS[metric]}
                  </div>
                  {latest && (
                    <div className="text-xs font-mono text-ink mt-0.5">{latest.value}</div>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Mood timeline */}
        {recentCheckins.length > 0 && (
          <div className="card p-4 mb-5">
            <h2 className="font-syne font-bold text-ink text-base mb-3">Recent Mood</h2>
            <div className="flex gap-2 justify-between">
              {recentCheckins.map((ci, i) => (
                <div key={i} className="flex flex-col items-center gap-1">
                  <span className="text-xl">{MOOD_EMOJI[ci.mood] || "⚪"}</span>
                  <span className="text-xs text-ink-3 font-syne">{ci.date?.slice(5)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Health log */}
        {recentLog.length > 0 && (
          <div className="card p-4 mb-5">
            <h2 className="font-syne font-bold text-ink text-base mb-3">Symptom History</h2>
            <div className="space-y-0">
              {recentLog.map((entry, i) => (
                <div
                  key={i}
                  className="flex items-start gap-3 py-2.5 border-b border-border last:border-0"
                >
                  <span className="text-xs text-ink-3 font-syne w-14 shrink-0 mt-0.5 tabular-nums">
                    {entry.date?.slice(5)}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-ink truncate">{entry.complaint}</p>
                    {entry.symptoms?.length > 0 && (
                      <p className="text-xs text-ink-3 mt-0.5">
                        {entry.symptoms.slice(0, 3).join(", ")}
                      </p>
                    )}
                  </div>
                  <span className="text-xs bg-bg-2 text-ink-3 px-2 py-0.5 rounded-full font-syne shrink-0">
                    {entry.category}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Telegram CTA */}
        {!profile.telegram_chat_id && (
          <div className="card p-4 mb-4 border-blue/20 bg-blue-light">
            <div className="flex items-center gap-3">
              <span className="text-3xl">📱</span>
              <div className="flex-1 min-w-0">
                <h3 className="font-syne font-bold text-ink text-sm">Connect Telegram</h3>
                <p className="text-xs text-ink-3 mt-0.5">
                  Chat with MedMind bot and your health data syncs here automatically
                </p>
              </div>
              <a
                href="/link-telegram"
                className="bg-blue text-white text-xs px-3 py-1.5 rounded-lg font-syne hover:bg-blue-2 transition-colors shrink-0"
              >
                Link
              </a>
            </div>
          </div>
        )}

        {/* AI Tutor link */}
        <div className="card p-4 mb-4 bg-bg-2 border-border-2">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-syne font-bold text-sm text-ink">Have questions about your health?</p>
              <p className="text-xs text-ink-3 mt-0.5">Ask our AI assistant — it knows your profile</p>
            </div>
            <a
              href="/ai-tutor"
              className="btn-secondary text-xs px-3 py-1.5 rounded-lg shrink-0"
            >
              Ask AI →
            </a>
          </div>
        </div>
      </div>

      {/* Modals */}
      {activeMetric && (
        <AddMetricModal
          metric={activeMetric}
          unit={TRACKER_UNITS[activeMetric] || ""}
          onSave={(v, n) => handleSaveMetric(activeMetric, v, n)}
          onClose={() => setActiveMetric(null)}
        />
      )}
      {showAddCondition && (
        <AddConditionPanel
          allDiseases={allDiseases}
          activeConditions={profile.conditions}
          onAdd={handleAddCondition}
          onClose={() => setShowAddCondition(false)}
        />
      )}
      {showEditProfile && (
        <ProfileEditPanel
          profile={profile}
          onSave={handleSaveProfile}
          onClose={() => setShowEditProfile(false)}
        />
      )}
    </div>
  );
}
