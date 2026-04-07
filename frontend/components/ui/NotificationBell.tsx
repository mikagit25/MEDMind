"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { notificationsApi } from "@/lib/api";

export function NotificationBell() {
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    const check = () => {
      notificationsApi.list({ unread_only: true })
        .then((data: any) => setUnread(data.unread_count ?? 0))
        .catch(() => {});
    };
    check();
    const interval = setInterval(check, 60_000); // poll every minute
    return () => clearInterval(interval);
  }, []);

  return (
    <Link href="/notifications" className="relative inline-flex items-center justify-center w-9 h-9 rounded-lg hover:bg-surface-2 transition-colors">
      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-ink-2">
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
        <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
      </svg>
      {unread > 0 && (
        <span className="absolute top-1 right-1 min-w-[16px] h-4 rounded-full bg-accent text-white text-[10px] font-bold flex items-center justify-center px-1">
          {unread > 9 ? "9+" : unread}
        </span>
      )}
    </Link>
  );
}
