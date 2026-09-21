"""get_product_details MCP tool."""

from __future__ import annotations
import asyncio
import logging
from joyory_mcp.errors import JoyoryProductNotFoundError, friendly_message
from joyory_mcp.cache import get_cache

log = logging.getLogger(__name__)


async def get_product_details(
    product_ids: list[str],
    adapter=None,
) -> dict:
    """
    Retrieve full product details from Joyory. Accepts 1–5 product IDs.

    Returns structured information including description, ingredients,
    images, variants (with shade/size/hex/stock), and skincare attributes
    (skin_types, spf, fragrance_free, finish, key_ingredients).

    Use this when the user wants ingredients, variants, detailed description,
    or to compare a few specific products. Do NOT call on every search result.

    Args:
        product_ids: List of 1–5 stable product IDs from search_products results.
        adapter:     JoyoryDataSource instance (injected by server).
    """
    if not product_ids:
        return {"error": "product_ids list is required."}

    # Tolerate a bare string (demo scripts call with a single ID)
    if isinstance(product_ids, str):
        product_ids = [product_ids]

    requested = len(product_ids)
    # Dedupe while preserving order, cap at 5
    seen: set[str] = set()
    ids: list[str] = []
    for pid in product_ids:
        clean = str(pid).strip() if pid else ""
        if clean and clean not in seen:
            seen.add(clean)
            ids.append(clean)
        if len(ids) == 5:
            break

    dropped = requested - len(ids)

    if not ids:
        return {"error": "No valid product IDs provided."}

    if adapter is None:
        return {"error": "Joyory data source not initialized.", "product_ids": ids}

    cache = get_cache()

    async def _fetch_one(pid: str) -> dict:
        cache_key = cache.detail_key(pid)
        cached = cache.get(cache_key)
        if cached is not None:
            log.debug("Cache hit: %s", cache_key)
            return cached
        try:
            detail = await adapter.get_detail(pid)
            out = detail.model_dump(exclude_none=True)
            if out.get("name") and out["name"] != "Unknown Product":
                cache.set(cache_key, out)
            return out
        except JoyoryProductNotFoundError:
            return {"error": f"Product '{pid}' not found.", "id": pid}
        except Exception as exc:
            log.error("get_product_details error for %s: %s", pid, exc, exc_info=True)
            return {"error": friendly_message(exc), "id": pid}

    # Fetch all concurrently
    results = await asyncio.gather(*(_fetch_one(pid) for pid in ids))

    if len(ids) == 1:
        return results[0]

    out: dict = {"products": list(results), "count": len(results)}
    if dropped:
        out["warning"] = (
            f"Requested {requested} IDs, returned {len(ids)} "
            f"({requested - len(ids)} dropped: duplicates removed or cap of 5 reached)."
        )
    return out
