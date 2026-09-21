"""Simple in-memory TTL cache."""

from __future__ import annotations
import time
from typing import Any


class TTLCache:
    def __init__(self, ttl_seconds: int = 600) -> None:
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (value, time.monotonic() + self._ttl)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def clear(self) -> None:
        """Purge all cached entries. Used by tests and admin resets."""
        self._store.clear()

    def size(self) -> int:
        now = time.monotonic()
        return sum(1 for _, (_, exp) in self._store.items() if exp > now)

    @staticmethod
    def search_key(
        query: str,
        limit: int = 10,
        *args,
        offset: int = 0,
        min_price: float | None = None,
        max_price: float | None = None,
        brand: str | None = None,
        category: str | None = None,
        in_stock_only: bool = False,
        sort: str = "relevance",
        **kwargs,
    ) -> str:
        if len(args) == 2:
            max_price, brand = args
        elif len(args) == 7:
            offset, min_price, max_price, brand, category, in_stock_only, sort = args
        return (
            f"search:{query.lower().strip()}:{limit}:{offset}:"
            f"{min_price}:{max_price}:{(brand or '').lower()}:"
            f"{category}:{in_stock_only}:{sort}"
        )

    @staticmethod
    def detail_key(product_id: str) -> str:
        return f"detail:{product_id}"


_cache: TTLCache | None = None


def get_cache() -> TTLCache:
    global _cache
    if _cache is None:
        from joyory_mcp.config import CACHE_TTL_SECONDS
        _cache = TTLCache(ttl_seconds=CACHE_TTL_SECONDS)
    return _cache
