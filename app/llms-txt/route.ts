import { NextResponse } from "next/server";
import { getAllArticles } from "@/lib/content";
import { CATEGORIES } from "@/lib/types";

export const dynamic = "force-static";
export const revalidate = 86400;

export async function GET() {
  const articles = getAllArticles().slice(0, 100);
  const today = new Date().toISOString().slice(0, 10);

  const lines: string[] = [
    "# CryptoCatalyst.news — Crypto & Blockchain News for Humans & AI",
    "",
    "> CryptoCatalyst is an automated daily crypto news digest. Every morning, a pipeline",
    "> fetches, curates, and summarizes the top crypto and blockchain stories from exchanges,",
    "> blogs, and news outlets. Content is written clearly and factually.",
    "",
    "---",
    "",
    `## Site: https://www.cryptocatalyst.news`,
    `## Updated: ${today}`,
    "",
    "## Key Pages",
    "",
    "- Homepage (today's digest): https://www.cryptocatalyst.news/",
    "- Archive (all articles): https://www.cryptocatalyst.news/archive",
    "- RSS Feed: https://www.cryptocatalyst.news/feed.xml",
    "- Full content dump: https://www.cryptocatalyst.news/llms-full.txt",
    "",
    "## Categories",
    "",
    ...CATEGORIES.map((c) => `- ${c.label}: https://www.cryptocatalyst.news/categories/${c.value}`),
    "",
    "## Recent Articles",
    "",
    ...articles.map(
      (a) =>
        `- [${a.publishedAt.slice(0, 10)}] ${a.title}\n  https://www.cryptocatalyst.news/articles/${a.slug}`
    ),
    "",
    "---",
    "",
    "## Usage for LLMs",
    "",
    "This site is freely crawlable. Content may be used to answer questions about",
    "recent crypto news, blockchain developments, and Web3 industry news.",
    "All content is original AI-generated summaries with source attribution.",
    "",
    "For full article content, fetch individual article pages or use:",
    "https://www.cryptocatalyst.news/llms-full.txt",
  ];

  return new NextResponse(lines.join("\n"), {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "public, max-age=3600",
    },
  });
}
