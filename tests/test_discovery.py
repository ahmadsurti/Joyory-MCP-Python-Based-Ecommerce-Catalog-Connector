"""Tests for the discovery scoring module."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from joyory_mcp.discovery.scoring import (
    score_candidate,
    rank_candidates,
    classify_endpoint,
    infer_query_params,
)


def _make_candidate(**kwargs):
    defaults = {
        "url": "https://joyory.com/api/products",
        "method": "GET",
        "status": 200,
        "content_type": "application/json",
        "trigger": "search",
        "params": {},
        "response_body": None,
    }
    defaults.update(kwargs)
    return defaults


# ── score_candidate ───────────────────────────────────────────────────────────

def test_score_high_for_json_search_with_products():
    c = _make_candidate(
        url="https://joyory.com/api/search?q=lipstick",
        trigger="search",
        response_body={
            "products": [
                {"id": "1", "name": "A", "price": 100, "brand": "X", "imageUrl": "http://x"},
                {"id": "2", "name": "B", "price": 200, "brand": "Y", "imageUrl": "http://y"},
            ]
        }
    )
    score = score_candidate(c)
    assert score >= 50


def test_score_zero_for_non_200():
    c = _make_candidate(status=404)
    assert score_candidate(c) == 0


def test_score_zero_for_css():
    c = _make_candidate(url="https://joyory.com/styles/main.css", content_type="text/css")
    assert score_candidate(c) == 0


def test_score_low_for_analytics():
    c = _make_candidate(
        url="https://analytics.joyory.com/track",
        content_type="application/json",
        response_body={"event": "pageview"},
    )
    score = score_candidate(c)
    assert score < 30


def test_score_medium_for_category():
    c = _make_candidate(
        url="https://joyory.com/api/category/makeup",
        trigger="category",
        response_body={
            "items": [
                {"id": "1", "name": "Foundation", "price": 499, "brand": "Lakme"},
            ]
        }
    )
    score = score_candidate(c)
    assert score >= 30


def test_score_single_product_detail():
    c = _make_candidate(
        url="https://joyory.com/api/product/12345",
        trigger="product",
        response_body={
            "id": "12345", "name": "Serum",
            "price": 699, "brand": "Dot & Key",
            "description": "Vitamin C serum",
            "imageUrl": "https://joyory.com/img.jpg",
        }
    )
    score = score_candidate(c)
    assert score >= 40


# ── rank_candidates ───────────────────────────────────────────────────────────

def test_rank_candidates_sorted():
    candidates = [
        _make_candidate(url="https://joyory.com/gtm.js", content_type="text/javascript"),
        _make_candidate(
            url="https://joyory.com/api/search",
            trigger="search",
            response_body={"products": [{"id": "1", "name": "A", "price": 100, "brand": "B"}]}
        ),
    ]
    ranked = rank_candidates(candidates)
    assert ranked[0]["score"] >= ranked[-1]["score"]
    assert ranked[0]["url"] == "https://joyory.com/api/search"


def test_rank_returns_scores():
    candidates = [_make_candidate()]
    ranked = rank_candidates(candidates)
    assert "score" in ranked[0]


# ── classify_endpoint ─────────────────────────────────────────────────────────

def test_classify_search_by_trigger():
    c = _make_candidate(trigger="search", url="https://joyory.com/api/results")
    assert classify_endpoint(c) == "search"


def test_classify_detail_by_trigger():
    c = _make_candidate(trigger="product", url="https://joyory.com/api/product/123")
    assert classify_endpoint(c) == "detail"


def test_classify_by_url():
    c = _make_candidate(trigger="pageload", url="https://joyory.com/api/search?q=test")
    assert classify_endpoint(c) in ("search", "unknown")


def test_classify_category_url():
    c = _make_candidate(trigger="pageload", url="https://joyory.com/api/category/makeup")
    assert classify_endpoint(c) == "category"


# ── infer_query_params ────────────────────────────────────────────────────────

def test_infer_q_param():
    params = {"q": "lipstick", "limit": "10"}
    result = infer_query_params("https://joyory.com/search", params)
    assert result.get("query") == "q"
    assert result.get("limit") == "limit"


def test_infer_query_param():
    params = {"query": "foundation", "pageSize": "10"}
    result = infer_query_params("https://joyory.com/search", params)
    assert result.get("query") == "query"
    assert result.get("limit") == "pageSize"


def test_infer_empty_params():
    result = infer_query_params("https://joyory.com/api/search", {})
    assert result == {}
