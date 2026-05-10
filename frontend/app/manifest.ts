import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "MedMind AI — Medical Education",
    short_name: "MedMind",
    description: "AI-powered medical education platform — cases, imaging, AI tutor, flashcards",
    start_url: "/dashboard",
    display: "standalone",
    orientation: "portrait",
    background_color: "#f0ede8",
    theme_color: "#1a1814",
    categories: ["education", "medical", "health"],
    lang: "en",
    icons: [
      {
        src: "/icon-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "maskable",
      },
      {
        src: "/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "any",
      },
      {
        src: "/icon.svg",
        sizes: "any",
        type: "image/svg+xml",
        purpose: "any",
      },
    ],
    screenshots: [
      {
        src: "/screenshot-mobile.png",
        sizes: "390x844",
        type: "image/png",
        // @ts-ignore — form_factor is valid in Chrome but not yet in TS types
        form_factor: "narrow",
        label: "MedMind AI Dashboard",
      },
    ],
    shortcuts: [
      {
        name: "AI Tutor",
        short_name: "AI Tutor",
        description: "Chat with your AI medical tutor",
        url: "/ai-tutor",
        icons: [{ src: "/icon-192.png", sizes: "192x192" }],
      },
      {
        name: "Flashcards",
        short_name: "Cards",
        description: "Review your flashcards",
        url: "/flashcards",
        icons: [{ src: "/icon-192.png", sizes: "192x192" }],
      },
      {
        name: "Imaging Library",
        short_name: "Imaging",
        description: "Browse medical images",
        url: "/imaging",
        icons: [{ src: "/icon-192.png", sizes: "192x192" }],
      },
    ],
  };
}
