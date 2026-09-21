"""get_offers MCP tool — active promotions from Joyory's real promotions API."""

from __future__ import annotations
import logging
import re
import httpx
from joyory_mcp.cache import get_cache
from joyory_mcp import config as cfg

log = logging.getLogger(__name__)

# Confirmed from JS bundle: https://beauty.joyory.com/api/user/promotions/active?section=offers
_PROMOTIONS_URL = cfg.BEAUTY_BASE_URL + "/api/user/promotions/active"
_HEADERS = cfg.BEAUTY_HEADERS


async def get_offers() -> dict:
    """
    Fetch active promotions, BOGO deals, and discounts on Joyory.

    Returns structured offer data including:
    - type: 'bogo' (buy 1 get 1), 'discount' (% or flat off), 'collection' (price-capped bundles)
    - scope: 'brand' (applies to one brand) or 'global'
    - brand_slug: pass this as 'brand' to search_products to find eligible products
    - expires_at: ISO date when the offer ends
    - countdown_days: days remaining

    Always call this before finalising a cart — active BOGOs can effectively halve your cost.
    """
    cache = get_cache()
    cache_key = "offers:v2"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        async with httpx.AsyncClient(headers=_HEADERS, timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(_PROMOTIONS_URL, params={"section": "offers"})

        if resp.status_code >= 400:
            return {
                "status": "error",
                "offers": [],
                "count": 0,
                "error": f"Promotions API returned HTTP {resp.status_code}. No offer data available.",
            }

        raw = resp.json()
        if not isinstance(raw, list):
            raw = raw.get("data") or raw.get("promotions") or []

        offers = []
        for o in raw:
            if not isinstance(o, dict):
                continue

            meta = o.get("promoMeta") or {}
            brands = meta.get("brands") or []
            brand_info = brands[0] if brands else {}
            config = meta.get("promotionConfig") or {}
            countdown = o.get("countdown") or {}
            description = o.get("description") or ""

            # Extract coupon code from description text (e.g. "Use code GLOW")
            code = None
            code_match = re.search(r'\bcode\s+([A-Z0-9]{3,12})\b', description, re.IGNORECASE)
            if code_match:
                code = code_match.group(1).upper()

            discount_percent = o.get("discountPercent")
            label = o.get("discountLabel") or ""

            # Warn when label and discountPercent contradict (e.g. label="5% OFF" but desc says "15%")
            desc_percent_match = re.search(r'(\d+)\s*%', description)
            contradiction = None
            if desc_percent_match and discount_percent is not None:
                desc_pct = int(desc_percent_match.group(1))
                if desc_pct != int(discount_percent):
                    contradiction = (
                        f"discount_percent={discount_percent} but description says {desc_pct}% — "
                        "verify the actual discount at checkout."
                    )

            entry = {
                "title": o.get("title"),
                "description": description,
                "type": o.get("type"),
                "label": label,
                "discount_percent": discount_percent,
                "discount_amount": o.get("discountAmount"),
                "code": code,
                "scope": o.get("scope"),
                "brand_name": brand_info.get("name"),
                "brand_slug": brand_info.get("slug"),
                "max_price": config.get("maxProductPrice"),
                "expires_at": meta.get("endDate"),
                "countdown_days": countdown.get("days"),
                "tags": o.get("tags") or [],
            }
            if contradiction:
                entry["warning"] = contradiction
            # Skip silently expired offers (countdown went negative but endDate not cleaned up)
            if isinstance(entry.get("countdown_days"), (int, float)) and entry["countdown_days"] < 0:
                continue
            offers.append(entry)

        out = {
            "status": "ok",
            "count": len(offers),
            "offers": offers,
            "tip": (
                "For brand-scoped offers, use brand_slug as the 'brand' filter in search_products "
                "to find eligible products. BOGO deals can halve your effective cost."
            ),
        }
        if not offers:
            out["message"] = "No active promotions right now."

        cache.set(cache_key, out)
        return out

    except Exception as exc:
        log.error("get_offers error: %s", exc, exc_info=True)
        # Explicit error status — never dress up a failure as empty results
        return {
            "status": "error",
            "offers": [],
            "count": 0,
            "error": f"Failed to fetch offers: {exc}. This is a fetch failure, not 'no offers'.",
        }
