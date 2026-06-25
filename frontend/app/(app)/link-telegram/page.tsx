"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { API_URL } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import Link from "next/link";

export default function LinkTelegramPage() {
  const params     = useSearchParams();
  const router     = useRouter();
  const { user, isAuthenticated } = useAuthStore();
  const token = params.get("token");

  const [status, setStatus] = useState<"idle" | "linking" | "success" | "error">("idle");
  const [error,  setError]  = useState("");

  useEffect(() => {
    if (!token) { setStatus("error"); setError("No link token provided."); return; }
    if (!isAuthenticated) return; // wait for auth check
    // Auto-link if already logged in
    linkAccount();
  }, [token, isAuthenticated]);

  async function linkAccount() {
    if (!token || status === "linking" || status === "success") return;
    setStatus("linking");
    try {
      const accessToken = localStorage.getItem("access_token") ?? "";
      const res = await fetch(`${API_URL}/telegram/link-account`, {
        method:  "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${accessToken}` },
        body:    JSON.stringify({ token }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? "Linking failed");
      }
      setStatus("success");
    } catch (e: any) {
      setStatus("error");
      setError(e.message ?? "Something went wrong");
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="max-w-sm w-full bg-surface border border-border rounded-2xl p-8 text-center space-y-4">
          <div className="text-4xl">🔗</div>
          <h1 className="font-syne font-bold text-xl text-ink">Link Telegram Account</h1>
          <p className="font-serif text-sm text-ink-2">
            Sign in to your MedMind account to connect it with Telegram.
          </p>
          <Link
            href={`/login?redirect=/link-telegram?token=${token}`}
            className="block w-full btn-primary py-2.5 rounded-xl font-syne font-semibold text-sm text-center"
          >
            Sign In
          </Link>
          <Link href="/register" className="block text-xs font-syne text-ink-3 hover:text-ink">
            Don&apos;t have an account? Register free →
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="max-w-sm w-full bg-surface border border-border rounded-2xl p-8 text-center space-y-5">
        {status === "linking" && (
          <>
            <div className="text-4xl animate-pulse">🔗</div>
            <h1 className="font-syne font-bold text-xl text-ink">Linking your account…</h1>
            <p className="font-serif text-sm text-ink-3">Please wait.</p>
          </>
        )}
        {status === "success" && (
          <>
            <div className="text-4xl">✅</div>
            <h1 className="font-syne font-bold text-xl text-ink">Telegram Connected!</h1>
            <p className="font-serif text-sm text-ink-2">
              Your MedMind account (<strong>{user?.email}</strong>) is now linked to Telegram.
            </p>
            <p className="font-serif text-sm text-ink-2">
              Go back to @Medmindpro_bot and send a message to start using your {user?.subscription_tier} plan.
            </p>
            <a
              href="https://t.me/Medmindpro_bot"
              className="block w-full btn-primary py-2.5 rounded-xl font-syne font-semibold text-sm text-center"
            >
              Open @Medmindpro_bot →
            </a>
          </>
        )}
        {status === "error" && (
          <>
            <div className="text-4xl">❌</div>
            <h1 className="font-syne font-bold text-xl text-ink">Link Failed</h1>
            <p className="font-serif text-sm text-red">{error}</p>
            <p className="font-serif text-xs text-ink-3">
              The link may have expired (10 minutes). Get a new one by sending /link to @Medmindpro_bot.
            </p>
            <Link href="/dashboard" className="block text-xs font-syne text-ink-3 hover:text-ink">
              ← Back to Dashboard
            </Link>
          </>
        )}
        {status === "idle" && (
          <>
            <div className="text-4xl">🔗</div>
            <h1 className="font-syne font-bold text-xl text-ink">Link Telegram</h1>
            <button onClick={linkAccount} className="w-full btn-primary py-2.5 rounded-xl font-syne font-semibold text-sm">
              Connect as {user?.email}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
