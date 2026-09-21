"""search_products MCP tool."""

from __future__ import annotations
import logging
from typing import Literal
from joyory_mcp.models import SearchResponse
from joyory_mcp.errors import JoyoryNoResultsError, friendly_message
from joyory_mcp.cache import get_cache
from joyory_mcp.normalize import score_relevance
from joyory_mcp.normalize import _to_brand_slug
from joyory_mcp import config as cfg

log = logging.getLogger(__name__)

SortOption = Literal["relevance", "price_asc", "price_desc", "rating", "newest"]


async def search_products(
    query: str,
    limit: int = 10,
    offset: int = 0,
    min_price: float | None = None,
    max_price: float | None = None,
    brand: str | None = None,
    category: str | None = None,
    in_stock_only: bool = False,
    sort: SortOption = "relevance",
    include_images: bool = False,
    adapter=None,
) -> dict:
    """
    Search Joyory products. Keyword search — not semantic.

    Args:
        query:         Free-text search (e.g. 'vitamin C serum', 'spf 50 sunscreen').
        limit:         Results per page (1–100, default 10).
        offset:        Skip N results for paging (default 0).
        min_price:     Minimum price in INR.
        max_price:     Maximum price in INR.
        brand:         Case-insensitive brand filter. Use brand slug from get_catalog_overview.
        category:      Category slug filter. Use slug from get_catalog_overview.
        in_stock_only: Exclude out-of-stock products.
        sort:          'relevance' (default) | 'price_asc' | 'price_desc' | 'rating' | 'newest'.
        include_images: Include image_url in results (default false — saves tokens).
        adapter:       JoyoryDataSource instance (injected by server).
    """
    limit = max(1, min(limit, cfg.MAX_RESULTS))
    offset = max(0, offset)
    # Normalise brand input at the boundary — "DOT & KEY", "dot-key", "Dot Key" all work
    if brand:
        brand = _to_brand_slug(brand)

    cache = get_cache()
    cache_key = cache.search_key(query, limit, offset, min_price, max_price, brand, category, in_stock_only, sort)
    cached = cache.get(cache_key)
    if cached is not None:
        log.debug("Cache hit: %s", cache_key)
        return _maybe_strip_images(cached, include_images)

    if adapter is None:
        return {"error": "Joyory data source not initialized.", "query": query, "results": [], "total_matches": 0, "has_more": False, "count": 0}

    try:
        # Fetch generously so client-side sort/filter has material to work with
        fetch_limit = min(cfg.MAX_RESULTS, max(limit + offset + 10, 20))

        results = await adapter.search(
            query,
            limit=fetch_limit,
            min_price=min_price,
            max_price=max_price,
            brand=brand,
            category=category,
        )

        if in_stock_only:
            results = [r for r in results if r.in_stock is True]

        # Score + annotate match quality
        scored = [(score_relevance(r, query), r) for r in results]
        for (score, match), product in scored:
            product.match = match  # type: ignore[assignment]

        # Sort
        hint_parts = []
        if sort == "relevance":
            scored.sort(key=lambda x: x[0][0], reverse=True)
            results = [r for _, r in scored]
        elif sort == "price_asc":
            results = sorted(results, key=lambda r: (r.price is None, r.price or 0))
        elif sort == "price_desc":
            results = sorted(results, key=lambda r: (r.price is None, -(r.price or 0)))
        elif sort == "rating":
            results = sorted(results, key=lambda r: (r.rating is None, -(r.rating or 0)))
            # Warn if sort=rating is meaningless because all products have no reviews
            if all(r.rating is None for r in results):
                hint_parts.append(
                    "sort='rating' is uninformative here — no products in these results have reviews yet. "
                    "Results are in default API order. Call get_reviews on promising products to check quality."
                )
        # "newest" — keep API order

        total_matches = len(results)
        if results and query.strip() and all(r.match == "weak" for r in results):
            hint_parts.append(
                f"Results for '{query}' may only be loosely related. "
                "Try a shorter query, a different keyword, or use category/brand filters."
            )

        page = results[offset: offset + limit]
        # Compute has_more from the final total_matches (after potential zeroing above)
        has_more = (offset + limit) < total_matches

        # Build hint
        if not page:
            hint_parts.append(
                f"No matches for '{query}'"
                + (f" (brand: {brand})" if brand else "")
                + (f" (category: {category})" if category else "")
                + ". Call get_catalog_overview to see valid category slugs and brand names."
            )
        elif has_more:
            hint_parts.append(
                f"Showing {offset + 1}–{offset + len(page)} of {total_matches} matches. "
                f"Pass offset={offset + limit} to see more."
            )

        # Warn about weak matches dominating
        weak_count = sum(1 for r in page if r.match == "weak")
        if weak_count > len(page) // 2 and len(page) > 2:
            hint_parts.append(
                f"{weak_count}/{len(page)} results are weak matches — they may not be what you asked for. "
                "Try a more specific query or add a category filter."
            )

        response = SearchResponse(
            query=query,
            total_matches=total_matches,
            has_more=has_more,
            count=len(page),
            offset=offset,
            results=page,
            hint=(" | ".join(hint_parts) if hint_parts else None),
        )
        out = response.model_dump(exclude_none=True)
        cache.set(cache_key, out)
        return _maybe_strip_images(out, include_images)

    except JoyoryNoResultsError:
        return {
            "query": query,
            "results": [],
            "total_matches": 0,
            "has_more": False,
            "count": 0,
            "hint": f"No products found for '{query}'. Call get_catalog_overview to browse available categories.",
        }
    except Exception as exc:
        log.error("search_products error: %s", exc, exc_info=True)
        return {"error": friendly_message(exc), "query": query, "results": [], "total_matches": 0, "has_more": False, "count": 0}


def _maybe_strip_images(out: dict, include_images: bool) -> dict:
    if include_images:
        return out
    results = out.get("results", [])
    if not results:
        return out
    return {**out, "results": [{k: v for k, v in r.items() if k != "image_url"} for r in results]}
