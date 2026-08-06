"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

const DOMAINS = [
  "scope_of_practice",
  "medication_administration",
  "consent",
  "end_of_life",
  "documentation_reporting",
  "infection_control",
  "patient_rights",
  "cultural_religious_care",
  "region_salient_clinical",
  "emergency_activation",
];

type RuleCounts = { verified: number; needs_human: number; unverified: number };

type JurisdictionSummary = {
  slug: string;
  country: string;
  regulator: string;
  exam_slugs: string[];
  locale_primary: string;
  status: string;
  verified_at: string | null;
  overdue: boolean;
  rule_counts: RuleCounts;
  total_rules: number;
  missing_domains: string[];
};

type JurisdictionRule = {
  id: string;
  rule_key: string;
  statement: string;
  source_title: string | null;
  source_url: string | null;
  source_type: string | null;
  status: string;
  divergence_from_us: boolean;
  verified_at: string | null;
  verified_by: string | null;
};

type JurisdictionDetail = {
  slug: string;
  country: string;
  regulator: string;
  exam_slugs: string[];
  rules_by_domain: Record<string, JurisdictionRule[]>;
};

const STATUS_COLORS: Record<string, string> = {
  verified: "bg-green-100 text-green-800",
  needs_human: "bg-amber-100 text-amber-800",
  unverified: "bg-gray-100 text-gray-600",
};

const DOMAIN_LABELS: Record<string, string> = {
  scope_of_practice: "Scope of Practice",
  medication_administration: "Medication Administration",
  consent: "Consent",
  end_of_life: "End of Life",
  documentation_reporting: "Documentation & Reporting",
  infection_control: "Infection Control",
  patient_rights: "Patient Rights",
  cultural_religious_care: "Cultural & Religious Care",
  region_salient_clinical: "Regional Clinical Topics",
  emergency_activation: "Emergency Activation",
};

export default function JurisdictionsAdminPage() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const [profiles, setProfiles] = useState<JurisdictionSummary[]>([]);
  const [selected, setSelected] = useState<JurisdictionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [requestingReview, setRequestingReview] = useState<string | null>(null);
  const [reviewMsg, setReviewMsg] = useState<Record<string, string>>({});

  useEffect(() => {
    if (user && user.role !== "admin") router.push("/dashboard");
  }, [user, router]);

  useEffect(() => {
    fetchProfiles();
  }, []);

  async function fetchProfiles() {
    setLoading(true);
    try {
      const res = await api.get("/admin/jurisdictions");
      setProfiles(res.data);
    } catch {
      // handled silently
    } finally {
      setLoading(false);
    }
  }

  async function openDetail(slug: string) {
    setDetailLoading(true);
    try {
      const res = await api.get(`/admin/jurisdictions/${slug}`);
      setSelected(res.data);
    } finally {
      setDetailLoading(false);
    }
  }

  async function requestHumanReview(slug: string) {
    setRequestingReview(slug);
    try {
      const res = await api.post(`/admin/jurisdictions/${slug}/request-human-review`);
      setReviewMsg((m) => ({ ...m, [slug]: res.data.message }));
    } finally {
      setRequestingReview(null);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-500">Loading jurisdiction profiles...</div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Jurisdiction Profiles</h1>
        <p className="text-sm text-gray-500 mt-1">
          Gulf nursing exam jurisdiction rules — Phase L1. All norms must have a source URL before
          being set to <span className="font-mono">verified</span>.
        </p>
      </div>

      {/* Summary grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        {profiles.map((p) => (
          <div
            key={p.slug}
            className={`border rounded-lg p-4 cursor-pointer hover:border-blue-400 transition-colors ${
              selected?.slug === p.slug ? "border-blue-500 bg-blue-50" : "border-gray-200"
            } ${p.overdue ? "border-l-4 border-l-red-400" : ""}`}
            onClick={() => openDetail(p.slug)}
          >
            <div className="flex items-start justify-between">
              <div>
                <div className="font-semibold text-gray-900">{p.country}</div>
                <div className="text-xs text-gray-500">{p.regulator} · {p.exam_slugs.join(", ")}</div>
              </div>
              {p.overdue && (
                <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded">Overdue</span>
              )}
            </div>

            {/* Rule status bar */}
            <div className="mt-3 flex gap-2 flex-wrap">
              <span className="text-xs px-2 py-0.5 rounded bg-green-100 text-green-800">
                {p.rule_counts.verified} verified
              </span>
              <span className="text-xs px-2 py-0.5 rounded bg-amber-100 text-amber-800">
                {p.rule_counts.needs_human} needs human
              </span>
              {p.rule_counts.unverified > 0 && (
                <span className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600">
                  {p.rule_counts.unverified} unverified
                </span>
              )}
            </div>

            {p.missing_domains.length > 0 && (
              <div className="mt-2 text-xs text-red-600">
                Missing: {p.missing_domains.map((d) => DOMAIN_LABELS[d] ?? d).join(", ")}
              </div>
            )}

            {/* Actions */}
            <div className="mt-3 flex gap-2">
              <button
                className="text-xs bg-amber-50 border border-amber-300 text-amber-700 px-3 py-1 rounded hover:bg-amber-100 disabled:opacity-50"
                disabled={requestingReview === p.slug}
                onClick={(e) => {
                  e.stopPropagation();
                  requestHumanReview(p.slug);
                }}
              >
                {requestingReview === p.slug ? "..." : "Request Human Review"}
              </button>
            </div>
            {reviewMsg[p.slug] && (
              <div className="mt-2 text-xs text-green-700">{reviewMsg[p.slug]}</div>
            )}
          </div>
        ))}
      </div>

      {/* Detail panel */}
      {detailLoading && (
        <div className="text-center text-gray-500 py-8">Loading rules...</div>
      )}

      {selected && !detailLoading && (
        <div className="border rounded-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-900">
              {selected.country}
              <span className="ml-2 text-sm font-normal text-gray-500">({selected.regulator})</span>
            </h2>
            <button
              className="text-sm text-gray-500 hover:text-gray-700"
              onClick={() => setSelected(null)}
            >
              Close
            </button>
          </div>

          <div className="space-y-6">
            {DOMAINS.map((domain) => {
              const rules = selected.rules_by_domain[domain] ?? [];
              return (
                <div key={domain}>
                  <h3 className="font-semibold text-gray-800 mb-2 flex items-center gap-2">
                    {DOMAIN_LABELS[domain]}
                    {rules.length === 0 && (
                      <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded">
                        Missing
                      </span>
                    )}
                  </h3>
                  {rules.length === 0 ? (
                    <p className="text-sm text-gray-400 italic">No rules seeded — needs human review.</p>
                  ) : (
                    <div className="space-y-3">
                      {rules.map((rule) => (
                        <div key={rule.id} className="bg-gray-50 rounded p-3 text-sm">
                          <div className="flex items-start justify-between gap-2">
                            <span className="font-mono text-xs text-gray-500">{rule.rule_key}</span>
                            <div className="flex gap-1 flex-shrink-0">
                              <span
                                className={`text-xs px-2 py-0.5 rounded ${STATUS_COLORS[rule.status] ?? "bg-gray-100 text-gray-600"}`}
                              >
                                {rule.status}
                              </span>
                              {rule.divergence_from_us && (
                                <span className="text-xs px-2 py-0.5 rounded bg-purple-100 text-purple-700">
                                  diverges from US
                                </span>
                              )}
                            </div>
                          </div>
                          <p className="mt-1 text-gray-700">{rule.statement}</p>
                          {rule.source_url ? (
                            <a
                              href={rule.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="mt-1 text-xs text-blue-600 hover:underline block"
                            >
                              {rule.source_title ?? rule.source_url}
                            </a>
                          ) : (
                            <span className="mt-1 text-xs text-red-500 block">
                              No source URL — cannot be verified automatically
                            </span>
                          )}
                          {rule.verified_at && (
                            <span className="text-xs text-gray-400">
                              Verified {new Date(rule.verified_at).toLocaleDateString()} by {rule.verified_by}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
