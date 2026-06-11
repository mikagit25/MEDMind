import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "MedMind Quiz";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

type Props = { params: { slug: string } };

export default async function QuizOgImage({ params }: Props) {
  let title = "Free Medical Quiz";
  let description = "Test your medical knowledge — no signup required.";
  let category = "general";

  try {
    const res = await fetch(`${API_URL}/public/quiz/${params.slug}`, {
      next: { revalidate: 3600 },
    });
    if (res.ok) {
      const data = await res.json();
      title = data.title ?? title;
      description = data.description ?? description;
      category = data.category ?? category;
    }
  } catch {}

  const ICONS: Record<string, string> = {
    "first-aid": "🚑",
    pharmacology: "💊",
    symptoms: "🩺",
    veterinary: "🐾",
    anatomy: "🫀",
    general: "📋",
  };
  const icon = ICONS[category] ?? "📋";

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: "linear-gradient(135deg, #0f0f0f 0%, #1a1a1a 100%)",
          padding: "60px",
        }}
      >
        <div style={{ fontSize: 80, marginBottom: 24 }}>{icon}</div>
        <div
          style={{
            color: "#ffffff",
            fontSize: 48,
            fontWeight: 900,
            textAlign: "center",
            lineHeight: 1.2,
            maxWidth: 900,
            marginBottom: 20,
          }}
        >
          {title}
        </div>
        <div
          style={{
            color: "#a0a0a0",
            fontSize: 24,
            textAlign: "center",
            maxWidth: 800,
            marginBottom: 40,
          }}
        >
          {description}
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 16,
            background: "rgba(255,255,255,0.08)",
            border: "1px solid rgba(255,255,255,0.15)",
            borderRadius: 16,
            padding: "16px 32px",
          }}
        >
          <div style={{ color: "#ffffff", fontSize: 20, fontWeight: 700 }}>
            MedMind
          </div>
          <div style={{ color: "#666", fontSize: 20 }}>·</div>
          <div style={{ color: "#a0a0a0", fontSize: 18 }}>
            Free quiz · No signup required
          </div>
        </div>
      </div>
    ),
    { ...size }
  );
}
