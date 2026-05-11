"use client";

import { useEffect, useState, useCallback } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "/api/v1";

interface Props {
  articleId: string;
  className?: string;
}

export function BookmarkButton({ articleId, className = "" }: Props) {
  const [saved, setSaved]       = useState(false);
  const [loading, setLoading]   = useState(true);
  const [authed, setAuthed]     = useState(false);
  const [pulse, setPulse]       = useState(false);

  useEffect(() => {
    const token = document.cookie
      .split("; ")
      .find((c) => c.startsWith("access_token="))
      ?.split("=")[1];

    if (!token) { setLoading(false); return; }
    setAuthed(true);

    fetch(`${API}/bookmarks/check/article/${articleId}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.ok ? r.json() : null)
      .then((d) => { if (d) setSaved(d.bookmarked); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [articleId]);

  const toggle = useCallback(async () => {
    const token = document.cookie
      .split("; ")
      .find((c) => c.startsWith("access_token="))
      ?.split("=")[1];
    if (!token) { window.location.href = "/login"; return; }

    const next = !saved;
    setSaved(next);
    setPulse(true);
    setTimeout(() => setPulse(false), 600);

    try {
      await fetch(`${API}/bookmarks/article/${articleId}`, {
        method: next ? "POST" : "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      setSaved(!next); // revert on error
    }
  }, [saved, articleId]);

  if (loading) return null;
  if (!authed)  return null; // not logged in — hide silently

  return (
    <button
      onClick={toggle}
      title={saved ? "Remove bookmark" : "Bookmark this article"}
      className={`inline-flex items-center gap-1.5 text-xs font-syne font-semibold rounded-full px-3 py-1.5 border transition-all ${
        saved
          ? "bg-accent/10 border-accent/40 text-accent"
          : "bg-surface border-border text-ink-3 hover:border-accent/40 hover:text-accent"
      } ${pulse ? "scale-110" : ""} ${className}`}
    >
      <svg
        viewBox="0 0 24 24"
        className="w-3.5 h-3.5 transition-all"
        fill={saved ? "currentColor" : "none"}
        stroke="currentColor"
        strokeWidth={2}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"
        />
      </svg>
      {saved ? "Saved" : "Save"}
    </button>
  );
}
