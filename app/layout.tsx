import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import { SpeedInsights } from "@vercel/speed-insights/next";
import { Analytics } from "@vercel/analytics/next";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://www.cryptocatalyst.news"),
  title: {
    default: "CryptoCatalyst — Daily Crypto & Blockchain News",
    template: "%s | CryptoCatalyst",
  },
  description:
    "The latest crypto, blockchain, and Web3 news — curated and summarized daily by AI. Bitcoin, Ethereum, DeFi, NFTs, policy, and more.",
  keywords: [
    "crypto news",
    "blockchain",
    "Bitcoin",
    "Ethereum",
    "DeFi",
    "Web3",
    "daily crypto digest",
  ],
  openGraph: {
    type: "website",
    siteName: "CryptoCatalyst",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    site: "@CryptoCatalystN",
  },
  alternates: {
    types: {
      "application/rss+xml": "https://www.cryptocatalyst.news/feed.xml",
    },
  },
};

const orgSchema = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "CryptoCatalyst",
  url: "https://www.cryptocatalyst.news",
  logo: "https://www.cryptocatalyst.news/logo.png",
  sameAs: ["https://twitter.com/CryptoCatalystN"],
};

const websiteSchema = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: "CryptoCatalyst",
  url: "https://www.cryptocatalyst.news",
  description:
    "Daily crypto and blockchain news curated and summarized by artificial intelligence.",
  potentialAction: {
    "@type": "SearchAction",
    target: {
      "@type": "EntryPoint",
      urlTemplate: "https://www.cryptocatalyst.news/archive?q={search_term_string}",
    },
    "query-input": "required name=search_term_string",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(orgSchema) }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(websiteSchema) }}
        />
      </head>
      <body className="min-h-full flex flex-col bg-neutral-950 text-neutral-100">
        <Header />
        <main className="flex-1">{children}</main>
        <Footer />
        <SpeedInsights />
        <Analytics />
      </body>
    </html>
  );
}
