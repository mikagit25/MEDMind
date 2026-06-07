"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { commentsApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { useI18n } from "@/lib/i18n";

interface Comment {
  id: string;
  user_id: string;
  user_name: string;
  user_avatar: string | null;
  body: string;
  created_at: string;
  likes: number;
  liked_by_me: boolean;
  reported_by_me: boolean;
}

interface Props {
  contentType: "article" | "news";
  slug: string;
}

function timeAgo(iso: string, c: Record<string, string>): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return c.just_now;
  if (mins < 60) return `${mins}${c.ago_min}`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}${c.ago_hour}`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}${c.ago_day}`;
  try {
    return new Intl.DateTimeFormat("en", { month: "short", day: "numeric" }).format(new Date(iso));
  } catch {
    return iso.split("T")[0];
  }
}

function Avatar({ name, url, size = 32 }: { name: string; url: string | null; size?: number }) {
  const initials = name.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();
  const COLORS = ["bg-red", "bg-blue-500", "bg-green", "bg-amber", "bg-purple-500", "bg-teal-500"];
  const color = COLORS[name.charCodeAt(0) % COLORS.length];
  if (url) {
    return (
      <img src={url} alt={name} width={size} height={size}
        className="rounded-full object-cover flex-shrink-0"
        style={{ width: size, height: size }}
        onError={e => { (e.target as HTMLImageElement).style.display = "none"; }}
      />
    );
  }
  return (
    <div
      className={`${color} rounded-full flex items-center justify-center flex-shrink-0 text-white font-syne font-bold`}
      style={{ width: size, height: size, fontSize: size * 0.38 }}
    >
      {initials}
    </div>
  );
}

export function CommentsBlock({ contentType, slug }: Props) {
  const { user, isAuthenticated } = useAuthStore();
  const { t, isRTL } = useI18n();
  const c = (key: string) => t(`comments.${key}`);

  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const [draft, setDraft] = useState("");
  const [posting, setPosting] = useState(false);
  const [error, setError] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    commentsApi.list(contentType, slug)
      .then(setComments)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [contentType, slug]);

  const handlePost = async () => {
    const body = draft.trim();
    if (body.length < 5) { setError(c("min_error")); return; }
    setPosting(true); setError("");
    try {
      const created: Comment = await commentsApi.post(contentType, slug, body);
      setComments(prev => [...prev, created]);
      setDraft("");
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? c("post_error"));
    } finally {
      setPosting(false);
    }
  };

  const handleLike = async (id: string) => {
    if (!isAuthenticated) return;
    try {
      const res = await commentsApi.like(id);
      setComments(prev => prev.map(cm =>
        cm.id === id ? { ...cm, likes: res.likes, liked_by_me: res.liked } : cm
      ));
    } catch {}
  };

  const handleReport = async (id: string) => {
    if (!isAuthenticated) return;
    if (!confirm(c("report_confirm"))) return;
    try {
      await commentsApi.report(id);
      setComments(prev => prev.map(cm =>
        cm.id === id ? { ...cm, reported_by_me: true } : cm
      ));
    } catch {}
  };

  const handleDelete = async (id: string) => {
    if (!confirm(c("delete_confirm"))) return;
    try {
      await commentsApi.delete(id);
      setComments(prev => prev.filter(cm => cm.id !== id));
    } catch {}
  };

  const userName = user?.first_name
    ? `${user.first_name} ${user.last_name ?? ""}`.trim()
    : user?.email ?? "?";

  return (
    <section className="mt-12 border-t border-border pt-8" dir={isRTL ? "rtl" : "ltr"}>
      {/* Heading */}
      <div className="flex items-center gap-3 mb-6">
        <h2 className="font-syne font-bold text-base text-ink flex items-center gap-2">
          {c("heading")}
          {!loading && comments.length > 0 && (
            <span className="text-xs font-syne font-semibold text-ink-3 bg-bg-2 border border-border rounded-full px-2 py-0.5">
              {comments.length}
            </span>
          )}
        </h2>
        {/* Unified-thread note */}
        <span className="text-xs font-serif text-ink-3 italic hidden sm:block">
          {c("unified_note")}
        </span>
      </div>

      {/* Compose */}
      {isAuthenticated ? (
        <div className="flex gap-3 mb-8">
          <Avatar name={userName} url={null} size={36} />
          <div className="flex-1">
            <textarea
              ref={textareaRef}
              value={draft}
              onChange={e => { setDraft(e.target.value); setError(""); }}
              onKeyDown={e => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handlePost(); }}
              placeholder={c("placeholder")}
              rows={3}
              maxLength={2000}
              className="w-full px-4 py-3 rounded-xl border border-border bg-surface text-ink font-serif text-sm resize-none focus:outline-none focus:border-ink transition-colors placeholder:text-ink-3"
            />
            {error && <p className="text-xs text-red mt-1 font-serif">{error}</p>}
            <div className="flex items-center justify-between mt-2">
              <span className="text-xs text-ink-3 font-serif">
                {draft.length}/2000 · {c("char_hint")}
              </span>
              <button
                onClick={handlePost}
                disabled={posting || draft.trim().length < 5}
                className="px-4 py-1.5 rounded-lg bg-ink text-white font-syne font-semibold text-sm hover:bg-ink/80 disabled:opacity-40 transition-all"
              >
                {posting ? c("posting") : c("post")}
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="mb-8 p-4 rounded-xl border border-border bg-surface flex items-center gap-3">
          <span className="text-2xl flex-shrink-0">💬</span>
          <div>
            <p className="font-syne font-semibold text-sm text-ink">{c("join_title")}</p>
            <p className="font-serif text-xs text-ink-3 mt-0.5">
              <Link href="/login" className="text-red hover:underline font-semibold">{c("sign_in")}</Link>
              {" "}{t("common.or")}{" "}
              <Link href="/register" className="text-red hover:underline font-semibold">{c("register")}</Link>
              {" "}{c("join_desc")}
            </p>
          </div>
        </div>
      )}

      {/* Comments list */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2].map(i => (
            <div key={i} className="flex gap-3 animate-pulse">
              <div className="w-9 h-9 rounded-full bg-border flex-shrink-0" />
              <div className="flex-1 space-y-2">
                <div className="h-3 bg-border rounded w-1/4" />
                <div className="h-3 bg-border rounded w-full" />
                <div className="h-3 bg-border rounded w-3/4" />
              </div>
            </div>
          ))}
        </div>
      ) : comments.length === 0 ? (
        <p className="font-serif text-ink-3 text-sm text-center py-8">{c("empty")}</p>
      ) : (
        <div className="space-y-6">
          {comments.map(cm => (
            <div key={cm.id} className="flex gap-3 group">
              <Avatar name={cm.user_name} url={cm.user_avatar} size={36} />
              <div className="flex-1 min-w-0">
                <div className="flex items-baseline gap-2 mb-1 flex-wrap">
                  <span className="font-syne font-semibold text-sm text-ink">{cm.user_name}</span>
                  <span className="font-serif text-xs text-ink-3">{timeAgo(cm.created_at, {
                    just_now: c("just_now"),
                    ago_min: c("ago_min"),
                    ago_hour: c("ago_hour"),
                    ago_day: c("ago_day"),
                  })}</span>
                </div>
                <p className="font-serif text-sm text-ink leading-relaxed whitespace-pre-wrap break-words">
                  {cm.body}
                </p>
                <div className="flex items-center gap-3 mt-2">
                  {/* Like */}
                  <button
                    onClick={() => handleLike(cm.id)}
                    disabled={!isAuthenticated}
                    className={`flex items-center gap-1 text-xs font-syne font-semibold transition-colors ${
                      cm.liked_by_me ? "text-red" : "text-ink-3 hover:text-ink disabled:cursor-default"
                    }`}
                    title={c("like")}
                  >
                    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill={cm.liked_by_me ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2">
                      <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
                    </svg>
                    {cm.likes > 0 && <span>{cm.likes}</span>}
                  </button>

                  {/* Report (not own comment) */}
                  {isAuthenticated && cm.user_id !== user?.id && (
                    <button
                      onClick={() => handleReport(cm.id)}
                      disabled={cm.reported_by_me}
                      className="text-xs font-syne text-ink-3 hover:text-amber transition-colors disabled:opacity-40 disabled:cursor-default opacity-0 group-hover:opacity-100"
                    >
                      {cm.reported_by_me ? c("reported") : c("report")}
                    </button>
                  )}

                  {/* Delete own */}
                  {isAuthenticated && cm.user_id === user?.id && (
                    <button
                      onClick={() => handleDelete(cm.id)}
                      className="text-xs font-syne text-ink-3 hover:text-red transition-colors opacity-0 group-hover:opacity-100"
                    >
                      {c("delete")}
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
