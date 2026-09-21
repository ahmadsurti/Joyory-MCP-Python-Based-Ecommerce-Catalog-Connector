"""
Joyory MCP Server — MCP 2.x, Streamable HTTP transport.

Tools:
  - search_products       Find / filter products (relevance ranked)
  - get_product_details   Full details for 1–5 products by ID
  - get_catalog_overview  Categories + brands map — call this first
  - get_reviews           Customer reviews for a product
  - get_similar_products  Alternatives / cheaper options
  - get_offers            Active coupons and deals

Run with:  python server.py
"""

from __future__ import annotations
import logging

# config.py suppresses logfire/opentelemetry warnings at import time
from joyory_mcp import config as cfg  # noqa: E402 — must be first after std imports
from mcp.server.mcpserver import MCPServer
from joyory_mcp.tools.search import search_products as _search, SortOption
from joyory_mcp.tools.details import get_product_details as _details
from joyory_mcp.tools.catalog import get_catalog_overview as _catalog
from joyory_mcp.tools.reviews import get_reviews as _reviews
from joyory_mcp.tools.similar import get_similar_products as _similar
from joyory_mcp.tools.offers import get_offers as _offers

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("joyory_mcp.server")

# ── Adapter ───────────────────────────────────────────────────────────────────

_adapter = None


def _init_adapter():
    global _adapter
    source_config = cfg.load_source_config()
    if source_config:
        adapter_type = source_config.get("adapter", "api")
        log.info("Using adapter: %s", adapter_type)
        if adapter_type == "graphql":
            from joyory_mcp.adapters.graphql import GraphQLJoyoryDataSource
            _adapter = GraphQLJoyoryDataSource(source_config)
        elif adapter_type == "browser":
            from joyory_mcp.adapters.browser import BrowserJoyoryDataSource
            _adapter = BrowserJoyoryDataSource(source_config)
        else:
            from joyory_mcp.adapters.api import ApiJoyoryDataSource
            _adapter = ApiJoyoryDataSource(source_config)
    else:
        log.warning("No joyory_source.json found. Run 'python scripts/discover_joyory.py' first.")
        from joyory_mcp.adapters.browser import BrowserJoyoryDataSource
        _adapter = BrowserJoyoryDataSource()
    return _adapter


def _adapter_or_init():
    return _adapter or _init_adapter()


# ── MCP app ───────────────────────────────────────────────────────────────────

mcp = MCPServer(
    name="joyory-product-mcp",
    title="Joyory Product MCP",
    description="Read-only MCP server for the Joyory beauty & wellness catalog.",
    instructions="""
You are connected to the Joyory Product MCP server.
Joyory (https://joyory.com) sells skincare, makeup, haircare, and wellness products. Prices in INR.

RULES — read before calling any tool:
1. ON SESSION START — always call get_catalog_overview AND get_offers in the same turn, in parallel, before doing anything else. Do not call them sequentially; fire both at once.
2. search_products is KEYWORD search, not semantic. Use exact words likely in product names.
3. rating=null means no reviews yet — not a bad product.
4. match="partial"|"weak" = lower confidence result.
5. Call get_reviews before recommending any product.
6. Call get_offers before finalising a purchase — active BOGOs can halve cost.
7. There is NO shareable cart URL — Joyory's cart is client-side and auth-gated. Give the user product page URLs from search results instead.
8. Never say "Joyory doesn't have X" without calling get_catalog_overview first.

WHEN TO USE include_images=true in search_products:
Pass include_images=true when the user is doing any of these:
- Browsing or discovering ("show me lipsticks", "what moisturisers do you have")
- Gift shopping ("something for my sister", "gift ideas under ₹500")
- Visual comparison ("show me options", "what does this look like")
- Colour or shade picking ("nude lipstick shades", "red options")
- First-time category exploration ("what sunscreens are available")
- Expressing any excitement or emotional intent about shopping

Keep include_images=false (default) when:
- Comparing ingredients, checking fragrance-free, SPF, or skin type suitability
- Price-only queries ("what's the cheapest", "under ₹300")
- Stock checks ("is this in stock")
- The user already has a specific product in mind and just wants details

When in doubt about a shopping-intent query, use include_images=true. Images cost tokens but they dramatically improve the shopping experience. The default false is for efficiency on data queries, not for shopping sessions.

Available tools:
- search_products       — keyword search with brand/category/price/sort/paging filters
- get_product_details   — full details for 1–5 IDs (ingredients, variants, attributes)
- get_catalog_overview  — full category tree + all brands (call this first, in parallel with get_offers)
- get_reviews           — customer reviews for a product
- get_similar_products  — alternatives, optionally cheaper or in-stock only
- get_offers            — active coupons and deals (call in parallel with get_catalog_overview)

DO NOT fabricate data, call get_product_details on every result, or assume stock status.
""",
)


@mcp.tool(description=(
    "Search Joyory's live product catalog. KEYWORD search — not semantic. "
    "Returns relevance-ranked results with category, size, price_per_100ml, tags, and match quality. "
    "Format matching results using product cards with name, price, and URL. "
    "Filters: brand (slug from get_catalog_overview), category (slug from get_catalog_overview), "
    "min_price/max_price (INR), in_stock_only, sort (relevance|price_asc|price_desc|rating|newest). "
    "Paging via offset. "
    "include_images: set true when the user is browsing, comparing visually, gift shopping, or exploring "
    "a category for the first time — Claude.ai renders these as inline product images. "
    "Keep false for ingredient/price/stock data queries. "
    "match='partial'|'weak' = result may not match query. "
    "Example: search_products(query='vitamin c serum', category='skin-serums-and-essences-serum', max_price=500, include_images=true)"
))
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
) -> dict:
    """
    Args:
        query:          What to search for (e.g. 'matte lipstick', 'vitamin C serum')
        limit:          Results per page (1-100, default 10)
        offset:         Skip N results for paging (default 0)
        min_price:      Minimum price in INR
        max_price:      Maximum price in INR
        brand:          Brand slug from get_catalog_overview
        category:       Category slug from get_catalog_overview
        in_stock_only:  Exclude out-of-stock products
        sort:           relevance|price_asc|price_desc|rating|newest
        include_images: Include image_url in results (default false)
    """
    return await _search(
        query, limit=limit, offset=offset, min_price=min_price, max_price=max_price,
        brand=brand, category=category, in_stock_only=in_stock_only, sort=sort,
        include_images=include_images, adapter=_adapter_or_init(),
    )


@mcp.tool(description=(
    "Get full Joyory product details for 1–5 products in one call. "
    "Returns ingredients, how_to_use, structured attributes (skin_types, SPF, fragrance_free, "
    "key_ingredients, inci_complete), variants with shade/size/hex/stock/price. "
    "Use to compare products or inspect ingredients. Do NOT call on every search result. "
    "Pass IDs from search_products results only."
))
async def get_product_details(product_ids: list[str]) -> dict:
    """Args: product_ids — list of 1–5 product IDs from search_products results."""
    return await _details(product_ids, adapter=_adapter_or_init())


@mcp.tool(description=(
    "Get the full Joyory catalog: complete category tree and all brands with product counts. "
    "Uses dedicated /api/user/categories/tree and /api/user/brands endpoints — accurate, not sampled. "
    "CALL THIS FIRST to get valid category and brand slugs for search_products filters. "
    "Cached 10 minutes."
))
async def get_catalog_overview() -> dict:
    """Return Joyory catalog: categories (with slugs) and brands (with slugs and product counts)."""
    return await _catalog()


@mcp.tool(description=(
    "Fetch customer reviews for a Joyory product. "
    "Reviews are the strongest quality signal — call this before recommending. "
    "rating=null in search means no reviews yet (new product), not a bad rating."
))
async def get_reviews(product_id: str, limit: int = 10) -> dict:
    """
    Args:
        product_id: Product _id from search_products (MongoDB ObjectId)
        limit:      Reviews to return (default 10, max 20)
    """
    return await _reviews(product_id, limit=limit)


@mcp.tool(description=(
    "Find products similar to a given product — uses category search + relevance scoring. "
    "cheaper=true filters to products under the source product's price. "
    "in_stock_only=true excludes out-of-stock alternatives."
))
async def get_similar_products(
    product_id: str,
    cheaper: bool = False,
    in_stock_only: bool = False,
    limit: int = 5,
) -> dict:
    """
    Args:
        product_id:    ID of the product to find alternatives for
        cheaper:       Only return products cheaper than the source
        in_stock_only: Only return in-stock products
        limit:         Max results (1-10, default 5)
    """
    return await _similar(
        product_id, cheaper=cheaper, in_stock_only=in_stock_only,
        limit=limit, adapter=_adapter_or_init(),
    )


@mcp.tool(description=(
    "Get active Joyory promotions: BOGO deals, % discounts, and price-capped collections. "
    "Returns coupon codes, brand_slug (use as 'brand' filter in search_products), expiry, and countdown. "
    "Call this before any purchase recommendation — BOGOs can halve effective cost. "
    "Cached 10 minutes."
))
async def get_offers() -> dict:
    """Return active Joyory promotions and coupon codes."""
    return await _offers()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    import asyncio

    _init_adapter()

    async def _prewarm() -> None:
        """Fire catalog + offers concurrently so first user call hits cache, not network."""
        try:
            await asyncio.gather(_catalog(), _offers())
            log.info("Pre-warm complete: catalog + offers cached")
        except Exception as e:
            log.warning("Pre-warm failed (non-fatal): %s", e)

    asyncio.run(_prewarm())

    log.info("Joyory MCP on http://%s:%s/mcp", cfg.MCP_HOST, cfg.MCP_PORT)
    from mcp.server.transport_security import TransportSecuritySettings
    mcp.run(
        transport="streamable-http",
        host=cfg.MCP_HOST,
        port=cfg.MCP_PORT,
        streamable_http_path="/mcp",
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=False,
            allowed_hosts=[],
        ),
    )


if __name__ == "__main__":
    main()
