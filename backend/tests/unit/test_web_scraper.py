"""Tests for web scraper utilities."""

from unittest.mock import AsyncMock, patch

import pytest


class TestWebScraper:
    """Tests for WebScraper."""

    def test_scraper_initializes(self):
        """Test that scraper initializes."""
        from app.services.enrichment.scraper import WebScraper

        scraper = WebScraper()
        assert scraper is not None

    @pytest.mark.asyncio
    async def test_fetch_page_returns_html(self):
        """Test fetching a page returns HTML content."""
        from app.services.enrichment.scraper import WebScraper

        scraper = WebScraper()

        mock_html = """
        <html>
            <head><title>About Us</title></head>
            <body>
                <h1>About Our Company</h1>
                <p>We are a leading provider of video solutions.</p>
            </body>
        </html>
        """

        with patch.object(scraper, "_fetch", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_html

            result = await scraper.fetch_page("https://example.com/about")

        assert result is not None
        assert "About Our Company" in result

    @pytest.mark.asyncio
    async def test_extract_text_strips_html(self):
        """Test extracting clean text from HTML."""
        from app.services.enrichment.scraper import WebScraper

        scraper = WebScraper()

        html = """
        <html>
            <head>
                <title>Test</title>
                <script>var x = 1;</script>
                <style>.test { color: red; }</style>
            </head>
            <body>
                <nav>Navigation here</nav>
                <main>
                    <h1>Main Content</h1>
                    <p>This is the important text.</p>
                </main>
                <footer>Footer content</footer>
            </body>
        </html>
        """

        result = scraper.extract_text(html)

        assert "Main Content" in result
        assert "important text" in result
        # Scripts and styles should be removed
        assert "var x = 1" not in result
        assert "color: red" not in result

    @pytest.mark.asyncio
    async def test_scrape_company_info_returns_structured_data(self):
        """Test scraping company info from a domain."""
        from app.services.enrichment.scraper import WebScraper

        scraper = WebScraper()

        mock_about_html = """
        <html>
            <body>
                <h1>About TechCorp</h1>
                <p>Founded in 2010, TechCorp is a leader in enterprise software.
                   Our mission is to simplify business operations.</p>
            </body>
        </html>
        """

        with patch.object(scraper, "_fetch", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_about_html

            result = await scraper.scrape_company_info("techcorp.com")

        assert result is not None
        assert "about_text" in result
        assert "TechCorp" in result["about_text"]

    @pytest.mark.asyncio
    async def test_handles_fetch_error(self):
        """Test handling fetch errors gracefully."""
        from app.services.enrichment.scraper import ScraperError, WebScraper

        scraper = WebScraper()

        with patch.object(scraper, "_fetch", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = ScraperError("Connection failed")

            with pytest.raises(ScraperError):
                await scraper.fetch_page("https://example.com")

    @pytest.mark.asyncio
    async def test_respects_robots_txt(self):
        """Test that scraper checks robots.txt."""
        from app.services.enrichment.scraper import WebScraper

        scraper = WebScraper()

        # Simulate a disallowed path
        with patch.object(
            scraper, "_is_allowed", new_callable=AsyncMock
        ) as mock_allowed:
            mock_allowed.return_value = False

            result = await scraper.fetch_page(
                "https://example.com/private", respect_robots=True
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_extract_news_finds_recent_items(self):
        """Test extracting news/press releases."""
        from app.services.enrichment.scraper import WebScraper

        scraper = WebScraper()

        mock_news_html = """
        <html>
            <body>
                <article>
                    <h2>TechCorp Announces New Partnership</h2>
                    <time datetime="2025-01-15">January 15, 2025</time>
                    <p>TechCorp today announced a strategic partnership...</p>
                </article>
                <article>
                    <h2>Q4 Results Exceed Expectations</h2>
                    <time datetime="2025-01-10">January 10, 2025</time>
                    <p>Fourth quarter revenue grew 25% year-over-year...</p>
                </article>
            </body>
        </html>
        """

        with patch.object(scraper, "_fetch", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_news_html

            result = await scraper.extract_news("https://techcorp.com/news")

        assert result is not None
        assert len(result) >= 1
        assert "Partnership" in result[0]["title"] or "Results" in result[0]["title"]
