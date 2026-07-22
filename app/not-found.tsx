import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Page Not Found",
  robots: { index: false, follow: true },
};

export default function NotFound() {
  return (
    <div className="max-w-xl mx-auto px-4 sm:px-6 py-24 text-center">
      <p className="text-sm font-mono text-amber-400 mb-3">404</p>
      <h1 className="text-2xl font-bold text-neutral-100 mb-3">
        Page not found
      </h1>
      <p className="text-neutral-500 mb-8">
        The story or page you&apos;re looking for doesn&apos;t exist or may
        have moved.
      </p>
      <div className="flex items-center justify-center gap-4">
        <Link
          href="/"
          className="text-sm bg-amber-600 hover:bg-amber-500 text-white font-medium px-4 py-2 rounded-md transition-colors"
        >
          Back to homepage
        </Link>
        <Link
          href="/archive"
          className="text-sm text-neutral-400 hover:text-neutral-100 transition-colors"
        >
          Browse archive
        </Link>
      </div>
    </div>
  );
}
