import { NextResponse } from "next/server";
import { getAllArticles } from "@/lib/content";

export const dynamic = "force-static";
export const revalidate = 3600;

/**
 * /llms-full.txt — Complete plain-text dump of all article content.
 * Designed for LLM ingestion / RAG pipelines.
 */
export async function GET() {
  const articles = getAllArticles();

  const sections = articles.map((a) =>
    [
      `## ${a.title}`,
      `URL: https://cryptocatalyst.news/articles/${a.slug}`,
      `Date: ${a.publishedAt.slice(0, 10)}`,
      `Category: ${a.category}`,
      `Source: ${a.sourceName} (${a.sourceUrl})`,
      `Tags: ${a.tags.join(", ")}`,
      "",
      `Summary: ${a.summary}`,
      "",
      a.body,
      "",
      "---",
    ].join("\n")
  );

  const output = [
    "# CryptoCatalyst.news — Full Content Dump",
    `Generated: ${new Date().toISOString()}`,
    `Articles: ${articles.length}`,
    "",
    "This file contains the full text of every article published on CryptoCatalyst.news.",
    "It is provided for LLM crawlers, RAG pipelines, and AI research tools.",
    "",
    "===",
    "",
    ...sections,
  ].join("\n");

  return new NextResponse(output, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "public, max-age=3600",
    },
  });
}
