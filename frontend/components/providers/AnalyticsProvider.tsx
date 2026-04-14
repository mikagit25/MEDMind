"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import { useAuthStore } from "@/lib/store";
import { initAnalytics, identifyUser, trackPageView } from "@/lib/analytics";

export function AnalyticsProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const user = useAuthStore(s => s.user);
  const identified = useRef(false);

  // Initialize PostHog once on mount
  useEffect(() => {
    initAnalytics();
  }, []);

  // Identify user when they log in
  useEffect(() => {
    if (user && !identified.current) {
      identifyUser(user.id, {
        role: user.role,
        subscription_tier: user.subscription_tier,
        level: user.level,
      });
      identified.current = true;
    }
    if (!user) {
      identified.current = false;
    }
  }, [user]);

  // Track page views on navigation
  useEffect(() => {
    trackPageView(pathname);
  }, [pathname]);

  return <>{children}</>;
}
