import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    // Catalogue photography is imported with the products it belongs to.
    remotePatterns: [{ protocol: "https", hostname: "cdn.dummyjson.com" }],
  },
};

export default nextConfig;
