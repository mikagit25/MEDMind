"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

const SPECIALTIES = [
  { code: "cardiology", label: "Cardiology" },
  { code: "neurology", label: "Neurology" },
  { code: "surgery", label: "Surgery" },
  { code: "obstetrics", label: "Obstetrics & Gynecology" },
  { code: "pediatrics", label: "Pediatrics" },
  { code: "therapy", label: "Internal Medicine" },
  { code: "veterinary", label: "Veterinary" },
];

const GOALS = [
  { value: "exam_prep", label: "Exam preparation", icon: "📝" },
  { value: "clinical_refresh", label: "Clinical knowledge refresh", icon: "🔄" },
  { value: "new_specialty", label: "Learn new specialty", icon: "📚" },
  { value: "daily_learning", label: "Daily continuous learning", icon: "📅" },
];

const TIME_OPTIONS = [
  { value: 5, label: "5 min" },
  { value: 10, label: "10 min" },
  { value: 20, label: "20 min" },
  { value: 30, label: "30+ min" },
];

type Step = 1 | 2 | 3 | 4 | 5;

export default function OnboardingPage() {
  const router = useRouter();
  const { user, updateUser } = useAuthStore();
  const [step, setStep] = useState<Step>(1);
  const [data, setData] = useState({
    goal: "",
    specialties: [] as string[],
    daily_minutes: 10,
  });
  const [loading, setLoading] = useState(false);

  const toggleSpecialty = (code: string) =>
    setData((p) => ({
      ...p,
      specialties: p.specialties.includes(code)
        ? p.specialties.filter((s) => s !== code)
        : [...p.specialties, code],
    }));

  const finish = async () => {
    setLoading(true);
    try {
      const res = await authApi.onboarding(data);
      updateUser(res.data);
      router.replace("/dashboard");
    } catch {
      router.replace("/dashboard");
    } finally {
      setLoading(false);
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
        {/* Step 1: Welcome */}
        {step === 1 && (
          <div className="text-center">
            <div className="text-6xl mb-4">👋</div>
            <h2 className="font-syne font-bold text-2xl text-ink mb-2">
              Welcome, {user?.first_name}!
            </h2>
            <p className="font-serif text-ink-2 mb-6">
              Let's personalize your learning experience. This takes just 2 minutes.
            </p>
            <button onClick={() => setStep(2)} className="btn-primary px-8 py-2.5 text-base">
              Let's get started →
            </button>
          </div>
        )}

        {/* Step 2: Goal */}
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
              <button onClick={() => setStep(1)} className="btn-secondary px-5">
                ← Back
              </button>
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

        {/* Step 3: Specialties */}
        {step === 3 && (
          <div>
            <h2 className="font-syne font-bold text-xl text-ink mb-1">Choose your specialties</h2>
            <p className="font-serif text-ink-3 text-sm mb-5">Select all that apply to your work or studies</p>
            <div className="flex flex-wrap gap-2 mb-6">
              {SPECIALTIES.map((sp) => (
                <button
                  key={sp.code}
                  onClick={() => toggleSpecialty(sp.code)}
                  className={`px-3.5 py-2 rounded-full border font-syne font-semibold text-sm transition-all ${
                    data.specialties.includes(sp.code)
                      ? "border-ink bg-ink text-white"
                      : "border-border bg-surface hover:border-ink-3 text-ink-2"
                  }`}
                >
                  {sp.label}
                </button>
              ))}
            </div>
            <div className="flex justify-between">
              <button onClick={() => setStep(2)} className="btn-secondary px-5">
                ← Back
              </button>
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

        {/* Step 4: Daily time */}
        {step === 4 && (
          <div>
            <h2 className="font-syne font-bold text-xl text-ink mb-1">Daily learning time</h2>
            <p className="font-serif text-ink-3 text-sm mb-5">How much time can you dedicate each day?</p>
            <div className="grid grid-cols-2 gap-3 mb-6">
              {TIME_OPTIONS.map((t) => (
                <button
                  key={t.value}
                  onClick={() => setData((p) => ({ ...p, daily_minutes: t.value }))}
                  className={`py-4 rounded border font-syne font-bold text-lg transition-all ${
                    data.daily_minutes === t.value
                      ? "border-ink bg-ink text-white"
                      : "border-border bg-surface hover:border-ink-3 text-ink"
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
            <div className="flex justify-between">
              <button onClick={() => setStep(3)} className="btn-secondary px-5">
                ← Back
              </button>
              <button onClick={() => setStep(5)} className="btn-primary px-5">
                Next →
              </button>
            </div>
          </div>
        )}

        {/* Step 5: Ready */}
        {step === 5 && (
          <div className="text-center">
            <div className="text-6xl mb-4">🎯</div>
            <h2 className="font-syne font-bold text-2xl text-ink mb-2">You're all set!</h2>
            <div className="font-serif text-ink-2 text-sm space-y-1 mb-6">
              <p>✓ Goal: <strong>{GOALS.find((g) => g.value === data.goal)?.label}</strong></p>
              <p>✓ {data.specialties.length} specialties selected</p>
              <p>✓ {data.daily_minutes} min/day learning plan</p>
            </div>
            <p className="font-serif text-ink-3 text-sm mb-6">
              Your personalized AI tutor is ready. Start learning with evidence-based content today.
            </p>
            <button
              onClick={finish}
              disabled={loading}
              className="btn-primary px-10 py-2.5 text-base disabled:opacity-60"
            >
              {loading ? "Setting up…" : "Start learning →"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
