"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { examOutcomesApi } from "@/lib/api";

const BLUEPRINT_TOPICS = [
  { slug: "management-of-care", label: "Management of Care" },
  { slug: "safety-infection-control", label: "Safety & Infection Control" },
  { slug: "health-promotion-maintenance", label: "Health Promotion & Maintenance" },
  { slug: "psychosocial-integrity", label: "Psychosocial Integrity" },
  { slug: "basic-care-comfort", label: "Basic Care & Comfort" },
  { slug: "pharmacological-therapies", label: "Pharmacological Therapies" },
  { slug: "reduction-of-risk", label: "Reduction of Risk Potential" },
  { slug: "physiological-adaptation", label: "Physiological Adaptation" },
];

type Step = 1 | 2 | 3 | "done";

export default function ExamSurveyPage() {
  const params = useParams();
  const router = useRouter();
  const outcomeId = params.id as string;

  const [step, setStep] = useState<Step>(1);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  // Step 1
  const [result, setResult] = useState<"passed" | "failed" | "postponed" | "no_answer" | "">("");
  const [selfScore, setSelfScore] = useState("");

  // Step 2
  const [harderTopics, setHarderTopics] = useState<string[]>([]);
  const [weakerTopics, setWeakerTopics] = useState<string[]>([]);
  const [feedbackNote, setFeedbackNote] = useState("");

  // Step 3
  const [nps, setNps] = useState<number | null>(null);

  function toggleTopic(list: string[], setList: (v: string[]) => void, slug: string) {
    setList(list.includes(slug) ? list.filter(s => s !== slug) : [...list, slug]);
  }

  async function handleSubmit() {
    if (!result) return;
    setSubmitting(true);
    setError("");
    try {
      await examOutcomesApi.submit(outcomeId, {
        result: result as "passed" | "failed" | "postponed" | "no_answer",
        self_reported_score: selfScore || undefined,
        harder_topics: harderTopics.length > 0 ? harderTopics : undefined,
        weaker_topics: weakerTopics.length > 0 ? weakerTopics : undefined,
        feedback_note: feedbackNote || undefined,
        nps_score: nps ?? undefined,
      });
      setStep("done");
    } catch (e: any) {
      setError(e?.response?.data?.detail || "Something went wrong. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleUnsubscribe() {
    try {
      await examOutcomesApi.unsubscribe(outcomeId);
      router.push("/dashboard");
    } catch {
      router.push("/dashboard");
    }
  }

  if (step === "done") {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface p-6">
        <div className="max-w-md w-full bg-white rounded-2xl border border-border p-8 text-center">
          <div className="text-4xl mb-4">🎓</div>
          <h1 className="font-syne font-bold text-xl text-ink mb-2">Thank you!</h1>
          <p className="font-serif text-sm text-ink-3 mb-6">
            Your feedback helps us improve MedMind for every student.
          </p>
          <button
            onClick={() => router.push("/dashboard")}
            className="btn-primary w-full"
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface p-6">
      <div className="max-w-lg mx-auto">
        <div className="mb-6">
          <div className="font-syne font-black text-xl text-ink">
            Med<span className="text-red">Mind</span>
          </div>
        </div>

        {/* NDA Notice */}
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6">
          <p className="font-syne font-semibold text-xs text-amber-800 mb-1">IMPORTANT — NDA NOTICE</p>
          <p className="font-serif text-xs text-amber-700 leading-relaxed">
            Do not share verbatim exam questions — this violates your exam agreement with the testing body.
            We only ask about topic themes, not specific question content.
          </p>
        </div>

        <div className="bg-white rounded-2xl border border-border p-6">
          {/* Progress */}
          <div className="flex items-center gap-2 mb-6">
            {[1, 2, 3].map(s => (
              <div
                key={s}
                className={`h-1.5 flex-1 rounded-full transition-colors ${
                  (step as number) >= s ? "bg-red" : "bg-surface-2"
                }`}
              />
            ))}
          </div>

          {/* Step 1 */}
          {step === 1 && (
            <div>
              <h2 className="font-syne font-bold text-lg text-ink mb-4">
                How did your exam go?
              </h2>
              <div className="space-y-2 mb-4">
                {[
                  { value: "passed", label: "I passed 🎉", color: "border-green-400 bg-green-50" },
                  { value: "failed", label: "I didn't pass this time", color: "border-red bg-red/5" },
                  { value: "postponed", label: "I postponed / rescheduled", color: "border-amber-400 bg-amber-50" },
                  { value: "no_answer", label: "Prefer not to say", color: "border-border bg-surface-2" },
                ].map(opt => (
                  <button
                    key={opt.value}
                    onClick={() => setResult(opt.value as any)}
                    className={`w-full text-left p-3 rounded-xl border-2 font-syne font-semibold text-sm transition-all ${
                      result === opt.value ? opt.color + " border-opacity-100" : "border-border hover:border-ink-2"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>

              {result && result !== "no_answer" && result !== "postponed" && (
                <div className="mb-4">
                  <label className="font-syne text-xs font-semibold text-ink-2 block mb-1">
                    Self-reported score (optional)
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. 78%"
                    value={selfScore}
                    onChange={e => setSelfScore(e.target.value)}
                    className="input w-full"
                  />
                </div>
              )}

              <button
                onClick={() => result && setStep(2)}
                disabled={!result}
                className="btn-primary w-full disabled:opacity-40"
              >
                Next →
              </button>
            </div>
          )}

          {/* Step 2 */}
          {step === 2 && (
            <div>
              <h2 className="font-syne font-bold text-lg text-ink mb-1">
                Which topics felt harder than expected?
              </h2>
              <p className="font-serif text-xs text-ink-3 mb-4">
                Select topic areas — no specific questions please.
              </p>

              <div className="grid grid-cols-2 gap-2 mb-4">
                {BLUEPRINT_TOPICS.map(t => (
                  <button
                    key={t.slug}
                    onClick={() => toggleTopic(harderTopics, setHarderTopics, t.slug)}
                    className={`p-2.5 rounded-lg border text-xs font-syne font-semibold text-left transition-all ${
                      harderTopics.includes(t.slug)
                        ? "border-red bg-red/10 text-red"
                        : "border-border text-ink-3 hover:border-ink-2"
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>

              <h3 className="font-syne font-bold text-sm text-ink mb-1">
                Where did MedMind prepare you least well? (optional)
              </h3>
              <div className="grid grid-cols-2 gap-2 mb-4">
                {BLUEPRINT_TOPICS.map(t => (
                  <button
                    key={t.slug}
                    onClick={() => toggleTopic(weakerTopics, setWeakerTopics, t.slug)}
                    className={`p-2.5 rounded-lg border text-xs font-syne font-semibold text-left transition-all ${
                      weakerTopics.includes(t.slug)
                        ? "border-amber-500 bg-amber-50 text-amber-800"
                        : "border-border text-ink-3 hover:border-ink-2"
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>

              <textarea
                placeholder="Any other feedback? (optional)"
                value={feedbackNote}
                onChange={e => setFeedbackNote(e.target.value)}
                maxLength={1000}
                className="input w-full h-24 mb-4 resize-none"
              />

              <div className="flex gap-3">
                <button onClick={() => setStep(1)} className="btn-secondary flex-1">← Back</button>
                <button onClick={() => setStep(3)} className="btn-primary flex-1">Next →</button>
              </div>
            </div>
          )}

          {/* Step 3 */}
          {step === 3 && (
            <div>
              <h2 className="font-syne font-bold text-lg text-ink mb-2">
                How likely are you to recommend MedMind?
              </h2>
              <p className="font-serif text-xs text-ink-3 mb-4">
                0 = not at all, 10 = definitely
              </p>

              <div className="flex gap-1 mb-6 flex-wrap">
                {Array.from({ length: 11 }, (_, i) => i).map(n => (
                  <button
                    key={n}
                    onClick={() => setNps(n)}
                    className={`w-9 h-9 rounded-lg border font-syne font-bold text-sm transition-all ${
                      nps === n
                        ? "border-red bg-red text-white"
                        : "border-border text-ink-3 hover:border-ink"
                    }`}
                  >
                    {n}
                  </button>
                ))}
              </div>

              {error && (
                <p className="font-serif text-xs text-red mb-3">{error}</p>
              )}

              <div className="flex gap-3">
                <button onClick={() => setStep(2)} className="btn-secondary flex-1">← Back</button>
                <button
                  onClick={handleSubmit}
                  disabled={submitting}
                  className="btn-primary flex-1 disabled:opacity-40"
                >
                  {submitting ? "Submitting…" : "Submit →"}
                </button>
              </div>

              <button
                onClick={handleUnsubscribe}
                className="w-full mt-3 font-serif text-xs text-ink-3 hover:text-ink underline"
              >
                Don't ask me again
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
