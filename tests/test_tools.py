"""Tests for search_products and get_product_details tools."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from unittest.mock import AsyncMock, MagicMock
from joyory_mcp.models import ProductSummary, ProductDetail
from joyory_mcp.tools.search import search_products
from joyory_mcp.tools.details import get_product_details
from joyory_mcp.errors import (
    JoyoryNoResultsError,
    JoyoryProductNotFoundError,
    JoyoryUnavailableError,
    JoyoryTimeoutError,
)
from joyory_mcp.cache import TTLCache


def _make_mock_adapter(search_result=None, detail_result=None, search_error=None, detail_error=None):
    adapter = MagicMock()

    if search_error is not None:
        adapter.search = AsyncMock(side_effect=search_error)
    else:
        adapter.search = AsyncMock(return_value=search_result if search_result is not None else [])

    if detail_error is not None:
        adapter.get_detail = AsyncMock(side_effect=detail_error)
    else:
        adapter.get_detail = AsyncMock(return_value=detail_result)

    return adapter


def _make_product(id="p1", name="Test Product", price=299.0, brand="Brand"):
    return ProductSummary(
        id=id, name=name, price=price, brand=brand,
        currency="INR", in_stock=True,
    )


def _make_detail(id="p1", name="Test Product"):
    return ProductDetail(
        id=id, name=name, price=299.0, brand="Brand",
        currency="INR", description="A test product.",
        ingredients=["Water", "Aloe"],
        in_stock=True,
    )


# ── search_products ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_returns_results():
    products = [_make_product("1", "Lipstick A"), _make_product("2", "Lipstick B")]
    adapter = _make_mock_adapter(search_result=products)
    result = await search_products("lipstick", limit=10, adapter=adapter)
    assert result["count"] == 2
    assert result["query"] == "lipstick"
    assert len(result["results"]) == 2


@pytest.mark.asyncio
async def test_search_no_results():
    adapter = _make_mock_adapter(search_error=JoyoryNoResultsError("xyz"))
    result = await search_products("xyz", limit=3, adapter=adapter)
    assert result["count"] == 0
    assert "message" in result or "error" not in result or result.get("results") == []


@pytest.mark.asyncio
async def test_search_joyory_unavailable():
    from joyory_mcp.cache import get_cache
    get_cache().clear()
    adapter = _make_mock_adapter(search_error=JoyoryUnavailableError("down"))
    result = await search_products("lipstick_unavail_test", limit=3, adapter=adapter)
    assert "error" in result
    assert "unavailable" in result["error"].lower() or "Joyory" in result["error"]


@pytest.mark.asyncio
async def test_search_timeout():
    from joyory_mcp.cache import get_cache
    get_cache().clear()
    adapter = _make_mock_adapter(search_error=JoyoryTimeoutError())
    result = await search_products("lipstick_timeout_test", limit=3, adapter=adapter)
    assert "error" in result


@pytest.mark.asyncio
async def test_search_limit_clamped():
    """Limit > MAX_RESULTS should be clamped."""
    products = [_make_product(str(i)) for i in range(5)]
    adapter = _make_mock_adapter(search_result=products)
    from joyory_mcp import config as cfg
    result = await search_products("test", limit=999, adapter=adapter)
    # The call should succeed and clamp to MAX_RESULTS
    assert result.get("count", 0) >= 0
    call_limit = adapter.search.call_args[1].get("limit") or adapter.search.call_args[0][1]
    assert call_limit <= cfg.MAX_RESULTS


@pytest.mark.asyncio
async def test_search_price_filter():
    """Client-side max_price filter when adapter doesn't support it."""
    products = [
        _make_product("1", "Cheap", price=200),
        _make_product("2", "Expensive", price=2000),
    ]
    adapter = _make_mock_adapter(search_result=products)
    # The tool uses client-side filter after search; pass max_price in tool call
    # But actual filtering is done by adapter.search with max_price arg
    result = await search_products("lipstick", limit=10, max_price=500, adapter=adapter)
    # Adapter was called with max_price=500
    adapter.search.assert_called_once()
    call_kwargs = adapter.search.call_args[1]
    assert call_kwargs.get("max_price") == 500


@pytest.mark.asyncio
async def test_search_no_adapter():
    result = await search_products("test", limit=3, adapter=None)
    assert "error" in result


@pytest.mark.asyncio
async def test_search_caching():
    """Second call with same params should hit cache."""
    from joyory_mcp.cache import get_cache
    cache = get_cache()
    cache.clear()

    products = [_make_product("1", "Lipstick")]
    adapter = _make_mock_adapter(search_result=products)

    await search_products("lipstick", limit=3, adapter=adapter)
    await search_products("lipstick", limit=3, adapter=adapter)

    # Adapter should only be called once (second is from cache)
    assert adapter.search.call_count == 1
    cache.clear()


# ── get_product_details ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_detail_returns_data():
    detail = _make_detail("p1", "Vitamin C Serum")
    adapter = _make_mock_adapter(detail_result=detail)
    result = await get_product_details("p1", adapter=adapter)
    assert result["id"] == "p1"
    assert result["name"] == "Vitamin C Serum"


@pytest.mark.asyncio
async def test_detail_not_found():
    adapter = _make_mock_adapter(detail_error=JoyoryProductNotFoundError("bad_id"))
    result = await get_product_details("bad_id", adapter=adapter)
    assert "error" in result
    assert "bad_id" in result["error"]


@pytest.mark.asyncio
async def test_detail_unavailable():
    from joyory_mcp.cache import get_cache
    get_cache().clear()
    adapter = _make_mock_adapter(detail_error=JoyoryUnavailableError("down"))
    result = await get_product_details("p1_unavail_test", adapter=adapter)
    assert "error" in result


@pytest.mark.asyncio
async def test_detail_empty_id():
    adapter = _make_mock_adapter()
    result = await get_product_details("", adapter=adapter)
    assert "error" in result


@pytest.mark.asyncio
async def test_detail_no_adapter():
    from joyory_mcp.cache import get_cache
    get_cache().clear()
    result = await get_product_details("p1_no_adapter_test", adapter=None)
    assert "error" in result


@pytest.mark.asyncio
async def test_detail_caching():
    """Second call with same ID should hit cache."""
    from joyory_mcp.cache import get_cache
    cache = get_cache()
    cache.clear()

    detail = _make_detail("p1", "Serum")
    adapter = _make_mock_adapter(detail_result=detail)

    await get_product_details("p1", adapter=adapter)
    await get_product_details("p1", adapter=adapter)

    assert adapter.get_detail.call_count == 1
    cache.clear()
