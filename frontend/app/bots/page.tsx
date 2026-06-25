import type { Metadata } from "next";
import BotsPage from "./BotsPage";

export const metadata: Metadata = {
  title: "MedMind AI Telegram Bot — Medical AI Assistant in Telegram",
  description:
    "MedMind AI bot for Telegram: medical tutor, clinical cases, differential diagnosis, patient explanations and second opinion. Free 10 messages/day. Available in 9 languages.",
  openGraph: {
    title: "MedMind AI Telegram Bot",
    description: "AI medical education assistant in Telegram — free to try, no signup required.",
    url: "https://medmind.pro/bots",
  },
};

export default function Page() {
  return <BotsPage />;
}
