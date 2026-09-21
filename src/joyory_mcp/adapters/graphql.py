"""
GraphQL adapter for Joyory.
Used when discovery reveals a GraphQL endpoint.
"""

from __future__ import annotations
import logging
import httpx
from joyory_mcp.adapters.base import JoyoryDataSource, validate_url, BROWSER_HEADERS as _BASE_HEADERS
from joyory_mcp.models import ProductSummary, ProductDetail
from joyory_mcp.normalize import (
    normalize_product,
    normalize_product_detail,
    extract_products_from_response,
)
from joyory_mcp.errors import (
    JoyoryNoResultsError,
    JoyoryProductNotFoundError,
    JoyoryUnavailableError,
    JoyoryTimeoutError,
)
from joyory_mcp import config as cfg

log = logging.getLogger(__name__)

BROWSER_HEADERS = {**_BASE_HEADERS, "Content-Type": "application/json"}


# Default search query — will be replaced with the one from source config
DEFAULT_SEARCH_GQL = """
query SearchProducts($query: String!, $first: Int) {
  products(search: $query, first: $first) {
    edges {
      node {
        id
        name
        sku
        price {
          value
          currency
        }
        brand { name }
        rating
        thumbnail { url }
        url
        isAvailable
      }
    }
    totalCount
  }
}
"""

DEFAULT_PRODUCT_GQL = """
query GetProduct($id: ID!) {
  product(id: $id) {
    id
    name
    sku
    description
    price { value currency }
    brand { name }
    rating
    images { url }
    isAvailable
    category { name }
    ingredients
    howToUse
  }
}
"""


class GraphQLJoyoryDataSource(JoyoryDataSource):
    """Uses a GraphQL endpoint for Joyory data."""

    def __init__(self, source_config: dict):
        self._cfg = source_config
        self._base = source_config.get("base_url", cfg.BASE_URL).rstrip("/")
        gql_cfg = source_config.get("graphql", {})
        self._endpoint = self._base + gql_cfg.get("url", "/graphql")
        self._search_query = gql_cfg.get("search_query", DEFAULT_SEARCH_GQL)
        self._product_query = gql_cfg.get("product_query", DEFAULT_PRODUCT_GQL)
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers=BROWSER_HEADERS,
                timeout=httpx.Timeout(connect=10.0, read=cfg.TIMEOUT_SECONDS),
                follow_redirects=True,
            )
        return self._client

    async def _gql(self, query: str, variables: dict) -> dict:
        validate_url(self._endpoint)
        client = self._get_client()
        try:
            resp = await client.post(
                self._endpoint,
                json={"query": query, "variables": variables},
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.TimeoutException:
            raise JoyoryTimeoutError()
        except httpx.NetworkError as e:
            raise JoyoryUnavailableError(str(e))

    async def search(
        self,
        query: str,
        limit: int = 10,
        min_price: float | None = None,
        max_price: float | None = None,
        brand: str | None = None,
        category: str | None = None,
    ) -> list[ProductSummary]:
        data = await self._gql(
            self._search_query,
            {"query": query, "first": min(limit, cfg.MAX_RESULTS)},
        )
        raw = data.get("data", {})
        products = extract_products_from_response(raw)
        if not products:
            raise JoyoryNoResultsError(query)
        results = [normalize_product(p) for p in products]
        if min_price is not None:
            results = [r for r in results if r.price is None or r.price >= min_price]
        if max_price is not None:
            results = [r for r in results if r.price is None or r.price <= max_price]
        if brand:
            brand_lower = brand.lower()
            results = [r for r in results if r.brand and brand_lower in r.brand.lower()]
        if category:
            cat_lower = category.lower()
            results = [r for r in results if
                       (r.category_slug and cat_lower in r.category_slug.lower()) or
                       (r.category and cat_lower in r.category.lower())]
        return results[:limit]

    async def get_detail(self, product_id: str) -> ProductDetail:
        data = await self._gql(self._product_query, {"id": product_id})
        raw = data.get("data", {}).get("product")
        if not raw:
            raise JoyoryProductNotFoundError(product_id)
        return normalize_product_detail(raw)

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
