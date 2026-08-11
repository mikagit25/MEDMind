"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { useT } from "@/lib/i18n";
import Link from "next/link";
import {
  TrendingUp, Users, MousePointerClick, DollarSign,
  Copy, CheckCircle2, Clock, ExternalLink, AlertCircle,
  Loader2, ArrowRight,
} from "lucide-react";

interface AffiliateProfile {
  id: string;
  code: string;
  status: string;
  commission_type: string;
  commission_value: number;
  payout_info: { type: string; address: string };
  total_clicks: number;
  total_signups: number;
  total_conversions: number;
  total_earned: number;
  total_paid: number;
  pending_payout: number;
  referral_url: string;
  cookie_days: number;
}

interface Conversion {
  id: string;
  event_type: string;
  tier: string | null;
  amount_paid: number | null;
  commission_amount: number | null;
  is_paid_out: boolean;
  created_at: string;
}

export default function PartnerPage() {
  const t = useT();
  const { user } = useAuthStore();
  const [profile, setProfile] = useState<AffiliateProfile | null>(null);
  const [conversions, setConversions] = useState<Conversion[]>([]);
  const [loading, setLoading] = useState(true);
  const [noAffiliate, setNoAffiliate] = useState(false);
  const [copied, setCopied] = useState(false);
  const [payoutMsg, setPayoutMsg] = useState("");
  const [payoutLoading, setPayoutLoading] = useState(false);

  const isAffiliate = user?.role === "affiliate" || user?.role === "admin";

  useEffect(() => {
    // Wait for auth store to hydrate before making authenticated request.
    // Dependency on user?.id ensures this re-runs once the user is loaded.
    if (!user?.id) return;

    api.get("/affiliate/me")
      .then((r: { data: AffiliateProfile }) => {
        setProfile(r.data);
        // Fetch conversions for active affiliates and admins
        if (r.data.status === "active" || user.role === "admin") {
          api.get("/affiliate/conversions")
            .then((cr: { data: Conversion[] }) => setConversions(cr.data))
            .catch(() => {});
        }
      })
      .catch(() => setNoAffiliate(true))
      .finally(() => setLoading(false));
  }, [user?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const copyLink = () => {
    if (!profile) return;
    navigator.clipboard.writeText(profile.referral_url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const requestPayout = async () => {
    setPayoutLoading(true);
    try {
      const r = await api.post("/affiliate/payout-request", {});
      setPayoutMsg(r.data.message);
    } catch (e: any) {
      setPayoutMsg(e.response?.data?.detail || t("common.error"));
    } finally {
      setPayoutLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-red" />
      </div>
    );
  }

  // Not an affiliate yet — show apply prompt
  if (noAffiliate || !profile) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16 text-center">
        <div className="w-16 h-16 bg-red/10 rounded-2xl flex items-center justify-center mx-auto mb-6">
          <TrendingUp className="w-8 h-8 text-red" />
        </div>
        <h1 className="text-3xl font-syne font-bold text-ink mb-4">
          {t("partner.not_affiliate_title")}
        </h1>
        <p className="text-ink-2 mb-8 leading-relaxed">
          {t("partner.not_affiliate_body")}
        </p>
        <Link
          href="/partner/apply"
          className="inline-flex items-center gap-2 bg-red text-white px-6 py-3 rounded-xl font-semibold hover:bg-red/90 transition-colors"
        >
          {t("partner.apply_cta")}
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    );
  }

  const commissionLabel =
    profile.commission_type === "percent"
      ? `${profile.commission_value}%`
      : `$${profile.commission_value}`;

  const statusColors: Record<string, string> = {
    active: "bg-green-100 text-green-700",
    pending: "bg-yellow-100 text-yellow-700",
    suspended: "bg-red-100 text-red-700",
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-syne font-bold text-ink">{t("partner.title")}</h1>
          <p className="text-ink-3 mt-1">{t("partner.subtitle")}</p>
        </div>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusColors[profile.status] || ""}`}>
          {t(`partner.status.${profile.status}`)}
        </span>
      </div>

      {profile.status === "pending" && (
        <div className="flex gap-3 bg-yellow-50 border border-yellow-200 rounded-xl p-4 text-yellow-800">
          <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
          <p className="text-sm">{t("partner.pending_notice")}</p>
        </div>
      )}

      {/* Stats grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { icon: MousePointerClick, label: t("partner.stat.clicks"), value: profile.total_clicks },
          { icon: Users, label: t("partner.stat.signups"), value: profile.total_signups },
          { icon: TrendingUp, label: t("partner.stat.conversions"), value: profile.total_conversions },
          { icon: DollarSign, label: t("partner.stat.earned"), value: `$${profile.total_earned.toFixed(2)}` },
        ].map(({ icon: Icon, label, value }) => (
          <div key={label} className="bg-bg-2 rounded-xl p-4">
            <div className="flex items-center gap-2 text-ink-3 text-sm mb-1">
              <Icon className="w-4 h-4" />
              {label}
            </div>
            <div className="text-2xl font-syne font-bold text-ink">{value}</div>
          </div>
        ))}
      </div>

      {/* Referral link + sharing */}
      <div className="bg-bg-2 rounded-xl p-5">
        <h2 className="font-syne font-semibold text-ink mb-3">{t("partner.your_link")}</h2>
        <div className="flex items-center gap-2 bg-bg rounded-lg border border-line p-3 mb-3">
          <ExternalLink className="w-4 h-4 text-ink-3 shrink-0" />
          <span className="text-ink-2 text-sm font-mono flex-1 truncate">{profile.referral_url}</span>
          <button
            onClick={copyLink}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-red text-white text-sm rounded-lg hover:bg-red/90 transition-colors shrink-0"
          >
            {copied ? <CheckCircle2 className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            {copied ? t("partner.copied") : t("partner.copy")}
          </button>
        </div>
        {/* Social sharing */}
        <div className="flex gap-2 flex-wrap">
          <a
            href={`https://wa.me/?text=${encodeURIComponent(`Study smarter for Gulf nursing exams with AI. Use my link: ${profile.referral_url}`)}`}
            target="_blank" rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-syne font-semibold rounded-lg border border-line text-ink-2 hover:border-green hover:text-green transition-colors"
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
            </svg>
            WhatsApp
          </a>
          <a
            href={`https://twitter.com/intent/tweet?text=${encodeURIComponent(`I use MedMind AI to study for nursing exams — try it with my link and get a bonus week:`)}&url=${encodeURIComponent(profile.referral_url)}`}
            target="_blank" rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-syne font-semibold rounded-lg border border-line text-ink-2 hover:border-ink hover:text-ink transition-colors"
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-4.714-6.231-5.401 6.231H2.744l7.73-8.835L1.254 2.25H8.08l4.253 5.622zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
            </svg>
            X / Twitter
          </a>
          <a
            href={`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(profile.referral_url)}`}
            target="_blank" rel="noopener noreferrer"
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-syne font-semibold rounded-lg border border-line text-ink-2 hover:border-blue-500 hover:text-blue-600 transition-colors"
          >
            <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
              <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
            </svg>
            LinkedIn
          </a>
        </div>
        <p className="text-xs text-ink-3 mt-3">
          {t("partner.cookie_notice", { days: profile.cookie_days })}
        </p>
      </div>

      {/* Commission + Payout */}
      <div className="grid md:grid-cols-2 gap-4">
        <div className="bg-bg-2 rounded-xl p-5">
          <h2 className="font-syne font-semibold text-ink mb-3">{t("partner.commission")}</h2>
          <div className="text-3xl font-bold text-red mb-1">{commissionLabel}</div>
          <p className="text-sm text-ink-3">
            {profile.commission_type === "percent" ? t("partner.per_payment") : t("partner.per_conversion")}
          </p>
        </div>
        <div className="bg-bg-2 rounded-xl p-5">
          <h2 className="font-syne font-semibold text-ink mb-1">{t("partner.payout")}</h2>
          <div className="text-3xl font-bold text-green-600 mb-1">${profile.pending_payout.toFixed(2)}</div>
          <p className="text-xs text-ink-3 mb-3">
            {t("partner.via")} {profile.payout_info?.type || "—"}: {profile.payout_info?.address || "—"}
          </p>
          {payoutMsg ? (
            <p className="text-sm text-green-600">{payoutMsg}</p>
          ) : (
            <button
              onClick={requestPayout}
              disabled={payoutLoading || profile.pending_payout < 10 || profile.status !== "active"}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {payoutLoading && <Loader2 className="w-4 h-4 animate-spin" />}
              {t("partner.request_payout")}
            </button>
          )}
        </div>
      </div>

      {/* Conversions table */}
      <div>
        <h2 className="font-syne font-semibold text-ink mb-3">{t("partner.conversions_title")}</h2>
        {conversions.length === 0 ? (
          <div className="text-ink-3 text-sm py-8 text-center">{t("partner.no_conversions")}</div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-line">
            <table className="w-full text-sm">
              <thead className="bg-bg-2 text-ink-3">
                <tr>
                  <th className="text-left px-4 py-3">{t("partner.col.date")}</th>
                  <th className="text-left px-4 py-3">{t("partner.col.type")}</th>
                  <th className="text-left px-4 py-3">{t("partner.col.tier")}</th>
                  <th className="text-right px-4 py-3">{t("partner.col.amount")}</th>
                  <th className="text-right px-4 py-3">{t("partner.col.commission")}</th>
                  <th className="text-center px-4 py-3">{t("partner.col.paid")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {conversions.map((c) => (
                  <tr key={c.id} className="hover:bg-bg-2/50 transition-colors">
                    <td className="px-4 py-3 text-ink-3 whitespace-nowrap">
                      {new Date(c.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        c.event_type === "subscription" ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-600"
                      }`}>
                        {t(`partner.event.${c.event_type}`)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-ink-2">{c.tier || "—"}</td>
                    <td className="px-4 py-3 text-right text-ink-2">
                      {c.amount_paid != null ? `$${c.amount_paid.toFixed(2)}` : "—"}
                    </td>
                    <td className="px-4 py-3 text-right font-semibold text-ink">
                      {c.commission_amount != null ? `$${c.commission_amount.toFixed(2)}` : "—"}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {c.is_paid_out
                        ? <CheckCircle2 className="w-4 h-4 text-green-500 mx-auto" />
                        : <Clock className="w-4 h-4 text-yellow-500 mx-auto" />}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
