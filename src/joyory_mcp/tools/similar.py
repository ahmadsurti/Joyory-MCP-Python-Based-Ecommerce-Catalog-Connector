"""get_similar_products MCP tool."""

from __future__ import annotations
import logging
from joyory_mcp.errors import JoyoryProductNotFoundError, friendly_message
from joyory_mcp.cache import get_cache
from joyory_mcp.normalize import score_relevance

log = logging.getLogger(__name__)

# Module-level — not rebuilt on every call
_SIMILAR_SKIP_WORDS: frozenset[str] = frozenset({
    "for", "and", "with", "the", "a", "an", "of", "or", "&", "-",
})


async def get_similar_products(
    product_id: str,
    cheaper: bool = False,
    in_stock_only: bool = False,
    limit: int = 5,
    adapter=None,
) -> dict:
    """
    Find products similar to a given product.

    Args:
        product_id:    Product ID to find alternatives for.
        cheaper:       If true, only return products cheaper than the source product.
        in_stock_only: If true, exclude out-of-stock results.
        limit:         Max results (1–10, default 5).
        adapter:       JoyoryDataSource instance (injected by server).
    """
    if not product_id or not str(product_id).strip():
        return {"error": "product_id is required."}

    product_id = str(product_id).strip()
    if limit <= 0:
        return {"error": f"limit must be between 1 and 10, got {limit}.", "product_id": product_id}
    limit = min(limit, 10)

    cache = get_cache()
    # ponytail: include all filter params in key to avoid collision across cheaper/in_stock variants
    cache_key = f"similar:{product_id}:cheaper={cheaper}:stock={in_stock_only}:limit={limit}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    if adapter is None:
        return {"error": "Joyory data source not initialized.", "product_id": product_id}

    try:
        detail = await adapter.get_detail(product_id)
    except JoyoryProductNotFoundError:
        return {"error": f"Product '{product_id}' not found.", "product_id": product_id}
    except Exception as exc:
        log.error("get_similar_products fetch error: %s", exc, exc_info=True)
        return {"error": friendly_message(exc), "product_id": product_id}

    source_price = detail.price
    source_category = detail.category_slug or detail.category or ""
    source_name = detail.name

    # Build a meaningful search query — skip filler words, use up to 3 meaningful words
    name_words = [w for w in source_name.split() if w.lower() not in _SIMILAR_SKIP_WORDS]
    search_query = " ".join(name_words[:3]) if name_words else source_name

    try:
        candidates = await adapter.search(
            search_query,
            limit=20,
            category=source_category if source_category else None,
        )
    except Exception:
        candidates = []

    results = [p for p in candidates if p.id != product_id]

    if cheaper and source_price is not None:
        results = [r for r in results if r.price is not None and r.price < source_price]

    if in_stock_only:
        results = [r for r in results if r.in_stock is True]

    scored = sorted(results, key=lambda p: -score_relevance(p, source_name)[0])
    page = scored[:limit]

    out = {
        "source_product_id": product_id,
        "source_name": source_name,
        "results": [p.model_dump(exclude_none=True) for p in page],
        "count": len(page),
    }
    if not page:
        out["message"] = "No similar products found. Try search_products with the same category."

    cache.set(cache_key, out)
    return out
