import * as Sentry from "@sentry/nextjs";

const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,
    environment: process.env.NODE_ENV,
    release: `medmind-frontend@${process.env.npm_package_version ?? "1.0.0"}`,
    tracesSampleRate: 0.1,
    // Don't send PII by default
    sendDefaultPii: false,
  });
}
