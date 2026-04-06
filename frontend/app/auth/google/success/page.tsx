"use client";

import { useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuthStore } from "@/lib/store";
import { authApi } from "@/lib/api";
import { Suspense } from "react";

function GoogleSuccessHandler() {
  const router = useRouter();
  const params = useSearchParams();
  const { setAuth } = useAuthStore();

  useEffect(() => {
    const accessToken = params.get("access_token");
    const refreshToken = params.get("refresh_token");
    const needsOnboarding = params.get("onboarding") === "1";

    if (!accessToken || !refreshToken) {
      router.replace("/login?error=google_failed");
      return;
    }

    // Store tokens in localStorage first so the /me request works
    localStorage.setItem("access_token", accessToken);
    localStorage.setItem("refresh_token", refreshToken);

    // Fetch user profile
    authApi.me()
      .then((res) => {
        setAuth(res.data, accessToken, refreshToken);
        if (needsOnboarding) {
          router.replace("/onboarding");
        } else {
          router.replace("/dashboard");
        }
      })
      .catch(() => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
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
