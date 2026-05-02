"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

const ROLES = [
  { value: "doctor", label: "Doctor / Physician" },
  { value: "student", label: "Medical Student" },
  { value: "nurse", label: "Nurse" },
  { value: "vet", label: "Veterinarian" },
  { value: "vet_student", label: "Vet Student" },
  { value: "paramedic", label: "Paramedic / EMT" },
  { value: "other", label: "Other Healthcare" },
];

export default function RegisterPage() {
  const router = useRouter();
  const { setAuth } = useAuthStore();
  const [form, setForm] = useState({
    email: "",
    password: "",
    first_name: "",
    last_name: "",
    role: "student",
    consent_terms: false,
    consent_data_processing: false,
    consent_marketing: false,
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const update = (field: string, value: any) =>
    setForm((p) => ({ ...p, [field]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!form.consent_terms || !form.consent_data_processing) {
      setError("You must accept the required consents to proceed.");
      return;
    }
    setLoading(true);
    try {
      const res = await authApi.register(form);
      const data = res.data;
      setAuth(data.user, data.access_token, data.refresh_token);
      router.replace("/onboarding");
    } catch (err: any) {
      setError(err.response?.data?.detail ?? "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card p-8 shadow-xl animate-fade-up">
      <h1 className="font-syne font-bold text-2xl text-ink mb-1">Create account</h1>
      <p className="text-ink-3 font-serif text-sm mb-6">Join the MedMind platform</p>

      <form onSubmit={handleSubmit} className="space-y-3.5">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block font-syne font-semibold text-xs text-ink-2 mb-1">
              First name
            </label>
            <input
              type="text"
              value={form.first_name}
              onChange={(e) => update("first_name", e.target.value)}
              required
              className="w-full px-3 py-2 rounded border border-border bg-bg text-ink font-serif text-sm focus:outline-none focus:border-ink transition-colors"
            />
          </div>
          <div>
            <label className="block font-syne font-semibold text-xs text-ink-2 mb-1">
              Last name
            </label>
            <input
              type="text"
              value={form.last_name}
              onChange={(e) => update("last_name", e.target.value)}
              required
              className="w-full px-3 py-2 rounded border border-border bg-bg text-ink font-serif text-sm focus:outline-none focus:border-ink transition-colors"
            />
          </div>
        </div>

        <div>
          <label className="block font-syne font-semibold text-xs text-ink-2 mb-1">
            Email
          </label>
          <input
            type="email"
            value={form.email}
            onChange={(e) => update("email", e.target.value)}
            required
            autoComplete="email"
            className="w-full px-3 py-2 rounded border border-border bg-bg text-ink font-serif text-sm focus:outline-none focus:border-ink transition-colors"
          />
        </div>

        <div>
          <label className="block font-syne font-semibold text-xs text-ink-2 mb-1">
            Password
          </label>
          <input
            type="password"
            value={form.password}
            onChange={(e) => update("password", e.target.value)}
            required
            minLength={8}
            autoComplete="new-password"
            className="w-full px-3 py-2 rounded border border-border bg-bg text-ink font-serif text-sm focus:outline-none focus:border-ink transition-colors"
          />
        </div>

        <div>
          <label className="block font-syne font-semibold text-xs text-ink-2 mb-1">
            Role
          </label>
          <select
            value={form.role}
            onChange={(e) => update("role", e.target.value)}
            className="w-full px-3 py-2 rounded border border-border bg-bg text-ink font-serif text-sm focus:outline-none focus:border-ink transition-colors"
          >
            {ROLES.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-2 pt-1">
          <label className="flex items-start gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={form.consent_terms}
              onChange={(e) => update("consent_terms", e.target.checked)}
              className="mt-0.5 accent-ink"
            />
            <span className="text-xs font-serif text-ink-2">
              I accept the{" "}
              <span className="font-semibold text-ink">Terms of Service</span> and{" "}
              <span className="font-semibold text-ink">Privacy Policy</span>{" "}
              <span className="text-red">*</span>
            </span>
          </label>
          <label className="flex items-start gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={form.consent_data_processing}
              onChange={(e) => update("consent_data_processing", e.target.checked)}
              className="mt-0.5 accent-ink"
            />
            <span className="text-xs font-serif text-ink-2">
              I consent to processing of personal data (GDPR){" "}
              <span className="text-red">*</span>
            </span>
          </label>
          <label className="flex items-start gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={form.consent_marketing}
              onChange={(e) => update("consent_marketing", e.target.checked)}
              className="mt-0.5 accent-ink"
            />
            <span className="text-xs font-serif text-ink-2">
              I agree to receive educational updates and product news (optional)
            </span>
          </label>
        </div>

        {error && (
          <p className="text-red text-sm font-syne font-semibold bg-red-light border border-red/20 rounded px-3 py-2">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="btn-primary w-full py-2.5 text-base disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {loading ? "Creating account…" : "Create account"}
        </button>
      </form>

      <div className="relative my-4">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-border" />
        </div>
        <div className="relative flex justify-center text-xs">
          <span className="bg-surface px-2 text-ink-3 font-serif">or sign up with</span>
        </div>
      </div>

      <a
        href={`${process.env.NEXT_PUBLIC_API_URL}/auth/google`}
        className="flex items-center justify-center gap-2.5 w-full border border-border rounded-lg px-4 py-2.5 text-sm font-syne font-semibold text-ink hover:bg-surface-2 transition-colors"
      >
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
          <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.716v2.258h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4"/>
          <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 009 18z" fill="#34A853"/>
          <path d="M3.964 10.71A5.41 5.41 0 013.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 000 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/>
          <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 00.957 4.958L3.964 6.29C4.672 4.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
        </svg>
        Continue with Google
      </a>

      <p className="text-center text-ink-3 font-serif text-sm mt-4">
        Already have an account?{" "}
        <Link href="/login" className="text-ink font-syne font-semibold hover:text-red transition-colors">
          Sign in
        </Link>
      </p>
    </div>
  );
}
