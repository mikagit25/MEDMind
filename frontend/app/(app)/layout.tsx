"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore, useUIStore } from "@/lib/store";
import { Sidebar } from "@/components/layout/Sidebar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, user } = useAuthStore();
  const { darkMode } = useUIStore();
  const router = useRouter();

  // Apply dark mode class on mount and when changed
  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
  }, [darkMode]);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push("/login");
    } else if (user && !user.onboarding_completed) {
      router.push("/onboarding");
    }
  }, [isAuthenticated, user, router]);

  if (!isAuthenticated || (user && !user.onboarding_completed)) return null;

  return (
    <div className="flex h-screen overflow-hidden bg-bg dark:bg-[#1a1814]">
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-hidden">{children}</main>
    </div>
  );
}
