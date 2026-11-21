import type { Metadata } from "next";
import Link from "next/link";
import { LegalPage, type LegalSection } from "@/components/layout/LegalPage";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const CONTACT = "legal@medmind.pro";
const UPDATED = "November 21, 2026";

export const metadata: Metadata = {
  title: "Terms of Service | MedMind AI",
  description: "Terms governing the use of the MedMind AI medical education platform.",
  alternates: { canonical: `${SITE_URL}/terms` },
  openGraph: {
    title: "Terms of Service | MedMind AI",
    url: `${SITE_URL}/terms`,
    siteName: "MedMind AI",
    type: "website",
  },
};

const sections: LegalSection[] = [
  {
    id: "acceptance",
    title: "Acceptance of these terms",
    body: (
      <p>
        By accessing or using medmind.pro, the MedMind apps, our Telegram bot or other MedMind services (the
        &ldquo;Service&rdquo;), you agree to these Terms of Service and to our{" "}
        <Link href="/privacy">Privacy Policy</Link>. If you do not agree, please do not use the Service.
      </p>
    ),
  },
  {
    id: "service",
    title: "The Service",
    body: (
      <p>
        MedMind AI is an educational platform for medical students, healthcare professionals and interested
        learners. It provides lessons, articles, question banks, flashcards, clinical calculators and an AI
        tutor. We may add, change or remove features at any time.
      </p>
    ),
  },
  {
    id: "not-medical-advice",
    title: "Educational use only — not medical advice",
    body: (
      <>
        <p>
          All content, including AI-generated answers, is provided for educational purposes only. It is not
          medical advice and must not be used to diagnose or treat any person. Always rely on current
          clinical guidelines, official drug labelling and the judgement of a qualified clinician.
        </p>
        <p>
          In a medical emergency, contact your local emergency services immediately. See our{" "}
          <Link href="/medical-disclaimer">Medical Disclaimer</Link>.
        </p>
      </>
    ),
  },
  {
    id: "accounts",
    title: "Accounts",
    body: (
      <p>
        You must provide accurate information when creating an account and keep your login credentials
        confidential. You are responsible for activity under your account. You must be at least 16 years old
        to create an account.
      </p>
    ),
  },
  {
    id: "subscriptions",
    title: "Subscriptions and payments",
    body: (
      <p>
        Some features require a paid subscription. Prices and plan limits are shown on the{" "}
        <Link href="/pricing">Pricing</Link> page. Subscriptions renew automatically at the end of each billing
        period until cancelled. You can cancel at any time from your account settings; access continues until
        the end of the paid period. Payments are processed by Stripe or PayPal. Refund requests can be sent to{" "}
        <a href={`mailto:${CONTACT}`}>{CONTACT}</a> and are handled in line with applicable consumer law.
      </p>
    ),
  },
  {
    id: "acceptable-use",
    title: "Acceptable use",
    body: (
      <>
        <p>You agree not to:</p>
        <ul>
          <li>use the Service for any unlawful purpose or to harm others;</li>
          <li>copy, scrape or redistribute content in bulk, or resell access to the Service;</li>
          <li>attempt to bypass usage limits, security measures or access controls;</li>
          <li>share your account or subscription with others outside your plan;</li>
          <li>upload content that is illegal, infringing, or contains patient-identifiable information.</li>
        </ul>
      </>
    ),
  },
  {
    id: "ai",
    title: "AI-generated content",
    body: (
      <p>
        The AI tutor and other AI features may produce inaccurate, incomplete or outdated information. You
        are responsible for verifying anything you rely on. Do not enter information that could identify a
        real patient.
      </p>
    ),
  },
  {
    id: "ip",
    title: "Intellectual property",
    body: (
      <p>
        The Service and its content (text, questions, images, videos and software) are owned by MedMind or
        its licensors and are protected by copyright and other laws. You may use them for your personal,
        non-commercial study. Notes and other content you create remain yours; you grant us the rights
        needed to store and display them to you.
      </p>
    ),
  },
  {
    id: "third-party",
    title: "Third-party services",
    body: (
      <p>
        The Service links to or integrates with third-party services such as Google, YouTube, Telegram,
        Stripe and PayPal. Their own terms and privacy policies apply to your use of them, including the{" "}
        <a href="https://www.youtube.com/t/terms" rel="noopener noreferrer">YouTube Terms of Service</a> for
        MedMind videos on YouTube.
      </p>
    ),
  },
  {
    id: "termination",
    title: "Suspension and termination",
    body: (
      <p>
        You may stop using the Service and delete your account at any time. We may suspend or terminate
        accounts that violate these terms or that put the Service or other users at risk.
      </p>
    ),
  },
  {
    id: "liability",
    title: "Disclaimers and limitation of liability",
    body: (
      <p>
        The Service is provided &ldquo;as is&rdquo; and &ldquo;as available&rdquo;, without warranties of any
        kind. To the maximum extent permitted by law, MedMind is not liable for any indirect, incidental or
        consequential damages, or for any decisions made based on content from the Service. Our total
        liability for any claim is limited to the amount you paid us in the 12 months before the claim.
        Nothing in these terms limits liability that cannot be limited by law.
      </p>
    ),
  },
  {
    id: "changes",
    title: "Changes to these terms",
    body: (
      <p>
        We may update these terms from time to time. The &ldquo;Last updated&rdquo; date shows the latest
        version. Continued use of the Service after changes take effect means you accept the updated terms.
      </p>
    ),
  },
  {
    id: "contact",
    title: "Contact",
    body: (
      <p>
        Questions about these terms: <a href={`mailto:${CONTACT}`}>{CONTACT}</a>.
      </p>
    ),
  },
];

export default function TermsPage() {
  return (
    <LegalPage
      title="Terms of Service"
      updated={UPDATED}
      intro={<p>These terms govern your use of the MedMind AI platform. Please read them carefully.</p>}
      sections={sections}
    />
  );
}
