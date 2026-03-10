"""
Browser Automation Tool
Uses Playwright to control a headless browser for web scraping,
form filling, and autonomous web interactions.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Playwright browser instance (lazy-loaded)
_browser = None
_playwright = None


async def _get_browser():
    """Lazy-load Playwright browser."""
    global _browser, _playwright
    if _browser is None:
        from playwright.async_api import async_playwright
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(headless=True)
        logger.info("Playwright browser launched")
    return _browser


async def scrape_page(url: str, wait_for: Optional[str] = None) -> dict:
    """
    Navigate to a URL and extract page content.

    Args:
        url: URL to navigate to
        wait_for: Optional CSS selector to wait for before extracting

    Returns:
        dict with title, text content, and links
    """
    try:
        browser = await _get_browser()
        page = await browser.new_page()

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        if wait_for:
            await page.wait_for_selector(wait_for, timeout=10000)

        title = await page.title()
        text = await page.inner_text("body")
        # Truncate very long pages
        text = text[:5000] if len(text) > 5000 else text

        # Extract links
        links = await page.evaluate("""
            () => Array.from(document.querySelectorAll('a[href]'))
                .slice(0, 20)
                .map(a => ({text: a.innerText.trim(), href: a.href}))
                .filter(l => l.text && l.href.startsWith('http'))
        """)

        await page.close()

        return {
            "title": title,
            "content": text,
            "links": links,
            "url": url,
        }

    except Exception as e:
        logger.error(f"Scrape error for {url}: {e}")
        return {"error": str(e), "url": url}


async def fill_form(
    url: str,
    fields: dict,
    submit_selector: Optional[str] = None,
) -> dict:
    """
    Navigate to a page and fill in form fields.

    Args:
        url: URL of the page with the form
        fields: Dict of {selector: value} pairs to fill
        submit_selector: CSS selector of the submit button (optional)

    Returns:
        dict with result of form submission
    """
    try:
        browser = await _get_browser()
        page = await browser.new_page()

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        for selector, value in fields.items():
            await page.fill(selector, value)

        if submit_selector:
            await page.click(submit_selector)
            await page.wait_for_load_state("domcontentloaded")

        result_text = await page.inner_text("body")
        result_url = page.url

        await page.close()

        return {
            "success": True,
            "result_url": result_url,
            "result_preview": result_text[:2000],
        }

    except Exception as e:
        logger.error(f"Form fill error: {e}")
        return {"success": False, "error": str(e)}


async def take_screenshot(url: str) -> dict:
    """Take a screenshot of a webpage and save it."""
    try:
        from pathlib import Path

        browser = await _get_browser()
        page = await browser.new_page()

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        screenshot_dir = Path.home() / "OMNIA_Downloads" / "screenshots"
        screenshot_dir.mkdir(parents=True, exist_ok=True)

        filename = f"screenshot_{hash(url) % 10000}.png"
        filepath = screenshot_dir / filename
        await page.screenshot(path=str(filepath), full_page=False)

        await page.close()

        return {
            "success": True,
            "path": str(filepath),
            "url": url,
        }

    except Exception as e:
        logger.error(f"Screenshot error: {e}")
        return {"success": False, "error": str(e)}


async def close_browser():
    """Cleanup: close the browser on shutdown."""
    global _browser, _playwright
    if _browser:
        await _browser.close()
        _browser = None
    if _playwright:
        await _playwright.stop()
        _playwright = None
