import { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";
import { getArticleBySlug, getAllArticles } from "@/lib/content";
import SchemaMarkup from "@/components/SchemaMarkup";
import { formatDateTime } from "@/lib/utils";

export const revalidate = 3600;

interface Props {
  params: Promise<{ slug: string }>;
}

export async function generateStaticParams() {
  const articles = getAllArticles();
  return articles.map((a) => ({ slug: a.slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const article = getArticleBySlug(slug);
  if (!article) return {};

  return {
    title: article.title,
    description: article.summary,
    keywords: article.tags,
    openGraph: {
      title: article.title,
      description: article.summary,
      url: `https://cryptocatalyst.news/articles/${article.slug}`,
      type: "article",
      publishedTime: article.publishedAt,
      authors: ["CryptoCatalyst"],
      tags: article.tags,
      images: [
        {
          url: `/api/og?title=${encodeURIComponent(article.title)}`,
          width: 1200,
          height: 630,
          alt: article.title,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: article.title,
      description: article.summary,
      images: [`/api/og?title=${encodeURIComponent(article.title)}`],
    },
    alternates: {
      canonical: `https://cryptocatalyst.news/articles/${article.slug}`,
    },
  };
}

export default async function ArticlePage({ params }: Props) {
  const { slug } = await params;
  const article = getArticleBySlug(slug);
  if (!article) notFound();

  const paragraphs = article.body
    .split(/\n\n+/)
    .map((p) => p.trim())
    .filter(Boolean);

  const breadcrumbSchema = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Home", item: "https://cryptocatalyst.news" },
      { "@type": "ListItem", position: 2, name: article.category, item: `https://cryptocatalyst.news/categories/${article.category}` },
      { "@type": "ListItem", position: 3, name: article.title, item: `https://cryptocatalyst.news/articles/${article.slug}` },
    ],
  };

  return (
    <>
      <SchemaMarkup article={article} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbSchema) }} />
      <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
        {/* Breadcrumb */}
        <nav className="text-xs text-neutral-500 mb-6 flex items-center gap-1.5">
          <Link href="/" className="hover:text-neutral-300">
            Home
          </Link>
          <span>/</span>
          <Link
            href={`/categories/${article.category}`}
            className="hover:text-neutral-300 capitalize"
          >
            {article.category}
          </Link>
          <span>/</span>
          <span className="text-neutral-400 truncate max-w-xs">
            {article.title}
          </span>
        </nav>

        {/* Category + meta */}
        <div className="flex items-center gap-3 mb-4">
          <Link
            href={`/categories/${article.category}`}
            className="text-xs font-medium uppercase tracking-wider px-2 py-0.5 rounded-full bg-violet-500/20 text-violet-400 border border-violet-500/30 hover:bg-violet-500/30 transition-colors"
          >
            {article.category}
          </Link>
          <time
            dateTime={article.publishedAt}
            className="text-xs text-neutral-500"
          >
            {formatDateTime(article.publishedAt)}
          </time>
          <span className="text-xs text-neutral-600">via {article.sourceName}</span>
        </div>

        {/* Title */}
        <h1 className="text-2xl sm:text-3xl font-bold text-neutral-100 leading-tight mb-4">
          {article.title}
        </h1>

        {/* Summary callout */}
        <p className="text-base text-violet-300 border-l-2 border-violet-500 pl-4 mb-8 leading-relaxed">
          {article.summary}
        </p>

        {/* Hero image */}
        {article.imageUrl && (
          <div className="relative w-full aspect-video rounded-lg overflow-hidden mb-8 bg-neutral-800">
            <img
              src={article.imageUrl}
              alt={article.title}
              className="w-full h-full object-cover"
            />
          </div>
        )}

        {/* Body */}
        <div className="prose prose-invert prose-neutral max-w-none">
          {paragraphs.map((para, i) => (
            <p key={i} className="text-neutral-300 leading-relaxed mb-5">
              {para}
            </p>
          ))}
        </div>

        {/* Tags */}
        <div className="flex flex-wrap gap-2 mt-8 pt-6 border-t border-neutral-800">
          {article.tags.map((tag) => (
            <span
              key={tag}
              className="text-xs text-neutral-500 bg-neutral-800 border border-neutral-700 px-2 py-1 rounded"
            >
              #{tag}
            </span>
          ))}
        </div>

        {/* Source link */}
        <div className="mt-4 pt-4 border-t border-neutral-800">
          <a
            href={article.sourceUrl}
            target="_blank"
            rel="noopener noreferrer nofollow"
            className="text-sm text-violet-400 hover:text-violet-300 transition-colors"
          >
            Read original at {article.sourceName} →
          </a>
        </div>
      </div>
    </>
  );
}
