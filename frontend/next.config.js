/** @type {import('next').NextConfig} */
const { withSentryConfig } = require("@sentry/nextjs");

const nextConfig = {
  output: "standalone",
  reactStrictMode: false,
  typescript: {
    ignoreBuildErrors: true,  // skip tsc during build — handled separately
  },
  eslint: {
    ignoreDuringBuilds: true, // skip eslint during build
  },
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "**" },
    ],
  },
  webpack: (config, { dev }) => {
    if (dev) {
      // Write webpack cache to local SSD for faster dev recompilation
      config.cache = {
        type: "filesystem",
        cacheDirectory: "/tmp/medmind-next-cache",
        buildDependencies: {
          config: [__filename],
        },
      };
    }
    return config;
  },
};

module.exports = withSentryConfig(nextConfig, {
  // Sentry webpack plugin options (for source map upload)
  org: process.env.SENTRY_ORG || "",
  project: process.env.SENTRY_PROJECT || "medmind-frontend",
  authToken: process.env.SENTRY_AUTH_TOKEN,
  // Only upload source maps in CI/production builds to avoid slowing down dev
  silent: true,
  disableServerWebpackPlugin: !process.env.SENTRY_AUTH_TOKEN,
  disableClientWebpackPlugin: !process.env.SENTRY_AUTH_TOKEN,
  // Wrap route handlers and API routes automatically
  autoInstrumentServerFunctions: true,
});
