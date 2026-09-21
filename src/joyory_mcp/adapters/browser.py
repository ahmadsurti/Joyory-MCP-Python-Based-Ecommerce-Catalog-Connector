"""
Browser fallback adapter using Playwright.
Used only when no clean API is available.
"""

from __future__ import annotations
import logging
from urllib.parse import quote_plus

from joyory_mcp.adapters.base import JoyoryDataSource
from joyory_mcp.models import ProductSummary, ProductDetail
from joyory_mcp.normalize import (
    normalize_product,
    normalize_product_detail,
    extract_products_from_response,
    looks_like_product,
)
from joyory_mcp.errors import JoyoryNoResultsError, JoyoryProductNotFoundError
from joyory_mcp import config as cfg

log = logging.getLogger(__name__)

_SKIP_URL_KEYWORDS = frozenset({
    "analytics", "telemetry", "tracking", "ads", "gtm",
    "facebook", "hotjar", "clarity", ".css", ".js", ".woff",
})


class BrowserJoyoryDataSource(JoyoryDataSource):
    """Captures XHR/fetch responses from Joyory's own UI via Playwright."""

    def __init__(self, source_config: dict | None = None):
        self._cfg = source_config or {}
        self._base = cfg.BASE_URL
        self._playwright = None
        self._browser = None

    async def _ensure_playwright(self) -> None:
        if self._playwright is None:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=cfg.BROWSER_HEADLESS,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )

    async def search(
        self,
        query: str,
        limit: int = 10,
        min_price: float | None = None,
        max_price: float | None = None,
        brand: str | None = None,
        category: str | None = None,
    ) -> list[ProductSummary]:
        await self._ensure_playwright()
        found_products: list[dict] = []
        q = quote_plus(query)  # safe URL encoding

        async def handle_response(response) -> None:
            try:
                if "json" not in response.headers.get("content-type", ""):
                    return
                if any(k in response.url.lower() for k in _SKIP_URL_KEYWORDS):
                    return
                body = await response.json()
                products = extract_products_from_response(body)
                if products:
                    found_products.extend(products)
            except Exception:
                pass

        page = await self._browser.new_page()
        try:
            page.on("response", handle_response)
            await page.goto(cfg.BASE_URL, timeout=30000, wait_until="networkidle")

            search_selectors = [
                'input[type="search"]', 'input[placeholder*="search" i]',
                'input[name="search"]', 'input[name="q"]',
                '#search', '.search-input', '[data-testid*="search" i]',
            ]
            search_input = None
            for selector in search_selectors:
                try:
                    el = await page.wait_for_selector(selector, timeout=3000)
                    if el:
                        search_input = el
                        break
                except Exception:
                    continue

            if search_input:
                await search_input.click()
                await search_input.fill(query)
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(4000)
            else:
                for url in [
                    f"{cfg.BASE_URL}/search?q={q}",
                    f"{cfg.BASE_URL}/search?query={q}",
                    f"{cfg.BASE_URL}/search/{q}",
                ]:
                    await page.goto(url, timeout=20000, wait_until="networkidle")
                    if found_products:
                        break
            await page.wait_for_timeout(3000)
        except Exception as e:
            log.error("Browser search error: %s", e)
        finally:
            await page.close()

        if not found_products:
            raise JoyoryNoResultsError(query)

        results = [normalize_product(p) for p in found_products]
        if min_price is not None:
            results = [r for r in results if r.price is None or r.price >= min_price]
        if max_price is not None:
            results = [r for r in results if r.price is None or r.price <= max_price]
        if brand:
            bl = brand.lower()
            results = [r for r in results if r.brand and bl in r.brand.lower()]
        return results[:limit]

    async def get_detail(self, product_id: str) -> ProductDetail:
        await self._ensure_playwright()
        found_detail: dict | None = None

        async def handle_response(response) -> None:
            nonlocal found_detail
            if found_detail is not None:
                return
            try:
                if "json" not in response.headers.get("content-type", ""):
                    return
                body = await response.json()
                if isinstance(body, dict) and looks_like_product(body):
                    found_detail = body
                    return
                for key in ("product", "data", "result"):
                    inner = body.get(key) if isinstance(body, dict) else None
                    if isinstance(inner, dict) and looks_like_product(inner):
                        found_detail = inner
                        return
            except Exception:
                pass

        page = await self._browser.new_page()
        try:
            page.on("response", handle_response)
            await page.goto(
                f"{cfg.BASE_URL}/product/{product_id}",
                timeout=20000, wait_until="networkidle",
            )
            await page.wait_for_timeout(3000)
        except Exception as e:
            log.error("Browser detail error: %s", e)
        finally:
            await page.close()

        if not found_detail:
            raise JoyoryProductNotFoundError(product_id)
        return normalize_product_detail(found_detail)

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._browser = None
        self._playwright = None
