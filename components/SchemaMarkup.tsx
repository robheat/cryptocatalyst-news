import { Article } from "@/lib/types";

interface Props {
  article: Article;
}

export default function SchemaMarkup({ article }: Props) {
  const articleUrl = `https://www.cryptocatalyst.news/articles/${article.slug}`;
  const ogImage = `https://www.cryptocatalyst.news/api/og?title=${encodeURIComponent(article.title)}`;
  const imageUrl = article.imageUrl
    ? article.imageUrl.startsWith("http")
      ? article.imageUrl
      : `https://www.cryptocatalyst.news${article.imageUrl}`
    : ogImage;

  const fallbackSchema = {
    "@context": "https://schema.org",
    "@type": "NewsArticle",
    headline: article.title,
    description: article.summary,
    url: articleUrl,
    inLanguage: "en-US",
    datePublished: article.publishedAt,
    dateModified: article.publishedAt,
    author: {
      "@type": "Organization",
      name: "CryptoCatalyst",
      url: "https://www.cryptocatalyst.news",
    },
    publisher: {
      "@type": "Organization",
      name: "CryptoCatalyst",
      url: "https://www.cryptocatalyst.news",
      logo: {
        "@type": "ImageObject",
        url: "https://www.cryptocatalyst.news/logo.png",
      },
    },
    mainEntityOfPage: {
      "@type": "WebPage",
      "@id": articleUrl,
    },
    image: {
      "@type": "ImageObject",
      url: imageUrl,
      width: article.imageUrl ? undefined : 1200,
      height: article.imageUrl ? undefined : 630,
    },
    keywords: article.tags.join(", "),
    articleSection: article.category,
    isAccessibleForFree: true,
  };

  const schema = {
    ...fallbackSchema,
    ...(article.schema ?? {}),
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(schema, null, 2) }}
    />
  );
}
