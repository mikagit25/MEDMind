"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { notificationsApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

/**
 * Notification bell with real-time unread count.
 * Uses SSE (fetch-based, supports Bearer auth) with 30s polling fallback.
 */
export function NotificationBell() {
  const [unread, setUnread] = useState(0);
  const { isAuthenticated } = useAuthStore();
  const abortRef = useRef<AbortController | null>(null);
  const fallbackRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!isAuthenticated) return;

    // Initial fetch for count
    notificationsApi.list({ unread_only: true, limit: 1 })
      .then((data: any) => setUnread(data.unread_count ?? 0))
      .catch(() => {});

    let sseActive = false;

    async function connectSSE() {
      const token = localStorage.getItem("medmind_token");
      if (!token) return;

      abortRef.current = new AbortController();
      try {
        const res = await fetch(`${API_URL}/notifications/stream`, {
          headers: { Authorization: `Bearer ${token}` },
          signal: abortRef.current.signal,
        });
        if (!res.ok || !res.body) return;

        sseActive = true;
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buf = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          const lines = buf.split("\n");
          buf = lines.pop() ?? "";
          for (const line of lines) {
            if (!line.startsWith("data:")) continue;
            try {
              const payload = JSON.parse(line.slice(5).trim());
              if (payload.unread_count !== undefined) setUnread(payload.unread_count);
              else if (payload.type === "new_notification") setUnread((n) => n + 1);
            } catch { /* malformed line */ }
          }
        }
      } catch {
        // AbortError on cleanup or network error — fall through to polling
      } finally {
        sseActive = false;
      }
    }

    connectSSE();

    // Polling fallback (runs always, SSE is best-effort on top)
    fallbackRef.current = setInterval(() => {
      if (sseActive) return; // SSE covers us
      notificationsApi.list({ unread_only: true, limit: 1 })
        .then((data: any) => setUnread(data.unread_count ?? 0))
        .catch(() => {});
    }, 30_000);

    return () => {
      abortRef.current?.abort();
      if (fallbackRef.current) clearInterval(fallbackRef.current);
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
