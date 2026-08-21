import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  poweredByHeader: false,
  reactStrictMode: true,
  output: "standalone",
  typedRoutes: false,
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  images: {
    remotePatterns: [],
  },
};

export default nextConfig;
