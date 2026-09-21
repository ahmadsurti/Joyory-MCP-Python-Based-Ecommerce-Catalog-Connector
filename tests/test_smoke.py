"""
Smoke tests — verify the MCP server starts and tools are callable.
Does NOT make real network requests.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from joyory_mcp.models import ProductSummary, ProductDetail
from joyory_mcp.tools.search import search_products
from joyory_mcp.tools.details import get_product_details


def _mock_product(n=1):
    return [
        ProductSummary(
            id=f"prod_{i}",
            name=f"Product {i}",
            brand="TestBrand",
            price=float(100 * i),
            currency="INR",
            in_stock=True,
            url=f"https://joyory.com/product/{i}",
        )
        for i in range(1, n + 1)
    ]


def _mock_detail(pid="prod_1"):
    return ProductDetail(
        id=pid,
        name="Test Product",
        brand="TestBrand",
        price=299.0,
        currency="INR",
        description="A wonderful test product.",
        ingredients=["Water", "Aloe Vera", "Vitamin E"],
        how_to_use="Apply gently to face.",
        rating=4.5,
        rating_count=100,
        in_stock=True,
        images=["https://joyory.com/img1.jpg"],
        url=f"https://joyory.com/product/{pid}",
        category="Skincare",
    )


# ── Basic tool shape ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_response_shape():
    adapter = MagicMock()
    adapter.search = AsyncMock(return_value=_mock_product(3))

    result = await search_products("lipstick", limit=3, adapter=adapter)

    assert "query" in result
    assert "results" in result
    assert "count" in result
    assert result["count"] == 3
    assert isinstance(result["results"], list)

    # Each result must have required fields
    for r in result["results"]:
        assert "id" in r
        assert "name" in r


@pytest.mark.asyncio
async def test_detail_response_shape():
    adapter = MagicMock()
    adapter.get_detail = AsyncMock(return_value=_mock_detail("prod_1"))

    result = await get_product_details("prod_1", adapter=adapter)

    assert result["id"] == "prod_1"
    assert "name" in result
    assert "brand" in result
    assert "price" in result
    assert "ingredients" in result
    assert isinstance(result["ingredients"], list)


@pytest.mark.asyncio
async def test_search_result_ids_are_stable():
    """Product IDs should not be array indexes."""
    adapter = MagicMock()
    adapter.search = AsyncMock(return_value=_mock_product(3))

    result = await search_products("foundation", limit=3, adapter=adapter)
    for r in result["results"]:
        assert r["id"] not in ("0", "1", "2", "3")
        assert not r["id"].startswith("result-")


@pytest.mark.asyncio
async def test_search_compact_response():
    """Search result should NOT include description or ingredients."""
    adapter = MagicMock()
    adapter.search = AsyncMock(return_value=_mock_product(1))

    result = await search_products("serum", limit=1, adapter=adapter)
    product = result["results"][0]

    # These fields belong in detail, not search
    assert "description" not in product
    assert "ingredients" not in product
    assert "how_to_use" not in product


@pytest.mark.asyncio
async def test_error_handling_does_not_crash():
    """Any exception from adapter should return a dict with 'error' key."""
    adapter = MagicMock()
    adapter.search = AsyncMock(side_effect=Exception("unexpected boom"))

    result = await search_products("test", limit=3, adapter=adapter)
    assert isinstance(result, dict)
    assert "error" in result


@pytest.mark.asyncio
async def test_detail_error_handling():
    adapter = MagicMock()
    adapter.get_detail = AsyncMock(side_effect=Exception("boom"))

    result = await get_product_details("some_id", adapter=adapter)
    assert isinstance(result, dict)
    assert "error" in result


@pytest.mark.asyncio
async def test_search_limit_minimum():
    adapter = MagicMock()
    adapter.search = AsyncMock(return_value=[])

    result = await search_products("test", limit=0, adapter=adapter)
    # Should not crash; limit gets clamped to 1
    assert isinstance(result, dict)
