# Product Requirements Document (PRD)
## Joyory MCP — Conversational E-Commerce Catalog Connector
**Version:** 2.0 (Full Tool Suite)  
**Status:** Working Hackathon Prototype  
**Date:** September 2026  
**Author:** Software Architecture & Product Team  

---

## 1. Product Overview & Vision

The **Joyory MCP Connector** is a production-grade Model Context Protocol (MCP) server providing read-only, real-time access to Joyory's complete beauty, skincare, haircare, and wellness catalog.

### Vision
To make Joyory the most accessible, AI-queryable beauty catalog in India, enabling consumers to discover personalized beauty regimens, verify ingredients, and access real-time discounts directly through conversational AI platforms.

---

## 2. Target Users & User Stories

### 2.1 User Personas
* **Primary Shopper:** Mobile-first consumer using conversational AI for skincare consultations and product advice.
* **Gift Shopper:** Non-expert searching for curated cosmetic bundles under strict price ceilings.
* **Clinical / Ingredient Shopper:** Highly knowledgeable buyer seeking specific formulations (e.g., fragrance-free, specific % actives, mineral UV filters).

### 2.2 User Stories
* **US-001:** *As a skincare shopper*, I want to search for products by skin concern or ingredient so that I can find products tailored to my skin type.
* **US-002:** *As a conscious consumer*, I want to inspect the full INCI ingredient list and allergens of a product before purchasing so that I avoid skin irritation.
* **US-003:** *As a price-sensitive buyer*, I want to filter recommendations by a price ceiling and find cheaper alternatives so that I stay within my budget.
* **US-004:** *As a makeup shopper*, I want to see all available shades, hex colors, and their live stock statuses so that I pick a matching, purchasable shade.
* **US-005:** *As a smart shopper*, I want to know if any active BOGO deals or discount coupons apply to the brands I am buying so that I maximize value.

---

## 3. Core Features & Tool Specifications

Joyory MCP exposes six discrete tools to connected AI models:

```
┌────────────────────────────────────────────────────────┐
│                   Joyory MCP Server                    │
│                                                        │
│  ┌──────────────────────┐    ┌──────────────────────┐  │
│  │   search_products    │    │ get_product_details  │  │
│  └──────────────────────┘    └──────────────────────┘  │
│  ┌──────────────────────┐    ┌──────────────────────┐  │
│  │ get_catalog_overview │    │     get_reviews      │  │
│  └──────────────────────┘    └──────────────────────┘  │
│  ┌──────────────────────┐    ┌──────────────────────┐  │
│  │ get_similar_products │    │      get_offers      │  │
│  └──────────────────────┘    └──────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

---

### Feature 1: `search_products`
* **Why it exists:** Provides targeted keyword search across Joyory's catalog with client-side ranking, pagination, and multi-parameter filtering.
* **Who uses it:** Any shopper starting a discovery journey or looking for specific item types.
* **How it works:** Queries Joyory's catalog API with optional brand/category slug constraints, then applies client-side price bounds, in-stock verification, and TF-IDF-inspired relevance scoring.
* **Inputs:**
  * `query` (str, required): Text keywords (e.g. `'salicylic acid cleanser'`).
  * `limit` (int, default 10, max 100): Results per page.
  * `offset` (int, default 0): Paging offset.
  * `min_price` / `max_price` (float, optional): Price bounds in INR.
  * `brand` (str, optional): Brand slug (e.g., `'the-derma-co'`).
  * `category` (str, optional): Category slug (e.g., `'skin-eye-care'`).
  * `in_stock_only` (bool, default False): Exclude out-of-stock items.
  * `sort` (enum, default `'relevance'`): `'relevance' | 'price_asc' | 'price_desc' | 'rating' | 'newest'`.
  * `include_images` (bool, default False): Include `image_url` for visual rendering.
* **Outputs:** `SearchResponse` containing `results` (list of `ProductSummary`), `total_matches`, `has_more`, `count`, and actionable `hint`.
* **Failure Behavior:** If no matches exist, returns `results: []` with an actionable `hint` directing the model to check `get_catalog_overview`.

---

### Feature 2: `get_product_details`
* **Why it exists:** Provides deep technical and dermatological data (INCI ingredients, usage steps, shade/size variants) for up to 5 products in a single round-trip.
* **Who uses it:** Consumers comparing specific candidate products or verifying ingredient safety.
* **How it works:** Executes concurrent lookups via `asyncio.gather` for up to 5 product IDs against `/api/user/products/{id}`, normalizes attributes, extracts variants, and calculates unit pricing.
* **Inputs:** `product_ids` (list of 1–5 string IDs).
* **Outputs:** Single product dictionary if 1 ID requested; `{"products": [...], "count": N}` if multiple IDs requested.
* **Failure Behavior:** Returns structured error block `{"error": "...", "id": pid}` for individual missing IDs without failing the entire batch.

---

### Feature 3: `get_catalog_overview`
* **Why it exists:** Gives the AI assistant a bird's-eye map of all valid brand names, product counts, and the hierarchical category tree.
* **Who uses it:** The AI model during session initialization (Rule 1) or when resolving category/brand slugs.
* **How it works:** Queries `/api/user/categories/tree` and `/api/user/brands` concurrently, flattens categories into navigable paths, and caches the result for 10 minutes.
* **Inputs:** None.
* **Outputs:** `{"categories": [...], "brands": [...], "total_brands": int}`.
* **Failure Behavior:** Returns partial cached data if one upstream endpoint fails.

---

### Feature 4: `get_reviews`
* **Why it exists:** Retrieves authentic customer reviews to validate product efficacy and customer satisfaction before purchase recommendations.
* **Who uses it:** Shoppers seeking social proof; AI validating whether a product is good.
* **How it works:** Hits `/api/reviews/product/{id}` with pagination parameters; parses star ratings, review titles, author names, and verified purchase flags.
* **Inputs:** `product_id` (str, required), `limit` (int, default 10, max 20).
* **Outputs:** `{"status": "ok", "avg_rating": float, "total": int, "reviews": [...]}`.
* **Failure Behavior:** If no reviews exist, returns `status: "no_reviews"` with an explicit message that the product may be new to the catalog.

---

### Feature 5: `get_similar_products`
* **Why it exists:** Enables "dupe" discovery and budget substitution when a product is out of stock or exceeds a user's price threshold.
* **Who uses it:** Budget-conscious shoppers or consumers facing stock-outs.
* **How it works:** Fetches source product details, extracts category and non-filler keywords, searches candidate items, filters by `price < source_price` if `cheaper=True`, and ranks by relevance.
* **Inputs:** `product_id` (str), `cheaper` (bool, default False), `in_stock_only` (bool, default False), `limit` (int, default 5).
* **Outputs:** `{"source_product_id": id, "source_name": name, "results": [...], "count": N}`.
* **Failure Behavior:** Returns friendly fallback message advising manual category search if no candidates meet criteria.

---

### Feature 6: `get_offers`
* **Why it exists:** Injects active promotional campaigns, coupon codes, and bundle collections into conversational shopping sessions.
* **Who uses it:** Any customer finalizing a cart or looking for deals.
* **How it works:** Calls Joyory's active promotions endpoint (`/api/user/promotions/active?section=offers`), extracts BOGO rules, discount percentages, applicable `brand_slug`, and expiry dates.
* **Inputs:** None.
* **Outputs:** `{"offers": [{"title": str, "type": "bogo"|"discount"|"collection", "code": str, "brand_slug": str, ...}], "count": N}`.
* **Failure Behavior:** Returns empty offer list with explanatory message if promotions API is temporarily unreachable.

---

## 4. Product Requirements (Functional & Non-Functional)

### 4.1 Functional Requirements Table
| ID | Requirement | Priority | Implementation Source |
|---|---|---|---|
| **PR-001** | Keyword catalog search with relevance scoring | P0 | `tools/search.py` |
| **PR-002** | Slug normalization for brands with special characters | P0 | `normalize.py` |
| **PR-003** | Deep product specification extraction (INCI, variants) | P0 | `tools/details.py` |
| **PR-004** | Complete hierarchical category tree mapping | P0 | `tools/catalog.py` |
| **PR-005** | Customer social proof and review aggregation | P1 | `tools/reviews.py` |
| **PR-006** | Automated alternative / cheaper dupe finder | P1 | `tools/similar.py` |
| **PR-007** | Active promotion and coupon code discovery | P0 | `tools/offers.py` |
| **PR-008** | In-memory TTL caching layer (10-minute validity) | P0 | `cache.py` |
| **PR-009** | Batch detail resolution (up to 5 items) | P1 | `tools/details.py` |
| **PR-010** | Headless browser fallback when API is blocked | P2 | `adapters/browser.py` |
| **PR-011** | Streamable HTTP MCP 2.x transport compliance | P0 | `server.py` |
| **PR-012** | Inline visual card presentation instructions | P1 | `server.py` |

### 4.2 Non-Functional Requirements
* **NFR-Performance:** Cached queries resolve in < 5ms; live external queries complete within 800ms.
* **NFR-Reliability:** 100% test pass rate across unit, cache, normalization, and smoke suites.
* **NFR-Security:** Zero credential storage; outbound network restricted strictly to Joyory and Cloudinary CDNs.
* **NFR-Politeness:** Concurrency capped; cache prevents duplicate upstream traffic within 10 minutes.

---

## 5. User Workflows & Edge Cases

### Workflow A: Deal-Driven Skincare Routine
1. User: *"What deals do you have, and can you build me a morning routine under ₹1,000?"*
2. AI calls `get_offers()` and `get_catalog_overview()` concurrently.
3. AI identifies Aqualogica BOGO offer (code: `GLOW`).
4. AI executes `search_products(brand="aqualogica", category="skin", max_price=600)`.
5. AI selects cleanser and sunscreen, notes BOGO discount, and presents items as visual cards with purchase links.

### Edge Case Handling
* **Edge Case 1: All Results Have Zero Reviews (`rating=None`):** `search.py` inspects page results; if all ratings are None, it emits a hint clarifying that rating sort is uninformative and products may be recently cataloged.
* **Edge Case 2: Brand Contains Punctuation (e.g., "Dr Sheth's" or "DOT & KEY"):** Normalizer slugifies both query and catalog brand strings so punctuation mismatches never cause zero hits.
* **Edge Case 3: More than 5 IDs Passed to Details:** `details.py` safely truncates to 5, deduplicates, and returns a warning explaining the truncation.
