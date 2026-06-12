"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { teamApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { useT } from "@/lib/i18n";
import {
  Users, Crown, UserMinus, Mail, BarChart2, Zap, BookOpen, Flame,
} from "lucide-react";

type Member = {
  id: string;
  name: string;
  email: string;
  role: "admin" | "member";
  xp: number;
  level: number;
  streak_days: number;
  subscription_tier: string;
  joined_at: string;
};

type TeamData = {
  team_id: string;
  my_role: string;
  member_count: number;
  max_members: number;
  members: Member[];
};

type TeamStats = {
  total_xp: number;
  total_lessons: number;
  avg_streak: number;
  member_count: number;
  members: (Member & { modules_started: number; lessons_done: number })[];
};

export default function TeamPage() {
  const t = useT();
  const { user } = useAuthStore();

  const [team, setTeam] = useState<TeamData | null>(null);
  const [stats, setStats] = useState<TeamStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteStatus, setInviteStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [inviteMsg, setInviteMsg] = useState("");

  const [removingId, setRemovingId] = useState<string | null>(null);

  const isClinic = user?.subscription_tier === "clinic" || user?.role === "admin";

  const load = useCallback(async () => {
    if (!isClinic) { setLoading(false); return; }
    setLoading(true);
    setError("");
    try {
      const [teamRes, statsRes] = await Promise.all([teamApi.list(), teamApi.stats()]);
      setTeam(teamRes);
      setStats(statsRes);
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to load team data.");
    } finally {
      setLoading(false);
    }
  }, [isClinic]);

  useEffect(() => { load(); }, [load]);

  async function handleInvite() {
    if (!inviteEmail.trim()) return;
    setInviteStatus("loading");
    setInviteMsg("");
    try {
      await teamApi.invite(inviteEmail.trim());
      setInviteStatus("success");
      setInviteMsg(t("team.invite_success"));
      setInviteEmail("");
    } catch (e: any) {
      setInviteStatus("error");
      const detail = e?.response?.data?.detail ?? "";
      if (detail.toLowerCase().includes("full")) setInviteMsg(t("team.invite_error_full"));
      else setInviteMsg(t("team.invite_error"));
    }
  }

  async function handleRemove(memberId: string, name: string) {
    if (!confirm(t("team.remove_confirm").replace("{name}", name))) return;
    setRemovingId(memberId);
    try {
      await teamApi.removeMember(memberId);
      await load();
    } catch {
      // silent
    } finally {
      setRemovingId(null);
    }
  }

  // ── Not on Clinic plan ────────────────────────────────────────────────────
  if (!isClinic) {
    return (
      <div className="flex-1 overflow-y-auto p-3 sm:p-6 max-w-2xl mx-auto w-full">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-amber/10 flex items-center justify-center flex-shrink-0">
            <Users size={20} className="text-amber" />
          </div>
          <h1 className="font-syne font-black text-2xl text-ink">{t("team.title")}</h1>
        </div>
        <div className="card p-8 text-center space-y-4">
          <Users size={40} className="text-ink-3 mx-auto" />
          <p className="font-syne font-semibold text-ink">{t("team.upgrade_prompt")}</p>
          <Link href="/upgrade" className="btn-primary inline-block px-6">{t("team.upgrade_link")}</Link>
        </div>
      </div>
    );
  }

  // ── Loading ───────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-ink-3 border-t-ink rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 overflow-y-auto p-3 sm:p-6 max-w-2xl mx-auto w-full">
        <p className="text-red font-serif text-sm">{error}</p>
      </div>
    );
  }

  const isAdmin = team?.my_role === "admin";

  return (
    <div className="flex-1 overflow-y-auto p-3 sm:p-6 max-w-3xl mx-auto w-full">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-amber/10 flex items-center justify-center flex-shrink-0">
          <Users size={20} className="text-amber" />
        </div>
        <div>
          <h1 className="font-syne font-black text-2xl text-ink">{t("team.title")}</h1>
          <p className="font-serif text-ink-3 text-sm">
            {t("team.member_count")
              .replace("{count}", String(team?.member_count ?? 0))
              .replace("{max}", String(team?.max_members ?? 10))}
          </p>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="card p-5 mb-4">
          <div className="flex items-center gap-2 mb-3">
            <BarChart2 size={14} className="text-ink-3" />
            <p className="font-syne font-semibold text-xs text-ink-2">{t("team.stats_title")}</p>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-surface-2 rounded-xl p-3 text-center">
              <Zap size={16} className="text-amber mx-auto mb-1" />
              <p className="font-syne font-black text-xl text-ink">{stats.total_xp.toLocaleString()}</p>
              <p className="font-serif text-[10px] text-ink-3">{t("team.total_xp")}</p>
            </div>
            <div className="bg-surface-2 rounded-xl p-3 text-center">
              <BookOpen size={16} className="text-ink-3 mx-auto mb-1" />
              <p className="font-syne font-black text-xl text-ink">{stats.total_lessons}</p>
              <p className="font-serif text-[10px] text-ink-3">{t("team.total_lessons")}</p>
            </div>
            <div className="bg-surface-2 rounded-xl p-3 text-center">
              <Flame size={16} className="text-red mx-auto mb-1" />
              <p className="font-syne font-black text-xl text-ink">{stats.avg_streak}</p>
              <p className="font-serif text-[10px] text-ink-3">{t("team.avg_streak")} {t("team.days")}</p>
            </div>
          </div>
        </div>
      )}

      {/* Member list */}
      <div className="card p-5 mb-4">
        <div className="flex items-center gap-2 mb-3">
          <Users size={14} className="text-ink-3" />
          <p className="font-syne font-semibold text-xs text-ink-2">{t("team.members")}</p>
        </div>
        {team && team.members.length === 0 ? (
          <p className="font-serif text-sm text-ink-3 text-center py-4">{t("team.no_members")}</p>
        ) : (
          <div className="space-y-2">
            {(stats?.members ?? team?.members ?? []).map((m: any) => {
              const isSelf = m.id === user?.id;
              return (
                <div key={m.id}
                  className="flex items-center gap-3 bg-surface-2 rounded-xl border border-border px-3 py-2.5">
                  {/* Avatar */}
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-gold to-amber flex items-center justify-center flex-shrink-0">
                    <span className="font-syne font-black text-xs text-ink">
                      {m.name.charAt(0).toUpperCase()}
                    </span>
                  </div>
                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="font-syne font-semibold text-sm text-ink truncate">{m.name}</span>
                      {m.role === "admin" && (
                        <span className="flex items-center gap-0.5 bg-amber/10 text-amber text-[10px] font-syne font-bold px-1.5 py-0.5 rounded-full flex-shrink-0">
                          <Crown size={9} />{t("team.admin_badge")}
                        </span>
                      )}
                      {isSelf && (
                        <span className="text-[10px] text-ink-3 font-serif flex-shrink-0">(you)</span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 mt-0.5">
                      <span className="font-syne text-[10px] text-ink-3">
                        {t("team.level")}{m.level} · {m.xp.toLocaleString()} {t("team.xp")}
                      </span>
                      {m.streak_days > 0 && (
                        <span className="font-syne text-[10px] text-orange-500">
                          🔥 {m.streak_days}d
                        </span>
                      )}
                      {m.lessons_done !== undefined && (
                        <span className="font-syne text-[10px] text-ink-3">
                          {m.lessons_done} lessons
                        </span>
                      )}
                    </div>
                  </div>
                  {/* Remove button — admin only, not self */}
                  {isAdmin && !isSelf && (
                    <button
                      onClick={() => handleRemove(m.id, m.name)}
                      disabled={removingId === m.id}
                      className="flex items-center gap-1 text-red text-[11px] font-syne font-semibold px-2 py-1 rounded hover:bg-red/10 transition-colors disabled:opacity-40 flex-shrink-0">
                      <UserMinus size={12} />
                      {removingId === m.id ? t("team.removing") : t("team.remove_member")}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Invite form — admin only */}
      {isAdmin && (
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-3">
            <Mail size={14} className="text-ink-3" />
            <p className="font-syne font-semibold text-xs text-ink-2">{t("team.invite_title")}</p>
          </div>
          <div className="flex gap-2">
            <input
              type="email"
              value={inviteEmail}
              onChange={e => setInviteEmail(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleInvite()}
              placeholder={t("team.invite_placeholder")}
              className="flex-1 px-3 py-2 rounded-lg border border-border bg-bg text-ink font-serif text-sm focus:outline-none focus:border-ink"
            />
            <button
              onClick={handleInvite}
              disabled={!inviteEmail.trim() || inviteStatus === "loading"}
              className="btn-primary px-4 disabled:opacity-40 text-sm whitespace-nowrap">
              {inviteStatus === "loading" ? t("team.inviting") : t("team.invite_btn")}
            </button>
          </div>
          {inviteStatus === "success" && (
            <p className="mt-2 text-green font-serif text-xs">{inviteMsg}</p>
          )}
          {inviteStatus === "error" && (
            <p className="mt-2 text-red font-serif text-xs">{inviteMsg}</p>
          )}
          {inviteStatus === "success" && team && (
            <p className="mt-1 font-serif text-[11px] text-ink-3">
              Share this link: <span className="font-mono text-ink">medmind.pro/team/join?token=…</span>
            </p>
          )}
        </div>
      )}
    </div>
  );
}
