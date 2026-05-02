"use client";
import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await api.post("/auth/forgot-password", { email });
      setSubmitted(true);
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  if (submitted) {
    return (
      <div className="min-h-screen bg-bg flex items-center justify-center px-4">
        <div className="bg-surface border border-border rounded-xl p-8 max-w-md w-full text-center">
          <div className="text-4xl mb-4">📬</div>
          <h1 className="font-syne font-bold text-xl text-ink mb-2">Check your email</h1>
          <p className="text-ink-2 text-sm mb-6">
            If <strong>{email}</strong> is registered, you&apos;ll receive a reset link shortly.
          </p>
          <Link href="/login" className="btn-primary">Back to Login</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center px-4">
      <div className="bg-surface border border-border rounded-xl p-8 max-w-md w-full">
        <div className="mb-6">
          <Link href="/login" className="text-ink-3 text-sm hover:text-ink transition-colors">
            ← Back to Login
          </Link>
        </div>
        <h1 className="font-syne font-bold text-2xl text-ink mb-2">Forgot password?</h1>
        <p className="text-ink-2 text-sm mb-6">
          Enter your email address and we&apos;ll send you a reset link.
        </p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-syne font-semibold text-ink mb-1">
              Email address
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full border border-border rounded-lg px-3 py-2 bg-bg text-ink text-sm focus:outline-none focus:border-ink transition-colors"
            />
          </div>
          {error && <p className="text-red text-sm">{error}</p>}
          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? "Sending…" : "Send Reset Link"}
          </button>
        </form>
      </div>
    </div>
  );
}
