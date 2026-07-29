"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { examOutcomesApi } from "@/lib/api";

interface PendingSurvey {
  pending: boolean;
  outcome_id?: string;
  exam_slug?: string;
  exam_date?: string;
}

export default function ExamSurveyBanner() {
  const router = useRouter();
  const [survey, setSurvey] = useState<PendingSurvey | null>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    examOutcomesApi
      .getPending()
      .then(setSurvey)
      .catch(() => {});
  }, []);

  if (!survey?.pending || dismissed) return null;

  const examLabel = survey.exam_slug?.toUpperCase() ?? "your exam";

  return (
    <div className="card p-4 mb-4 border-l-4 border-l-red bg-red/5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <p className="font-syne font-bold text-sm text-ink mb-1">
            How did your {examLabel} go?
          </p>
          <p className="font-serif text-xs text-ink-3 leading-relaxed">
            Share your exam outcome to help us improve. Takes 2 minutes. No verbatim questions — topics only.
          </p>
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="text-ink-3 hover:text-ink text-lg leading-none shrink-0"
          aria-label="Dismiss"
        >
          ×
        </button>
      </div>
      <div className="flex gap-2 mt-3">
        <button
          onClick={() => router.push(`/survey/exam-outcome/${survey.outcome_id}`)}
          className="btn-primary text-xs px-4 py-2"
        >
          Share outcome →
        </button>
        <button
          onClick={async () => {
            if (survey.outcome_id) {
              await examOutcomesApi.unsubscribe(survey.outcome_id).catch(() => {});
            }
            setDismissed(true);
          }}
          className="btn-secondary text-xs px-4 py-2"
        >
          Don't ask again
        </button>
      </div>
    </div>
  );
}
