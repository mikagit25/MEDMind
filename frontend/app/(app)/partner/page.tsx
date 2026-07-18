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
    if (!isAffiliate) { setLoading(false); setNoAffiliate(true); return; }
    Promise.all([
      api.get("/affiliate/me").then((r: { data: AffiliateProfile }) => setProfile(r.data)).catch(() => setNoAffiliate(true)),
      api.get("/affiliate/conversions").then((r: { data: Conversion[] }) => setConversions(r.data)).catch(() => {}),
    ]).finally(() => setLoading(false));
  }, [isAffiliate]);

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

      {/* Referral link */}
      <div className="bg-bg-2 rounded-xl p-5">
        <h2 className="font-syne font-semibold text-ink mb-3">{t("partner.your_link")}</h2>
        <div className="flex items-center gap-2 bg-bg rounded-lg border border-line p-3">
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
        <p className="text-xs text-ink-3 mt-2">
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
