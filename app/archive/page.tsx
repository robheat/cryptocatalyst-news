import { Metadata } from "next";
import { getPaginatedArticles } from "@/lib/content";
import ArticleCard from "@/components/ArticleCard";
import Link from "next/link";

export const revalidate = 86400;

export const metadata: Metadata = {
  title: "Archive — All Crypto News",
  description:
    "Browse the complete archive of crypto and blockchain news stories curated daily by CryptoCatalyst.",
  alternates: { canonical: "https://www.cryptocatalyst.news/archive" },
};

interface Props {
  searchParams: Promise<{ page?: string }>;
}

export default async function ArchivePage({ searchParams }: Props) {
  const { page: pageParam } = await searchParams;
  const page = Math.max(1, parseInt(pageParam ?? "1", 10));
  const { articles, totalPages } = getPaginatedArticles(page, 20);

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
      <h1 className="text-2xl font-bold mb-2">Archive</h1>
      <p className="text-neutral-500 text-sm mb-8">
        All crypto stories, newest first.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-10">
        {articles.map((a) => (
          <ArticleCard key={a.slug} article={a} />
        ))}
      </div>

      {articles.length === 0 && (
        <p className="text-neutral-500 text-center py-16">
          No articles yet. Check back after the first pipeline run.
        </p>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          {page > 1 && (
            <Link
              href={`/archive?page=${page - 1}`}
              className="px-4 py-2 rounded border border-neutral-700 hover:border-violet-500 text-sm transition-colors"
            >
              ← Previous
            </Link>
          )}
          <span className="text-sm text-neutral-500">
            Page {page} of {totalPages}
          </span>
          {page < totalPages && (
            <Link
              href={`/archive?page=${page + 1}`}
              className="px-4 py-2 rounded border border-neutral-700 hover:border-violet-500 text-sm transition-colors"
            >
              Next →
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
