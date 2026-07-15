import { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: "/",
      },
      // Allow all known AI crawlers explicitly
      { userAgent: "GPTBot", allow: "/" },
      { userAgent: "OAI-SearchBot", allow: "/" },
      { userAgent: "ClaudeBot", allow: "/" },
      { userAgent: "anthropic-ai", allow: "/" },
      { userAgent: "PerplexityBot", allow: "/" },
      { userAgent: "Applebot", allow: "/" },
      { userAgent: "Googlebot-Extended", allow: "/" },
      { userAgent: "Meta-ExternalAgent", allow: "/" },
      { userAgent: "cohere-ai", allow: "/" },
      { userAgent: "AI2Bot", allow: "/" },
      { userAgent: "Diffbot", allow: "/" },
      { userAgent: "YouBot", allow: "/" },
      { userAgent: "Amazonbot", allow: "/" },
    ],
    sitemap: "https://www.cryptocatalyst.news/sitemap.xml",
    host: "https://www.cryptocatalyst.news",
  };
}
