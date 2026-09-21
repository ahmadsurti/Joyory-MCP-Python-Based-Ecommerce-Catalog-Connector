# Model Context Protocol (MCP) Specification
## Project: Joyory Conversational Commerce MCP Connector
**Server Name:** `joyory-product-mcp`  
**Protocol Version:** MCP 2.x  
**Transport:** Streamable HTTP (`/mcp`)  
**Status:** Certified Read-Only Gateway  

---

## 1. Server Metadata & Capabilities

| Attribute | Value |
|---|---|
| **Server Identifier** | `joyory-product-mcp` |
| **Display Title** | Joyory Product MCP |
| **Description** | Read-only MCP server for the Joyory beauty & wellness catalog. |
| **Transport Type** | `streamable-http` (MCP 2.x standard) |
| **Default HTTP Endpoint** | `http://127.0.0.1:8000/mcp` (Local) / `http://0.0.0.0:${PORT}/mcp` (Cloud) |
| **Supported Primitives** | Tools (6 Tools). Resources: None. Prompts: None. |
| **Security Flags** | DNS Rebinding Protection: Disabled; Outbound Host Whitelist Enforced. |
| **Idempotency** | 100% of exposed tools are idempotent, safe, and read-only. |

---

## 2. Implemented Tools Summary

| Tool Name | Core Purpose | Typical Caller |
|---|---|---|
| [`search_products`](#1-search_products) | Parametric keyword search with price, brand, category, and in-stock filters. | Main discovery turns |
| [`get_product_details`](#2-get_product_details) | Full ingredient (INCI), usage, variant shades, and dermatological attributes for 1–5 IDs. | In-depth comparison |
| [`get_catalog_overview`](#3-get_catalog_overview) | Complete category tree and brand directory with product counts. | Session boot / Slugs |
| [`get_reviews`](#4-get_reviews) | Real customer reviews, star ratings, and verified buyer commentary. | Recommendation vetting |
| [`get_similar_products`](#5-get_similar_products) | Algorithmic "dupes" and cheaper alternative recommendations. | Stock-outs / Budget |
| [`get_offers`](#6-get_offers) | Active promotional campaigns, BOGOs, and coupon codes. | Cart finalization |

---

## 3. Tool Specifications

### 1. `search_products`

#### Description
Search Joyory's live product catalog. KEYWORD search — not semantic. Returns relevance-ranked results with category, size, price_per_100ml, tags, and match quality. Format matching results using product cards with name, price, and URL.

#### Parameters Schema
```json
{
  "type": "object",
  "properties": {
    "query": { "type": "string", "description": "What to search for (e.g. 'vitamin c serum')" },
    "limit": { "type": "integer", "default": 10, "minimum": 1, "maximum": 100, "description": "Results per page" },
    "offset": { "type": "integer", "default": 0, "minimum": 0, "description": "Paging offset" },
    "min_price": { "type": ["number", "null"], "default": null, "description": "Minimum price in INR" },
    "max_price": { "type": ["number", "null"], "default": null, "description": "Maximum price in INR" },
    "brand": { "type": ["string", "null"], "default": null, "description": "Brand slug from get_catalog_overview" },
    "category": { "type": ["string", "null"], "default": null, "description": "Category slug from get_catalog_overview" },
    "in_stock_only": { "type": "boolean", "default": false, "description": "Exclude out-of-stock products" },
    "sort": { "type": "string", "enum": ["relevance", "price_asc", "price_desc", "rating", "newest"], "default": "relevance" },
    "include_images": { "type": "boolean", "default": false, "description": "Include image_url for visual cards" }
  },
  "required": ["query"]
}
```

#### Example Invocation
```json
{
  "name": "search_products",
  "arguments": {
    "query": "sunscreen",
    "brand": "the-derma-co",
    "max_price": 600,
    "include_images": true
  }
}
```

#### Example Response
```json
{
  "query": "sunscreen",
  "total_matches": 1,
  "has_more": false,
  "count": 1,
  "hint": "Showing 1–1 of 1 matches.",
  "results": [
    {
      "id": "6a6af37c260c92beae2fb57f",
      "name": "1% Hyaluronic Sunscreen Aqua Gel SPF 50 PA++++",
      "brand": "The Derma Co",
      "category": "Sunscreen",
      "category_slug": "skin-sunscreen",
      "price": 449.0,
      "mrp": 499.0,
      "currency": "INR",
      "rating": 4.6,
      "rating_count": 84,
      "in_stock": true,
      "image_url": "https://res.cloudinary.com/joyory/image/upload/sample.jpg",
      "url": "https://joyory.com/product/1-hyaluronic-sunscreen-aqua-gel",
      "size": "50 g",
      "price_per_100ml": 898.0,
      "match": "high",
      "tags": ["sunscreen", "hyaluronic-acid", "spf-50"]
    }
  ]
}
```

---

### 2. `get_product_details`

#### Description
Get full Joyory product details for 1–5 products in one call. Returns ingredients, how_to_use, structured attributes (skin_types, SPF, fragrance_free, key_ingredients, inci_complete), and variants with shade/size/hex/stock/price.

#### Parameters Schema
```json
{
  "type": "object",
  "properties": {
    "product_ids": {
      "type": "array",
      "items": { "type": "string" },
      "description": "List of 1–5 stable product IDs from search_products results"
    }
  },
  "required": ["product_ids"]
}
```

#### Example Invocation
```json
{
  "name": "get_product_details",
  "arguments": {
    "product_ids": ["6a6af37c260c92beae2fb57f"]
  }
}
```

#### Output Characteristics
* When 1 ID is requested: Returns single `ProductDetail` object directly.
* When 2–5 IDs are requested: Returns `{"products": [ProductDetail, ...], "count": N}`.
* Input validation safely drops duplicate IDs and enforces a strict ceiling of 5 IDs per call.

---

### 3. `get_catalog_overview`

#### Description
Get the full Joyory catalog: complete category tree and all brands with product counts. Uses dedicated `/api/user/categories/tree` and `/api/user/brands` endpoints — accurate, not sampled. Caches response for 10 minutes.

#### Parameters Schema
```json
{
  "type": "object",
  "properties": {}
}
```

#### Example Response
```json
{
  "categories": [
    { "name": "Eye Care", "slug": "skin-eye-care", "subcategory_count": 3 },
    { "name": "Eye Cream & Serums", "slug": "skin-eye-care-eye-cream-and-serums", "subcategory_count": 0 }
  ],
  "brands": [
    { "name": "The Derma Co", "slug": "the-derma-co", "product_count": 83 },
    { "name": "DOT & KEY", "slug": "dot-key", "product_count": 60 }
  ],
  "total_brands": 21
}
```

---

### 4. `get_reviews`

#### Description
Fetch customer reviews for a Joyory product. Reviews are the strongest quality signal — call this before recommending. `rating=null` in search means no reviews yet (new product), not a bad rating.

#### Parameters Schema
```json
{
  "type": "object",
  "properties": {
    "product_id": { "type": "string", "description": "Product _id from search_products" },
    "limit": { "type": "integer", "default": 10, "maximum": 20, "description": "Reviews to return" }
  },
  "required": ["product_id"]
}
```

---

### 5. `get_similar_products`

#### Description
Find products similar to a given product — uses category search + relevance scoring. `cheaper=true` filters to products under the source product's price. `in_stock_only=true` excludes out-of-stock alternatives.

#### Parameters Schema
```json
{
  "type": "object",
  "properties": {
    "product_id": { "type": "string", "description": "ID of the product to find alternatives for" },
    "cheaper": { "type": "boolean", "default": false, "description": "Only return products cheaper than source" },
    "in_stock_only": { "type": "boolean", "default": false, "description": "Only return in-stock products" },
    "limit": { "type": "integer", "default": 5, "maximum": 10, "description": "Max results" }
  },
  "required": ["product_id"]
}
```

---

### 6. `get_offers`

#### Description
Get active Joyory promotions: BOGO deals, % discounts, and price-capped collections. Returns coupon codes, brand_slug, expiry, and countdown.

#### Parameters Schema
```json
{
  "type": "object",
  "properties": {}
}
```

#### Example Response
```json
{
  "offers": [
    {
      "title": "Aqualogica - Buy 1 Get 1 FREE",
      "type": "bogo",
      "scope": "brand",
      "brand_slug": "aqualogica",
      "code": "GLOW",
      "discount_pct": 50,
      "badge": "BUY 1 GET 1 FREE"
    }
  ],
  "count": 1,
  "status": "ok"
}
```
