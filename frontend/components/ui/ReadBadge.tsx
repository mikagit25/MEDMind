"use client";

import { useEffect, useState } from "react";

const STORAGE_KEY = "medmind_read";

interface Props {
  slug: string;
}

export function ReadBadge({ slug }: Props) {
  const [read, setRead] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw && JSON.parse(raw).includes(slug)) setRead(true);
    } catch {}
  }, [slug]);

  if (!read) return null;

  return (
    <span
      title="You've read this article"
      className="inline-flex items-center gap-1 text-[10px] font-syne font-semibold text-green bg-green/10 border border-green/25 rounded-full px-2 py-0.5"
    >
      <svg viewBox="0 0 16 16" className="w-2.5 h-2.5 fill-current" aria-hidden>
        <path d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.75.75 0 0 1 1.06-1.06L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0z" />
      </svg>
      Read
    </span>
  );
}
