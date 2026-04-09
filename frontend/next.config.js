/** @type {import('next').NextConfig} */
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

module.exports = nextConfig;
