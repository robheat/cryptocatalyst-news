import Link from "next/link";

export default function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="border-t border-neutral-800 bg-neutral-950 mt-16">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 flex flex-col sm:flex-row items-center justify-between gap-4">
        <p className="text-sm text-neutral-500">
          &copy; {year} CryptoCatalyst.news — Crypto news, automated daily.
        </p>
        <nav className="flex items-center gap-4">
          <Link
            href="/feed.xml"
            className="text-xs text-neutral-500 hover:text-amber-400 transition-colors"
          >
            RSS Feed
          </Link>
          <Link
            href="/newsletter"
            className="text-xs text-neutral-500 hover:text-amber-400 transition-colors"
          >
            Newsletter
          </Link>
          <Link
            href="/sitemap.xml"
            className="text-xs text-neutral-500 hover:text-neutral-300 transition-colors"
          >
            Sitemap
          </Link>
          <Link
            href="/llms.txt"
            className="text-xs text-neutral-500 hover:text-neutral-300 transition-colors"
          >
            llms.txt
          </Link>
          <a
            href="https://twitter.com/CryptoCatalystN"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-neutral-500 hover:text-sky-400 transition-colors"
          >
            Twitter / X
          </a>
        </nav>
      </div>
    </footer>
  );
}
