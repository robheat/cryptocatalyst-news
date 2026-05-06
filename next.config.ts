import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      { source: "/feed.xml", destination: "/feed" },
      { source: "/llms.txt", destination: "/llms-txt" },
      { source: "/llms-full.txt", destination: "/llms-full" },
    ];
  },
};

export default nextConfig;
