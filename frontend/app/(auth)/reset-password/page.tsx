"use client";
import { useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";

function ResetPasswordForm() {
  const router = useRouter();
  const params = useSearchParams();
  const t = useT();
  const token = params.get("token") || "";
  const email = params.get("email") || "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }
    if (password !== confirm) {
      setError("Passwords do not match");
      return;
    }
    setLoading(true);
    try {
      await api.post("/auth/reset-password", { token, new_password: password });
      setDone(true);
      setTimeout(() => router.push("/login"), 2000);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg || "Invalid or expired reset link.");
    } finally {
      setLoading(false);
    }
  }

  if (!token) {
    return (
      <div className="min-h-screen bg-bg flex items-center justify-center px-4">
        <div className="bg-surface border border-border rounded-xl p-8 max-w-md w-full text-center">
          <p className="text-red text-sm">Invalid reset link. Please request a new one.</p>
          <Link href="/forgot-password" className="btn-primary mt-4 inline-block">
            Request Reset Link
          </Link>
        </div>
      </div>
    );
  }

  if (done) {
    return (
      <div className="min-h-screen bg-bg flex items-center justify-center px-4">
        <div className="bg-surface border border-border rounded-xl p-8 max-w-md w-full text-center">
          <div className="text-4xl mb-4">✅</div>
          <h1 className="font-syne font-bold text-xl text-ink mb-2">{t("auth.reset_password.title")}</h1>
          <p className="text-ink-2 text-sm">{t("auth.reset_password.success")}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center px-4">
      <div className="bg-surface border border-border rounded-xl p-8 max-w-md w-full">
        <h1 className="font-syne font-bold text-2xl text-ink mb-2">{t("auth.reset_password.title")}</h1>
        {email && <p className="text-ink-2 text-sm mb-6">For {email}</p>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-syne font-semibold text-ink mb-1">
              {t("auth.reset_password.new_password")}
            </label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Min 8 characters"
              className="w-full border border-border rounded-lg px-3 py-2 bg-bg text-ink text-sm focus:outline-none focus:border-ink transition-colors"
            />
          </div>
          <div>
            <label className="block text-sm font-syne font-semibold text-ink mb-1">
              Confirm password
            </label>
            <input
              type="password"
              required
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              placeholder="Repeat password"
              className="w-full border border-border rounded-lg px-3 py-2 bg-bg text-ink text-sm focus:outline-none focus:border-ink transition-colors"
            />
          </div>
          {error && <p className="text-red text-sm">{error}</p>}
          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? t("auth.reset_password.submitting") : t("auth.reset_password.submit")}
          </button>
        </form>
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense>
      <ResetPasswordForm />
    </Suspense>
  );
}
