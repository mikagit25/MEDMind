"use client";

import { useEffect, useState } from "react";
import { notificationsApi } from "@/lib/api";

interface Notification {
  id: string;
  type: string;
  title: string;
  body: string | null;
  is_read: boolean;
  created_at: string;
}

const TYPE_ICONS: Record<string, string> = {
  achievement:   "🏆",
  flashcard_due: "🃏",
  daily_goal:    "🎯",
  system:        "📢",
};

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount]     = useState(0);
  const [loading, setLoading]             = useState(true);

  const load = () => {
    notificationsApi.list()
      .then((data: any) => {
        setNotifications(data.notifications ?? []);
        setUnreadCount(data.unread_count ?? 0);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const markAll = async () => {
    await notificationsApi.markAllRead();
    load();
  };

  const markOne = async (id: string) => {
    await notificationsApi.markRead(id);
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
    setUnreadCount(prev => Math.max(0, prev - 1));
  };

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-syne font-black text-2xl text-ink">Notifications</h1>
          {unreadCount > 0 && (
            <p className="text-ink-3 text-sm mt-0.5">{unreadCount} unread</p>
          )}
        </div>
        {unreadCount > 0 && (
          <button
            onClick={markAll}
            className="text-xs text-accent hover:underline"
          >
            Mark all as read
          </button>
        )}
      </div>

      {loading ? (
        <div className="text-center py-16 text-ink-3">Loading…</div>
      ) : notifications.length === 0 ? (
        <div className="text-center py-16 text-ink-3">
          <div className="text-4xl mb-3">🔔</div>
          <div>No notifications yet</div>
        </div>
      ) : (
        <div className="space-y-2">
          {notifications.map(n => (
            <div
              key={n.id}
              onClick={() => !n.is_read && markOne(n.id)}
              className={`card px-4 py-3 flex gap-4 items-start cursor-pointer transition-opacity ${
                n.is_read ? "opacity-60" : ""
              }`}
            >
              <div className="text-2xl mt-0.5">
                {TYPE_ICONS[n.type] ?? "📬"}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-sm text-ink">{n.title}</span>
                  {!n.is_read && (
                    <span className="w-2 h-2 rounded-full bg-accent shrink-0" />
                  )}
                </div>
                {n.body && (
                  <p className="text-xs text-ink-3 mt-0.5">{n.body}</p>
                )}
                <p className="text-xs text-ink-3 mt-1">
                  {new Date(n.created_at).toLocaleString()}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
