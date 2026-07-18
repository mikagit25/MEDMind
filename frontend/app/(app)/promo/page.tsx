"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { useT } from "@/lib/i18n";
import { Gift, CheckCircle2, XCircle, ArrowRight, Loader2 } from "lucide-react";
import Link from "next/link";

type ApplyResult = {
  type: string;
  tier?: string;
  expires_at?: string;
  message: string;
  discount_value?: number;
  code?: string;
};

export default function PromoPage() {
  const t = useT();
  const router = useRouter();
  const { user } = useAuthStore();
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ApplyResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleApply(e: React.FormEvent) {
    e.preventDefault();
    if (!code.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await api.post("/promo/apply", { code: code.trim() });
      setResult(res.data);
      // tier refreshes on next navigation / /auth/me call
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg || t("promo.err_generic"));
    } finally {
      setLoading(false);
    }
  }

  const tierLabel: Record<string, string> = {
    student: "Student",
    pro: "Pro",
    clinic: "Clinic",
  };

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-14 h-14 bg-ink rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Gift className="w-7 h-7 text-white" />
          </div>
          <h1 className="font-syne font-black text-2xl text-ink">{t("promo.title")}</h1>
          <p className="text-ink-3 font-serif text-sm mt-2">{t("promo.sub")}</p>
        </div>

        {/* Success state */}
        {result ? (
          <div className="bg-green/5 border border-green/30 rounded-2xl p-6 text-center space-y-4">
            <CheckCircle2 className="w-10 h-10 text-green mx-auto" />
            <div>
              {result.type === "trial" && result.tier ? (
                <>
                  <div className="font-syne font-black text-xl text-ink">
                    {tierLabel[result.tier] ?? result.tier} {t("promo.activated")}
                  </div>
                  {result.expires_at && (
                    <p className="text-ink-3 font-serif text-sm mt-1">
                      {t("promo.valid_until")} {new Date(result.expires_at).toLocaleDateString()}
                    </p>
                  )}
                </>
              ) : (
                <div className="font-syne font-bold text-base text-ink">{result.message}</div>
              )}
            </div>
            <button
              onClick={() => router.push("/dashboard")}
              className="font-syne font-bold text-sm bg-ink text-white px-6 py-3 rounded-xl hover:bg-red transition-colors flex items-center gap-2 mx-auto"
            >
              {t("promo.go_dashboard")} <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        ) : (
          /* Input form */
          <form onSubmit={handleApply} className="bg-surface border border-border rounded-2xl p-6 space-y-4">
            <div>
              <label className="block text-xs font-syne font-bold text-ink-3 uppercase tracking-wider mb-2">
                {t("promo.code_label")}
              </label>
              <input
                value={code}
                onChange={e => setCode(e.target.value.toUpperCase())}
                placeholder={t("promo.code_placeholder")}
                className="w-full bg-bg border border-border rounded-xl px-4 py-3 font-mono text-sm text-ink tracking-widest focus:outline-none focus:border-ink transition-colors uppercase"
                disabled={loading}
                autoFocus
              />
            </div>

            {error && (
              <div className="flex items-center gap-2 text-red text-sm font-serif bg-red/5 border border-red/20 rounded-xl px-4 py-3">
                <XCircle className="w-4 h-4 flex-shrink-0" />
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || !code.trim()}
              className="w-full font-syne font-bold text-sm bg-ink text-white py-3 rounded-xl hover:bg-red transition-colors disabled:opacity-40 flex items-center justify-center gap-2"
            >
              {loading ? (
                <><Loader2 className="w-4 h-4 animate-spin" /> {t("promo.applying")}</>
              ) : (
                t("promo.apply_cta")
              )}
            </button>

            {!user && (
              <p className="text-center text-xs font-serif text-ink-3">
                {t("promo.login_note")}{" "}
                <Link href="/login" className="text-ink underline">{t("promo.login_link")}</Link>
              </p>
            )}
          </form>
        )}

        <p className="text-center text-xs font-serif text-ink-3 mt-6">
          <Link href="/pricing" className="hover:text-ink transition-colors">{t("promo.view_plans")}</Link>
          {" · "}
          <Link href="/dashboard" className="hover:text-ink transition-colors">{t("promo.go_home")}</Link>
        </p>
      </div>
    </div>
  );
}
