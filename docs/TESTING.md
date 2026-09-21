# Verification & Testing Strategy
## Project: Joyory Conversational Commerce MCP Connector
**Document Version:** 2.0  
**Test Framework:** Pytest 8.4+ / Hypothesis 6.150+ / AnyIO  
**Verified Status:** 69 Passed / 0 Failed (100% Pass Rate in ~2.6s)  

---

## 1. Testing Philosophy & Strategy

Because the Joyory MCP server acts as an intelligent intermediary between non-deterministic AI models and production e-commerce backends, testing enforces three core pillars:
1. **Zero Flakiness:** Unit and tool tests execute against hermetic, deterministic mock fixtures without depending on live network connectivity.
2. **Property-Based Invariant Verification:** Uses `hypothesis` to test mathematical invariants, size extraction edge cases, and normalization boundary values.
3. **Dedicated Live Smoke Testing:** Standalone live test scripts (`scripts/test_joyory_source.py`) validate active upstream contract compatibility without polluting CI/CD runs.

---

## 2. Test Suite Breakdown

The test suite is organized into five specialized modules:

| Test Module | Scope & Coverage | Test Count | Execution Time |
|---|---|---|---|
| `tests/test_cache.py` | In-memory TTLCache, key generation, expiry, thread safety, clear/size methods. | 11 Tests | ~0.08s |
| `tests/test_discovery.py` | Automated endpoint discovery, heuristic scoring, pattern matching. | 15 Tests | ~0.12s |
| `tests/test_normalization.py` | Pydantic V2 models, HTML stripping, size/price parsing, slugification, scoring. | 22 Tests | ~0.25s |
| `tests/test_smoke.py` | End-to-end server initialization, adapter fallback, config loading. | 7 Tests | ~0.35s |
| `tests/test_tools.py` | MCP tool execution (`search`, `details`, `catalog`, `reviews`, `similar`, `offers`). | 14 Tests | ~1.80s |
| **Total** | **Complete System Regression** | **69 Tests** | **~2.60s** |

---

## 3. Formal Test Case Traceability Table

| Test ID | Traced Req | Test Scenario | Input Data | Expected Result | Verified Status |
|---|---|---|---|---|---|
| **TC-001** | FR-001 | Basic keyword search execution | `query="serum", limit=5` | Returns `SearchResponse` with count ≤ 5 and valid IDs. | **PASS** |
| **TC-002** | FR-002 | Price ceiling bounding | `max_price=500` | 100% of returned items have `price <= 500` or `price is None`. | **PASS** |
| **TC-003** | FR-003 | Brand slug normalization | `brand="Dr Sheth's"` | Normalized to `dr-sheth-s`; returns matching brand items. | **PASS** |
| **TC-004** | FR-003 | Ampersand brand normalization | `brand="DOT & KEY"` | Normalized to `dot-key`; returns Dot & Key products. | **PASS** |
| **TC-005** | FR-004 | In-stock only filter | `in_stock_only=True` | All returned products have `in_stock=True`. | **PASS** |
| **TC-006** | FR-005 | Price ascending sort | `sort="price_asc"` | Results sorted strictly by `price` ascending. | **PASS** |
| **TC-007** | FR-006 | Zero results hint generation | `query="xyznonexistent"` | Returns `results: []` with actionable catalog guidance hint. | **PASS** |
| **TC-008** | FR-007 | Single product detail fetch | `product_ids=["valid_id"]` | Returns single `ProductDetail` dictionary directly. | **PASS** |
| **TC-009** | FR-007 | Multi-product batch detail fetch | `product_ids=["id1", "id2"]` | Returns `{"products": [...], "count": 2}`. | **PASS** |
| **TC-010** | FR-008 | Detail batch cap enforcement | 7 product IDs provided | Truncates to first 5 unique IDs; emits advisory warning. | **PASS** |
| **TC-011** | FR-009 | Skincare attribute extraction | Raw product JSON | Extracts `fragrance_free`, `spf`, and `key_ingredients`. | **PASS** |
| **TC-012** | FR-011 | Catalog overview category tree | `get_catalog_overview()` | Returns flattened categories with valid slug paths. | **PASS** |
| **TC-013** | FR-013 | Customer review aggregation | `product_id="valid_id"` | Returns status `ok` or `no_reviews` with numeric avg_rating. | **PASS** |
| **TC-014** | FR-014 | Cheaper alternative discovery | `cheaper=True` | Returns items with `price < source_price` in same category. | **PASS** |
| **TC-015** | FR-015 | Active BOGO promotion extraction | `get_offers()` | Extracts BOGO campaigns with coupon codes (e.g. `GLOW`). | **PASS** |

---

## 4. Live Verification & Smoke Testing Tools

In addition to the automated pytest suite, the repository includes standalone verification utilities:
* **`python scripts/test_joyory_source.py`:** Executes live network smoke tests directly against `beauty.joyory.com`, verifying that endpoint paths, schemas, and live products are actively responding.
* **`python scripts/demo.py`:** Runs an interactive command-line walkthrough of all 6 tools, displaying colored terminal outputs and benchmark latency measurements.

---

## 5. Continuous Testing Execution Command

To execute the entire test suite locally:
```bash
python -m pytest
```
*Configured with `addopts = "-p no:logfire"` in `pyproject.toml` to ensure clean execution across all standard Python environments.*
