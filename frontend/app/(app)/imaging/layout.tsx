import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Medical Imaging Library — MedMind AI",
  description:
    "Browse 6,700+ medical images: X-rays, CT, MRI, Ultrasound, ECG, Histology, Dermatoscopy. Annotated cases for radiologists, students, and clinicians. Available in 7 languages.",
  keywords:
    "medical imaging, radiology, X-ray, CT scan, MRI, ultrasound, ECG, histology, medical education, radiology cases",
  openGraph: {
    title: "Medical Imaging Library — MedMind AI",
    description: "6,700+ medical images: X-ray, CT, MRI, Ultrasound, ECG, Histology in 7 languages.",
    type: "website",
    url: "https://medmind.pro/imaging",
  },
  alternates: {
    canonical: "https://medmind.pro/imaging",
    languages: {
      ru: "https://medmind.pro/imaging?lang=ru",
      ar: "https://medmind.pro/imaging?lang=ar",
      de: "https://medmind.pro/imaging?lang=de",
      fr: "https://medmind.pro/imaging?lang=fr",
      es: "https://medmind.pro/imaging?lang=es",
      tr: "https://medmind.pro/imaging?lang=tr",
    },
  },
  robots: { index: true, follow: true },
};

export default function ImagingLayout({ children }: { children: React.ReactNode }) {
  return children;
}
