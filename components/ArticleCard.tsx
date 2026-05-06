import Link from "next/link";
import Image from "next/image";
import { Article } from "@/lib/types";
import { formatDate } from "@/lib/utils";

interface Props {
  article: Article;
  featured?: boolean;
}

export default function ArticleCard({ article, featured = false }: Props) {
  return (
    <article
      className={`group rounded-xl border border-neutral-800 bg-neutral-900 hover:border-violet-500 transition-colors duration-200 overflow-hidden ${
        featured ? "md:col-span-2" : ""
      }`}
    >
      <Link href={`/articles/${article.slug}`} className="block h-full">
        {article.imageUrl && (
          <div className={`relative w-full overflow-hidden bg-neutral-800 ${
            featured ? "h-48 md:h-56" : "h-40"
          }`}>
            <Image
              src={article.imageUrl}
              alt={article.title}
              fill
              className="object-cover group-hover:scale-105 transition-transform duration-300"
              sizes={featured ? "(max-width: 768px) 100vw, 66vw" : "(max-width: 768px) 100vw, 33vw"}
            />
          </div>
        )}
        <div className="p-5">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xs font-medium uppercase tracking-wider px-2 py-0.5 rounded-full bg-violet-500/20 text-violet-400 border border-violet-500/30">
            {article.category}
          </span>
          <time
            dateTime={article.publishedAt}
            className="text-xs text-neutral-500"
          >
            {formatDate(article.publishedAt)}
          </time>
        </div>

        <h2
          className={`font-semibold text-neutral-100 group-hover:text-violet-300 transition-colors leading-snug mb-2 ${
            featured ? "text-xl md:text-2xl" : "text-base"
          }`}
        >
          {article.title}
        </h2>

        <p className="text-sm text-neutral-400 line-clamp-3 leading-relaxed">
          {article.summary}
        </p>

        <div className="mt-4 flex items-center gap-2">
          <span className="text-xs text-neutral-600">via {article.sourceName}</span>
          {article.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="text-xs text-neutral-600 bg-neutral-800 px-1.5 py-0.5 rounded"
            >
              #{tag}
            </span>
          ))}
        </div>
        </div>
      </Link>
    </article>
  );
}
