import { NextRequest, NextResponse } from "next/server";
import { getLatestArticles } from "@/lib/content";
import { Article } from "@/lib/types";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const secret = searchParams.get("secret");

  if (secret !== process.env.NEWSLETTER_SECRET) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const days = parseInt(searchParams.get("days") ?? "7", 10);
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - days);
  const cutoffStr = cutoff.toISOString().slice(0, 10);

  const articles = getLatestArticles(100).filter(
    (a) => a.publishedAt.slice(0, 10) >= cutoffStr
  );

  if (articles.length === 0) {
    return NextResponse.json(
      { error: "No articles found for this period" },
      { status: 404 }
    );
  }

  const weekEnd = new Date().toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });

  const html = renderDigestEmail(articles, weekEnd);
  const subject = `CryptoCatalyst Weekly: ${articles.length} crypto stories — ${weekEnd}`;

  return NextResponse.json({ html, subject, articleCount: articles.length });
}

function renderDigestEmail(articles: Article[], weekEnd: string): string {
  const articleRows = articles
    .slice(0, 15)
    .map(
      (a) => `
    <tr>
      <td style="padding:16px 0;border-bottom:1px solid #1f2937">
        <a href="https://cryptocatalyst.news/articles/${a.slug}"
           style="color:#a78bfa;text-decoration:none;font-size:16px;font-weight:600;line-height:1.4">
          ${escapeHtml(a.title)}
        </a>
        <div style="margin-top:4px">
          <span style="display:inline-block;background:#1f2937;color:#9ca3af;font-size:11px;padding:2px 8px;border-radius:99px;text-transform:uppercase;letter-spacing:0.5px">
            ${escapeHtml(a.category)}
          </span>
        </div>
        <p style="color:#9ca3af;font-size:14px;line-height:1.5;margin:8px 0 0 0">
          ${escapeHtml(a.summary.slice(0, 200))}${a.summary.length > 200 ? "…" : ""}
        </p>
      </td>
    </tr>`
    )
    .join("");

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="color-scheme" content="dark">
  <title>CryptoCatalyst Weekly Digest</title>
</head>
<body style="margin:0;padding:0;background:#0a0a0a;color:#ededed;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif">
  <div style="max-width:600px;margin:0 auto;padding:32px 20px">
    <!-- Header -->
    <div style="text-align:center;padding-bottom:24px;border-bottom:1px solid #1f2937">
      <h1 style="margin:0;font-size:24px;font-weight:700">
        <span style="color:#ffffff">Crypto</span><span style="color:#f59e0b">Catalyst</span><span style="color:#6b7280;font-size:14px">.news</span>
      </h1>
      <p style="margin:8px 0 0;color:#6b7280;font-size:13px">Weekly Crypto Digest — ${escapeHtml(weekEnd)}</p>
    </div>

    <!-- Intro -->
    <div style="padding:24px 0">
      <p style="margin:0;color:#d1d5db;font-size:15px;line-height:1.6">
        Here are the top ${articles.length} crypto and blockchain stories from this week. Click any headline to read the full article on CryptoCatalyst.
      </p>
    </div>

    <!-- Articles -->
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse">
      ${articleRows}
    </table>

    <!-- CTA -->
    <div style="text-align:center;padding:32px 0">
      <a href="https://cryptocatalyst.news"
         style="display:inline-block;background:#d97706;color:#ffffff;text-decoration:none;font-size:14px;font-weight:600;padding:12px 24px;border-radius:8px">
        Read all stories on CryptoCatalyst →
      </a>
    </div>

    <!-- Footer -->
    <div style="border-top:1px solid #1f2937;padding-top:20px;text-align:center">
      <p style="margin:0;color:#6b7280;font-size:12px;line-height:1.6">
        You received this because you subscribed to the CryptoCatalyst weekly digest.<br>
        <a href="https://cryptocatalyst.news/api/newsletter/unsubscribe?id={{CONTACT_ID}}" style="color:#f59e0b;text-decoration:none">Unsubscribe</a>
        &nbsp;·&nbsp;
        <a href="https://cryptocatalyst.news" style="color:#f59e0b;text-decoration:none">CryptoCatalyst.news</a>
        &nbsp;·&nbsp;
        <a href="https://twitter.com/CryptoCatalystN" style="color:#f59e0b;text-decoration:none">@CryptoCatalystN</a>
      </p>
    </div>
  </div>
</body>
</html>`;
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
