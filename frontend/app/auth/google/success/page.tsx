"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuthStore } from "@/lib/store";
import { authApi, api } from "@/lib/api";
import { Suspense } from "react";

function GoogleSuccessHandler() {
  const router = useRouter();
  const params = useSearchParams();
  const { setAuth } = useAuthStore();

  useEffect(() => {
    const code = params.get("code");

    if (!code) {
      router.replace("/login?error=google_failed");
      return;
    }

    // Exchange one-time code for tokens (server-side, tokens never in URL)
    api.post("/auth/google/exchange", null, { params: { code } })
      .then(async (res) => {
        const { access_token, refresh_token, onboarding } = res.data;

        // Store tokens
        localStorage.setItem("access_token", access_token);
        localStorage.setItem("refresh_token", refresh_token);

        // Fetch user profile
        const meRes = await authApi.me();
        setAuth(meRes.data, access_token, refresh_token);

        if (onboarding) {
          router.replace("/onboarding");
        } else {
          router.replace("/dashboard");
        }
      })
      .catch(() => {
        router.replace("/login?error=google_failed");
      });
  }, [params, router, setAuth]);

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center">
      <div className="text-center">
        <div className="text-3xl mb-4 animate-pulse">🔐</div>
        <p className="font-serif text-ink-3 text-sm">Signing you in…</p>
      </div>
    </div>
  );
}

export default function GoogleSuccessPage() {
  return (
    <Suspense>
      <GoogleSuccessHandler />
    </Suspense>
  );
}
