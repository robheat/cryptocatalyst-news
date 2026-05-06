import { Article } from "@/lib/types";

interface Props {
  article: Article;
}

export default function SchemaMarkup({ article }: Props) {
  const ogImage = `https://cryptocatalyst.news/api/og?title=${encodeURIComponent(article.title)}`;

  const schema = {
    "@context": "https://schema.org",
    "@type": "NewsArticle",
    headline: article.title,
    description: article.summary,
    url: `https://cryptocatalyst.news/articles/${article.slug}`,
    inLanguage: "en-US",
    datePublished: article.publishedAt,
    dateModified: article.publishedAt,
    author: {
      "@type": "Organization",
      name: "CryptoCatalyst",
      url: "https://cryptocatalyst.news",
    },
    publisher: {
      "@type": "Organization",
      name: "CryptoCatalyst",
      url: "https://cryptocatalyst.news",
      logo: {
        "@type": "ImageObject",
        url: "https://cryptocatalyst.news/logo.png",
      },
    },
    mainEntityOfPage: {
      "@type": "WebPage",
      "@id": `https://cryptocatalyst.news/articles/${article.slug}`,
    },
    image: {
      "@type": "ImageObject",
      url: article.imageUrl ?? ogImage,
      width: article.imageUrl ? undefined : 1200,
      height: article.imageUrl ? undefined : 630,
    },
    keywords: article.tags.join(", "),
    articleSection: article.category,
    isAccessibleForFree: true,
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema, null, 2) }}
    />
  );
}
