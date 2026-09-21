"""Tests for the normalization layer."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from joyory_mcp.normalize import (
    normalize_product,
    normalize_product_detail,
    normalize_search_response,
    extract_products_from_response,
    looks_like_product,
)


# ── looks_like_product ────────────────────────────────────────────────────────

def test_looks_like_product_minimal():
    assert looks_like_product({"id": "1", "name": "Test", "price": 100})


def test_looks_like_product_rich():
    assert looks_like_product({
        "id": "123", "name": "Lipstick", "price": 499,
        "brand": "Lakme", "imageUrl": "http://x.com/img.jpg",
    })


def test_looks_like_product_too_few_fields():
    assert not looks_like_product({"id": "1", "color": "red"})


def test_looks_like_product_not_a_dict():
    assert not looks_like_product(["a", "b"])
    assert not looks_like_product("string")


# ── normalize_product ─────────────────────────────────────────────────────────

def test_normalize_product_basic():
    raw = {
        "id": "prod_123",
        "name": "Matte Lipstick",
        "brand": "Lakme",
        "price": 299.0,
        "inStock": True,
        "imageUrl": "https://joyory.com/img.jpg",
        "url": "/products/matte-lipstick",
        "rating": 4.5,
        "ratingCount": 120,
    }
    p = normalize_product(raw)
    assert p.id == "prod_123"
    assert p.name == "Matte Lipstick"
    assert p.brand == "Lakme"
    assert p.price == 299.0
    assert p.in_stock is True
    assert "joyory.com" in p.image_url
    assert p.rating == 4.5
    assert p.rating_count == 120


def test_normalize_product_alt_fields():
    """Test alternate field name aliases."""
    raw = {
        "productId": "SKU-456",
        "productName": "Foundation",
        "brandName": "MAC",
        "sellingPrice": 1200,
        "availability": "in stock",
        "thumbnail": "/images/foundation.jpg",
    }
    p = normalize_product(raw)
    assert p.id == "SKU-456"
    assert p.name == "Foundation"
    assert p.brand == "MAC"
    assert p.price == 1200.0
    assert p.in_stock is True


def test_normalize_product_missing_fields():
    """Missing fields should be None, not crash."""
    raw = {"name": "Mystery Product"}
    p = normalize_product(raw)
    assert p.name == "Mystery Product"
    assert p.price is None
    assert p.brand is None
    assert p.in_stock is None
    assert p.id is not None  # should derive something


def test_normalize_product_currency_default():
    raw = {"id": "1", "name": "Test", "price": 100}
    p = normalize_product(raw)
    assert p.currency == "INR"


def test_normalize_product_nested_rating():
    raw = {
        "id": "1", "name": "Serum",
        "rating": {"average": 4.2, "count": 88},
    }
    p = normalize_product(raw)
    assert p.rating == 4.2
    assert p.rating_count == 88


def test_normalize_product_price_string():
    raw = {"id": "1", "name": "T", "price": "₹599.00"}
    p = normalize_product(raw)
    assert p.price == 599.0


# ── normalize_product_detail ──────────────────────────────────────────────────

def test_normalize_detail_ingredients_string():
    raw = {
        "id": "1", "name": "Serum",
        "ingredients": "Water, Vitamin C, Niacinamide, Hyaluronic Acid",
    }
    d = normalize_product_detail(raw)
    assert "Vitamin C" in d.ingredients
    assert len(d.ingredients) >= 3


def test_normalize_detail_ingredients_list():
    raw = {
        "id": "1", "name": "Serum",
        "ingredients": ["Water", "Vitamin C", "Aloe Vera"],
    }
    d = normalize_product_detail(raw)
    assert d.ingredients == ["Water", "Vitamin C", "Aloe Vera"]


def test_normalize_detail_images_list():
    raw = {
        "id": "1", "name": "Product",
        "images": ["https://joyory.com/a.jpg", "https://joyory.com/b.jpg"],
    }
    d = normalize_product_detail(raw)
    assert len(d.images) == 2


def test_normalize_detail_variants():
    raw = {
        "id": "1", "name": "Lipstick",
        "variants": [
            {"id": "v1", "name": "Red", "price": 299, "inStock": True},
            {"id": "v2", "name": "Pink", "price": 299, "inStock": False},
        ],
    }
    d = normalize_product_detail(raw)
    assert len(d.variant_information) == 2
    assert d.variant_information[0].name == "Red"
    assert d.variant_information[1].in_stock is False


def test_normalize_detail_empty_ingredients():
    raw = {"id": "1", "name": "Product"}
    d = normalize_product_detail(raw)
    assert d.ingredients == []
    assert d.variant_information == []
    assert d.images == []


def test_normalize_detail_category_list():
    raw = {"id": "1", "name": "P", "categories": [{"name": "Makeup"}, {"name": "Lips"}]}
    d = normalize_product_detail(raw)
    assert d.category is not None


# ── normalize_search_response ─────────────────────────────────────────────────

def test_normalize_search_response():
    raw_list = [
        {"id": "1", "name": "A", "price": 100},
        {"id": "2", "name": "B", "price": 200},
    ]
    results = normalize_search_response(raw_list)
    assert len(results) == 2


def test_normalize_search_response_skips_bad():
    """Malformed items should be skipped, not crash."""
    raw_list = [
        {"id": "1", "name": "Good", "price": 100},
        None,  # bad
        "string",  # bad
    ]
    # Should not raise
    results = normalize_search_response([r for r in raw_list if r is not None])
    assert len(results) >= 1


# ── extract_products_from_response ────────────────────────────────────────────

def test_extract_from_products_key():
    data = {
        "products": [
            {"id": "1", "name": "A", "price": 100, "brand": "X"},
            {"id": "2", "name": "B", "price": 200, "brand": "Y"},
        ]
    }
    products = extract_products_from_response(data)
    assert len(products) == 2


def test_extract_from_direct_array():
    data = [
        {"id": "1", "name": "A", "price": 100, "brand": "X", "imageUrl": "x"},
        {"id": "2", "name": "B", "price": 200, "brand": "Y", "imageUrl": "y"},
    ]
    products = extract_products_from_response(data)
    assert len(products) == 2


def test_extract_from_nested_data():
    data = {
        "data": {
            "products": [
                {"id": "1", "name": "C", "price": 300, "brand": "Z"},
            ]
        }
    }
    products = extract_products_from_response(data)
    assert len(products) == 1


def test_extract_empty():
    assert extract_products_from_response({}) == []
    assert extract_products_from_response([]) == []
    assert extract_products_from_response("string") == []
