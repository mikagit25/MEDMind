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
  longest_streak: number;
  is_me: boolean;
}

interface LeaderboardData {
  period: Period;
  my_rank: number | null;
  opted_in: boolean;
  total_shown: number;
  leaderboard: LeaderEntry[];
  my_entry: LeaderEntry | null;
}

const LEVEL_NAMES = ["", "Novice", "Learner", "Resident", "Specialist", "Expert", "Master"];

export default function LeaderboardPage() {
  const t = useT();
  const [period, setPeriod] = useState<Period>("week");
  const [data, setData] = useState<LeaderboardData | null>(null);
  const [loading, setLoading] = useState(true);

  // Settings panel state
  const [showSettings, setShowSettings] = useState(false);
  const [optIn, setOptIn] = useState(false);
  const [displayName, setDisplayName] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveOk, setSaveOk] = useState(false);

  const fetchBoard = () => {
    setLoading(true);
    progressApi.getLeaderboard?.(period)
      .then((res: any) => {
        setData(res);
        setOptIn(res.opted_in ?? false);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchBoard(); }, [period]);

  const handleSaveSettings = async () => {
    setSaving(true);
    try {
      await progressApi.updateLeaderboardSettings?.({ leaderboard_opt_in: optIn, leaderboard_display_name: displayName });
      setSaveOk(true);
      setTimeout(() => setSaveOk(false), 2000);
      fetchBoard();
    } catch {}
    setSaving(false);
  };

  const board = data?.leaderboard ?? [];
  const myRank = data?.my_rank ?? null;
  const myEntry = board.find((e) => e.is_me) ?? data?.my_entry ?? null;
  const top3 = board.slice(0, 3);
  const rest = board.slice(3);

  return (
    <div className="flex-1 overflow-y-auto p-3 sm:p-6 max-w-2xl mx-auto w-full">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="font-syne font-black text-2xl text-ink">{t("leaderboard.title")}</h1>
          {myRank && (
            <p className="font-serif text-ink-3 text-sm mt-0.5">
              {t("leaderboard.your_rank")}: <span className="font-syne font-bold text-ink">#{myRank}</span>
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSettings((s) => !s)}
            className="p-2 rounded-lg hover:bg-bg-2 transition-colors text-ink-3 hover:text-ink"
            title="Leaderboard settings"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/>
              <path d="M12 2v2M12 20v2M2 12h2M20 12h2"/>
            </svg>
          </button>
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
      </div>

      {/* Settings panel */}
      {showSettings && (
        <div className="card mb-6 p-4 border-ink/20">
          <h2 className="font-syne font-bold text-sm text-ink mb-3">Leaderboard Settings</h2>
          <div className="space-y-3">
            <label className="flex items-center gap-3 cursor-pointer">
              <div
                onClick={() => setOptIn((v) => !v)}
                className={`w-10 h-5 rounded-full transition-colors relative ${optIn ? "bg-ink" : "bg-bg-3"}`}
              >
                <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${optIn ? "translate-x-5" : "translate-x-0.5"}`} />
              </div>
              <span className="font-serif text-sm text-ink">Show me on the leaderboard</span>
            </label>
            {optIn && (
              <div>
                <label className="font-serif text-xs text-ink-3 block mb-1">Display name (optional)</label>
                <input
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="Leave blank to use your real name"
                  maxLength={100}
                  className="w-full border border-border rounded-lg px-3 py-2 font-serif text-sm focus:outline-none focus:border-ink bg-bg"
                />
              </div>
            )}
            <button
              onClick={handleSaveSettings}
              disabled={saving}
              className="btn-primary text-sm px-4 py-2"
            >
              {saving ? "Saving…" : saveOk ? "Saved!" : "Save"}
            </button>
          </div>
        </div>
      )}

      {/* Opt-in banner for users not yet participating */}
      {!loading && data && !data.opted_in && !showSettings && (
        <div className="card mb-6 p-4 border-dashed border-ink/30 flex items-start gap-3">
          <span className="text-2xl flex-shrink-0">🏆</span>
          <div className="flex-1">
            <p className="font-syne font-semibold text-sm text-ink">Join the leaderboard</p>
            <p className="font-serif text-xs text-ink-3 mt-0.5">
              Compete with other learners and track your progress. Your name is hidden until you opt in.
            </p>
          </div>
          <button
            onClick={() => { setOptIn(true); setShowSettings(true); }}
            className="btn-primary text-xs px-3 py-1.5 flex-shrink-0"
          >
            Join
          </button>
        </div>
      )}

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
              {top3[1] && <PodiumSlot entry={top3[1]} height="h-20" medal="🥈" bg="bg-slate-100" />}
              {top3[0] && <PodiumSlot entry={top3[0]} height="h-28" medal="🥇" bg="bg-amber-light" crown />}
              {top3[2] && <PodiumSlot entry={top3[2]} height="h-14" medal="🥉" bg="bg-orange-50" />}
            </div>
          )}

          {rest.length > 0 && (
            <div className="space-y-2 mb-4">
              {rest.map((entry) => <LeaderRow key={entry.user_id} entry={entry} />)}
            </div>
          )}

          {/* My position if outside top list */}
          {myEntry && myRank && myRank > board.length && (
            <div className="mt-4 pt-4 border-t border-border">
              <p className="font-serif text-ink-3 text-xs mb-2 text-center">{t("leaderboard.your_rank")}</p>
              <LeaderRow entry={myEntry} />
            </div>
          )}

          {myEntry && myRank && myRank > 1 && (
            <XPGapWidget board={board} myEntry={myEntry} myRank={myRank} />
          )}
        </>
      )}
    </div>
  );
}

function PodiumSlot({ entry, height, medal, bg, crown }: {
  entry: LeaderEntry; height: string; medal: string; bg: string; crown?: boolean;
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
        <div className="font-serif text-xs text-ink-3 mt-0.5 flex items-center gap-2">
          <span>{LEVEL_NAMES[entry.level] ?? `Lvl ${entry.level}`}</span>
          {entry.streak_days > 1 && <span>🔥 {entry.streak_days}d</span>}
          {entry.longest_streak > 7 && <span title="Best streak">⭐ {entry.longest_streak}d best</span>}
        </div>
      </div>
      <div className="font-syne font-bold text-sm text-ink flex-shrink-0">
        {entry.xp.toLocaleString()} XP
      </div>
    </div>
  );
}

function XPGapWidget({ board, myEntry, myRank }: {
  board: LeaderEntry[]; myEntry: LeaderEntry; myRank: number;
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
