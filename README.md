# CryptoCatalyst.news

Automated daily crypto and blockchain news digest powered by AI. Built on Next.js.

Live at: **https://cryptocatalyst.news**

## What it does

- Fetches crypto/blockchain news from top RSS feeds (CoinDesk, CoinTelegraph, The Block, Decrypt, Bitcoin Magazine, Ethereum Foundation, and more)
- Curates and scores stories using Venice AI
- Generates full articles, Twitter threads, and OG images
- Publishes daily via GitHub Actions
- Sends weekly newsletter via Resend

## Getting Started

First, run the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Environment Variables

```
VENICE_AI_API_KEY=
RESEND_API_KEY=
RESEND_AUDIENCE_ID=
NEWSLETTER_SECRET=
TWITTER_API_KEY=
TWITTER_API_SECRET=
TWITTER_ACCESS_TOKEN=
TWITTER_ACCESS_SECRET=
```

## Stack

- **Frontend**: Next.js 16, TypeScript, Tailwind CSS
- **Pipeline**: Python 3.12, Venice AI
- **Newsletter**: Resend
- **Deployment**: Vercel + GitHub Actions


## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
