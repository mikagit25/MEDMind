"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { commentsApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

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

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d ago`;
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric" }).format(new Date(iso));
}

function Avatar({ name, url, size = 32 }: { name: string; url: string | null; size?: number }) {
  const initials = name.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();
  const colors = ["bg-red", "bg-blue-500", "bg-green", "bg-amber", "bg-purple-500", "bg-teal-500"];
  const color = colors[name.charCodeAt(0) % colors.length];

  if (url) {
    return (
      <img src={url} alt={name} width={size} height={size}
        className="rounded-full object-cover flex-shrink-0"
        style={{ width: size, height: size }}
        onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
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
    if (body.length < 5) { setError("Minimum 5 characters"); return; }
    setPosting(true); setError("");
    try {
      const created: Comment = await commentsApi.post(contentType, slug, body);
      setComments(prev => [...prev, created]);
      setDraft("");
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? "Failed to post. Please try again.");
    } finally {
      setPosting(false);
    }
  };

  const handleLike = async (id: string) => {
    if (!isAuthenticated) return;
    try {
      const res = await commentsApi.like(id);
      setComments(prev => prev.map(c =>
        c.id === id ? { ...c, likes: res.likes, liked_by_me: res.liked } : c
      ));
    } catch {}
  };

  const handleReport = async (id: string) => {
    if (!isAuthenticated) return;
    if (!confirm("Report this comment as inappropriate?")) return;
    try {
      await commentsApi.report(id);
      setComments(prev => prev.map(c =>
        c.id === id ? { ...c, reported_by_me: true } : c
      ));
    } catch {}
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this comment?")) return;
    try {
      await commentsApi.delete(id);
      setComments(prev => prev.filter(c => c.id !== id));
    } catch {}
  };

  return (
    <section className="mt-12 border-t border-border pt-8">
      <h2 className="font-syne font-bold text-base text-ink mb-6 flex items-center gap-2">
        Discussion
        {!loading && comments.length > 0 && (
          <span className="text-xs font-syne font-semibold text-ink-3 bg-bg-2 border border-border rounded-full px-2 py-0.5">
            {comments.length}
          </span>
        )}
      </h2>

      {/* Compose */}
      {isAuthenticated ? (
        <div className="flex gap-3 mb-8">
          <Avatar name={user?.first_name ? `${user.first_name} ${user.last_name ?? ""}`.trim() : user?.email ?? "?"} url={null} size={36} />
          <div className="flex-1">
            <textarea
              ref={textareaRef}
              value={draft}
              onChange={e => { setDraft(e.target.value); setError(""); }}
              onKeyDown={e => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) handlePost(); }}
              placeholder="Share a clinical observation, question, or insight…"
              rows={3}
              className="w-full px-4 py-3 rounded-xl border border-border bg-surface text-ink font-serif text-sm resize-none focus:outline-none focus:border-ink transition-colors placeholder:text-ink-3"
            />
            {error && <p className="text-xs text-red mt-1 font-serif">{error}</p>}
            <div className="flex items-center justify-between mt-2">
              <span className="text-xs text-ink-3 font-serif">{draft.length}/2000 · Ctrl+Enter to submit</span>
              <button
                onClick={handlePost}
                disabled={posting || draft.trim().length < 5}
                className="px-4 py-1.5 rounded-lg bg-ink text-white font-syne font-semibold text-sm hover:bg-ink/80 disabled:opacity-40 transition-all"
              >
                {posting ? "Posting…" : "Post"}
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="mb-8 p-4 rounded-xl border border-border bg-surface flex items-center gap-3">
          <span className="text-2xl">💬</span>
          <div>
            <p className="font-syne font-semibold text-sm text-ink">Join the discussion</p>
            <p className="font-serif text-xs text-ink-3 mt-0.5">
              <Link href="/login" className="text-red hover:underline font-semibold">Sign in</Link>
              {" "}or{" "}
              <Link href="/register" className="text-red hover:underline font-semibold">create a free account</Link>
              {" "}to post a comment.
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
        <p className="font-serif text-ink-3 text-sm text-center py-8">
          No comments yet. Be the first to share an insight.
        </p>
      ) : (
        <div className="space-y-6">
          {comments.map(c => (
            <div key={c.id} className="flex gap-3 group">
              <Avatar name={c.user_name} url={c.user_avatar} size={36} />
              <div className="flex-1 min-w-0">
                <div className="flex items-baseline gap-2 mb-1 flex-wrap">
                  <span className="font-syne font-semibold text-sm text-ink">{c.user_name}</span>
                  <span className="font-serif text-xs text-ink-3">{timeAgo(c.created_at)}</span>
                </div>
                <p className="font-serif text-sm text-ink leading-relaxed whitespace-pre-wrap">{c.body}</p>
                <div className="flex items-center gap-3 mt-2">
                  {/* Like */}
                  <button
                    onClick={() => handleLike(c.id)}
                    disabled={!isAuthenticated}
                    className={`flex items-center gap-1 text-xs font-syne font-semibold transition-colors ${
                      c.liked_by_me ? "text-red" : "text-ink-3 hover:text-ink disabled:cursor-default"
                    }`}
                  >
                    <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill={c.liked_by_me ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2">
                      <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
                    </svg>
                    {c.likes > 0 && <span>{c.likes}</span>}
                  </button>

                  {/* Report */}
                  {isAuthenticated && c.user_id !== user?.id && (
                    <button
                      onClick={() => handleReport(c.id)}
                      disabled={c.reported_by_me}
                      className="text-xs font-syne text-ink-3 hover:text-amber transition-colors disabled:opacity-40 disabled:cursor-default opacity-0 group-hover:opacity-100"
                    >
                      {c.reported_by_me ? "Reported" : "Report"}
                    </button>
                  )}

                  {/* Delete own */}
                  {isAuthenticated && c.user_id === user?.id && (
                    <button
                      onClick={() => handleDelete(c.id)}
                      className="text-xs font-syne text-ink-3 hover:text-red transition-colors opacity-0 group-hover:opacity-100"
                    >
                      Delete
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
