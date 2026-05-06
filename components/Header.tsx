import Link from "next/link";
import { CATEGORIES } from "@/lib/types";

export default function Header() {
  return (
    <header className="sticky top-0 z-50 border-b border-neutral-800 bg-neutral-950/90 backdrop-blur-sm">
      <div className="max-w-6xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-14">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-xl font-bold text-white">
              Crypto<span className="text-amber-400">Catalyst</span>
            </span>
            <span className="hidden sm:block text-xs text-neutral-500 font-mono">.news</span>
          </Link>

          <nav className="hidden md:flex items-center gap-1">
            {CATEGORIES.slice(0, 5).map((cat) => (
              <Link
                key={cat.value}
                href={`/categories/${cat.value}`}
                className="text-sm text-neutral-400 hover:text-neutral-100 px-3 py-1 rounded-md hover:bg-neutral-800 transition-colors"
              >
                {cat.label}
              </Link>
            ))}
          </nav>

          <div className="flex items-center gap-3">
            <Link
              href="/newsletter"
              className="text-xs bg-amber-600 hover:bg-amber-500 text-white font-medium px-3 py-1 rounded-md transition-colors"
            >
              Newsletter
            </Link>
            <Link
              href="/feed.xml"
              className="text-xs text-neutral-500 hover:text-orange-400 transition-colors font-mono"
              title="RSS Feed"
            >
              RSS
            </Link>
            <Link
              href="/archive"
              className="text-sm text-neutral-400 hover:text-neutral-100 transition-colors"
            >
              Archive
            </Link>
          </div>
        </div>
      </div>
    </header>
  );
}
