"""Web scraper with multi-engine fallback: Firecrawl → Crawl4AI → httpx+BS4."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class ScrapedPage:
    url: str
    title: str = ""
    text: str = ""
    links: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    engine: str = "httpx"


def scrape_url(url: str) -> ScrapedPage:
    """Scrape a single URL with Firecrawl → Crawl4AI → httpx fallback."""
    # 1. Try Firecrawl (hosted, best quality)
    if settings.firecrawl_api_key:
        try:
            return _scrape_firecrawl(url)
        except Exception as exc:
            logger.warning("Firecrawl failed: %s", exc)

    # 2. Try Crawl4AI (local headless)
    try:
        return _scrape_crawl4ai(url)
    except Exception as exc:
        logger.warning("Crawl4AI failed: %s", exc)

    # 3. Fallback: plain httpx + BeautifulSoup
    return _scrape_httpx(url)


def scrape_urls(urls: list[str]) -> list[ScrapedPage]:
    return [scrape_url(u) for u in urls]


# ── Engines ──────────────────────────────────────────────────────────────────

def _scrape_firecrawl(url: str) -> ScrapedPage:
    from firecrawl import FirecrawlApp
    app = FirecrawlApp(api_key=settings.firecrawl_api_key)
    result = app.scrape_url(url, params={"formats": ["markdown"]})
    return ScrapedPage(
        url=url,
        title=result.get("metadata", {}).get("title", ""),
        text=result.get("markdown", result.get("content", "")),
        metadata=result.get("metadata", {}),
        engine="firecrawl",
    )


def _scrape_crawl4ai(url: str) -> ScrapedPage:
    import asyncio
    from crawl4ai import AsyncWebCrawler

    async def _run():
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(url=url)
            return ScrapedPage(
                url=url,
                title=result.metadata.get("title", "") if result.metadata else "",
                text=result.markdown or result.html or "",
                metadata=result.metadata or {},
                engine="crawl4ai",
            )

    return asyncio.run(_run())


def _scrape_httpx(url: str) -> ScrapedPage:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        )
    }
    resp = httpx.get(url, headers=headers, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove noise elements
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    title = soup.title.string.strip() if soup.title else urlparse(url).netloc
    text = soup.get_text(separator="\n", strip=True)
    links = [a.get("href", "") for a in soup.find_all("a") if a.get("href")]

    return ScrapedPage(url=url, title=title, text=text, links=links, engine="httpx")
