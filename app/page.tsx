import { Metadata } from "next";
import { getLatestArticles, getTodaysDigest } from "@/lib/content";
import ArticleCard from "@/components/ArticleCard";
import NewsletterSignup from "@/components/NewsletterSignup";
import { formatDate } from "@/lib/utils";

export const revalidate = 86400; // ISR: revalidate once daily (matches pipeline schedule)

export const metadata: Metadata = {
  title: "CryptoCatalyst — Daily Crypto & Blockchain News",
  description:
    "The latest crypto, blockchain, and Web3 news — curated and summarized daily by AI.",
  alternates: {
    canonical: "https://www.cryptocatalyst.news/",
  },
  openGraph: {
    title: "CryptoCatalyst — Daily Crypto & Blockchain News",
    description:
      "The latest crypto, blockchain, and Web3 news — curated and summarized daily by AI.",
    url: "https://www.cryptocatalyst.news",
    images: [
      {
        url: "/api/og?title=CryptoCatalyst+%E2%80%94+Daily+Crypto+News",
        width: 1200,
        height: 630,
        alt: "CryptoCatalyst — Daily Crypto & Blockchain News",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "CryptoCatalyst — Daily Crypto & Blockchain News",
    description:
      "The latest crypto, blockchain, and Web3 news — curated and summarized daily by AI.",
    images: ["/api/og?title=CryptoCatalyst+%E2%80%94+Daily+Crypto+News"],
  },
};

export default function HomePage() {
  const todayArticles = getTodaysDigest();
  const recentArticles = getLatestArticles(12);
  const heroArticles = todayArticles.length > 0 ? todayArticles : recentArticles;
  const [featured, ...rest] = heroArticles;
  const today = new Date().toISOString();

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
      {/* Header bar */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-neutral-100">
            Today&apos;s Crypto Digest
          </h1>
          <p className="text-sm text-neutral-500 mt-0.5">
            {formatDate(today)} — curated &amp; summarized by AI
          </p>
        </div>
        <span
          className="text-xs font-mono text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-1 rounded"
        >
          {heroArticles.length} stories
        </span>
      </div>

      {/* Featured grid */}
      {featured && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
          <ArticleCard article={featured} featured />
          <div className="flex flex-col gap-4">
            {rest.slice(0, 2).map((a) => (
              <ArticleCard key={a.slug} article={a} />
            ))}
          </div>
        </div>
      )}

      {/* Secondary grid */}
      {rest.length > 2 && (
        <>
          <h2 className="text-lg font-semibold text-neutral-300 mb-4">
            More Stories
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-10">
            {rest.slice(2).map((a) => (
              <ArticleCard key={a.slug} article={a} />
            ))}
          </div>
        </>
      )}

      {/* Empty state */}
      {heroArticles.length === 0 && (
        <div className="text-center py-24 text-neutral-500">
          <p className="text-lg">Pipeline runs daily at 7 AM UTC.</p>
          <p className="text-sm mt-2">Check back soon for today&apos;s AI digest.</p>
        </div>
      )}

      {/* Newsletter CTA */}
      <div className="mt-4">
        <NewsletterSignup />
      </div>
    </div>
  );
}

