export interface Article {
  slug: string;
  title: string;
  summary: string;
  body: string;
  sourceUrl: string;
  sourceName: string;
  category: Category;
  tags: string[];
  publishedAt: string; // ISO 8601
  imageUrl?: string;
  twitterThread?: string[];
  standaloneTweet?: string;
}

export type Category =
  | "bitcoin"
  | "ethereum"
  | "defi"
  | "nft"
  | "policy"
  | "web3"
  | "general";

export const CATEGORIES: { value: Category; label: string }[] = [
  { value: "bitcoin", label: "Bitcoin" },
  { value: "ethereum", label: "Ethereum" },
  { value: "defi", label: "DeFi" },
  { value: "nft", label: "NFTs" },
  { value: "policy", label: "Policy" },
  { value: "web3", label: "Web3" },
  { value: "general", label: "General" },
];
