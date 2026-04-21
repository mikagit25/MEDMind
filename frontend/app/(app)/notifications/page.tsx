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

const TYPE_META: Record<string, { icon: string; color: string; action?: string; actionHref?: string }> = {
  achievement:    { icon: "🏆", color: "bg-amber-light", action: "View achievements", actionHref: "/achievements" },
  flashcard_due:  { icon: "🃏", color: "bg-green-light",  action: "Review now",        actionHref: "/flashcards"   },
  daily_goal:     { icon: "🎯", color: "bg-blue-light",   action: "Go to dashboard",   actionHref: "/dashboard"    },
  quiz_result:    { icon: "📝", color: "bg-blue-light",   action: "View quiz",         actionHref: "/quiz"         },
  course_update:  { icon: "🎓", color: "bg-ink/10",       action: "My courses",        actionHref: "/my-courses"   },
  system:         { icon: "📢", color: "bg-bg-2" },
};

function groupByDate(notifications: Notification[]): { label: string; items: Notification[] }[] {
  const today = new Date().toDateString();
  const yesterday = new Date(Date.now() - 86400000).toDateString();
  const groups: Record<string, Notification[]> = {};

  for (const n of notifications) {
    const d = new Date(n.created_at).toDateString();
    const label = d === today ? "Today" : d === yesterday ? "Yesterday" : new Date(n.created_at).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
    if (!groups[label]) groups[label] = [];
    groups[label].push(n);
  }

  return Object.entries(groups).map(([label, items]) => ({ label, items }));
}

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);

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
    await notificationsApi.markAllRead().catch(() => {});
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    setUnreadCount(0);
  };

  const markOne = (id: string) => {
    notificationsApi.markRead(id).catch(() => {});
    setNotifications((prev) => prev.map((n) => n.id === id ? { ...n, is_read: true } : n));
    setUnreadCount((prev) => Math.max(0, prev - 1));
  };

  const dismiss = (id: string) => {
    const wasUnread = notifications.find((n) => n.id === id && !n.is_read);
    setNotifications((prev) => prev.filter((n) => n.id !== id));
    if (wasUnread) setUnreadCount((prev) => Math.max(0, prev - 1));
    // Persist deletion on server
    notificationsApi.delete(id).catch(() => {});
  };

  const groups = groupByDate(notifications);

  return (
    <div className="flex-1 overflow-y-auto p-6 max-w-2xl mx-auto w-full">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-syne font-black text-2xl text-ink">Notifications</h1>
          {unreadCount > 0 && (
            <p className="font-serif text-ink-3 text-sm mt-0.5">
              {unreadCount} unread
            </p>
          )}
        </div>
        {unreadCount > 0 && (
          <button
            onClick={markAll}
            className="font-syne font-semibold text-xs text-ink-3 hover:text-ink transition-colors"
          >
            Mark all read
          </button>
        )}
      </div>

      {loading ? (
        <div className="text-center py-16 font-serif text-ink-3 text-sm">Loading…</div>
      ) : notifications.length === 0 ? (
        <div className="text-center py-16">
          <div className="text-4xl mb-3">🔔</div>
          <p className="font-syne font-bold text-sm text-ink">All caught up!</p>
          <p className="font-serif text-ink-3 text-xs mt-1">No notifications at the moment.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {groups.map(({ label, items }) => (
            <section key={label}>
              <h2 className="font-syne font-bold text-xs text-ink-3 uppercase mb-2">{label}</h2>
              <div className="space-y-2">
                {items.map((n) => {
                  const meta = TYPE_META[n.type] ?? TYPE_META.system;
                  return (
                    <div
                      key={n.id}
                      className={`card flex gap-3 p-4 transition-all ${n.is_read ? "opacity-60" : ""}`}
                      onClick={() => !n.is_read && markOne(n.id)}
                    >
                      {/* Icon */}
                      <div className={`w-10 h-10 rounded-xl ${meta.color} flex items-center justify-center text-xl flex-shrink-0`}>
                        {meta.icon}
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-syne font-bold text-sm text-ink">{n.title}</span>
                          {!n.is_read && (
                            <span className="w-2 h-2 rounded-full bg-blue flex-shrink-0" />
                          )}
                        </div>
                        {n.body && (
                          <p className="font-serif text-xs text-ink-2 mt-0.5 leading-relaxed">{n.body}</p>
                        )}
                        <div className="flex items-center gap-3 mt-1.5">
                          <span className="font-serif text-xs text-ink-3">
                            {new Date(n.created_at).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}
                          </span>
                          {meta.action && meta.actionHref && (
                            <a
                              href={meta.actionHref}
                              className="font-syne font-semibold text-xs text-ink hover:underline"
                              onClick={(e) => e.stopPropagation()}
                            >
                              {meta.action} →
                            </a>
                          )}
                        </div>
                      </div>

                      {/* Dismiss */}
                      <button
                        onClick={(e) => { e.stopPropagation(); dismiss(n.id); }}
                        className="text-ink-3 hover:text-ink text-lg flex-shrink-0 self-start -mt-1"
                        title="Dismiss"
                      >
                        ×
                      </button>
                    </div>
                  );
                })}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
