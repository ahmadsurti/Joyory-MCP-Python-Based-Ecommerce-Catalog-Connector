"""get_reviews MCP tool — confirmed path: /api/reviews/product/{id}"""

from __future__ import annotations
import logging
import httpx
from joyory_mcp.cache import get_cache
from joyory_mcp import config as cfg

log = logging.getLogger(__name__)

# Confirmed from JS bundle: /api/reviews/product/${u._id}${K}  (K = query string)
_REVIEWS_URL = cfg.BEAUTY_BASE_URL + "/api/reviews/product/{id}"
_HEADERS = cfg.BEAUTY_HEADERS


async def get_reviews(product_id: str, limit: int = 10) -> dict:
    """
    Fetch customer reviews for a Joyory product.

    Reviews are the strongest signal for real-world product quality.
    Call this before recommending a product, especially when rating=null
    in search results (null means no reviews yet, not a bad product).

    Args:
        product_id: Product _id from search_products results (MongoDB ObjectId, e.g. '6a605e236325869f0ac3b497')
        limit:      Number of reviews to return (default 10, max 20)

    Returns:
        avg_rating:  null if no reviews
        total:       total number of reviews
        reviews:     list with rating, title, body, author, date, verified
        status:      "ok" | "error" | "no_reviews"
    """
    if not product_id or not str(product_id).strip():
        return {"status": "error", "error": "product_id is required."}

    product_id = str(product_id).strip()
    limit = max(1, min(limit, 20))

    cache = get_cache()
    cache_key = f"reviews:{product_id}:{limit}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    url = _REVIEWS_URL.format(id=product_id)

    try:
        async with httpx.AsyncClient(headers=_HEADERS, timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, params={"limit": limit, "page": 1})

        if resp.status_code == 404:
            return {
                "status": "no_reviews",
                "product_id": product_id,
                "avg_rating": None,
                "total": 0,
                "reviews": [],
                "message": "No reviews found for this product.",
            }
        if resp.status_code >= 400:
            return {
                "status": "error",
                "product_id": product_id,
                "error": f"Reviews API returned HTTP {resp.status_code}.",
                "reviews": [],
            }

        data = resp.json()

        # Confirmed schema: {"total": 0, "page": 1, "limit": 10, "reviews": []}
        reviews_raw = data.get("reviews") or []
        total = data.get("total", len(reviews_raw))
        avg = data.get("avgRating") or data.get("averageRating")

        reviews = []
        for r in reviews_raw[:limit]:
            if not isinstance(r, dict):
                continue
            reviews.append({
                "rating": r.get("rating") or r.get("stars"),
                "title": r.get("title") or r.get("heading"),
                "body": r.get("body") or r.get("comment") or r.get("review") or r.get("text"),
                "author": r.get("userName") or r.get("user") or r.get("author") or "Anonymous",
                "date": r.get("createdAt") or r.get("date"),
                "verified": r.get("verifiedPurchase") or r.get("verified"),
            })

        if total == 0 or not reviews:
            out = {
                "status": "no_reviews",
                "product_id": product_id,
                "avg_rating": None,
                "total": 0,
                "reviews": [],
                "message": "This product has no reviews yet — it may be new to the platform.",
            }
        else:
            out = {
                "status": "ok",
                "product_id": product_id,
                "avg_rating": float(avg) if avg else None,
                "total": total,
                "reviews": reviews,
            }

        cache.set(cache_key, out)
        return out

    except Exception as exc:
        log.error("get_reviews error for %s: %s", product_id, exc, exc_info=True)
        return {
            "status": "error",
            "product_id": product_id,
            "error": str(exc),
            "reviews": [],
        }
