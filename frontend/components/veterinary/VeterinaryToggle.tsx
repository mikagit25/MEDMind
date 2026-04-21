"use client";

import { useState } from "react";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

export function VeterinaryToggle() {
  const { user, updateUser } = useAuthStore();
  const vetMode = user?.preferences?.vet_mode ?? false;
  const [loading, setLoading] = useState(false);

  const toggle = async () => {
    setLoading(true);
    try {
      const currentSpecies = (user?.preferences?.vet_species as string[]) ?? [];
      await authApi.updateVetSettings({ vet_mode: !vetMode, species: currentSpecies });
      updateUser({ preferences: { ...(user?.preferences ?? {}), vet_mode: !vetMode } });
    } catch {
      alert("Failed to update veterinary mode.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center gap-3">
      <button
        onClick={toggle}
        disabled={loading}
        className={`w-12 h-6 rounded-full transition-colors shrink-0 ${
          vetMode ? "bg-green-500" : "bg-surface-3"
        } ${loading ? "opacity-50" : ""}`}
        aria-label="Toggle veterinary mode"
      >
        <span className={`block w-5 h-5 rounded-full bg-white shadow mx-0.5 transition-transform ${
          vetMode ? "translate-x-6" : "translate-x-0"
        }`} />
      </button>
      <div>
        <div className="font-semibold text-sm text-ink">Veterinary Mode</div>
        <div className="text-xs text-ink-3">
          {vetMode ? "🐾 Active — showing vet content" : "Switch to veterinary curriculum"}
        </div>
      </div>
    </div>
  );
}
