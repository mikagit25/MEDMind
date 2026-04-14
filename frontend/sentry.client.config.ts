import * as Sentry from "@sentry/nextjs";

const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN;

if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,
    environment: process.env.NODE_ENV,
    release: `medmind-frontend@${process.env.npm_package_version ?? "1.0.0"}`,
    // Capture 10% of transactions for performance monitoring
    tracesSampleRate: 0.1,
    // Replay 1% of sessions, 10% of sessions with errors
    replaysSessionSampleRate: 0.01,
    replaysOnErrorSampleRate: 0.1,
    integrations: [
      Sentry.replayIntegration({
        maskAllText: true,      // mask PII in recordings
        blockAllMedia: false,
      }),
    ],
    // Filter noisy browser errors that aren't actionable
    ignoreErrors: [
      "ResizeObserver loop limit exceeded",
      "Non-Error promise rejection captured",
      /^Load failed$/,
      /^NetworkError/,
    ],
  });
}
