import { NextResponse } from "next/server";
import { Feed } from "feed";
import { getAllArticles } from "@/lib/content";

export const dynamic = "force-static";
export const revalidate = 86400;

export async function GET() {
  const articles = getAllArticles().slice(0, 50);

  const feed = new Feed({
    title: "CryptoCatalyst — Daily Crypto & Blockchain News",
    description:
      "The latest crypto, blockchain, and Web3 news — curated and summarized daily by AI.",
    id: "https://www.cryptocatalyst.news/",
    link: "https://www.cryptocatalyst.news/",
    language: "en",
    favicon: "https://www.cryptocatalyst.news/favicon.ico",
    copyright: `© ${new Date().getFullYear()} CryptoCatalyst`,
    author: {
      name: "CryptoCatalyst",
      link: "https://www.cryptocatalyst.news",
    },
    feedLinks: {
      rss2: "https://www.cryptocatalyst.news/feed.xml",
    },
  });

  for (const article of articles) {
    const itemTitle = article.seoTitle || article.title;
    const itemDescription = article.metaDescription || article.summary;
    const llmSummaryBlock = article.llmSummary
      ? `\n\nLLM Summary:\n${article.llmSummary}`
      : "";

    feed.addItem({
      title: itemTitle,
      id: `https://www.cryptocatalyst.news/articles/${article.slug}`,
      link: `https://www.cryptocatalyst.news/articles/${article.slug}`,
      description: itemDescription,
      content: `${article.body}${llmSummaryBlock}`,
      date: new Date(article.publishedAt),
      category: [{ name: article.category }],
    });
  }

  return new NextResponse(feed.rss2(), {
    headers: {
      "Content-Type": "application/rss+xml; charset=utf-8",
      "Cache-Control": "public, max-age=86400, stale-while-revalidate=604800",
    },
  });
}
