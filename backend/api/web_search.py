"""Lightweight web search via Google News RSS and targeted sports feeds.

No API keys required — uses public RSS endpoints.
"""

from __future__ import annotations

import logging
import re
from html import unescape

import httpx

logger = logging.getLogger(__name__)

TIMEOUT = httpx.Timeout(10.0)
GNEWS_RSS = "https://news.google.com/rss/search"

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return unescape(_TAG_RE.sub("", text)).strip()


def _parse_rss_items(xml: str, max_items: int = 8) -> list[dict]:
    items = re.findall(
        r"<item>(.*?)</item>", xml, re.DOTALL
    )
    results = []
    for item_xml in items[:max_items]:
        title_m = re.search(r"<title>(.*?)</title>", item_xml)
        link_m = re.search(r"<link>(.*?)</link>", item_xml, re.DOTALL)
        # Google News uses <link/>\nURL format sometimes
        if not link_m:
            link_m = re.search(r"<link\s*/>\s*(https?://\S+)", item_xml)
        desc_m = re.search(r"<description>(.*?)</description>", item_xml, re.DOTALL)
        pub_m = re.search(r"<pubDate>(.*?)</pubDate>", item_xml)
        source_m = re.search(r"<source[^>]*>(.*?)</source>", item_xml)

        results.append({
            "title": _strip_html(title_m.group(1)) if title_m else "",
            "url": (link_m.group(1).strip() if link_m else ""),
            "snippet": _strip_html(desc_m.group(1))[:300] if desc_m else "",
            "published": pub_m.group(1) if pub_m else "",
            "source": _strip_html(source_m.group(1)) if source_m else "",
        })
    return results


async def search_news(query: str, max_results: int = 8) -> list[dict]:
    """Search Google News RSS for a query. Returns titles, snippets, sources, dates."""
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        resp = await client.get(GNEWS_RSS, params={
            "q": query,
            "hl": "en-US",
            "gl": "US",
            "ceid": "US:en",
        })
        resp.raise_for_status()

    return _parse_rss_items(resp.text, max_results)


async def search_player_news(player_name: str) -> list[dict]:
    """Search for recent fantasy-relevant news about a specific player."""
    return await search_news(
        f"{player_name} MLB fantasy baseball",
        max_results=6,
    )


async def search_fantasy_news(topic: str = "fantasy baseball") -> list[dict]:
    """Search for general fantasy baseball news, waiver wire, or injury updates."""
    return await search_news(topic, max_results=8)
