"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { useRouter } from "next/navigation";
import { TrendingUp, CheckCircle2, Loader2 } from "lucide-react";

export default function PartnerApplyPage() {
  const t = useT();
  const router = useRouter();
  const [form, setForm] = useState({
    code: "",
    payout_type: "paypal",
    payout_address: "",
    notes: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const update = (k: string, v: string) => setForm((p) => ({ ...p, [k]: v }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.post("/affiliate/apply", form);
      setSuccess(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || t("common.error"));
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="max-w-lg mx-auto px-4 py-16 text-center">
        <div className="w-16 h-16 bg-green-100 rounded-2xl flex items-center justify-center mx-auto mb-6">
          <CheckCircle2 className="w-8 h-8 text-green-600" />
        </div>
        <h1 className="text-2xl font-syne font-bold text-ink mb-3">{t("partner.apply_success_title")}</h1>
        <p className="text-ink-2 mb-6">{t("partner.apply_success_body")}</p>
        <button
          onClick={() => router.push("/partner")}
          className="px-6 py-3 bg-red text-white rounded-xl font-semibold hover:bg-red/90 transition-colors"
        >
          {t("partner.go_to_dashboard")}
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-xl mx-auto px-4 py-10">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 bg-red/10 rounded-xl flex items-center justify-center">
          <TrendingUp className="w-5 h-5 text-red" />
        </div>
        <div>
          <h1 className="text-xl font-syne font-bold text-ink">{t("partner.apply_title")}</h1>
          <p className="text-sm text-ink-3">{t("partner.apply_subtitle")}</p>
        </div>
      </div>

      {/* Benefits */}
      <div className="bg-bg-2 rounded-xl p-4 mb-6 space-y-2 text-sm text-ink-2">
        {[t("partner.benefit_1"), t("partner.benefit_2"), t("partner.benefit_3")].map((b) => (
          <div key={b} className="flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
            <span>{b}</span>
          </div>
        ))}
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label className="block text-sm font-medium text-ink mb-1">{t("partner.your_code")}</label>
          <input
            value={form.code}
            onChange={(e) => update("code", e.target.value.toUpperCase().replace(/[^A-Z0-9_]/g, ""))}
            placeholder="DR_SMITH"
            maxLength={30}
            required
            className="w-full bg-bg-2 border border-line rounded-lg px-3 py-2.5 text-ink focus:outline-none focus:border-red font-mono"
          />
          <p className="text-xs text-ink-3 mt-1">{t("partner.code_hint")}</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-ink mb-1">{t("partner.payout_method")}</label>
          <select
            value={form.payout_type}
            onChange={(e) => update("payout_type", e.target.value)}
            className="w-full bg-bg-2 border border-line rounded-lg px-3 py-2.5 text-ink focus:outline-none focus:border-red"
          >
            <option value="paypal">PayPal</option>
            <option value="bank">{t("partner.bank_transfer")}</option>
            <option value="crypto">Crypto (USDT/BTC)</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-ink mb-1">
            {form.payout_type === "paypal" ? "PayPal Email" : t("partner.payout_details")}
          </label>
          <input
            value={form.payout_address}
            onChange={(e) => update("payout_address", e.target.value)}
            placeholder={form.payout_type === "paypal" ? "your@paypal.com" : ""}
            required
            className="w-full bg-bg-2 border border-line rounded-lg px-3 py-2.5 text-ink focus:outline-none focus:border-red"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-ink mb-1">{t("partner.about_channel")}</label>
          <textarea
            value={form.notes}
            onChange={(e) => update("notes", e.target.value)}
            rows={3}
            placeholder={t("partner.about_placeholder")}
            className="w-full bg-bg-2 border border-line rounded-lg px-3 py-2.5 text-ink focus:outline-none focus:border-red resize-none"
          />
        </div>

        {error && <p className="text-red text-sm">{error}</p>}

        <button
          type="submit"
          disabled={loading}
          className="w-full flex items-center justify-center gap-2 bg-red text-white py-3 rounded-xl font-semibold hover:bg-red/90 transition-colors disabled:opacity-60"
        >
          {loading && <Loader2 className="w-4 h-4 animate-spin" />}
          {t("partner.submit_application")}
        </button>
      </form>
    </div>
  );
}
