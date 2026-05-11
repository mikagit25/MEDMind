"use client";

/**
 * Tracks reading progress for an article:
 *  - Shows a thin blue progress bar fixed at the top of the viewport
 *  - Marks article as "read" in localStorage when user scrolls past 80%
 *
 * localStorage key: "medmind_read" → JSON array of slugs
 */

import { useEffect, useState } from "react";

const STORAGE_KEY = "medmind_read";
const READ_THRESHOLD = 0.80; // 80% scrolled = "read"

export function markRead(slug: string) {
  try {
    const raw   = localStorage.getItem(STORAGE_KEY);
    const slugs: string[] = raw ? JSON.parse(raw) : [];
    if (!slugs.includes(slug)) {
      slugs.push(slug);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(slugs));
    }
  } catch {}
}

export function isRead(slug: string): boolean {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return false;
    return JSON.parse(raw).includes(slug);
  } catch {
    return false;
  }
}

export function getReadSlugs(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

interface Props {
  slug: string;
}

export function ArticleReadTracker({ slug }: Props) {
  const [progress, setProgress] = useState(0);
  const [markedRead, setMarkedRead] = useState(false);

  useEffect(() => {
    if (isRead(slug)) setMarkedRead(true);

    const onScroll = () => {
      const scrollTop    = window.scrollY;
      const docHeight    = document.documentElement.scrollHeight - window.innerHeight;
      const pct          = docHeight > 0 ? scrollTop / docHeight : 0;
      const clamped      = Math.min(1, Math.max(0, pct));

      setProgress(clamped);

      if (!markedRead && clamped >= READ_THRESHOLD) {
        markRead(slug);
        setMarkedRead(true);
      }
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [slug, markedRead]);

  return (
    <>
      {/* Fixed reading progress bar at top */}
      <div
        className="fixed top-0 left-0 z-50 h-0.5 bg-accent transition-all duration-100"
        style={{ width: `${progress * 100}%` }}
        aria-hidden
      />
    </>
  );
}
