import { Metadata } from "next";
import NewsletterSignup from "@/components/NewsletterSignup";

export const metadata: Metadata = {
  title: "Newsletter",
  description:
    "Subscribe to the CryptoCatalyst weekly digest — the top crypto and blockchain stories of the week, delivered every Sunday.",
  alternates: { canonical: "https://www.cryptocatalyst.news/newsletter" },
  openGraph: {
    type: "website",
    siteName: "CryptoCatalyst",
    locale: "en_US",
    title: "Newsletter — CryptoCatalyst",
    description:
      "Subscribe to the CryptoCatalyst weekly digest — the top crypto and blockchain stories of the week, delivered every Sunday.",
    url: "https://www.cryptocatalyst.news/newsletter",
    images: [
      {
        url: "/api/og?title=Weekly+Crypto+Digest+Newsletter",
        width: 1200,
        height: 630,
        alt: "CryptoCatalyst Weekly Newsletter",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    site: "@CryptoCatalystN",
    title: "Newsletter — CryptoCatalyst",
    description:
      "Subscribe to the CryptoCatalyst weekly digest — the top crypto and blockchain stories of the week, delivered every Sunday.",
    images: ["/api/og?title=Weekly+Crypto+Digest+Newsletter"],
  },
};

export default function NewsletterPage() {
  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-16">
      <div className="text-center mb-10">
        <h1 className="text-3xl font-bold text-neutral-100 mb-3">
          Weekly Crypto Digest
        </h1>
        <p className="text-neutral-400 text-lg leading-relaxed">
          Every Sunday, we send a curated email with the most important crypto
          and blockchain stories of the week — Bitcoin, Ethereum, DeFi, Web3,
          policy changes, and more.
        </p>
      </div>

      <NewsletterSignup />

      <div className="mt-16 grid grid-cols-1 sm:grid-cols-3 gap-6 text-center">
        <div>
          <div className="text-2xl mb-2">📰</div>
          <h3 className="text-sm font-semibold text-neutral-200 mb-1">
            Curated by AI
          </h3>
          <p className="text-xs text-neutral-500">
            Our pipeline reads hundreds of sources so you don&apos;t have to.
          </p>
        </div>
        <div>
          <div className="text-2xl mb-2">⚡</div>
          <h3 className="text-sm font-semibold text-neutral-200 mb-1">
            Once a Week
          </h3>
          <p className="text-xs text-neutral-500">
            No daily spam. Just the stories that matter, every Sunday.
          </p>
        </div>
        <div>
          <div className="text-2xl mb-2">🔓</div>
          <h3 className="text-sm font-semibold text-neutral-200 mb-1">
            Free Forever
          </h3>
          <p className="text-xs text-neutral-500">
            No paywall. Unsubscribe with one click anytime.
          </p>
        </div>
      </div>
    </div>
  );
}
