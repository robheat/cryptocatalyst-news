import { MetadataRoute } from "next";
import { getAllArticles } from "@/lib/content";
import { CATEGORIES } from "@/lib/types";

const BASE_URL = "https://www.cryptocatalyst.news";

export default function sitemap(): MetadataRoute.Sitemap {
  const articles = getAllArticles();

  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
  const articleEntries: MetadataRoute.Sitemap = articles.map((a) => ({
    url: `${BASE_URL}/articles/${a.slug}`,
    lastModified: new Date(a.publishedAt),
    changeFrequency: "weekly" as const,
    priority: new Date(a.publishedAt) > thirtyDaysAgo ? 0.8 : 0.6,
  }));

  const categoryEntries: MetadataRoute.Sitemap = CATEGORIES.map((c) => ({
    url: `${BASE_URL}/categories/${c.value}`,
    lastModified: new Date(),
    changeFrequency: "daily",
    priority: 0.5,
  }));

  return [
    {
      url: BASE_URL,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 1.0,
    },
    {
      url: `${BASE_URL}/archive`,
      lastModified: new Date(),
      changeFrequency: "daily",
      priority: 0.6,
    },
    {
      url: `${BASE_URL}/newsletter`,
      lastModified: new Date(),
      changeFrequency: "monthly",
      priority: 0.4,
    },
    ...categoryEntries,
    ...articleEntries,
  ];
}
