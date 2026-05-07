"use client";

import { useEffect } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export function ArticleViewTracker({ slug }: { slug: string }) {
  useEffect(() => {
    fetch(`${API_URL}/articles/${slug}/view`, { method: "POST" }).catch(() => {});
  }, [slug]);
  return null;
}
