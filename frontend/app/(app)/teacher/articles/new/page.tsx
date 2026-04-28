"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { teacherApi } from "@/lib/api";
import { useT } from "@/lib/i18n";

// Redirect to the editor with an unsaved "new" state.
// We simply render the editor in "new" mode via the [id]/edit page.
export default function NewArticlePage() {
  const t = useT();
  const router = useRouter();

  useEffect(() => {
    // Create a blank article immediately and redirect to its editor.
    teacherApi.createArticle({
      title: "Untitled Article",
      slug: `draft-${Date.now()}`,
      excerpt: "",
      category: "diseases",
      body: [],
    }).then(res => {
      router.replace(`/teacher/articles/${res.id}/edit`);
    }).catch(() => {
      // If create fails just go back to the list
      router.replace("/teacher/articles");
    });
  }, [router]);

  return (
    <div className="flex-1 flex items-center justify-center text-ink-3 font-serif text-sm">
      {t("teacher.articles.creating")}
    </div>
  );
}
