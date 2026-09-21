"""
Score and rank API candidate requests to find the best Joyory product endpoints.
"""

from __future__ import annotations
import re
from typing import Any
from joyory_mcp.normalize import looks_like_product, extract_products_from_response


# URL keywords that increase/decrease usefulness score
POSITIVE_URL_KEYWORDS = [
    "search", "product", "products", "catalog", "catalogue",
    "category", "categories", "item", "items", "listing",
    "browse", "shop", "inventory",
]

NEGATIVE_URL_KEYWORDS = [
    "analytics", "telemetry", "tracking", "track", "pixel",
    "ads", "gtm", "ga4", "facebook", "hotjar", "clarity",
    "auth", "login", "register", "account", "session", "token",
    "font", "css", "js", "webpack", "bundle", "chunk",
    "recommend", "suggest", "autocomplete",  # lower score (not product detail)
]

PRODUCT_FIELDS = {
    "id", "productId", "product_id", "sku",
    "name", "title", "productName", "product_name",
    "price", "salePrice", "sale_price", "mrp", "sellingPrice",
    "brand", "brandName", "brand_name",
    "image", "imageUrl", "image_url", "images", "thumbnail",
    "slug", "handle", "url", "permalink",
    "stock", "inStock", "in_stock", "availability",
    "rating", "ratings",
    "category", "categoryName",
    "description",
}

COLLECTION_FIELDS = {
    "products", "items", "results", "data", "productsData",
    "content", "hits", "records", "list", "productList",
    "edges", "nodes",
}


def score_candidate(candidate: dict) -> int:
    """
    Score a captured network request/response.
    Returns integer 0–100.
    """
    score = 0
    url: str = candidate.get("url", "").lower()
    method: str = candidate.get("method", "GET").upper()
    content_type: str = candidate.get("content_type", "").lower()
    status: int = candidate.get("status", 0)
    body: Any = candidate.get("response_body")
    trigger: str = candidate.get("trigger", "")  # "search", "category", "product", "pageload"

    # ── Immediate disqualifiers ───────────────────────────────────────────────
    if status not in (200, 201):
        return 0
    for neg in NEGATIVE_URL_KEYWORDS:
        if neg in url and "product" not in url:
            score -= 20

    if ".css" in url or ".js" in url or ".woff" in url or ".png" in url or ".jpg" in url:
        return 0

    # ── JSON response ─────────────────────────────────────────────────────────
    if "json" in content_type:
        score += 20
    else:
        return max(0, score)

    # ── URL keywords ──────────────────────────────────────────────────────────
    for kw in POSITIVE_URL_KEYWORDS:
        if kw in url:
            score += 8
            break  # only once

    # ── Trigger context ───────────────────────────────────────────────────────
    if trigger == "search":
        score += 15
    elif trigger == "product":
        score += 12
    elif trigger == "category":
        score += 8

    # ── Response body analysis ────────────────────────────────────────────────
    if body is None:
        return max(0, score)

    products = extract_products_from_response(body)

    if products:
        score += 25
        count = len(products)
        if count >= 5:
            score += 10
        elif count >= 2:
            score += 5

        # Check field richness
        if products:
            sample = products[0]
            matching_fields = PRODUCT_FIELDS.intersection(set(sample.keys()))
            score += min(15, len(matching_fields) * 2)

    elif isinstance(body, dict):
        # Maybe single product
        if looks_like_product(body):
            score += 15
            matching_fields = PRODUCT_FIELDS.intersection(set(body.keys()))
            score += min(10, len(matching_fields) * 2)

        # Collection field present but empty
        for cf in COLLECTION_FIELDS:
            if cf in body:
                score += 5
                break

    # ── Method bonus ─────────────────────────────────────────────────────────
    if method == "GET":
        score += 5  # prefer REST-style GET

    return max(0, min(100, score))


def rank_candidates(candidates: list[dict]) -> list[dict]:
    """Sort candidates by score descending, annotating each with its score."""
    scored = []
    for c in candidates:
        s = score_candidate(c)
        scored.append({**c, "score": s})
    return sorted(scored, key=lambda x: x["score"], reverse=True)


def detect_product_count(body: Any) -> int:
    products = extract_products_from_response(body)
    return len(products)


def infer_query_params(url: str, params: dict) -> dict:
    """Try to identify which query param is the search query."""
    query_param_names = ["q", "query", "search", "keyword", "term", "s", "searchTerm", "search_query"]
    found = {}
    for name in query_param_names:
        if name in params:
            found["query"] = name
            break
    limit_names = ["limit", "pageSize", "page_size", "size", "count", "per_page"]
    for name in limit_names:
        if name in params:
            found["limit"] = name
            break
    page_names = ["page", "pageNumber", "page_number", "offset"]
    for name in page_names:
        if name in params:
            found["page"] = name
            break
    return found


def classify_endpoint(candidate: dict) -> str:
    """
    Classify a candidate endpoint as 'search', 'detail', 'category', or 'unknown'.
    """
    url = candidate.get("url", "").lower()
    trigger = candidate.get("trigger", "")
    body = candidate.get("response_body")

    if trigger == "search":
        return "search"
    if trigger == "product":
        return "detail"

    if any(k in url for k in ["search", "find", "query"]):
        return "search"
    if any(k in url for k in ["/product/", "/products/", "/item/"]):
        # Check if it looks like a single product
        if isinstance(body, dict) and looks_like_product(body):
            return "detail"
        return "search"
    if "category" in url:
        return "category"

    # Infer from body
    products = extract_products_from_response(body) if body else []
    if len(products) > 1:
        return "search"
    if len(products) == 1 and trigger != "search":
        return "detail"

    return "unknown"
