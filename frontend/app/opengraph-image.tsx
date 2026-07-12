import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "MedMind AI — Medical Education Platform";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const API_URL =
  process.env.INTERNAL_API_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "https://medmind.pro/api/v1";

export default async function OGImage() {
  let modules = 124, drugs = 300, languages = 7;
  try {
    const res = await fetch(`${API_URL}/public/stats`, { next: { revalidate: 21600 } });
    if (res.ok) {
      const s = await res.json();
      modules = s.modules ?? modules;
      drugs = s.drugs ?? drugs;
      languages = s.languages ?? languages;
    }
  } catch { /* use defaults */ }

  return new ImageResponse(
    (
      <div
        style={{
          width: 1200,
          height: 630,
          background: "#1a1814",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "60px 72px",
          fontFamily: "Georgia, serif",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Background decorative circles */}
        <div style={{
          position: "absolute", right: -80, top: -80,
          width: 400, height: 400, borderRadius: "50%",
          background: "radial-gradient(circle, rgba(192,57,43,0.15) 0%, transparent 70%)",
          display: "flex",
        }} />
        <div style={{
          position: "absolute", right: 120, bottom: -60,
          width: 300, height: 300, borderRadius: "50%",
          background: "radial-gradient(circle, rgba(192,57,43,0.10) 0%, transparent 70%)",
          display: "flex",
        }} />

        {/* Top section: logo + badge */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          {/* Logo */}
          <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
            {/* Icon */}
            <div style={{
              width: 56, height: 56, borderRadius: "12px",
              background: "#c0392b",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 30, fontWeight: 900, color: "#fff",
              fontFamily: "Georgia, serif",
              letterSpacing: "-2px",
            }}>M</div>
            <div style={{ display: "flex", flexDirection: "column" }}>
              <span style={{ fontSize: 36, fontWeight: 900, color: "#f5f0e8", lineHeight: 1, letterSpacing: "-1px" }}>
                Med<span style={{ color: "#c0392b" }}>Mind</span>
              </span>
              <span style={{ fontSize: 13, color: "#8a8178", letterSpacing: "3px", textTransform: "uppercase", marginTop: 4 }}>
                AI Education Platform
              </span>
            </div>
          </div>

          {/* Badge */}
          <div style={{
            display: "flex", alignItems: "center", gap: "8px",
            background: "rgba(192,57,43,0.15)", border: "1px solid rgba(192,57,43,0.4)",
            borderRadius: "100px", padding: "8px 20px",
          }}>
            <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#c0392b", display: "flex" }} />
            <span style={{ color: "#c0392b", fontSize: 14, fontWeight: 600, letterSpacing: "1px" }}>
              Powered by Claude AI + PubMed
            </span>
          </div>
        </div>

        {/* Center: headline */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px", flex: 1, justifyContent: "center" }}>
          <div style={{ fontSize: 64, fontWeight: 900, color: "#f5f0e8", lineHeight: 1.1, letterSpacing: "-2px", maxWidth: 800 }}>
            Medical Education
            <br />
            <span style={{ color: "#c0392b" }}>Reimagined with AI</span>
          </div>
          <div style={{ fontSize: 22, color: "#8a8178", maxWidth: 680, lineHeight: 1.5 }}>
            Evidence-based AI tutor · Spaced repetition flashcards ·
            Clinical case simulations · 7 languages
          </div>
        </div>

        {/* Bottom: feature pills + stats */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", gap: "12px" }}>
            {[
              { icon: "🧠", label: "AI Tutor" },
              { icon: "📇", label: "Flashcards" },
              { icon: "🩺", label: "Clinical Cases" },
              { icon: "🔬", label: "PubMed Live" },
            ].map((f) => (
              <div key={f.label} style={{
                display: "flex", alignItems: "center", gap: "8px",
                background: "rgba(245,240,232,0.07)", border: "1px solid rgba(245,240,232,0.12)",
                borderRadius: "8px", padding: "10px 18px",
              }}>
                <span style={{ fontSize: 18 }}>{f.icon}</span>
                <span style={{ color: "#c8bfb5", fontSize: 14, fontWeight: 600 }}>{f.label}</span>
              </div>
            ))}
          </div>

          <div style={{ display: "flex", gap: "32px" }}>
            {[
              { val: `${modules}+`, label: "Modules" },
              { val: `${drugs}+`, label: "Drugs" },
              { val: `${languages}`, label: "Languages" },
            ].map((s) => (
              <div key={s.label} style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                <span style={{ fontSize: 28, fontWeight: 900, color: "#f5f0e8" }}>{s.val}</span>
                <span style={{ fontSize: 12, color: "#8a8178", letterSpacing: "2px", textTransform: "uppercase" }}>{s.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom border accent */}
        <div style={{
          position: "absolute", bottom: 0, left: 0, right: 0,
          height: 3, background: "linear-gradient(90deg, #c0392b 0%, rgba(192,57,43,0.3) 100%)",
          display: "flex",
        }} />
      </div>
    ),
    { ...size }
  );
}
