"use client";

import { useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { teamApi } from "@/lib/api";
import { useT } from "@/lib/i18n";
import { Users, CheckCircle } from "lucide-react";

export default function TeamJoinPage() {
  const t = useT();
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get("token") ?? "";

  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [msg, setMsg] = useState("");

  // Auto-join if token is in URL (can be triggered manually too)
  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMsg(t("team.join_error_invalid"));
    }
  }, [token, t]);

  async function handleJoin() {
    if (!token) return;
    setStatus("loading");
    setMsg("");
    try {
      await teamApi.join(token);
      setStatus("success");
      setMsg(t("team.join_success"));
      setTimeout(() => router.push("/team"), 2000);
    } catch (e: any) {
      setStatus("error");
      const detail = e?.response?.data?.detail ?? "";
      if (detail.toLowerCase().includes("already")) setMsg(t("team.join_error_already"));
      else if (detail.toLowerCase().includes("invalid") || detail.toLowerCase().includes("expired"))
        setMsg(t("team.join_error_invalid"));
      else setMsg(t("team.join_error"));
    }
  }

  return (
    <div className="flex-1 flex items-center justify-center p-6">
      <div className="card p-8 max-w-sm w-full text-center space-y-5">
        <div className="w-14 h-14 rounded-2xl bg-amber/10 flex items-center justify-center mx-auto">
          {status === "success" ? (
            <CheckCircle size={28} className="text-green" />
          ) : (
            <Users size={28} className="text-amber" />
          )}
        </div>

        <div>
          <h1 className="font-syne font-black text-xl text-ink mb-1">{t("team.join_title")}</h1>
          {status !== "success" && (
            <p className="font-serif text-ink-3 text-sm">{t("team.join_subtitle")}</p>
          )}
        </div>

        {status === "success" && (
          <p className="font-serif text-green text-sm">{msg}</p>
        )}

        {status === "error" && (
          <p className="font-serif text-red text-sm">{msg}</p>
        )}

        {status !== "success" && token && (
          <button
            onClick={handleJoin}
            disabled={status === "loading" || !token}
            className="w-full btn-primary disabled:opacity-40">
            {status === "loading" ? t("team.joining") : t("team.join_btn")}
          </button>
        )}

        {(status === "error" || !token) && (
          <p className="font-serif text-xs text-ink-3">
            If you believe this is an error, contact your team admin for a new invite link.
          </p>
        )}
      </div>
    </div>
  );
}
