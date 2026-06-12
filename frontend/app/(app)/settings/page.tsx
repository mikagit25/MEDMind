"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuthStore } from "@/lib/store";
import { authApi, complianceApi, progressApi } from "@/lib/api";
import { useI18n, useT } from "@/lib/i18n";

const TIER_COLORS: Record<string, string> = {
  free: "bg-surface-2 text-ink-3",
  student: "bg-blue-light text-blue",
  pro: "bg-amber-light text-amber",
  clinic: "bg-green-light text-green",
  lifetime: "bg-ink text-white",
};

const ALL_SPECIES = [
  { id: "canine", label: "🐕 Canine" },
  { id: "feline", label: "🐈 Feline" },
  { id: "equine", label: "🐎 Equine" },
  { id: "bovine", label: "🐄 Bovine" },
  { id: "porcine", label: "🐖 Porcine" },
  { id: "avian", label: "🦜 Avian" },
  { id: "exotic", label: "🦎 Exotic" },
];

const ROLE_OPTIONS = [
  { value: "student",     key: "onboarding.role_student",     icon: "🎓" },
  { value: "doctor",      key: "onboarding.role_doctor",      icon: "🩺" },
  { value: "teacher",     key: "onboarding.role_teacher",     icon: "🏛️" },
  { value: "nurse",       key: "onboarding.role_nurse",       icon: "👩‍⚕️" },
  { value: "vet",         key: "onboarding.role_vet",         icon: "🐾" },
  { value: "vet_student", key: "onboarding.role_vet_student", icon: "🎓" },
  { value: "other",       key: "onboarding.role_other",       icon: "👤" },
];

export default function SettingsPage() {
  const { user, updateUser, logout } = useAuthStore();
  const { locale, setLocale } = useI18n();
  const t = useT();
  const [firstName, setFirstName] = useState(user?.first_name ?? "");
  const [lastName, setLastName] = useState(user?.last_name ?? "");
  const [role, setRole] = useState(user?.role ?? "student");
  const [vetMode, setVetMode] = useState<boolean>((user?.preferences?.vet_mode as boolean) ?? false);
  const [vetSpecies, setVetSpecies] = useState<string[]>(
    (user?.preferences?.vet_species as string[]) ?? []
  );
  const [dailyGoal, setDailyGoal] = useState<number>((user?.preferences?.daily_goal_minutes as number) ?? 20);
  const [emailNotifs, setEmailNotifs] = useState<boolean>((user?.preferences?.email_notifications as boolean) ?? true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  const sub = user?.subscription_tier ?? "free";
  const canUseVet = true;

  const toggleSpecies = (id: string) => {
    setVetSpecies((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const [profileRes] = await Promise.all([
        authApi.updateMe({
          first_name: firstName,
          last_name: lastName,
          role,
          preferences: { ...(user?.preferences ?? {}), daily_goal_minutes: dailyGoal, email_notifications: emailNotifs },
        }),
        canUseVet
          ? authApi.updateVetSettings({ vet_mode: vetMode, species: vetSpecies })
          : Promise.resolve(null),
      ]);
      updateUser(profileRes);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (err: any) {
      setError(err.response?.data?.detail ?? t("settings.save_err"));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-3 sm:p-6 max-w-2xl mx-auto w-full">
      <h1 className="font-syne font-black text-2xl text-ink mb-6">{t("settings.title")}</h1>

      {/* Profile */}
      <section className="card p-6 mb-5">
        <h2 className="font-syne font-bold text-base text-ink mb-4">{t("settings.profile")}</h2>
        <form onSubmit={handleSave} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-syne font-semibold text-xs text-ink-2 mb-1">
                {t("settings.first_name")}
              </label>
              <input
                type="text"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                className="w-full px-3 py-2 rounded border border-border bg-bg text-ink font-serif text-sm focus:outline-none focus:border-ink"
              />
            </div>
            <div>
              <label className="block font-syne font-semibold text-xs text-ink-2 mb-1">
                {t("settings.last_name")}
              </label>
              <input
                type="text"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                className="w-full px-3 py-2 rounded border border-border bg-bg text-ink font-serif text-sm focus:outline-none focus:border-ink"
              />
            </div>
          </div>
          <div>
            <label className="block font-syne font-semibold text-xs text-ink-2 mb-1">
              {t("settings.email")}
            </label>
            <input
              type="email"
              value={user?.email ?? ""}
              disabled
              className="w-full px-3 py-2 rounded border border-border bg-surface-2 text-ink-3 font-serif text-sm cursor-not-allowed"
            />
            <p className="text-ink-3 text-xs font-serif mt-1">{t("settings.email_hint")}</p>
          </div>

          <div>
            <label className="block font-syne font-semibold text-xs text-ink-2 mb-1">
              {t("settings.role")}
            </label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full px-3 py-2 rounded border border-border bg-bg text-ink font-serif text-sm focus:outline-none focus:border-ink"
            >
              {ROLE_OPTIONS.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.icon} {t(r.key as any)}
                </option>
              ))}
            </select>
            <p className="text-ink-3 text-xs font-serif mt-1">
              {t("settings.role_hint")}
            </p>
          </div>

          {error && <p className="text-red font-serif text-xs">{error}</p>}
          <button type="submit" disabled={saving} className="btn-primary disabled:opacity-40">
            {saving ? "…" : saved ? `✓ ${t("settings.saved_success")}` : t("settings.save_profile")}
          </button>
        </form>
      </section>

      {/* Language */}
      <section className="card p-6 mb-5">
        <h2 className="font-syne font-bold text-base text-ink mb-1">🌐 {t("settings.language")}</h2>
        <p className="font-serif text-ink-3 text-sm mb-4">{t("settings.language_hint")}</p>
        <div className="flex flex-wrap gap-2">
          {(["en", "ru", "ar", "tr", "de", "fr", "es"] as const).map((lang) => (
            <button
              key={lang}
              onClick={() => setLocale(lang)}
              className={`px-4 py-1.5 rounded-full font-syne font-semibold text-sm border transition-colors ${
                locale === lang
                  ? "bg-ink text-white border-ink"
                  : "border-border text-ink-3 hover:border-ink-3 hover:text-ink"
              }`}
            >
              {t(`settings.languages.${lang}` as any) || lang}
            </button>
          ))}
        </div>
      </section>

      {/* Learning preferences */}
      <section className="card p-6 mb-5">
        <h2 className="font-syne font-bold text-base text-ink mb-4">{t("settings.learning_preferences")}</h2>
        <div className="space-y-5">
          {/* Daily goal */}
          <div>
            <label className="block font-syne font-semibold text-xs text-ink-2 mb-1">
              {t("settings.daily_goal")}
            </label>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min={5}
                max={120}
                step={5}
                value={dailyGoal}
                onChange={e => setDailyGoal(Number(e.target.value))}
                className="flex-1 accent-ink"
              />
              <span className="font-syne font-bold text-sm text-ink w-20 text-right">{t("settings.daily_goal_value", { goal: String(dailyGoal) })}</span>
            </div>
            <div className="flex justify-between text-[10px] font-serif text-ink-3 mt-1">
              <span>{t("settings.daily_goal_range_min")}</span>
              <span>{t("settings.daily_goal_range_max")}</span>
            </div>
          </div>

          {/* Email notifications */}
          <div className="flex items-center justify-between">
            <div>
              <div className="font-syne font-semibold text-sm text-ink">{t("settings.email_notifications")}</div>
              <div className="font-serif text-xs text-ink-3">{t("settings.email_notifications_hint")}</div>
            </div>
            <div
              onClick={() => setEmailNotifs(v => !v)}
              className={`relative w-11 h-6 rounded-full transition-colors cursor-pointer ${emailNotifs ? "bg-green" : "bg-border-2"}`}
            >
              <div className={`absolute top-1 w-4 h-4 bg-white rounded-full shadow transition-transform ${emailNotifs ? "translate-x-6" : "translate-x-1"}`} />
            </div>
          </div>
        </div>
      </section>

      {/* Veterinary mode */}
      <section className="card p-6 mb-5">
        <h2 className="font-syne font-bold text-base text-ink mb-1">🐾 {t("settings.veterinary_mode")}</h2>
        <p className="font-serif text-ink-3 text-sm mb-4">{t("settings.vet_description")}</p>
        {canUseVet ? (
          <div className="space-y-4">
            <label className="flex items-center gap-3 cursor-pointer select-none">
              <div
                onClick={() => setVetMode((v) => !v)}
                className={`relative w-11 h-6 rounded-full transition-colors ${
                  vetMode ? "bg-green" : "bg-border-2"
                }`}
              >
                <div
                  className={`absolute top-1 w-4 h-4 bg-white rounded-full shadow transition-transform ${
                    vetMode ? "translate-x-6" : "translate-x-1"
                  }`}
                />
              </div>
              <span className="font-syne font-semibold text-sm text-ink">
                {t("settings.veterinary_mode")} {vetMode ? t("settings.vet_on") : t("settings.vet_off")}
              </span>
            </label>
            {vetMode && (
              <div>
                <p className="font-syne font-semibold text-xs text-ink-2 mb-2">
                  {t("settings.vet_species")}:
                </p>
                <div className="flex flex-wrap gap-2">
                  {ALL_SPECIES.map((sp) => (
                    <button
                      key={sp.id}
                      type="button"
                      onClick={() => toggleSpecies(sp.id)}
                      className={`px-3 py-1 rounded-full text-xs font-syne font-semibold border transition-colors ${
                        vetSpecies.includes(sp.id)
                          ? "bg-ink text-white border-ink"
                          : "bg-surface-2 text-ink-2 border-border hover:border-ink"
                      }`}
                    >
                      {sp.label}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <div className="relative w-11 h-6 rounded-full bg-border-2 opacity-50 cursor-not-allowed">
              <div className="absolute top-1 left-1 w-4 h-4 bg-white rounded-full shadow" />
            </div>
            <span className="font-serif text-ink-3 text-sm">
              {t("settings.vet_pro_only")}{" "}
              <Link href="/pricing" className="text-blue underline">{t("common.upgrade")}</Link>
            </span>
          </div>
        )}
      </section>

      {/* Subscription */}
      <section className="card p-6 mb-5">
        <h2 className="font-syne font-bold text-base text-ink mb-3">{t("settings.subscription")}</h2>
        <div className="flex items-center gap-3">
          <span className={`badge px-3 py-1 ${TIER_COLORS[sub] ?? TIER_COLORS.free}`}>
            {sub.charAt(0).toUpperCase() + sub.slice(1)}
          </span>
        </div>
        {sub === "free" && (
          <div className="mt-4">
            <Link href="/pricing" className="btn-primary inline-block">
              {t("common.upgrade")}
            </Link>
          </div>
        )}
        {sub !== "free" && sub !== "lifetime" && (
          <div className="mt-4">
            <a
              href="/api/v1/payments/portal"
              target="_blank"
              className="btn-secondary inline-block text-sm"
            >
              {t("settings.manage_billing")}
            </a>
          </div>
        )}
      </section>

      {/* GDPR / Privacy */}
      <GDPRSection />

      {/* Leaderboard */}
      <LeaderboardSection />

      {/* Account */}
      <section className="card p-6">
        <h2 className="font-syne font-bold text-base text-ink mb-3">{t("settings.account")}</h2>
        <p className="font-serif text-ink-3 text-sm mb-4">
          {t("settings.member_since")} {user?.created_at ? new Date(user.created_at).toLocaleDateString() : "—"}
        </p>
        <button
          onClick={() => { logout(); window.location.href = "/login"; }}
          className="btn-secondary text-red border-red/30 hover:bg-red-light"
        >
          {t("settings.sign_out")}
        </button>
      </section>
    </div>
  );
}

function GDPRSection() {
  const { logout } = useAuthStore();
  const t = useT();
  const [exporting, setExporting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [exportDone, setExportDone] = useState(false);
  const [error, setError] = useState("");

  const handleExport = async () => {
    setExporting(true);
    setError("");
    try {
      const res = await complianceApi.exportData();
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `medmind-data-export-${new Date().toISOString().split("T")[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
      setExportDone(true);
      setTimeout(() => setExportDone(false), 3000);
    } catch {
      setError(t("compliance.export_error"));
    } finally {
      setExporting(false);
    }
  };

  const handleDeleteAccount = async () => {
    setDeleting(true);
    setError("");
    try {
      await complianceApi.deleteAccount();
      logout();
      window.location.href = "/";
    } catch {
      setError(t("compliance.delete_error"));
      setDeleting(false);
    }
  };

  return (
    <section className="card p-6 mb-5">
      <h2 className="font-syne font-bold text-base text-ink mb-1">🔒 {t("settings.privacy")}</h2>
      <p className="font-serif text-ink-3 text-sm mb-4">
        {t("settings.gdpr_desc")}
      </p>

      {error && <p className="font-serif text-red text-xs mb-3">{error}</p>}

      <div className="space-y-3">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="font-syne font-semibold text-sm text-ink">{t("settings.export_data")}</p>
            <p className="font-serif text-ink-3 text-xs">{t("settings.export_gdpr_hint")}</p>
          </div>
          <button
            onClick={handleExport}
            disabled={exporting}
            className="btn-secondary text-sm shrink-0 disabled:opacity-40"
          >
            {exporting ? "…" : exportDone ? "✓" : `${t("settings.export_data")} →`}
          </button>
        </div>

        <hr className="border-border" />

        <div>
          <p className="font-syne font-semibold text-sm text-ink">{t("settings.delete_account")}</p>
          <p className="font-serif text-ink-3 text-xs mb-2">
            {t("settings.delete_gdpr_hint")}
          </p>
          {!confirmDelete ? (
            <button
              onClick={() => setConfirmDelete(true)}
              className="btn-secondary text-red border-red/30 hover:bg-red-light text-sm"
            >
              {t("settings.delete_account")}
            </button>
          ) : (
            <div className="p-3 rounded bg-red-light border border-red/30">
              <p className="font-syne font-semibold text-sm text-red mb-2">
                {t("settings.delete_confirm")}
              </p>
              <div className="flex gap-2">
                <button
                  onClick={handleDeleteAccount}
                  disabled={deleting}
                  className="px-4 py-1.5 rounded bg-red text-white font-syne font-semibold text-xs hover:bg-red/90 disabled:opacity-40"
                >
                  {deleting ? "…" : t("settings.yes_delete_permanently")}
                </button>
                <button
                  onClick={() => setConfirmDelete(false)}
                  className="btn-secondary text-xs"
                >
                  {t("common.cancel")}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

function LeaderboardSection() {
  const t = useT();
  const [optIn, setOptIn] = useState(false);
  const [displayName, setDisplayName] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveOk, setSaveOk] = useState(false);

  // Lazy-load current settings on first render
  useState(() => {
    progressApi.getGamificationMe?.()
      .then((d: any) => {
        setOptIn(d.leaderboard_opt_in ?? false);
        setDisplayName(d.leaderboard_display_name ?? "");
        setLoaded(true);
      })
      .catch(() => setLoaded(true));
  });

  const handleSave = async () => {
    setSaving(true);
    try {
      await progressApi.updateLeaderboardSettings?.({ leaderboard_opt_in: optIn, leaderboard_display_name: displayName });
      setSaveOk(true);
      setTimeout(() => setSaveOk(false), 2000);
    } catch {}
    setSaving(false);
  };

  return (
    <section className="card p-6 mb-5">
      <h2 className="font-syne font-bold text-base text-ink mb-1">{t("settings.leaderboard_section")}</h2>
      <p className="font-serif text-xs text-ink-3 mb-4">
        {t("settings.leaderboard_desc")}
      </p>
      <div className="space-y-4">
        <label className="flex items-center gap-3 cursor-pointer">
          <div
            onClick={() => setOptIn((v) => !v)}
            className={`w-10 h-5 rounded-full transition-colors relative flex-shrink-0 ${optIn ? "bg-ink" : "bg-bg-3"}`}
          >
            <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${optIn ? "translate-x-5" : "translate-x-0.5"}`} />
          </div>
          <span className="font-serif text-sm text-ink">{t("settings.leaderboard_opt_in")}</span>
        </label>
        {optIn && (
          <div>
            <label className="font-serif text-xs text-ink-3 block mb-1">{t("settings.leaderboard_display_name")}</label>
            <input
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder={t("settings.leaderboard_name_hint")}
              maxLength={100}
              className="w-full border border-border rounded-lg px-3 py-2 font-serif text-sm focus:outline-none focus:border-ink bg-bg"
            />
          </div>
        )}
        <button onClick={handleSave} disabled={saving} className="btn-primary text-sm px-4 py-2">
          {saving ? t("common.saving") : saveOk ? t("common.saved") : t("common.save")}
        </button>
      </div>
    </section>
  );
}
