"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuthStore } from "@/lib/store";
import { authApi, complianceApi } from "@/lib/api";
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

export default function SettingsPage() {
  const { user, updateUser, logout } = useAuthStore();
  const { locale, setLocale } = useI18n();
  const t = useT();
  const [firstName, setFirstName] = useState(user?.first_name ?? "");
  const [lastName, setLastName] = useState(user?.last_name ?? "");
  const [vetMode, setVetMode] = useState<boolean>((user?.preferences?.vet_mode as boolean) ?? false);
  const [vetSpecies, setVetSpecies] = useState<string[]>(
    (user?.preferences?.vet_species as string[]) ?? []
  );
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
        authApi.updateMe({ first_name: firstName, last_name: lastName }),
        canUseVet
          ? authApi.updateVetSettings({ vet_mode: vetMode, species: vetSpecies })
          : Promise.resolve(null),
      ]);
      updateUser(profileRes);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (err: any) {
      setError(err.response?.data?.detail ?? "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 max-w-2xl mx-auto w-full">
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
                {t("settings.veterinary_mode")} {vetMode ? "ON" : "OFF"}
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
              Available on Pro plan and above.{" "}
              <Link href="/pricing" className="text-blue underline">Upgrade</Link>
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
              Upgrade Plan
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

      {/* Account */}
      <section className="card p-6">
        <h2 className="font-syne font-bold text-base text-ink mb-3">Account</h2>
        <p className="font-serif text-ink-3 text-sm mb-4">
          Member since: {user?.created_at ? new Date(user.created_at).toLocaleDateString() : "—"}
        </p>
        <button
          onClick={() => { logout(); window.location.href = "/login"; }}
          className="btn-secondary text-red border-red/30 hover:bg-red-light"
        >
          Sign Out
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
      setError("Export failed. Please try again.");
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
      setError("Account deletion failed. Please contact support.");
      setDeleting(false);
    }
  };

  return (
    <section className="card p-6 mb-5">
      <h2 className="font-syne font-bold text-base text-ink mb-1">🔒 {t("settings.privacy")}</h2>
      <p className="font-serif text-ink-3 text-sm mb-4">
        Under GDPR you have the right to access, export, and delete your personal data.
      </p>

      {error && <p className="font-serif text-red text-xs mb-3">{error}</p>}

      <div className="space-y-3">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="font-syne font-semibold text-sm text-ink">{t("settings.export_data")}</p>
            <p className="font-serif text-ink-3 text-xs">Download all your data as JSON (Art. 20 GDPR)</p>
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
            Permanently anonymizes your personal data (Art. 17 GDPR). Learning progress data is retained anonymously.
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
                  {deleting ? "…" : "Yes, delete permanently"}
                </button>
                <button
                  onClick={() => setConfirmDelete(false)}
                  className="btn-secondary text-xs"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
