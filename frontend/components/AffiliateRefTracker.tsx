"use client";
import { useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";

const COOKIE_NAME = "medmind_ref";
const COOKIE_DAYS = 30;

function setCookie(name: string, value: string, days: number) {
  const d = new Date();
  d.setTime(d.getTime() + days * 24 * 60 * 60 * 1000);
  document.cookie = `${name}=${value};expires=${d.toUTCString()};path=/;SameSite=Lax`;
}

export function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export default function AffiliateRefTracker() {
  const params = useSearchParams();

  useEffect(() => {
    const ref = params.get("ref");
    if (!ref) return;
    const code = ref.toUpperCase();
    setCookie(COOKIE_NAME, code, COOKIE_DAYS);
    // Fire-and-forget click tracking
    api.post("/affiliate/click", {
      code,
      referrer: document.referrer || "",
      utm_source: params.get("utm_source") || "",
      utm_medium: params.get("utm_medium") || "",
      utm_campaign: params.get("utm_campaign") || "",
    }).catch(() => {});
  }, [params]);

  return null;
}
