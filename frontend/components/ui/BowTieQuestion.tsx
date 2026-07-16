"use client";

/**
 * NGN Bow-Tie clinical judgment question component.
 *
 * Structure (left → center → right):
 *   [Actions column] → [Condition — CENTER] ← [Parameters column]
 *
 * Scoring: condition (1 pt) + each correct action (1 pt) + each correct parameter (1 pt)
 * → max 5 pts; partial credit per component.
 */

import { useState } from "react";
import { Check, X } from "lucide-react";

type BowTieData = {
  condition_options: string[];
  action_options: string[];
  parameter_options: string[];
  correct_condition?: string;
  correct_actions?: string[];
  correct_parameters?: string[];
};

type BowTieAnswer = {
  condition: string | null;
  actions: string[];       // exactly 2
  parameters: string[];    // exactly 2
};

type Props = {
  bowtie_data: BowTieData;
  submitted: boolean;
  onChange: (answer: BowTieAnswer) => void;
  showCorrect?: boolean;
};

function OptionButton({
  label,
  selected,
  disabled,
  onClick,
  correct,
  incorrect,
  maxReached,
}: {
  label: string;
  selected: boolean;
  disabled: boolean;
  onClick: () => void;
  correct?: boolean;
  incorrect?: boolean;
  maxReached: boolean;
}) {
  const base = "w-full text-left text-xs font-serif px-3 py-2 rounded-lg border transition-all leading-snug";
  let style = "border-border text-ink hover:border-ink cursor-pointer";

  if (selected && correct) style = "border-green bg-green/10 text-green font-semibold";
  else if (selected && incorrect) style = "border-red bg-red/10 text-red";
  else if (!selected && correct) style = "border-green/60 bg-green/5 text-green/80";
  else if (selected) style = "border-ink bg-ink/5 text-ink font-semibold";
  else if (maxReached && !selected) style = "border-border text-ink-3 cursor-not-allowed opacity-50";

  return (
    <button
      onClick={disabled ? undefined : onClick}
      disabled={disabled || (maxReached && !selected)}
      className={`${base} ${style}`}
    >
      <span className="flex items-center gap-1.5">
        {selected && correct && <Check className="w-3 h-3 flex-shrink-0" />}
        {selected && incorrect && <X className="w-3 h-3 flex-shrink-0" />}
        {label}
      </span>
    </button>
  );
}

export function BowTieQuestion({ bowtie_data, submitted, onChange, showCorrect }: Props) {
  const [answer, setAnswer] = useState<BowTieAnswer>({
    condition: null,
    actions: [],
    parameters: [],
  });

  function update(next: BowTieAnswer) {
    setAnswer(next);
    onChange(next);
  }

  function toggleCondition(opt: string) {
    if (submitted) return;
    const next = { ...answer, condition: answer.condition === opt ? null : opt };
    update(next);
  }

  function toggleAction(opt: string) {
    if (submitted) return;
    const has = answer.actions.includes(opt);
    const next = has
      ? { ...answer, actions: answer.actions.filter(a => a !== opt) }
      : answer.actions.length < 2
      ? { ...answer, actions: [...answer.actions, opt] }
      : answer; // max 2 reached
    update(next);
  }

  function toggleParameter(opt: string) {
    if (submitted) return;
    const has = answer.parameters.includes(opt);
    const next = has
      ? { ...answer, parameters: answer.parameters.filter(p => p !== opt) }
      : answer.parameters.length < 2
      ? { ...answer, parameters: [...answer.parameters, opt] }
      : answer; // max 2 reached
    update(next);
  }

  const correctCondition = bowtie_data.correct_condition;
  const correctActions = bowtie_data.correct_actions || [];
  const correctParameters = bowtie_data.correct_parameters || [];

  return (
    <div className="space-y-3">
      {/* Instructions */}
      <div className="text-xs font-serif text-ink-3 bg-surface border border-border rounded-lg px-3 py-2">
        <strong className="text-ink">NGN Bow-Tie:</strong>{" "}
        Select the most likely <em>condition</em> (center), <em>2 nursing actions</em> (left), and <em>2 parameters to monitor</em> (right).
      </div>

      {/* Bow-tie grid */}
      <div className="grid grid-cols-[1fr_auto_1fr] gap-3 items-start">
        {/* Left: Actions */}
        <div>
          <div className="text-xs font-syne font-bold text-ink mb-2 text-center">
            Actions to Take
            <span className="ml-1 text-ink-3 font-normal">(pick 2)</span>
          </div>
          <div className="space-y-1.5">
            {bowtie_data.action_options.map(opt => (
              <OptionButton
                key={opt}
                label={opt}
                selected={answer.actions.includes(opt)}
                disabled={submitted}
                onClick={() => toggleAction(opt)}
                correct={showCorrect && correctActions.includes(opt) ? true : undefined}
                incorrect={showCorrect && answer.actions.includes(opt) && !correctActions.includes(opt) ? true : undefined}
                maxReached={answer.actions.length >= 2}
              />
            ))}
          </div>
        </div>

        {/* Center arrows + condition */}
        <div className="flex flex-col items-center pt-6 gap-2">
          <div className="text-ink-3 text-xl">←</div>
          <div className="rotate-90 text-ink-3 text-xl">↑</div>
          <div className="text-center">
            <div className="text-xs font-syne font-bold text-ink mb-2 whitespace-nowrap">
              Condition
            </div>
            <div className="space-y-1.5">
              {bowtie_data.condition_options.map(opt => (
                <OptionButton
                  key={opt}
                  label={opt}
                  selected={answer.condition === opt}
                  disabled={submitted}
                  onClick={() => toggleCondition(opt)}
                  correct={showCorrect && opt === correctCondition ? true : undefined}
                  incorrect={showCorrect && answer.condition === opt && opt !== correctCondition ? true : undefined}
                  maxReached={false}
                />
              ))}
            </div>
          </div>
          <div className="rotate-90 text-ink-3 text-xl">↓</div>
          <div className="text-ink-3 text-xl">→</div>
        </div>

        {/* Right: Parameters */}
        <div>
          <div className="text-xs font-syne font-bold text-ink mb-2 text-center">
            Parameters to Monitor
            <span className="ml-1 text-ink-3 font-normal">(pick 2)</span>
          </div>
          <div className="space-y-1.5">
            {bowtie_data.parameter_options.map(opt => (
              <OptionButton
                key={opt}
                label={opt}
                selected={answer.parameters.includes(opt)}
                disabled={submitted}
                onClick={() => toggleParameter(opt)}
                correct={showCorrect && correctParameters.includes(opt) ? true : undefined}
                incorrect={showCorrect && answer.parameters.includes(opt) && !correctParameters.includes(opt) ? true : undefined}
                maxReached={answer.parameters.length >= 2}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Progress indicator */}
      {!submitted && (
        <div className="flex items-center gap-4 text-xs font-serif text-ink-3">
          <span className={answer.condition ? "text-green" : ""}>
            {answer.condition ? "✓" : "○"} Condition
          </span>
          <span className={answer.actions.length === 2 ? "text-green" : ""}>
            {answer.actions.length}/2 Actions
          </span>
          <span className={answer.parameters.length === 2 ? "text-green" : ""}>
            {answer.parameters.length}/2 Parameters
          </span>
        </div>
      )}
    </div>
  );
}
