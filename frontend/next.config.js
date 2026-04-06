/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false, // disable for faster dev startup
  typescript: {
    ignoreBuildErrors: false,
  },
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "**" },
    ],
  },
};

module.exports = nextConfig;
