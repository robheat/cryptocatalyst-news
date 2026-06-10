import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    // Only webp (skip avif) — halves transformation count
    formats: ["image/webp"],
    // Fewer breakpoints = fewer cache variants per image
    deviceSizes: [640, 1080, 1920],
    imageSizes: [32, 64, 128, 256],
    // Keep variants cached for 1 year — minimises cache write frequency
    minimumCacheTTL: 31536000,
  },
  async rewrites() {
    return [
      { source: "/feed.xml", destination: "/feed" },
      { source: "/llms.txt", destination: "/llms-txt" },
      { source: "/llms-full.txt", destination: "/llms-full" },
    ];
  },
};

export default nextConfig;
