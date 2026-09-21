"""get_catalog_overview MCP tool — real categories tree + brands from dedicated APIs."""

from __future__ import annotations
import asyncio
import logging
import httpx
from joyory_mcp.cache import get_cache
from joyory_mcp import config as cfg

log = logging.getLogger(__name__)

_BASE = cfg.BEAUTY_BASE_URL
_HEADERS = cfg.BEAUTY_HEADERS


def _flatten_categories(nodes: list) -> list[dict]:
    """Recursively flatten the category tree into a list with full slug paths."""
    out = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        name = node.get("name", "")
        slug = node.get("slug", "")
        subs = node.get("subCategories") or node.get("children") or []
        # ponytail: category tree API returns no product counts — omit rather than emit 0
        out.append({"name": name, "slug": slug, "subcategory_count": len(subs)})
        if subs:
            out.extend(_flatten_categories(subs))
    return out


async def get_catalog_overview() -> dict:
    """
    Return the complete Joyory catalog map: full category tree and all brands.

    Uses dedicated API endpoints — accurate and complete, not sampled.

    Call this FIRST before any search to:
    - Know which category slugs exist (use them in search_products 'category' param)
    - Know which brands are stocked (use them in search_products 'brand' param)
    - Avoid saying "Joyory doesn't have X" based on a failed search

    Returns:
        categories: flat list of all categories with name, slug, subcategory_count
        brands:     list of {name, slug, product_count} sorted by product_count desc
        total_brands: number of brands
    """
    cache = get_cache()
    cache_key = "catalog:overview:v2"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    errors = []

    async with httpx.AsyncClient(headers=_HEADERS, timeout=15.0, follow_redirects=True) as client:
        cats_task = client.get(f"{_BASE}/api/user/categories/tree")
        brands_task = client.get(f"{_BASE}/api/user/brands")
        cats_resp, brands_resp = await asyncio.gather(cats_task, brands_task, return_exceptions=True)

    categories = []
    if isinstance(cats_resp, Exception):
        errors.append(f"categories: {cats_resp}")
    elif cats_resp.status_code >= 400:
        errors.append(f"categories: HTTP {cats_resp.status_code}")
    else:
        try:
            cats_data = cats_resp.json()
            if isinstance(cats_data, list):
                categories = _flatten_categories(cats_data)
        except Exception as e:
            errors.append(f"categories parse: {e}")

    brands = []
    if isinstance(brands_resp, Exception):
        errors.append(f"brands: {brands_resp}")
    elif brands_resp.status_code >= 400:
        errors.append(f"brands: HTTP {brands_resp.status_code}")
    else:
        try:
            brands_data = brands_resp.json()
            if isinstance(brands_data, list):
                brands = [
                    {
                        "name": b.get("name", ""),
                        "slug": b.get("slug", ""),
                        "product_count": b.get("count", 0),
                        "description": (b.get("description") or "")[:120] or None,
                    }
                    for b in brands_data if isinstance(b, dict) and b.get("name")
                ]
                brands.sort(key=lambda b: -(b["product_count"] or 0))
        except Exception as e:
            errors.append(f"brands parse: {e}")

    if not categories and not brands:
        return {
            "status": "error",
            "error": "Could not fetch catalog data.",
            "details": errors,
        }

    out: dict = {
        "status": "ok",
        "total_brands": len(brands),
        "categories": categories,
        "brands": brands,
        "note": (
            "Use 'slug' values from categories as the 'category' filter in search_products. "
            "Use 'slug' values from brands as the 'brand' filter."
        ),
    }
    if errors:
        out["partial_errors"] = errors

    cache.set(cache_key, out)
    return out
