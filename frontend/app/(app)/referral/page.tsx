"use client";

import { useState, useEffect } from "react";
import { referralApi } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { Copy, Check, Gift, Users, CalendarDays, ArrowRight } from "lucide-react";

type ReferralInfo = {
  code: string;
  referral_url: string;
  referred_count: number;
  total_days_earned: number;
  reward_per_referral: number;
  new_user_bonus: number;
};

function CopyButton({ text, label, copiedLabel }: { text: string; label: string; copiedLabel: string }) {
  const [copied, setCopied] = useState(false);
  async function handleCopy() {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }
  return (
    <button onClick={handleCopy}
      className="flex items-center gap-1.5 font-syne font-semibold text-xs px-3 py-1.5 rounded-lg border border-border hover:border-border-2 hover:text-ink transition-colors text-ink-2">
      {copied ? <Check size={13} /> : <Copy size={13} />}
      {copied ? copiedLabel : label}
    </button>
  );
}

export default function ReferralPage() {
  const t = useT();
  const [info, setInfo] = useState<ReferralInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [applyCode, setApplyCode] = useState("");
  const [applyStatus, setApplyStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [applyMsg, setApplyMsg] = useState("");

  useEffect(() => {
    referralApi.getInfo()
      .then(setInfo)
      .finally(() => setLoading(false));
  }, []);

  async function handleApply() {
    if (!applyCode.trim()) return;
    setApplyStatus("loading");
    setApplyMsg("");
    try {
      const result = await referralApi.applyCode(applyCode.trim().toUpperCase());
      setApplyStatus("success");
      setApplyMsg(t("referral.apply_success").replace("{days}", String(result.message?.match(/\d+/)?.[0] ?? "7")));
      setApplyCode("");
    } catch (e: any) {
      setApplyStatus("error");
      const detail = e?.response?.data?.detail ?? "";
      if (detail.includes("already used")) setApplyMsg(t("referral.apply_error_used"));
      else if (detail.includes("30 days")) setApplyMsg(t("referral.apply_error_late"));
      else if (detail.includes("own")) setApplyMsg(t("referral.apply_error_own"));
      else if (detail.includes("not found")) setApplyMsg(t("referral.apply_error_invalid"));
      else setApplyMsg(detail || "Something went wrong.");
    }
  }

  return (
    <div className="flex-1 overflow-y-auto p-3 sm:p-6 max-w-2xl mx-auto w-full">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-amber/10 flex items-center justify-center flex-shrink-0">
          <Gift size={20} className="text-amber" />
        </div>
        <div>
          <h1 className="font-syne font-black text-2xl text-ink">{t("referral.title")}</h1>
          <p className="font-serif text-ink-3 text-sm">{t("referral.subtitle")}</p>
        </div>
      </div>

      {loading ? (
        <div className="card p-8 flex items-center justify-center">
          <div className="w-6 h-6 border-2 border-ink-3 border-t-ink rounded-full animate-spin" />
        </div>
      ) : info ? (
        <>
          {/* Your code */}
          <div className="card p-5 mb-4">
            <p className="font-syne font-semibold text-xs text-ink-2 mb-3">{t("referral.your_code")}</p>
            <div className="flex items-center gap-3">
              <div className="flex-1 bg-surface-2 rounded-xl px-4 py-3 border border-border">
                <span className="font-syne font-black text-2xl text-ink tracking-[0.2em]">{info.code}</span>
              </div>
              <CopyButton text={info.code} label={t("referral.copy")} copiedLabel={t("referral.copied")} />
            </div>
          </div>

          {/* Share link */}
          <div className="card p-5 mb-4">
            <p className="font-syne font-semibold text-xs text-ink-2 mb-2">{t("referral.share_link")}</p>
            <div className="flex items-center gap-2">
              <div className="flex-1 min-w-0 bg-surface-2 rounded-lg px-3 py-2 border border-border">
                <p className="font-serif text-xs text-ink-3 truncate">{info.referral_url}</p>
              </div>
              <CopyButton text={info.referral_url} label={t("referral.copy_link")} copiedLabel={t("referral.copied")} />
            </div>
          </div>

          {/* Stats */}
          <div className="card p-5 mb-4">
            <p className="font-syne font-semibold text-xs text-ink-2 mb-3">{t("referral.stats_title")}</p>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-surface-2 rounded-xl p-4 text-center">
                <Users size={18} className="text-ink-3 mx-auto mb-1" />
                <p className="font-syne font-black text-2xl text-ink">{info.referred_count}</p>
                <p className="font-serif text-[11px] text-ink-3">{t("referral.friends_joined")}</p>
              </div>
              <div className="bg-surface-2 rounded-xl p-4 text-center">
                <CalendarDays size={18} className="text-ink-3 mx-auto mb-1" />
                <p className="font-syne font-black text-2xl text-ink">{info.total_days_earned}</p>
                <p className="font-serif text-[11px] text-ink-3">{t("referral.days_earned")}</p>
              </div>
            </div>
            <div className="mt-3 flex gap-2 flex-wrap">
              <span className="bg-amber/10 text-amber font-syne font-semibold text-xs px-3 py-1 rounded-full">
                +{info.reward_per_referral} {t("referral.reward_per_ref")}
              </span>
              <span className="bg-green/10 text-green font-syne font-semibold text-xs px-3 py-1 rounded-full">
                +{info.new_user_bonus} {t("referral.new_user_bonus")}
              </span>
            </div>
          </div>

          {/* How it works */}
          <div className="card p-5 mb-4">
            <p className="font-syne font-semibold text-xs text-ink-2 mb-3">{t("referral.how_it_works")}</p>
            <div className="space-y-2">
              {[t("referral.step1"), t("referral.step2"), t("referral.step3")].map((step, i) => (
                <div key={i} className="flex items-start gap-3">
                  <div className="w-5 h-5 rounded-full bg-ink flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-white font-syne font-black text-[10px]">{i + 1}</span>
                  </div>
                  {i < 2 ? (
                    <div className="flex items-start gap-2 flex-1">
                      <p className="font-serif text-sm text-ink flex-1">{step}</p>
                      <ArrowRight size={14} className="text-ink-3 mt-0.5 flex-shrink-0" />
                    </div>
                  ) : (
                    <p className="font-serif text-sm text-ink flex-1">{step}</p>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Apply a code */}
          <div className="card p-5">
            <p className="font-syne font-semibold text-sm text-ink mb-1">{t("referral.apply_title")}</p>
            <div className="flex gap-2 mt-3">
              <input
                value={applyCode}
                onChange={e => setApplyCode(e.target.value.toUpperCase())}
                maxLength={8}
                placeholder={t("referral.apply_placeholder")}
                className="flex-1 px-3 py-2 rounded-lg border border-border bg-bg text-ink font-syne font-semibold text-sm tracking-widest focus:outline-none focus:border-ink uppercase placeholder:normal-case placeholder:font-serif placeholder:font-normal placeholder:tracking-normal placeholder:text-ink-3"
              />
              <button
                onClick={handleApply}
                disabled={applyCode.length !== 8 || applyStatus === "loading"}
                className="btn-primary px-4 disabled:opacity-40 text-sm whitespace-nowrap">
                {applyStatus === "loading" ? t("referral.applying") : t("referral.apply_btn")}
              </button>
            </div>
            {applyStatus === "success" && (
              <p className="mt-2 text-green font-serif text-xs">{applyMsg}</p>
            )}
            {applyStatus === "error" && (
              <p className="mt-2 text-red font-serif text-xs">{applyMsg}</p>
            )}
          </div>
        </>
      ) : null}
    </div>
  );
}
