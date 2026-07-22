import { Metadata } from "next";
import { getPaginatedArticles } from "@/lib/content";
import ArticleCard from "@/components/ArticleCard";
import Link from "next/link";

export const revalidate = 86400;

const BASE_URL = "https://www.cryptocatalyst.news";

interface Props {
  searchParams: Promise<{ page?: string; q?: string }>;
}

export async function generateMetadata({ searchParams }: Props): Promise<Metadata> {
  const { page: pageParam, q } = await searchParams;
  const page = Math.max(1, parseInt(pageParam ?? "1", 10));

  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (page > 1) params.set("page", String(page));
  const query = params.toString();
  const canonical = `${BASE_URL}/archive${query ? `?${query}` : ""}`;

  const title = q
    ? `Search results for "${q}" — Archive`
    : page > 1
      ? `Archive — Page ${page}`
      : "Archive — All Crypto News";

  const description =
    "Browse the complete archive of crypto and blockchain news stories curated daily by CryptoCatalyst.";

  return {
    title,
    description,
    alternates: { canonical },
    // Search-result and deep-pagination pages are thin/duplicative — keep them
    // crawlable but out of the index; only the canonical page 1 should rank.
    robots: q || page > 1 ? { index: false, follow: true } : undefined,
    openGraph: {
      type: "website",
      siteName: "CryptoCatalyst",
      locale: "en_US",
      title,
      description,
      url: canonical,
      images: [
        {
          url: "/api/og?title=Archive+%E2%80%94+All+Crypto+News",
          width: 1200,
          height: 630,
          alt: "CryptoCatalyst Archive",
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      site: "@CryptoCatalystN",
      title,
      description,
      images: ["/api/og?title=Archive+%E2%80%94+All+Crypto+News"],
    },
  };
}

export default async function ArchivePage({ searchParams }: Props) {
  const { page: pageParam, q } = await searchParams;
  const page = Math.max(1, parseInt(pageParam ?? "1", 10));
  const { articles, totalPages } = getPaginatedArticles(page, 20, q);

  const pageHref = (n: number) => {
    const params = new URLSearchParams();
    if (q) params.set("q", q);
    if (n > 1) params.set("page", String(n));
    const query = params.toString();
    return `/archive${query ? `?${query}` : ""}`;
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
      <h1 className="text-2xl font-bold mb-2">Archive</h1>
      <p className="text-neutral-500 text-sm mb-6">
        {q ? (
          <>
            Search results for <span className="text-neutral-300">&ldquo;{q}&rdquo;</span>
          </>
        ) : (
          "All crypto stories, newest first."
        )}
      </p>

      <form action="/archive" method="get" className="mb-8 max-w-md">
        <input
          type="search"
          name="q"
          defaultValue={q ?? ""}
          placeholder="Search articles…"
          className="w-full text-sm bg-neutral-900 border border-neutral-700 rounded-md px-3 py-2 text-neutral-100 placeholder:text-neutral-600 focus:outline-none focus:border-amber-500"
        />
      </form>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-10">
        {articles.map((a) => (
          <ArticleCard key={a.slug} article={a} />
        ))}
      </div>

      {articles.length === 0 && (
        <p className="text-neutral-500 text-center py-16">
          {q
            ? `No stories match "${q}".`
            : "No articles yet. Check back after the first pipeline run."}
        </p>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          {page > 1 && (
            <Link
              href={pageHref(page - 1)}
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
              href={pageHref(page + 1)}
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
