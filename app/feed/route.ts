import { NextResponse } from "next/server";
import { Feed } from "feed";
import { getAllArticles } from "@/lib/content";

export const dynamic = "force-static";
export const revalidate = 3600;

export async function GET() {
  const articles = getAllArticles().slice(0, 50);

  const feed = new Feed({
    title: "CryptoCatalyst — Daily Crypto & Blockchain News",
    description:
      "The latest crypto, blockchain, and Web3 news — curated and summarized daily by AI.",
    id: "https://cryptocatalyst.news/",
    link: "https://cryptocatalyst.news/",
    language: "en",
    favicon: "https://cryptocatalyst.news/favicon.ico",
    copyright: `© ${new Date().getFullYear()} CryptoCatalyst`,
    author: {
      name: "CryptoCatalyst",
      link: "https://cryptocatalyst.news",
    },
    feedLinks: {
      rss2: "https://cryptocatalyst.news/feed.xml",
    },
  });

  for (const article of articles) {
    feed.addItem({
      title: article.title,
      id: `https://cryptocatalyst.news/articles/${article.slug}`,
      link: `https://cryptocatalyst.news/articles/${article.slug}`,
      description: article.summary,
      content: article.body,
      date: new Date(article.publishedAt),
      category: [{ name: article.category }],
    });
  }

  return new NextResponse(feed.rss2(), {
    headers: {
      "Content-Type": "application/rss+xml; charset=utf-8",
      "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
    },
  });
}
