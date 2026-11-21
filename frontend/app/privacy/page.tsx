import type { Metadata } from "next";
import Link from "next/link";
import { LegalPage, type LegalSection } from "@/components/layout/LegalPage";

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://medmind.pro";
const CONTACT = "legal@medmind.pro";
const UPDATED = "November 21, 2026";

export const metadata: Metadata = {
  title: "Privacy Policy | MedMind AI",
  description:
    "How MedMind AI collects, uses, stores and protects personal data, including data obtained through Google Sign-In and the YouTube API.",
  alternates: { canonical: `${SITE_URL}/privacy` },
  openGraph: {
    title: "Privacy Policy | MedMind AI",
    url: `${SITE_URL}/privacy`,
    siteName: "MedMind AI",
    type: "website",
  },
};

const sections: LegalSection[] = [
  {
    id: "who-we-are",
    title: "Who we are",
    body: (
      <p>
        MedMind AI (&ldquo;MedMind&rdquo;, &ldquo;we&rdquo;, &ldquo;us&rdquo;) operates the medical education
        platform at <a href={SITE_URL}>medmind.pro</a>, its mobile app, its Telegram bot and the MedMind
        YouTube channels. This policy explains what personal data we process and why. Questions can be sent
        to <a href={`mailto:${CONTACT}`}>{CONTACT}</a>.
      </p>
    ),
  },
  {
    id: "data-we-collect",
    title: "Data we collect",
    body: (
      <>
        <ul>
          <li>
            <strong>Account data</strong>: email address, name and password. Passwords are stored only as a
            salted hash (bcrypt), never in plain text.
          </li>
          <li>
            <strong>Google Sign-In data</strong>: if you sign in with Google, we receive your name, email
            address and profile picture. We do not request access to your Gmail, Drive, contacts, calendar or
            any other Google data.
          </li>
          <li>
            <strong>Learning data</strong>: lessons, courses and quizzes you complete, progress, notes,
            bookmarks, flashcards and exam practice results.
          </li>
          <li>
            <strong>AI tutor conversations</strong>: messages you send to the AI tutor and the responses
            generated for you.
          </li>
          <li>
            <strong>Optional health data</strong>: if you choose to use the health profile or tracker, the
            values you enter (for example, measurements or medication reminders). This is entirely optional.
          </li>
          <li>
            <strong>Telegram</strong>: if you connect our Telegram bot, your Telegram chat ID so we can send
            the reminders and messages you requested.
          </li>
          <li>
            <strong>Payment data</strong>: subscriptions are processed by Stripe or PayPal. We receive the
            subscription status and billing details they share with us, but we never see or store your full
            card number.
          </li>
          <li>
            <strong>Technical data</strong>: IP address, browser type, device information and pages visited,
            collected through server logs and Google Analytics (with IP anonymization enabled).
          </li>
        </ul>
      </>
    ),
  },
  {
    id: "how-we-use",
    title: "How we use your data",
    body: (
      <ul>
        <li>To create and secure your account and let you sign in.</li>
        <li>To provide the learning features, track progress and personalize study recommendations.</li>
        <li>To generate AI tutor responses to your questions.</li>
        <li>To process subscriptions and send transactional emails (receipts, password resets).</li>
        <li>To send notifications and reminders you have opted into.</li>
        <li>To measure usage, fix errors and improve the service.</li>
      </ul>
    ),
  },
  {
    id: "google-youtube",
    title: "Google API and YouTube data",
    body: (
      <>
        <p>
          MedMind uses the YouTube Data API only to upload and manage educational videos on MedMind&rsquo;s
          own YouTube channels. This access is used by the MedMind team for our own channels; we do not access,
          collect or store data from the YouTube accounts of viewers or platform users.
        </p>
        <p>
          The OAuth tokens that authorize uploads to our channels are stored securely on our server, are used
          for no other purpose and are never sold or shared with third parties.
        </p>
        <p>
          MedMind&rsquo;s use and transfer of information received from Google APIs adheres to the{" "}
          <a href="https://developers.google.com/terms/api-services-user-data-policy" rel="noopener noreferrer">
            Google API Services User Data Policy
          </a>
          , including the Limited Use requirements. Google Sign-In data is used only to create and identify
          your MedMind account.
        </p>
        <p>
          By watching or interacting with MedMind content on YouTube you are also subject to the{" "}
          <a href="https://www.youtube.com/t/terms" rel="noopener noreferrer">YouTube Terms of Service</a> and
          the <a href="https://policies.google.com/privacy" rel="noopener noreferrer">Google Privacy Policy</a>.
          You can revoke any access granted to MedMind at any time via your{" "}
          <a href="https://myaccount.google.com/permissions" rel="noopener noreferrer">
            Google Account permissions page
          </a>
          .
        </p>
      </>
    ),
  },
  {
    id: "sharing",
    title: "Sharing and service providers",
    body: (
      <>
        <p>We do not sell your personal data. We share data only with providers that help us run the service:</p>
        <ul>
          <li>Hosting and infrastructure providers that store our databases and files.</li>
          <li>
            AI model providers (such as Anthropic, Groq, Google Gemini and similar providers) that receive the
            text of AI tutor requests in order to generate a response.
          </li>
          <li>Stripe and PayPal for payment processing.</li>
          <li>Email delivery providers for transactional emails.</li>
          <li>Google Analytics for aggregated usage statistics.</li>
          <li>Telegram, if you choose to connect our bot.</li>
        </ul>
        <p>We may also disclose data if required by law or to protect the rights and safety of users.</p>
      </>
    ),
  },
  {
    id: "cookies",
    title: "Cookies",
    body: (
      <p>
        We use cookies that are necessary for signing in and remembering your language, a referral cookie
        (kept for 30 days) when you arrive through a partner link, and Google Analytics cookies to understand
        how the site is used. You can block or delete cookies in your browser settings; some features may
        then stop working.
      </p>
    ),
  },
  {
    id: "retention",
    title: "Retention and deletion",
    body: (
      <p>
        We keep your data while your account is active. You can download a copy of your data or permanently
        delete your account at any time from the{" "}
        <Link href="/compliance">Privacy &amp; Compliance</Link> section of your account, or by emailing{" "}
        <a href={`mailto:${CONTACT}`}>{CONTACT}</a>. After deletion, your personal data is removed except
        where we are legally required to keep certain records (for example, payment records).
      </p>
    ),
  },
  {
    id: "security",
    title: "Security",
    body: (
      <p>
        Data is transmitted over HTTPS, passwords are hashed, and email addresses are stored encrypted. No
        method of transmission or storage is completely secure, but we take reasonable measures to protect your
        information.
      </p>
    ),
  },
  {
    id: "your-rights",
    title: "Your rights",
    body: (
      <p>
        Depending on where you live, you may have the right to access, correct, export or delete your data,
        to object to or restrict certain processing, and to withdraw consent. To exercise these rights, use
        your account settings or contact <a href={`mailto:${CONTACT}`}>{CONTACT}</a>. You may also lodge a
        complaint with your local data protection authority.
      </p>
    ),
  },
  {
    id: "children",
    title: "Children",
    body: (
      <p>
        MedMind is intended for students, healthcare professionals and adults. It is not directed to children
        under 16, and we do not knowingly collect their personal data.
      </p>
    ),
  },
  {
    id: "medical",
    title: "Not medical advice",
    body: (
      <p>
        MedMind provides educational content only and does not replace professional medical advice,
        diagnosis or treatment. See our <Link href="/medical-disclaimer">Medical Disclaimer</Link>.
      </p>
    ),
  },
  {
    id: "changes",
    title: "Changes to this policy",
    body: (
      <p>
        We may update this policy from time to time. The &ldquo;Last updated&rdquo; date above shows when it
        was last changed. Significant changes will be announced on the site or by email.
      </p>
    ),
  },
];

export default function PrivacyPage() {
  return (
    <LegalPage
      title="Privacy Policy"
      updated={UPDATED}
      intro={
        <p>
          Your privacy matters to us. This policy describes how MedMind AI handles personal data across
          medmind.pro, our apps, our Telegram bot and our YouTube channels.
        </p>
      }
      sections={sections}
    />
  );
}
