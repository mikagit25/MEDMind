"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { authApi, aiApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

const ROLES = [
  { value: "student", label: "Medical Student", icon: "🎓", desc: "Studying medicine or pharmacy" },
  { value: "doctor", label: "Doctor / Clinician", icon: "🩺", desc: "Practicing medicine or surgery" },
  { value: "professor", label: "Professor / Educator", icon: "🏛️", desc: "Teaching or researching" },
  { value: "veterinarian", label: "Veterinarian", icon: "🐾", desc: "Animal medicine practice" },
];

const GOALS = [
  { value: "exam_prep", label: "Exam preparation", icon: "📝" },
  { value: "clinical_refresh", label: "Clinical knowledge refresh", icon: "🔄" },
  { value: "new_specialty", label: "Learn a new specialty", icon: "📚" },
  { value: "daily_learning", label: "Daily continuous learning", icon: "📅" },
];

const SPECIALTIES = [
  { code: "cardiology", label: "Cardiology", icon: "❤️" },
  { code: "neurology", label: "Neurology", icon: "🧠" },
  { code: "surgery", label: "Surgery", icon: "🔪" },
  { code: "obstetrics", label: "Obstetrics & Gynecology", icon: "👶" },
  { code: "pediatrics", label: "Pediatrics", icon: "🧒" },
  { code: "therapy", label: "Internal Medicine", icon: "💊" },
  { code: "pharmacology", label: "Pharmacology", icon: "⚗️" },
  { code: "pathology", label: "Pathology", icon: "🔬" },
  { code: "veterinary", label: "Veterinary Medicine", icon: "🐾" },
];

const TIME_OPTIONS = [
  { value: 10, label: "10 min", sub: "Quick daily refresh" },
  { value: 20, label: "20 min", sub: "Focused practice" },
  { value: 30, label: "30 min", sub: "Deep learning" },
  { value: 45, label: "45+ min", sub: "Intensive study" },
];

type Step = 1 | 2 | 3 | 4 | 5;

export default function OnboardingPage() {
  const router = useRouter();
  const { user, updateUser } = useAuthStore();
  const [step, setStep] = useState<Step>(1);
  const [data, setData] = useState({
    role: "",
    goal: "",
    specialties: [] as string[],
    daily_minutes: 20,
  });
  const [aiPlan, setAiPlan] = useState<string>("");
  const [planLoading, setPlanLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const toggleSpecialty = (code: string) =>
    setData((p) => ({
      ...p,
      specialties: p.specialties.includes(code)
        ? p.specialties.filter((s) => s !== code)
        : [...p.specialties, code],
    }));

  const goToStep5 = async () => {
    setStep(5);
    setPlanLoading(true);
    const roleLabel = ROLES.find((r) => r.value === data.role)?.label ?? data.role;
    const goalLabel = GOALS.find((g) => g.value === data.goal)?.label ?? data.goal;
    const specLabels = data.specialties
      .map((c) => SPECIALTIES.find((s) => s.code === c)?.label ?? c)
      .join(", ");
    try {
      const res = await aiApi.ask({
        message: `I am a ${roleLabel}. My learning goal is: ${goalLabel}. My specialties: ${specLabels || "General Medicine"}. I have ${data.daily_minutes} minutes per day. Please create a short, personalized 4-week study plan for me with 3-4 actionable bullet points. Be concise and encouraging.`,
        mode: "tutor",
        specialty: data.specialties[0] ?? "General Medicine",
        search_pubmed: false,
      });
      setAiPlan(res.data?.reply ?? "");
    } catch {
      setAiPlan(
        `Welcome! Here's your personalized plan:\n\n• Start with ${data.specialties[0] ?? "core"} fundamentals (Week 1-2)\n• Daily ${data.daily_minutes}-minute focused sessions using flashcards\n• Practice clinical cases 3x per week\n• Track your progress and adjust based on weak areas`
      );
    } finally {
      setPlanLoading(false);
    }
  };

  const finish = async () => {
    setSaving(true);
    try {
      const res = await authApi.onboarding({
        role: data.role,
        goal: data.goal,
        specialties: data.specialties,
        daily_minutes: data.daily_minutes,
      });
      updateUser(res.data);
      router.replace("/dashboard");
    } catch {
      router.replace("/dashboard");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-bg flex flex-col items-center justify-center p-4">
      {/* Logo */}
      <div className="font-syne font-black text-3xl text-ink mb-8">
        Med<span className="text-red">Mind</span>
      </div>

      {/* Progress dots */}
      <div className="flex gap-2 mb-8">
        {[1, 2, 3, 4, 5].map((s) => (
          <div
            key={s}
            className={`h-1.5 rounded-full transition-all duration-300 ${
              s === step ? "w-8 bg-ink" : s < step ? "w-4 bg-ink-3" : "w-4 bg-border-2"
            }`}
          />
        ))}
      </div>

      <div className="w-full max-w-lg card p-8 shadow-xl animate-fade-up">

        {/* ── Step 1: Role ── */}
        {step === 1 && (
          <div>
            <h2 className="font-syne font-bold text-xl text-ink mb-1">
              What best describes you?
            </h2>
            <p className="font-serif text-ink-3 text-sm mb-5">
              We'll tailor your experience to your professional context
            </p>
            <div className="space-y-2.5 mb-6">
              {ROLES.map((role) => (
                <button
                  key={role.value}
                  onClick={() => setData((p) => ({ ...p, role: role.value }))}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded border text-left transition-all ${
                    data.role === role.value
                      ? "border-ink bg-ink text-white"
                      : "border-border bg-surface hover:border-ink-3"
                  }`}
                >
                  <span className="text-2xl">{role.icon}</span>
                  <div>
                    <div className="font-syne font-semibold text-sm">{role.label}</div>
                    <div className={`font-serif text-xs ${data.role === role.value ? "text-white/70" : "text-ink-3"}`}>
                      {role.desc}
                    </div>
                  </div>
                </button>
              ))}
            </div>
            <button
              onClick={() => setStep(2)}
              disabled={!data.role}
              className="btn-primary w-full py-2.5 disabled:opacity-40"
            >
              Next →
            </button>
          </div>
        )}

        {/* ── Step 2: Goal ── */}
        {step === 2 && (
          <div>
            <h2 className="font-syne font-bold text-xl text-ink mb-1">What's your main goal?</h2>
            <p className="font-serif text-ink-3 text-sm mb-5">Choose what best describes your learning intent</p>
            <div className="space-y-2.5 mb-6">
              {GOALS.map((goal) => (
                <button
                  key={goal.value}
                  onClick={() => setData((p) => ({ ...p, goal: goal.value }))}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded border text-left transition-all ${
                    data.goal === goal.value
                      ? "border-ink bg-ink text-white"
                      : "border-border bg-surface hover:border-ink-3"
                  }`}
                >
                  <span className="text-2xl">{goal.icon}</span>
                  <span className="font-syne font-semibold text-sm">{goal.label}</span>
                </button>
              ))}
            </div>
            <div className="flex justify-between">
              <button onClick={() => setStep(1)} className="btn-secondary px-5">← Back</button>
              <button
                onClick={() => setStep(3)}
                disabled={!data.goal}
                className="btn-primary px-5 disabled:opacity-40"
              >
                Next →
              </button>
            </div>
          </div>
        )}

        {/* ── Step 3: Specialties ── */}
        {step === 3 && (
          <div>
            <h2 className="font-syne font-bold text-xl text-ink mb-1">Choose your specialties</h2>
            <p className="font-serif text-ink-3 text-sm mb-5">Select all that apply to your work or studies</p>
            <div className="flex flex-wrap gap-2 mb-6">
              {SPECIALTIES.map((sp) => (
                <button
                  key={sp.code}
                  onClick={() => toggleSpecialty(sp.code)}
                  className={`px-3 py-2 rounded-full border font-syne font-semibold text-xs transition-all flex items-center gap-1.5 ${
                    data.specialties.includes(sp.code)
                      ? "border-ink bg-ink text-white"
                      : "border-border bg-surface hover:border-ink-3 text-ink-2"
                  }`}
                >
                  <span>{sp.icon}</span>
                  {sp.label}
                </button>
              ))}
            </div>
            <div className="flex justify-between">
              <button onClick={() => setStep(2)} className="btn-secondary px-5">← Back</button>
              <button
                onClick={() => setStep(4)}
                disabled={data.specialties.length === 0}
                className="btn-primary px-5 disabled:opacity-40"
              >
                Next →
              </button>
            </div>
          </div>
        )}

        {/* ── Step 4: Daily time ── */}
        {step === 4 && (
          <div>
            <h2 className="font-syne font-bold text-xl text-ink mb-1">Daily learning time</h2>
            <p className="font-serif text-ink-3 text-sm mb-5">How much time can you dedicate each day?</p>
            <div className="grid grid-cols-2 gap-3 mb-6">
              {TIME_OPTIONS.map((t) => (
                <button
                  key={t.value}
                  onClick={() => setData((p) => ({ ...p, daily_minutes: t.value }))}
                  className={`py-4 rounded border text-left px-4 transition-all ${
                    data.daily_minutes === t.value
                      ? "border-ink bg-ink text-white"
                      : "border-border bg-surface hover:border-ink-3 text-ink"
                  }`}
                >
                  <div className="font-syne font-bold text-lg">{t.label}</div>
                  <div className={`font-serif text-xs ${data.daily_minutes === t.value ? "text-white/70" : "text-ink-3"}`}>
                    {t.sub}
                  </div>
                </button>
              ))}
            </div>
            <div className="flex justify-between">
              <button onClick={() => setStep(3)} className="btn-secondary px-5">← Back</button>
              <button onClick={goToStep5} className="btn-primary px-5">
                Build my plan →
              </button>
            </div>
          </div>
        )}

        {/* ── Step 5: AI Welcome Plan ── */}
        {step === 5 && (
          <div>
            <div className="text-center mb-5">
              <div className="text-5xl mb-3">{planLoading ? "🤔" : "🎯"}</div>
              <h2 className="font-syne font-bold text-xl text-ink">
                {planLoading ? "Building your plan…" : "Your personal study plan"}
              </h2>
              <p className="font-serif text-ink-3 text-sm mt-1">
                {planLoading
                  ? "AI is crafting your personalized learning path"
                  : `Tailored for ${ROLES.find((r) => r.value === data.role)?.label}`}
              </p>
            </div>

            {planLoading ? (
              <div className="space-y-2 mb-6">
                {[1, 2, 3, 4].map((i) => (
                  <div key={i} className="h-4 bg-bg-2 rounded animate-pulse" style={{ width: `${85 - i * 8}%` }} />
                ))}
              </div>
            ) : (
              <div className="bg-bg-2 rounded-lg p-4 mb-5 text-sm font-serif text-ink-2 leading-relaxed whitespace-pre-wrap">
                {aiPlan}
              </div>
            )}

            <div className="font-serif text-ink-3 text-xs text-center mb-5 space-y-0.5">
              <p>✓ Role: <strong className="text-ink">{ROLES.find((r) => r.value === data.role)?.label}</strong></p>
              <p>✓ Goal: <strong className="text-ink">{GOALS.find((g) => g.value === data.goal)?.label}</strong></p>
              <p>✓ {data.specialties.length} {data.specialties.length === 1 ? "specialty" : "specialties"} · {data.daily_minutes} min/day</p>
            </div>

            <div className="flex justify-between">
              <button onClick={() => setStep(4)} className="btn-secondary px-5" disabled={saving}>
                ← Back
              </button>
              <button
                onClick={finish}
                disabled={saving || planLoading}
                className="btn-primary px-8 disabled:opacity-60"
              >
                {saving ? "Setting up…" : "Start learning →"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
