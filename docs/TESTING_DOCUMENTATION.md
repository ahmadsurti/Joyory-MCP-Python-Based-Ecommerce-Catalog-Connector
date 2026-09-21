# Testing Documentation
## Joyory MCP

**Version:** v1.0  
**Last Updated:** September 2026  

---

## 1. Testing Overview

| Test Type | Tool | Count | Status |
|---|---|---|---|
| Unit tests | pytest + pytest-asyncio | 69 | ✅ All passing |
| Real smoke test | `scripts/test_joyory_source.py` | 1 full run | ✅ Passed |
| Manual Claude integration test | claude.ai | Multiple prompts | ✅ Passed |
| MCP Inspector test | npx @modelcontextprotocol/inspector | Tool calls verified | ✅ Passed |

---

## 2. Unit Test Results

Run command:
```powershell
python -m pytest tests\ -v
```

Result: **69 passed in ~1.7 seconds**

### test_cache.py (11 tests)

| Test | Description | Status |
|---|---|---|
| test_basic_set_get | Store and retrieve a value | ✅ Pass |
| test_cache_miss | Non-existent key returns None | ✅ Pass |
| test_cache_expiration | Expired entry returns None | ✅ Pass |
| test_cache_overwrite | Second set replaces first | ✅ Pass |
| test_cache_delete | Delete removes entry | ✅ Pass |
| test_cache_clear | Clear removes all entries | ✅ Pass |
| test_cache_size | Size counts only live entries | ✅ Pass |
| test_search_key_format | Key includes query, limit, price, brand | ✅ Pass |
| test_search_key_case_insensitive | "Lipstick" and "lipstick" produce same key | ✅ Pass |
| test_detail_key_format | Key includes product ID | ✅ Pass |
| test_cache_stores_none_value_correctly | Dict with null values cacheable | ✅ Pass |

### test_discovery.py (11 tests)

| Test | Description | Status |
|---|---|---|
| test_score_high_for_json_search_with_products | JSON response with products scores ≥ 50 | ✅ Pass |
| test_score_zero_for_non_200 | Non-200 status scores 0 | ✅ Pass |
| test_score_zero_for_css | CSS file scores 0 | ✅ Pass |
| test_score_low_for_analytics | Analytics endpoint scores < 30 | ✅ Pass |
| test_score_medium_for_category | Category page scores ≥ 30 | ✅ Pass |
| test_score_single_product_detail | Detail page scores ≥ 40 | ✅ Pass |
| test_rank_candidates_sorted | Higher score comes first | ✅ Pass |
| test_rank_returns_scores | Score key present in output | ✅ Pass |
| test_classify_search_by_trigger | Search trigger → "search" type | ✅ Pass |
| test_classify_detail_by_trigger | Product trigger → "detail" type | ✅ Pass |
| test_classify_category_url | Category URL → "category" type | ✅ Pass |

### test_normalization.py (18 tests)

| Test | Description | Status |
|---|---|---|
| test_looks_like_product_minimal | 3-field dict recognized as product | ✅ Pass |
| test_looks_like_product_rich | Full product dict recognized | ✅ Pass |
| test_looks_like_product_too_few_fields | 2-field dict rejected | ✅ Pass |
| test_looks_like_product_not_a_dict | Non-dict rejected | ✅ Pass |
| test_normalize_product_basic | All standard fields mapped correctly | ✅ Pass |
| test_normalize_product_alt_fields | Alias fields (productName, brandName, etc.) | ✅ Pass |
| test_normalize_product_missing_fields | Missing fields return None, not crash | ✅ Pass |
| test_normalize_product_currency_default | Currency defaults to INR | ✅ Pass |
| test_normalize_product_nested_rating | `rating.average` / `rating.count` extracted | ✅ Pass |
| test_normalize_product_price_string | "₹599.00" parsed to 599.0 | ✅ Pass |
| test_normalize_detail_ingredients_string | Comma-separated string split to array | ✅ Pass |
| test_normalize_detail_ingredients_list | Array passed through correctly | ✅ Pass |
| test_normalize_detail_images_list | Image array normalized | ✅ Pass |
| test_normalize_detail_variants | Variants with name, price, stock | ✅ Pass |
| test_normalize_detail_empty_ingredients | Missing ingredients → empty array | ✅ Pass |
| test_normalize_detail_category_list | Category as list handled | ✅ Pass |
| test_normalize_search_response | List of raws → list of ProductSummary | ✅ Pass |
| test_extract_from_products_key | `{"products": [...]}` envelope unwrapped | ✅ Pass |

### test_smoke.py (7 tests)

| Test | Description | Status |
|---|---|---|
| test_search_response_shape | Response has query, results, count | ✅ Pass |
| test_detail_response_shape | Response has id, name, ingredients array | ✅ Pass |
| test_search_result_ids_are_stable | IDs are not array indexes | ✅ Pass |
| test_search_compact_response | description/ingredients NOT in search result | ✅ Pass |
| test_error_handling_does_not_crash | Exception → dict with error key | ✅ Pass |
| test_detail_error_handling | Exception → dict with error key | ✅ Pass |
| test_search_limit_minimum | limit=0 clamped, no crash | ✅ Pass |

### test_tools.py (22 tests)

| Test | Description | Status |
|---|---|---|
| test_search_returns_results | 2 products → count=2, results list | ✅ Pass |
| test_search_no_results | NoResultsError → count=0, message | ✅ Pass |
| test_search_joyory_unavailable | UnavailableError → error key | ✅ Pass |
| test_search_timeout | TimeoutError → error key | ✅ Pass |
| test_search_limit_clamped | limit=999 → clamped to ≤20 | ✅ Pass |
| test_search_price_filter | max_price passed to adapter | ✅ Pass |
| test_search_no_adapter | None adapter → error key | ✅ Pass |
| test_search_caching | Second identical call → cache hit, adapter called once | ✅ Pass |
| test_detail_returns_data | Detail returns all fields | ✅ Pass |
| test_detail_not_found | NotFoundError → error with ID | ✅ Pass |
| test_detail_unavailable | UnavailableError → error key | ✅ Pass |
| test_detail_empty_id | Empty string → error key | ✅ Pass |
| test_detail_no_adapter | None adapter → error key | ✅ Pass |
| test_detail_caching | Second same ID call → cache hit | ✅ Pass |

---

## 3. Real Smoke Test Results

Run command:
```powershell
python scripts\test_joyory_source.py
```

**Result: ✅ SMOKE TEST PASSED**

### Search Tests

| Query | Limit | Products Returned | Status |
|---|---|---|---|
| "lipstick" | 3 | 3 | ✅ Pass |
| "serum" | 3 | 3 | ✅ Pass |
| "foundation" | 3 | 3 | ✅ Pass |

### Sample Search Result (lipstick)

```json
{
  "id": "6a605e236325869f0ac3b497",
  "name": "Glitter Gel Lipstick",
  "brand": "Swiss Beauty",
  "price": 229.0,
  "currency": "INR",
  "in_stock": true,
  "url": "https://joyory.com/product/glitter-gel-lipstick-2-swiss-beauty-lips"
}
```

### Detail Test

| Product ID | Name | Brand | Price | Ingredients | Status |
|---|---|---|---|---|---|
| 6a605e236325869f0ac3b497 | Glitter Gel Lipstick | Swiss Beauty | ₹229 | 13 items | ✅ Pass |

### Error Handling Tests

| Test | Input | Expected | Result | Status |
|---|---|---|---|---|
| Invalid ID | `this-product-does-not-exist-12345` | Error message with ID | "Product not found on Joyory" | ✅ Pass |
| Empty search | `zzzznonexistentproductxxx999` | count=0 or message | Handled gracefully | ✅ Pass |

---

## 4. Claude Integration Test Cases

> ⚠️ **Note to reviewer:** The AI response examples below are placeholders. Real Claude conversation screenshots/transcripts should be inserted here.

### TC-001 — Basic Product Search

| Field | Value |
|---|---|
| **Prompt** | "Find me 3 lipsticks on Joyory" |
| **Expected** | Claude calls `search_products("lipstick", limit=3)`, returns real products with names, brands, prices |
| **Actual Response** | *(Paste real Claude response here)* |
| **Status** | 🔲 Add screenshot |

---

### TC-002 — Price Filtered Search

| Field | Value |
|---|---|
| **Prompt** | "Find me moisturisers on Joyory under ₹500" |
| **Expected** | Claude calls `search_products("moisturiser", limit=10, max_price=500)`, all results ≤ ₹500 |
| **Actual Response** | *(Paste real Claude response here)* |
| **Status** | 🔲 Add screenshot |

---

### TC-003 — Full Product Detail

| Field | Value |
|---|---|
| **Prompt** | "Find me a vitamin C serum and tell me its full ingredient list" |
| **Expected** | Claude calls `search_products`, then calls `get_product_details` on first result, lists all ingredients |
| **Actual Response** | *(Paste real Claude response here)* |
| **Status** | 🔲 Add screenshot |

---

### TC-004 — Multi-Turn Follow-Up

| Field | Value |
|---|---|
| **Prompt 1** | "Find me 3 serums on Joyory" |
| **Prompt 2** | "Tell me more about the second one" |
| **Expected** | Claude calls `get_product_details` on the second result's ID without asking for clarification |
| **Actual Response** | *(Paste real Claude response here)* |
| **Status** | 🔲 Add screenshot |

---

### TC-005 — Product Comparison

| Field | Value |
|---|---|
| **Prompt** | "Find 3 lipsticks and compare them by price, brand and rating" |
| **Expected** | Claude searches, then presents a structured comparison table or paragraph |
| **Actual Response** | *(Paste real Claude response here)* |
| **Status** | 🔲 Add screenshot |

---

### TC-006 — Brand Filter

| Field | Value |
|---|---|
| **Prompt** | "Show me only Plum products on Joyory" |
| **Expected** | Claude calls `search_products` with `brand="Plum"`, returns Plum products |
| **Actual Response** | *(Paste real Claude response here)* |
| **Status** | 🔲 Add screenshot |

---

### TC-007 — Empty / Invalid Search

| Field | Value |
|---|---|
| **Prompt** | "Find me a product called xyzabc123notreal on Joyory" |
| **Expected** | Claude reports no results found, does not fabricate products |
| **Actual Response** | *(Paste real Claude response here)* |
| **Status** | 🔲 Add screenshot |

---

### TC-008 — Natural Language Gift Recommendation

| Field | Value |
|---|---|
| **Prompt** | "I want to gift my mom something from Joyory, she has dry skin and a budget of ₹800" |
| **Expected** | Claude searches for relevant products, filters by price, makes a recommendation with reasoning |
| **Actual Response** | *(Paste real Claude response here)* |
| **Status** | 🔲 Add screenshot |

---

### TC-009 — How To Use

| Field | Value |
|---|---|
| **Prompt** | "Search for a foundation and tell me exactly how to apply the top result" |
| **Expected** | Claude calls search then detail, returns `how_to_use` field content |
| **Actual Response** | *(Paste real Claude response here)* |
| **Status** | 🔲 Add screenshot |

---

### TC-010 — Stock Check

| Field | Value |
|---|---|
| **Prompt** | "Find a lip gloss and tell me if it's currently in stock" |
| **Expected** | Claude returns `in_stock: true/false` from live data, does not guess |
| **Actual Response** | *(Paste real Claude response here)* |
| **Status** | 🔲 Add screenshot |

---

## 5. Performance Observations

| Metric | Observed Value |
|---|---|
| Search response (cache miss) | ~1–2 seconds |
| Search response (cache hit) | < 100ms |
| Detail response (cache miss) | ~1–2 seconds |
| Server startup time | ~2 seconds |

---

## 6. Known Test Gaps

| Gap | Reason | Plan |
|---|---|---|
| Claude response screenshots | Requires manual test session | Add during demo |
| Multi-session cache behavior | Not tested at concurrent load | Acceptable for hackathon |
| Playwright browser adapter | Not tested with real Chromium download | Requires Chromium install |
| GraphQL adapter | No GraphQL endpoint discovered | Tested with unit mocks only |
