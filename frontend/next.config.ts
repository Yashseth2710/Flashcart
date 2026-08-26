import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    // Catalogue photography is imported with the products it belongs to.
    remotePatterns: [{ protocol: "https", hostname: "cdn.dummyjson.com" }],
    // Served straight from the source rather than through Next's optimiser.
    // Both halves of the site are one deployment, and the optimiser is not
    // wired up inside that arrangement — every photo came back as the
    // storefront's own 404 page. The pictures are already thumbnail-sized
    // WebP on a CDN, so there is nothing for an optimiser to improve.
    unoptimized: true,
  },
};

export default nextConfig;
