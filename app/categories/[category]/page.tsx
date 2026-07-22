import { Metadata } from "next";
import { notFound } from "next/navigation";
import { getArticlesByCategory, getAllArticles } from "@/lib/content";
import { CATEGORIES, Category } from "@/lib/types";
import ArticleCard from "@/components/ArticleCard";

export const revalidate = 86400;

interface Props {
  params: Promise<{ category: string }>;
}

export async function generateStaticParams() {
  return CATEGORIES.map((c) => ({ category: c.value }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { category } = await params;
  const cat = CATEGORIES.find((c) => c.value === category);
  if (!cat) return {};
  return {
    title: `${cat.label} — Crypto News`,
    description: `Latest crypto ${cat.label.toLowerCase()} news, curated daily by CryptoCatalyst.`,
    alternates: { canonical: `https://www.cryptocatalyst.news/categories/${category}` },
    openGraph: {
      type: "website",
      siteName: "CryptoCatalyst",
      locale: "en_US",
      title: `${cat.label} — Crypto News | CryptoCatalyst`,
      description: `Latest crypto ${cat.label.toLowerCase()} news, curated daily by CryptoCatalyst.`,
      url: `https://www.cryptocatalyst.news/categories/${category}`,
      images: [{
        url: `/api/og?title=${encodeURIComponent(cat.label + " — Crypto News")}&category=${encodeURIComponent(cat.label)}`,
        width: 1200,
        height: 630,
        alt: `${cat.label} — Crypto News`,
      }],
    },
    twitter: {
      card: "summary_large_image",
      site: "@CryptoCatalystN",
      title: `${cat.label} — Crypto News | CryptoCatalyst`,
      description: `Latest crypto ${cat.label.toLowerCase()} news, curated daily by CryptoCatalyst.`,
      images: [`/api/og?title=${encodeURIComponent(cat.label + " — Crypto News")}&category=${encodeURIComponent(cat.label)}`],
    },
  };
}

export default async function CategoryPage({ params }: Props) {
  const { category } = await params;
  const cat = CATEGORIES.find((c) => c.value === category);
  if (!cat) notFound();

  const articles = getArticlesByCategory(category as Category);

  const breadcrumbSchema = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Home", item: "https://www.cryptocatalyst.news" },
      { "@type": "ListItem", position: 2, name: cat.label, item: `https://www.cryptocatalyst.news/categories/${cat.value}` },
    ],
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbSchema) }}
      />
      <div className="mb-8">
        <span className="text-xs font-medium uppercase tracking-wider px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30">
          {cat.label}
        </span>
        <h1 className="text-2xl font-bold mt-3">
          {cat.label} News
        </h1>
        <p className="text-neutral-500 text-sm mt-1">
          {articles.length} {articles.length === 1 ? "story" : "stories"} curated by CryptoCatalyst
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {articles.map((a) => (
          <ArticleCard key={a.slug} article={a} />
        ))}
      </div>

      {articles.length === 0 && (
        <p className="text-neutral-500 text-center py-16">
          No {cat.label.toLowerCase()} stories yet.
        </p>
      )}
    </div>
  );
}
