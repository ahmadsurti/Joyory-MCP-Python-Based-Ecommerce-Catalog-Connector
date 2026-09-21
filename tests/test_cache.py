"""Tests for the TTL cache."""

import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from joyory_mcp.cache import TTLCache


def test_basic_set_get():
    cache = TTLCache(ttl_seconds=60)
    cache.set("key1", {"data": "value"})
    result = cache.get("key1")
    assert result == {"data": "value"}


def test_cache_miss():
    cache = TTLCache(ttl_seconds=60)
    assert cache.get("nonexistent") is None


def test_cache_expiration():
    cache = TTLCache(ttl_seconds=1)
    cache.set("key", "value")
    assert cache.get("key") == "value"
    time.sleep(1.1)
    assert cache.get("key") is None


def test_cache_overwrite():
    cache = TTLCache(ttl_seconds=60)
    cache.set("key", "first")
    cache.set("key", "second")
    assert cache.get("key") == "second"


def test_cache_delete():
    cache = TTLCache(ttl_seconds=60)
    cache.set("key", "value")
    cache.delete("key")
    assert cache.get("key") is None


def test_cache_clear():
    cache = TTLCache(ttl_seconds=60)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.clear()
    assert cache.get("a") is None
    assert cache.get("b") is None


def test_cache_size():
    cache = TTLCache(ttl_seconds=60)
    cache.set("x", 1)
    cache.set("y", 2)
    assert cache.size() == 2
    cache.delete("x")
    assert cache.size() == 1


def test_search_key_format():
    key = TTLCache.search_key("lipstick", 10, 800.0, "lakme")
    assert "lipstick" in key
    assert "10" in key
    assert "800" in key
    assert "lakme" in key


def test_search_key_case_insensitive():
    k1 = TTLCache.search_key("Lipstick", 10, None, None)
    k2 = TTLCache.search_key("lipstick", 10, None, None)
    assert k1 == k2


def test_detail_key_format():
    key = TTLCache.detail_key("prod_123")
    assert "prod_123" in key


def test_cache_stores_none_value_correctly():
    """None should be cacheable."""
    cache = TTLCache(ttl_seconds=60)
    # We store a dict with None values
    cache.set("key", {"price": None, "name": "Product"})
    result = cache.get("key")
    assert result is not None
    assert result["name"] == "Product"
