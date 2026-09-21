"""Abstract base class for all Joyory data sources."""

from __future__ import annotations
from abc import ABC, abstractmethod
from urllib.parse import urlparse
from joyory_mcp.models import ProductSummary, ProductDetail
from joyory_mcp import config as cfg


def validate_url(url: str) -> str:
    """Raise ValueError if url points outside joyory.com."""
    host = urlparse(url).netloc.lower().split(":")[0]
    if host not in cfg.ALLOWED_HOSTS and not host.endswith(".joyory.com"):
        raise ValueError(f"Blocked outbound request to non-Joyory host: {host}")
    return url


BROWSER_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": cfg.BASE_URL + "/",
    "Origin": cfg.BASE_URL,
}


class JoyoryDataSource(ABC):
    """All Joyory adapters implement this interface."""

    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int = 10,
        min_price: float | None = None,
        max_price: float | None = None,
        brand: str | None = None,
        category: str | None = None,
    ) -> list[ProductSummary]:
        """Search Joyory products. Returns normalized summaries."""

    @abstractmethod
    async def get_detail(self, product_id: str) -> ProductDetail:
        """Fetch full product details by ID."""

    async def close(self) -> None:
        """Clean up resources (e.g. HTTP sessions, browser)."""
