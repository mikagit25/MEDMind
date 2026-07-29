"use client";

/**
 * ContentAttribution — renders source attribution for content that requires it.
 *
 * Only renders when the source has text_reuse_allowed=true and provides
 * an attribution_template. NC/ND/unclear sources get no attribution badge
 * (they are facts-only and listed on /content-sources).
 */

import { ExternalLink } from "lucide-react";

interface SourceRef {
  source_slug?: string;
  title?: string;
  url?: string;
  section?: string;
  attribution_template?: string;
  text_reuse_allowed?: boolean;
}

interface ContentAttributionProps {
  sources: SourceRef[];
  className?: string;
  compact?: boolean;
}

export function ContentAttribution({
  sources,
  className = "",
  compact = false,
}: ContentAttributionProps) {
  // Only show attribution for sources that explicitly allow text reuse
  const attributable = sources.filter(
    (s) => s.text_reuse_allowed && s.attribution_template
  );

  if (attributable.length === 0) return null;

  if (compact) {
    return (
      <p className={`text-xs text-ink-3 ${className}`}>
        {attributable.map((s, i) => (
          <span key={s.source_slug ?? i}>
            {i > 0 && " · "}
            {s.url ? (
              <a
                href={s.url}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-primary underline"
              >
                {s.title ?? s.source_slug}
              </a>
            ) : (
              s.title ?? s.source_slug
            )}
          </span>
        ))}
      </p>
    );
  }

  return (
    <div className={`space-y-1 ${className}`}>
      {attributable.map((s, i) => {
        const text = s.attribution_template!.replace(
          "{url}",
          s.url ?? ""
        ).replace("{title}", s.title ?? "");
        return (
          <div
            key={s.source_slug ?? i}
            className="flex items-start gap-2 text-xs text-ink-3 bg-surface border border-border rounded px-3 py-2"
          >
            <ExternalLink className="w-3 h-3 mt-0.5 shrink-0 text-ink-3" />
            <span>
              {s.url ? (
                <a
                  href={s.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-primary underline"
                >
                  {text}
                </a>
              ) : (
                text
              )}
            </span>
          </div>
        );
      })}
    </div>
  );
}
