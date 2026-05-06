import fs from "fs";
import path from "path";
import { Article, Category } from "./types";

const ARTICLES_DIR = path.join(process.cwd(), "content", "articles");

function ensureDir() {
  if (!fs.existsSync(ARTICLES_DIR)) {
    fs.mkdirSync(ARTICLES_DIR, { recursive: true });
  }
}

export function getAllArticles(): Article[] {
  ensureDir();
  const files = fs
    .readdirSync(ARTICLES_DIR)
    .filter((f) => f.endsWith(".json"))
    .sort()
    .reverse(); // newest first

  return files.map((file) => {
    const raw = fs.readFileSync(path.join(ARTICLES_DIR, file), "utf-8");
    return JSON.parse(raw) as Article;
  });
}

export function getArticleBySlug(slug: string): Article | undefined {
  const articles = getAllArticles();
  return articles.find((a) => a.slug === slug);
}

export function getArticlesByCategory(category: Category): Article[] {
  return getAllArticles().filter((a) => a.category === category);
}

export function getTodaysDigest(): Article[] {
  const today = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
  return getAllArticles().filter((a) => a.publishedAt.startsWith(today));
}

export function getLatestArticles(limit = 10): Article[] {
  return getAllArticles().slice(0, limit);
}

export function getPaginatedArticles(
  page: number,
  perPage = 20
): { articles: Article[]; total: number; totalPages: number } {
  const all = getAllArticles();
  const total = all.length;
  const totalPages = Math.max(1, Math.ceil(total / perPage));
  const articles = all.slice((page - 1) * perPage, page * perPage);
  return { articles, total, totalPages };
}
