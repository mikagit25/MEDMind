"use client";

import { useEffect, useState } from "react";
import { progressApi } from "@/lib/api";
import { useT } from "@/lib/i18n";

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
  const t = useT();
  const [period, setPeriod] = useState<Period>("week");
  const [board, setBoard] = useState<LeaderEntry[]>([]);
  const [myRank, setMyRank] = useState<number | null>(null);
  const [myEntry, setMyEntry] = useState<LeaderEntry | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    progressApi.getLeaderboard?.(period)
      .then((data: any) => {
        const list: LeaderEntry[] = data.leaderboard ?? [];
        setBoard(list);
        setMyRank(data.my_rank ?? null);
        setMyEntry(list.find((e) => e.is_me) ?? null);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [period]);

  const top3 = board.slice(0, 3);
  const rest = board.slice(3);

  return (
    <div className="flex-1 overflow-y-auto p-6 max-w-2xl mx-auto w-full">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-syne font-black text-2xl text-ink">{t("leaderboard.title")}</h1>
          {myRank && (
            <p className="font-serif text-ink-3 text-sm mt-0.5">
              {t("leaderboard.your_rank")}: <span className="font-syne font-bold text-ink">#{myRank}</span>
            </p>
          )}
        </div>
        <div className="flex gap-1 bg-bg-2 p-1 rounded-lg">
          {(["week", "month", "all"] as Period[]).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1.5 rounded font-syne font-semibold text-xs transition-all ${
                period === p ? "bg-white shadow text-ink" : "text-ink-3 hover:text-ink"
              }`}
            >
              {p === "week" ? t("leaderboard.weekly") : p === "month" ? t("leaderboard.monthly") : t("leaderboard.all_time")}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="text-center py-16 font-serif text-ink-3 text-sm">{t("common.loading")}</div>
      ) : board.length === 0 ? (
        <div className="text-center py-16">
          <div className="text-4xl mb-3">🏆</div>
          <p className="font-serif text-ink-3 text-sm">{t("leaderboard.no_data")}</p>
        </div>
      ) : (
        <>
          {/* Podium — top 3 */}
          {top3.length >= 2 && (
            <div className="flex items-end justify-center gap-3 mb-8 pt-4">
              {/* 2nd place */}
              {top3[1] && (
                <PodiumSlot entry={top3[1]} height="h-20" medal="🥈" bg="bg-slate-100" />
              )}
              {/* 1st place */}
              {top3[0] && (
                <PodiumSlot entry={top3[0]} height="h-28" medal="🥇" bg="bg-amber-light" crown />
              )}
              {/* 3rd place */}
              {top3[2] && (
                <PodiumSlot entry={top3[2]} height="h-14" medal="🥉" bg="bg-orange-50" />
              )}
            </div>
          )}

          {/* Rest of leaderboard */}
          {rest.length > 0 && (
            <div className="space-y-2 mb-4">
              {rest.map((entry) => (
                <LeaderRow key={entry.user_id} entry={entry} />
              ))}
            </div>
          )}

          {/* My position if outside top list */}
          {myEntry && myRank && myRank > board.length && (
            <div className="mt-4 pt-4 border-t border-border">
              <p className="font-serif text-ink-3 text-xs mb-2 text-center">{t("leaderboard.your_rank")}</p>
              <LeaderRow entry={myEntry} />
            </div>
          )}

          {/* XP gap to next rank */}
          {myEntry && myRank && myRank > 1 && (
            <XPGapWidget board={board} myEntry={myEntry} myRank={myRank} />
          )}
        </>
      )}
    </div>
  );
}

function PodiumSlot({
  entry,
  height,
  medal,
  bg,
  crown,
}: {
  entry: LeaderEntry;
  height: string;
  medal: string;
  bg: string;
  crown?: boolean;
}) {
  return (
    <div className="flex flex-col items-center gap-1.5 flex-1">
      {crown && <span className="text-lg">👑</span>}
      <div className="text-2xl">{medal}</div>
      <div className="font-syne font-bold text-xs text-ink text-center truncate w-full px-1">
        {entry.name?.split(" ")[0] ?? "Anonymous"}
        {entry.is_me && " (you)"}
      </div>
      <div className={`w-full ${height} ${bg} rounded-t-lg flex items-center justify-center`}>
        <span className="font-syne font-black text-sm text-ink-2">
          {entry.xp >= 1000 ? `${(entry.xp / 1000).toFixed(1)}k` : entry.xp} XP
        </span>
      </div>
    </div>
  );
}

function LeaderRow({ entry }: { entry: LeaderEntry }) {
  return (
    <div className={`card flex items-center gap-3 px-4 py-3 ${entry.is_me ? "border-ink" : ""}`}>
      <div className="w-8 font-syne font-bold text-sm text-ink-3 text-center flex-shrink-0">
        #{entry.rank}
      </div>
      <div className="flex-1 min-w-0">
        <div className="font-syne font-semibold text-sm text-ink truncate">
          {entry.name || "Anonymous"}{entry.is_me ? " (you)" : ""}
        </div>
        <div className="font-serif text-xs text-ink-3 mt-0.5">
          {LEVEL_NAMES[entry.level] ?? `Lvl ${entry.level}`}
          {entry.streak_days > 1 && ` · 🔥 ${entry.streak_days}d`}
        </div>
      </div>
      <div className="font-syne font-bold text-sm text-ink flex-shrink-0">
        {entry.xp.toLocaleString()} XP
      </div>
    </div>
  );
}

function XPGapWidget({
  board,
  myEntry,
  myRank,
}: {
  board: LeaderEntry[];
  myEntry: LeaderEntry;
  myRank: number;
}) {
  const above = board.find((e) => e.rank === myRank - 1);
  if (!above) return null;
  const gap = above.xp - myEntry.xp;
  if (gap <= 0) return null;

  return (
    <div className="mt-3 card p-3 flex items-center gap-3">
      <span className="text-lg">🎯</span>
      <p className="font-serif text-sm text-ink">
        <span className="font-syne font-bold">{gap.toLocaleString()} XP</span> to overtake{" "}
        <span className="font-syne font-bold">{above.name?.split(" ")[0] ?? "them"}</span> (#{above.rank})
      </p>
    </div>
  );
}
