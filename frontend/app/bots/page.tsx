import type { Metadata } from "next";
import BotsPage from "./BotsPage";

export const metadata: Metadata = {
  title: "AI Medical Consultation — MedMind",
  description:
    "AI medical consultation on the web: Medical Tutor, Clinical Cases, Differential Diagnosis, Patient Mode, Second Opinion. Also available in Telegram. Free to try.",
  openGraph: {
    title: "AI Medical Consultation — MedMind",
    description: "5 consultation modes: Tutor, Clinical Case, Differential Dx, Patient Mode, Second Opinion. Use on the web or link your Telegram.",
    url: "https://medmind.pro/bots",
  },
};

export default function Page() {
  return <BotsPage />;
}
