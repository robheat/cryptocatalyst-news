"""
fetch_feeds.py — Pull raw stories from RSS feeds and targeted web scraping.
Outputs: pipeline/cache/raw_stories.json
"""
import json
import os
import re
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from html import unescape

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)
OUTPUT_FILE = CACHE_DIR / "raw_stories.json"

# RSS feeds to poll
RSS_FEEDS = [
    {
        "name": "CoinDesk",
        "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "category_hint": "general",
    },
    {
        "name": "CoinTelegraph",
        "url": "https://cointelegraph.com/rss",
        "category_hint": "general",
    },
    {
        "name": "The Block",
        "url": "https://www.theblock.co/rss.xml",
        "category_hint": "industry",
    },
    {
        "name": "Decrypt",
        "url": "https://decrypt.co/feed",
        "category_hint": "general",
    },
    {
        "name": "Bitcoin Magazine",
        "url": "https://bitcoinmagazine.com/.rss/full/",
        "category_hint": "bitcoin",
    },
    {
        "name": "Ethereum Foundation Blog",
        "url": "https://blog.ethereum.org/en/feed.xml",
        "category_hint": "ethereum",
    },
    {
        "name": "DeFi Pulse",
        "url": "https://defipulse.com/blog/feed/",
        "category_hint": "defi",
    },
    {
        "name": "Hacker News Crypto",
        "url": "https://hnrss.org/newest?q=bitcoin+OR+ethereum+OR+crypto+OR+blockchain+OR+DeFi&count=30",
        "category_hint": "general",
    },
    {
        "name": "Messari",
        "url": "https://messari.io/rss/news.xml",
        "category_hint": "industry",
    },
    {
        "name": "Blockworks",
        "url": "https://blockworks.co/feed",
        "category_hint": "industry",
    },
]

MAX_STORIES_PER_FEED = 15
REQUEST_TIMEOUT = 15


def _strip_html(text: str) -> str:
    """Remove HTML tags and unescape entities."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _fetch_url(url: str) -> bytes | None:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "CryptoCatalystBot/1.0 (+https://cryptocatalyst.news/llms.txt)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return resp.read()
    except Exception as exc:
        print(f"  [WARN] Failed to fetch {url}: {exc}")
        return None


def _ns(tag: str, namespace: str = "") -> str:
    return f"{{{namespace}}}{tag}" if namespace else tag


def _find_first(el: ET.Element, *paths: str) -> ET.Element | None:
    """Find the first matching child element, avoiding deprecated truth-value tests."""
    for p in paths:
        found = el.find(p)
        if found is not None:
            return found
    return None


def _find_all_first(el: ET.Element, *paths: str) -> list[ET.Element]:
    """Find all children matching the first path that returns results."""
    for p in paths:
        found = el.findall(p)
        if len(found) > 0:
            return found
    return []


def parse_rss(raw: bytes, source_name: str, category_hint: str) -> list[dict]:
    stories = []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        print(f"  [WARN] XML parse error for {source_name}: {e}")
        return stories

    # Handle RSS 2.0, Atom, and RDF feeds
    ns_atom = "http://www.w3.org/2005/Atom"
    ns_rdf = "http://purl.org/rss/1.0/"

    items = _find_all_first(
        root,
        ".//item",
        f".//{_ns('entry', ns_atom)}",
        f".//{_ns('item', ns_rdf)}",
    )

    if not items:
        print(f"  [WARN] No items found in feed for {source_name}")

    for item in items[:MAX_STORIES_PER_FEED]:
        title_el = _find_first(item, "title", _ns("title", ns_atom), _ns("title", ns_rdf))
        link_el = _find_first(item, "link", _ns("link", ns_atom), _ns("link", ns_rdf))
        desc_el = _find_first(
            item,
            "description",
            "summary",
            _ns("summary", ns_atom),
            _ns("content", ns_atom),
            _ns("description", ns_rdf),
        )
        pub_el = _find_first(
            item,
            "pubDate",
            "published",
            _ns("published", ns_atom),
            _ns("updated", ns_atom),
            "dc:date",
            "{http://purl.org/dc/elements/1.1/}date",
        )

        title = _strip_html(title_el.text if title_el is not None else "")
        # Atom <link> stores URL in href attribute
        link = ""
        if link_el is not None:
            link = link_el.get("href") or (link_el.text or "")
        link = link.strip()
        description = _strip_html(desc_el.text if desc_el is not None else "")[:600]
        pub_date = pub_el.text.strip() if pub_el is not None and pub_el.text else ""

        if not title or not link:
            continue

        stories.append(
            {
                "title": title,
                "url": link,
                "description": description,
                "source_name": source_name,
                "category_hint": category_hint,
                "pub_date": pub_date,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    return stories


def _load_processed_urls() -> set[str]:
    """Load URLs of stories we've already published, so we never re-process them."""
    articles_dir = Path(__file__).parent.parent / "content" / "articles"
    urls: set[str] = set()
    if not articles_dir.exists():
        return urls
    for f in articles_dir.iterdir():
        if f.suffix == ".json":
            try:
                data = json.loads(f.read_text())
                src = data.get("sourceUrl", "")
                if src:
                    urls.add(src)
            except Exception:
                pass
    return urls


def fetch_all() -> list[dict]:
    all_stories: list[dict] = []
    seen_urls: set[str] = set()

    # Load URLs we've already turned into articles — skip them entirely
    processed = _load_processed_urls()
    print(f"Already processed: {len(processed)} article URLs")

    for feed in RSS_FEEDS:
        print(f"Fetching: {feed['name']} ...")
        raw = _fetch_url(feed["url"])
        if raw is None:
            continue

        stories = parse_rss(raw, feed["name"], feed["category_hint"])
        new = [s for s in stories if s["url"] not in seen_urls and s["url"] not in processed]
        seen_urls.update(s["url"] for s in new)
        all_stories.extend(new)
        print(f"  → {len(new)} new stories (skipped {len(stories) - len(new)} already processed)")

    print(f"\nTotal new raw stories: {len(all_stories)}")
    return all_stories


if __name__ == "__main__":
    stories = fetch_all()
    OUTPUT_FILE.write_text(json.dumps(stories, indent=2, ensure_ascii=False))
    print(f"Saved to {OUTPUT_FILE}")
