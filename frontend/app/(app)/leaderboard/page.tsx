"use client";

import { useEffect, useState } from "react";
import { progressApi } from "@/lib/api";

type Period = "week" | "month" | "all";

interface LeaderEntry {
  rank: number;
  user_id: string;
  name: string;
  level: number;
  xp: number;
  streak_days: number;
  is_me: boolean;
}

const LEVEL_NAMES = ["", "Novice", "Learner", "Resident", "Specialist", "Expert", "Master"];

export default function LeaderboardPage() {
  const [period, setPeriod] = useState<Period>("week");
  const [board, setBoard]   = useState<LeaderEntry[]>([]);
  const [myRank, setMyRank] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    progressApi.getLeaderboard?.(period)
      .then((data: any) => {
        setBoard(data.leaderboard ?? []);
        setMyRank(data.my_rank ?? null);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [period]);

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-syne font-black text-2xl text-ink">Leaderboard</h1>
          {myRank && <p className="text-ink-3 text-sm mt-0.5">Your rank: #{myRank}</p>}
        </div>
        <div className="flex gap-1 bg-surface-2 rounded-lg p-1">
          {(["week", "month", "all"] as Period[]).map(p => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold capitalize transition-colors ${
                period === p ? "bg-accent text-white" : "text-ink-3 hover:text-ink"
              }`}
            >
              {p === "all" ? "All time" : `This ${p}`}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="text-center py-16 text-ink-3">Loading…</div>
      ) : board.length === 0 ? (
        <div className="text-center py-16 text-ink-3">No data for this period yet.</div>
      ) : (
        <div className="space-y-2">
          {board.map(entry => (
            <div
              key={entry.user_id}
              className={`card flex items-center gap-4 px-4 py-3 ${entry.is_me ? "ring-2 ring-accent" : ""}`}
            >
              <div className={`w-8 text-center font-syne font-black text-lg ${
                entry.rank === 1 ? "text-yellow-500" :
                entry.rank === 2 ? "text-slate-400" :
                entry.rank === 3 ? "text-orange-400" : "text-ink-3"
              }`}>
                {entry.rank === 1 ? "🥇" : entry.rank === 2 ? "🥈" : entry.rank === 3 ? "🥉" : `#${entry.rank}`}
              </div>

              <div className="flex-1 min-w-0">
                <div className="font-semibold text-sm text-ink truncate">
                  {entry.name || "Anonymous"}{entry.is_me ? " (you)" : ""}
                </div>
                <div className="text-xs text-ink-3 mt-0.5">
                  {LEVEL_NAMES[entry.level] ?? `Level ${entry.level}`}
                  {entry.streak_days > 0 && ` · 🔥 ${entry.streak_days}d`}
                </div>
              </div>

              <div className="font-mono font-bold text-sm text-accent">
                {entry.xp.toLocaleString()} XP
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
