"use client";

import { useEffect, useState } from "react";
import { complianceApi } from "@/lib/api";
import { useT } from "@/lib/i18n";

const CONSENT_LABELS: Record<string, { label: string; description: string }> = {
  data_processing: {
    label: "Data Processing",
    description: "We process your personal data to provide the educational service.",
  },
  analytics: {
    label: "Analytics",
    description: "Help us improve by sharing anonymous usage data.",
  },
  marketing: {
    label: "Marketing",
    description: "Receive tips, updates, and news about new content.",
  },
};

interface Consent {
  consent_type: string;
  given: boolean;
  given_at: string | null;
}

export default function CompliancePage() {
  const t = useT();
  const [consents, setConsents]     = useState<Consent[]>([]);
  const [loading, setLoading]       = useState(true);
  const [exporting, setExporting]   = useState(false);
  const [deleting, setDeleting]     = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [exportDone, setExportDone] = useState(false);

  useEffect(() => {
    complianceApi.getConsents()
      .then((data: any) => setConsents(data.consents ?? []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const toggleConsent = async (type: string, current: boolean) => {
    await complianceApi.updateConsent(type, !current);
    setConsents(prev =>
      prev.map(c => c.consent_type === type ? { ...c, given: !current } : c)
    );
  };

  const exportData = async () => {
    setExporting(true);
    try {
      const data = await complianceApi.exportData();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `medmind-data-export-${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
      setExportDone(true);
    } catch {
      alert("Export failed. Please try again.");
    } finally {
      setExporting(false);
    }
  };

  const deleteAccount = async () => {
    setDeleting(true);
    try {
      await complianceApi.deleteAccount();
      window.location.href = "/auth/login";
    } catch {
      alert("Account deletion failed. Please contact support.");
      setDeleting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto py-8 px-4 space-y-8">
      <div>
        <h1 className="font-syne font-black text-2xl text-ink">{t("compliance.title")}</h1>
        <p className="text-ink-3 text-sm mt-1">Manage your data and GDPR rights</p>
      </div>

      {/* Consent Manager */}
      <section className="card p-6 space-y-4">
        <h2 className="font-syne font-bold text-base text-ink">Consent Settings</h2>
        {loading ? (
          <div className="text-ink-3 text-sm">Loading…</div>
        ) : (
          Object.entries(CONSENT_LABELS).map(([type, meta]) => {
            const consent = consents.find(c => c.consent_type === type);
            const given = consent?.given ?? false;
            return (
              <div key={type} className="flex items-start gap-4">
                <button
                  onClick={() => toggleConsent(type, given)}
                  className={`mt-0.5 w-10 h-6 rounded-full transition-colors shrink-0 ${
                    given ? "bg-accent" : "bg-surface-3"
                  }`}
                  aria-label={`Toggle ${meta.label}`}
                >
                  <span className={`block w-4 h-4 rounded-full bg-white mx-auto transition-transform ${
                    given ? "translate-x-2" : "-translate-x-2"
                  }`} />
                </button>
                <div>
                  <div className="font-semibold text-sm text-ink">{meta.label}</div>
                  <div className="text-xs text-ink-3 mt-0.5">{meta.description}</div>
                  {consent?.given_at && given && (
                    <div className="text-xs text-ink-3 mt-0.5">
                      Consented: {new Date(consent.given_at).toLocaleDateString()}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </section>

      {/* Data Export */}
      <section className="card p-6">
        <h2 className="font-syne font-bold text-base text-ink mb-2">Export Your Data</h2>
        <p className="text-xs text-ink-3 mb-4">
          Download a copy of all your personal data (profile, progress, AI conversations).
        </p>
        <button
          onClick={exportData}
          disabled={exporting}
          className="btn-primary text-sm"
        >
          {exporting ? "Preparing…" : exportDone ? "✓ Downloaded" : "Download my data"}
        </button>
      </section>

      {/* Delete Account */}
      <section className="card p-6 border border-red-200 dark:border-red-900">
        <h2 className="font-syne font-bold text-base text-red-600 mb-2">Delete Account</h2>
        <p className="text-xs text-ink-3 mb-4">
          Permanently delete your account and all associated data. This action is irreversible.
        </p>
        {!deleteConfirm ? (
          <button
            onClick={() => setDeleteConfirm(true)}
            className="btn text-sm border border-red-400 text-red-500 hover:bg-red-50 dark:hover:bg-red-950"
          >
            Delete my account
          </button>
        ) : (
          <div className="space-y-3">
            <p className="text-sm font-semibold text-red-600">
              Are you sure? This cannot be undone.
            </p>
            <div className="flex gap-3">
              <button
                onClick={deleteAccount}
                disabled={deleting}
                className="btn text-sm bg-red-600 text-white hover:bg-red-700"
              >
                {deleting ? "Deleting…" : "Yes, delete everything"}
              </button>
              <button
                onClick={() => setDeleteConfirm(false)}
                className="btn text-sm"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
