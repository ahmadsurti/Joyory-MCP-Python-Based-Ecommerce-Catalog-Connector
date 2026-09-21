"""
REST/JSON API adapter for Joyory.
Reads config/joyory_source.json and calls the discovered endpoint.
"""

from __future__ import annotations
import asyncio
import logging
import httpx
from joyory_mcp.adapters.base import JoyoryDataSource, validate_url, BROWSER_HEADERS
from joyory_mcp.models import ProductSummary, ProductDetail
from joyory_mcp.normalize import normalize_product, normalize_product_detail, extract_products_from_response, _to_brand_slug
from joyory_mcp.errors import (
    JoyoryAPIChangedError, JoyoryNoResultsError, JoyoryProductNotFoundError,
    JoyoryTimeoutError, JoyoryUnavailableError,
)
from joyory_mcp import config as cfg

log = logging.getLogger(__name__)



class ApiJoyoryDataSource(JoyoryDataSource):

    def __init__(self, source_config: dict) -> None:
        self._cfg = source_config
        self._base = source_config.get("base_url", cfg.BASE_URL).rstrip("/")
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                headers=BROWSER_HEADERS,
                timeout=httpx.Timeout(connect=10.0, read=cfg.TIMEOUT_SECONDS, write=10.0, pool=5.0),
                follow_redirects=True,
            )
        return self._client

    async def _request(
        self, method: str, url: str, *,
        params: dict | None = None, body: dict | None = None, retries: int = 2,
    ) -> dict | list:
        validate_url(url)
        client = self._get_client()
        delay = 1.0
        last_exc: Exception = RuntimeError("No attempt made")
        for attempt in range(retries + 1):
            try:
                resp = await (client.post(url, json=body) if method == "POST" else client.get(url, params=params))
                if resp.status_code == 404:
                    raise JoyoryProductNotFoundError(str(params or body or url))
                if resp.status_code >= 500:
                    raise JoyoryUnavailableError("HTTP %d" % resp.status_code)
                if resp.status_code >= 400:
                    raise JoyoryAPIChangedError()
                return resp.json()
            except (httpx.TimeoutException, httpx.ConnectTimeout):
                last_exc = JoyoryTimeoutError()
            except (httpx.NetworkError, httpx.RemoteProtocolError) as e:
                last_exc = JoyoryUnavailableError(str(e))
            except (JoyoryProductNotFoundError, JoyoryAPIChangedError):
                raise
            except Exception as e:
                last_exc = e
            if attempt < retries:
                await asyncio.sleep(delay)
                delay *= 2
        raise last_exc

    async def search(
        self,
        query: str,
        limit: int = 10,
        min_price: float | None = None,
        max_price: float | None = None,
        brand: str | None = None,
        category: str | None = None,
    ) -> list[ProductSummary]:
        search_cfg = self._cfg.get("search", {})
        method = search_cfg.get("method", "GET").upper()
        url_path = search_cfg.get("url", "")
        url = self._base + url_path if url_path.startswith("/") else url_path
        qp = search_cfg.get("query_parameters", {})

        if method == "GET":
            params: dict = {
                qp.get("limit", "limit"): min(limit, cfg.MAX_RESULTS),
            }
            if query.strip():
                params[qp.get("query", "q")] = query.strip()
            if min_price is not None and qp.get("min_price"):
                params[qp["min_price"]] = int(min_price)
            if max_price is not None and qp.get("max_price"):
                params[qp["max_price"]] = int(max_price)
            if brand:
                brand_key = qp.get("brand", "brandIds")
                params[brand_key] = _to_brand_slug(brand)
            if category:
                cat_key = qp.get("category", "categoryIds")
                params[cat_key] = category
            data = await self._request("GET", url, params=params)
        elif method == "POST":
            body_tmpl = search_cfg.get("body_template", {})
            body = {**body_tmpl, qp.get("query", "q"): query, qp.get("limit", "limit"): min(limit, cfg.MAX_RESULTS)}
            data = await self._request("POST", url, body=body)
        else:
            raise JoyoryAPIChangedError()

        products = extract_products_from_response(data)
        if not products:
            raise JoyoryNoResultsError(query)

        results = [normalize_product(p) for p in products]

        # Client-side filters — Joyory's server ignores most of these params
        if min_price is not None:
            results = [r for r in results if r.price is None or r.price >= min_price]
        if max_price is not None:
            results = [r for r in results if r.price is None or r.price <= max_price]
        if brand:
            # ponytail: slug-normalise both sides so "DOT & KEY" == "dot-key" == "Dot & Key"
            brand_slug = _to_brand_slug(brand)
            results = [r for r in results if r.brand and _to_brand_slug(r.brand) == brand_slug]
        if category:
            cat = category.lower()
            results = [
                r for r in results
                if (r.category_slug and cat in r.category_slug.lower())
                or (r.category and cat in r.category.lower())
                or any(cat in t.lower() for t in r.tags)
            ]

        return results[:limit]

    async def get_detail(self, product_id: str) -> ProductDetail:
        detail_cfg = self._cfg.get("product_details", {})
        method = detail_cfg.get("method", "GET").upper()
        path = detail_cfg.get("url_template", "").replace("{id}", product_id).replace("{slug}", product_id)
        url = self._base + path if path.startswith("/") else path

        if method == "GET":
            data = await self._request("GET", url)
        else:
            data = await self._request("POST", url, body={**detail_cfg.get("body_template", {}), "id": product_id})

        if isinstance(data, dict):
            for key in ("product", "data", "result", "item"):
                inner = data.get(key)
                if isinstance(inner, dict) and len(inner) > 3:
                    data = inner
                    break

        if not isinstance(data, dict):
            raise JoyoryProductNotFoundError(product_id)

        return normalize_product_detail(data)

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
