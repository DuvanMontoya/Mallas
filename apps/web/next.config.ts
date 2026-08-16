import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  poweredByHeader: false,
  reactStrictMode: true,
  output: "standalone",
  typedRoutes: false,
  images: {
    remotePatterns: [],
  },
};

export default nextConfig;
