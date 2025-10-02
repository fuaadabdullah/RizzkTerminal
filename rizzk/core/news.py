"""RSS feed aggregation."""

from __future__ import annotations

from functools import lru_cache

import feedparser

FEEDS: dict[str, str] = {
    "MarketWatch": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    "Yahoo Finance": "https://finance.yahoo.com/news/rssindex",
    "Investing.com": "https://www.investing.com/rss/news.rss",
}


@lru_cache(maxsize=1)
def fetch_news(limit: int = 30) -> list[dict[str, str]]:
    """Return a curated list of news items from RSS feeds."""
    items: list[dict[str, str]] = []
    for source, url in FEEDS.items():
        feed = feedparser.parse(url)
        for entry in feed.entries[:15]:
            items.append(
                {
                    "source": source,
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                }
            )
    return items[:limit]
