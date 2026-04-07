"use client";

import { useEffect, useState } from "react";

export interface AchievementToastData {
  code: string;
  name: string;
  icon: string;
  xp: number;
}

interface Props {
  achievement: AchievementToastData | null;
  onDismiss: () => void;
}

export function AchievementToast({ achievement, onDismiss }: Props) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!achievement) return;
    setVisible(true);
    const timer = setTimeout(() => {
      setVisible(false);
      setTimeout(onDismiss, 300);
    }, 4000);
    return () => clearTimeout(timer);
  }, [achievement, onDismiss]);

  if (!achievement) return null;

  return (
    <div
      className={`fixed bottom-6 right-6 z-50 transition-all duration-300 ${
        visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4"
      }`}
    >
      <div className="card flex items-center gap-4 px-5 py-4 shadow-xl border border-accent/30 bg-surface min-w-[280px]">
        <div className="text-3xl">{achievement.icon}</div>
        <div>
          <div className="text-xs font-semibold text-accent uppercase tracking-wide">Achievement Unlocked!</div>
          <div className="font-syne font-bold text-sm text-ink mt-0.5">{achievement.name}</div>
          <div className="text-xs text-ink-3">+{achievement.xp} XP</div>
        </div>
        <button onClick={() => { setVisible(false); setTimeout(onDismiss, 300); }} className="text-ink-3 hover:text-ink ml-2">×</button>
      </div>
    </div>
  );
}
