"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { notificationsApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

/**
 * Notification bell with real-time unread count.
 * Uses 30s polling (reliable across all auth setups).
 * On future PWA/WebSocket upgrade this component is the only place to change.
 */
export function NotificationBell() {
  const [unread, setUnread] = useState(0);
  const { isAuthenticated } = useAuthStore();
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchUnread = () => {
    notificationsApi.list({ unread_only: true, limit: 1 })
      .then((data: any) => setUnread(data.unread_count ?? 0))
      .catch(() => {});
  };

  useEffect(() => {
    if (!isAuthenticated) return;
    fetchUnread();
    intervalRef.current = setInterval(fetchUnread, 30_000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isAuthenticated]);

  return (
    <Link
      href="/notifications"
      className="relative inline-flex items-center justify-center w-9 h-9 rounded-lg hover:bg-white/10 transition-colors"
      onClick={() => setUnread(0)}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="text-white/70"
      >
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
        <path d="M13.73 21a2 2 0 0 1-3.46 0" />
      </svg>
      {unread > 0 && (
        <span className="absolute top-0.5 right-0.5 min-w-[16px] h-4 rounded-full bg-red text-white text-[10px] font-bold flex items-center justify-center px-1 leading-none">
          {unread > 9 ? "9+" : unread}
        </span>
      )}
    </Link>
  );
}
