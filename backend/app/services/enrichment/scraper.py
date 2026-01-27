"""Web scraper utilities for enrichment.

Provides functions to fetch and extract content from public web pages
for sales intelligence gathering.
"""

import re
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


class ScraperError(Exception):
    """Error during web scraping."""

    pass


class WebScraper:
    """
    Web scraper for extracting company information.

    Features:
    - Fetch pages with proper headers and timeouts
    - Extract clean text from HTML
    - Parse company about pages and news
    - Respect robots.txt (optional)
    """

    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (compatible; SalesBot/1.0; +https://epiphan.com)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    # Tags to remove entirely (content is noise)
    REMOVE_TAGS = ["script", "style", "nav", "footer", "header", "aside", "noscript"]

    def __init__(self, timeout: float = 15.0):
        """Initialize scraper with timeout."""
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._robots_cache: dict[str, set[str]] = {}

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers=self.DEFAULT_HEADERS,
                timeout=self.timeout,
                follow_redirects=True,
            )
        return self._client

    async def _fetch(self, url: str) -> str:
        """Fetch URL content."""
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as e:
            raise ScraperError(f"HTTP error {e.response.status_code}: {url}") from e
        except httpx.RequestError as e:
            raise ScraperError(f"Request failed: {e}") from e

    async def _is_allowed(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt."""
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        # Check cache
        if base_url in self._robots_cache:
            disallowed = self._robots_cache[base_url]
            return not any(parsed.path.startswith(p) for p in disallowed)

        # Fetch robots.txt
        try:
            robots_url = f"{base_url}/robots.txt"
            robots_text = await self._fetch(robots_url)

            disallowed: set[str] = set()
            for line in robots_text.split("\n"):
                line = line.strip().lower()
                if line.startswith("disallow:"):
                    path = line.split(":", 1)[1].strip()
                    if path:
                        disallowed.add(path)

            self._robots_cache[base_url] = disallowed
            return not any(parsed.path.startswith(p) for p in disallowed)

        except ScraperError:
            # No robots.txt or error fetching - assume allowed
            self._robots_cache[base_url] = set()
            return True

    async def fetch_page(
        self,
        url: str,
        respect_robots: bool = False,
    ) -> str | None:
        """
        Fetch a web page.

        Args:
            url: URL to fetch
            respect_robots: Check robots.txt before fetching

        Returns:
            HTML content or None if not allowed
        """
        if respect_robots and not await self._is_allowed(url):
            return None

        return await self._fetch(url)

    def extract_text(self, html: str) -> str:
        """
        Extract clean text from HTML.

        Removes scripts, styles, navigation, and other noise.

        Args:
            html: Raw HTML content

        Returns:
            Clean text content
        """
        soup = BeautifulSoup(html, "lxml")

        # Remove noise tags entirely
        for tag_name in self.REMOVE_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        # Get text, collapse whitespace
        text = soup.get_text(separator=" ", strip=True)

        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    async def scrape_company_info(self, domain: str) -> dict[str, Any] | None:
        """
        Scrape company information from a domain.

        Attempts to find and parse about page.

        Args:
            domain: Company domain (e.g., 'company.com')

        Returns:
            Dict with about_text, or None if not found
        """
        base_url = f"https://{domain}"

        # Common about page paths
        about_paths = ["/about", "/about-us", "/company", "/about.html"]

        for path in about_paths:
            try:
                url = urljoin(base_url, path)
                html = await self._fetch(url)
                text = self.extract_text(html)

                if len(text) > 100:  # Has meaningful content
                    return {
                        "about_url": url,
                        "about_text": text[:2000],  # Truncate for LLM context
                    }
            except ScraperError:
                continue

        # Try homepage as fallback
        try:
            html = await self._fetch(base_url)
            text = self.extract_text(html)
            return {
                "about_url": base_url,
                "about_text": text[:2000],
            }
        except ScraperError:
            return None

    async def extract_news(self, url: str) -> list[dict[str, Any]]:
        """
        Extract news/press release items from a page.

        Args:
            url: URL of news or press release page

        Returns:
            List of news items with title, date, summary
        """
        try:
            html = await self._fetch(url)
        except ScraperError:
            return []

        soup = BeautifulSoup(html, "lxml")
        news_items = []

        # Look for article elements
        articles = soup.find_all("article")

        for article in articles[:10]:  # Limit to 10 items
            item: dict[str, Any] = {}

            # Find title (h1, h2, or h3)
            title_tag = article.find(["h1", "h2", "h3"])
            if title_tag:
                item["title"] = title_tag.get_text(strip=True)

            # Find date
            time_tag = article.find("time")
            if time_tag:
                item["date"] = time_tag.get("datetime") or time_tag.get_text(strip=True)

            # Find summary (first paragraph)
            p_tag = article.find("p")
            if p_tag:
                item["summary"] = p_tag.get_text(strip=True)[:300]

            if item.get("title"):
                news_items.append(item)

        return news_items

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton instance
web_scraper = WebScraper()
