"use client";

import { useState } from "react";
import Link from "next/link";
import { useAuthStore } from "@/lib/store";
import { authApi } from "@/lib/api";

const SUBSCRIPTION_INFO: Record<string, { label: string; color: string; desc: string }> = {
  free: { label: "Free", color: "bg-surface-2 text-ink-3", desc: "Access to fundamental modules only" },
  student: { label: "Student", color: "bg-blue-light text-blue", desc: "Full library access" },
  pro: { label: "Pro", color: "bg-amber-light text-amber", desc: "Full access including vet content & drugs" },
  clinic: { label: "Clinic", color: "bg-green-light text-green", desc: "Team access with analytics" },
  lifetime: { label: "Lifetime", color: "bg-ink text-white", desc: "Unlimited access forever" },
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
  const subInfo = SUBSCRIPTION_INFO[sub] ?? SUBSCRIPTION_INFO.free;
  const canUseVet = ["pro", "clinic", "lifetime"].includes(sub);

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
      // Save profile + vet settings in parallel
      const [profileRes] = await Promise.all([
        authApi.updateMe({ first_name: firstName, last_name: lastName }),
        canUseVet
          ? authApi.updateVetSettings(vetMode, vetSpecies)
          : Promise.resolve(null),
      ]);
      updateUser(profileRes.data);
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
      <h1 className="font-syne font-black text-2xl text-ink mb-6">Settings</h1>

      {/* Profile */}
      <section className="card p-6 mb-5">
        <h2 className="font-syne font-bold text-base text-ink mb-4">Profile</h2>
        <form onSubmit={handleSave} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-syne font-semibold text-xs text-ink-2 mb-1">First name</label>
              <input
                type="text"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                className="w-full px-3 py-2 rounded border border-border bg-bg text-ink font-serif text-sm focus:outline-none focus:border-ink"
              />
            </div>
            <div>
              <label className="block font-syne font-semibold text-xs text-ink-2 mb-1">Last name</label>
              <input
                type="text"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                className="w-full px-3 py-2 rounded border border-border bg-bg text-ink font-serif text-sm focus:outline-none focus:border-ink"
              />
            </div>
          </div>
          <div>
            <label className="block font-syne font-semibold text-xs text-ink-2 mb-1">Email</label>
            <input
              type="email"
              value={user?.email ?? ""}
              disabled
              className="w-full px-3 py-2 rounded border border-border bg-surface-2 text-ink-3 font-serif text-sm cursor-not-allowed"
            />
          </div>
          {error && <p className="text-red font-serif text-xs">{error}</p>}
          <button type="submit" disabled={saving} className="btn-primary disabled:opacity-40">
            {saving ? "Saving…" : saved ? "✓ Saved" : "Save Changes"}
          </button>
        </form>
      </section>

      {/* Veterinary mode */}
      <section className="card p-6 mb-5">
        <h2 className="font-syne font-bold text-base text-ink mb-1">🐾 Veterinary Mode</h2>
        <p className="font-serif text-ink-3 text-sm mb-4">
          Show veterinary content, species-specific dosing, and vet modules alongside human medicine.
        </p>
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
                {vetMode ? "Veterinary mode ON" : "Veterinary mode OFF"}
              </span>
            </label>
            {vetMode && (
              <div>
                <p className="font-syne font-semibold text-xs text-ink-2 mb-2">Select species you work with:</p>
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
        <h2 className="font-syne font-bold text-base text-ink mb-3">Subscription</h2>
        <div className="flex items-center gap-3">
          <span className={`badge px-3 py-1 ${subInfo.color}`}>{subInfo.label}</span>
          <span className="font-serif text-ink-3 text-sm">{subInfo.desc}</span>
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
              Manage Billing ↗
            </a>
          </div>
        )}
      </section>

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
