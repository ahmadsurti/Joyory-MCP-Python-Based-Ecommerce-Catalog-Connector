# Software Requirements Specification (SRS)
## Project: Joyory Conversational Commerce MCP Connector
**Document Version:** 2.0  
**Status:** Approved for Prototype & Production Deployment  
**Standard:** IEEE 830 / ISO/IEC/IEEE 29148 Compliant Adaptation  

---

## 1. Introduction

### 1.1 Purpose
This specification establishes the complete technical and software requirements for the Joyory Model Context Protocol (MCP) server. It defines interface behaviors, data contracts, validation rules, error handling, performance targets, and architectural constraints.

### 1.2 System Scope
The Joyory MCP system is an in-memory, read-only middleware service connecting AI host clients to Joyory's live product catalog (`beauty.joyory.com`). The server implements the MCP 2.x Streamable HTTP specification and exposes 6 deterministic tools.

```
┌─────────────────┐       MCP 2.x HTTP       ┌──────────────────┐       HTTPS        ┌─────────────────────┐
│  AI Host Client │ ───────────────────────> │  Joyory MCP Svc  │ ─────────────────> │ beauty.joyory.com   │
│ (Claude/ChatGPT)│ <─────────────────────── │ (Streamable HTTP)│ <───────────────── │ (Upstream Catalog)  │
└─────────────────┘                          └──────────────────┘                    └─────────────────────┘
```

---

## 2. Functional Requirements (FR)

### 2.1 Catalog Search & Filtering (`tools/search.py`)
* **FR-001 (Keyword Catalog Search):** The system shall accept a UTF-8 query string and return ranked product matches from the Joyory catalog within 1.0s under standard network latency.
* **FR-002 (Parametric Bounding):** The system shall filter search results by `min_price` and `max_price` (inclusive, in INR) on the client side when upstream API parameters are ignored or inaccurate.
* **FR-003 (Taxonomic Filtering):** The system shall accept optional `brand` and `category` slugs and match against product catalog slugs, names, and secondary tag arrays.
* **FR-004 (Stock Availability Filter):** When `in_stock_only=True`, the system shall exclude all products where `in_stock != True`.
* **FR-005 (Multi-Modal Relevance Sorting):** The system shall support sorting by `relevance`, `price_asc`, `price_desc`, `rating`, and `newest`. When `sort='relevance'`, ranking shall prioritize exact phrase title matches, followed by brand matches, token hits, and tag associations.
* **FR-006 (Pagination & Paging Hints):** The system shall enforce `limit` (range 1–100, default 10) and `offset` (default 0), and emit actionable pagination instructions in `hint` when `has_more=True`.

### 2.2 Deep Product Details (`tools/details.py`)
* **FR-007 (Batch Product Lookup):** The system shall accept a list of 1 to 5 product IDs and retrieve full records concurrently using `asyncio.gather`.
* **FR-008 (Batch Cap Enforcement):** If more than 5 product IDs are supplied, the system shall safely truncate the input to the first 5 unique IDs and return an explicit advisory warning.
* **FR-009 (Ingredient & Clinical Extraction):** The system shall parse and normalize `ingredients` (full INCI array), `how_to_use` directions, and structured `attributes` (e.g., `skin_types`, `spf`, `fragrance_free`, `finish`, `key_ingredients`).
* **FR-010 (Variant & Shade Extraction):** The system shall expose a structured `variants` list containing SKU, shade name, hex color code, size, MRP, sale price, and stock status.

### 2.3 Catalog Taxonomy & Brand Mapping (`tools/catalog.py`)
* **FR-011 (Category Tree Flattening):** The system shall fetch Joyory's nested category tree from `/api/user/categories/tree` and flatten it into a list of complete slug paths with subcategory counts.
* **FR-012 (Brand Product Count Mapping):** The system shall fetch all registered brands from `/api/user/brands` and expose brand names, normalized slugs, and live product counts.

### 2.4 Social Proof & Customer Reviews (`tools/reviews.py`)
* **FR-013 (Review Aggregation):** The system shall fetch authentic customer reviews from `/api/reviews/product/{id}`, exposing average rating, total review volume, author names, review bodies, and verified purchase flags.

### 2.5 Alternative & Dupe Discovery (`tools/similar.py`)
* **FR-014 (Algorithmic Dupe Finder):** Given a source product ID, the system shall locate comparable items within the same category. If `cheaper=True`, it shall enforce `price < source_price`.

### 2.6 Active Promotions & Merchandising (`tools/offers.py`)
* **FR-015 (Live Promotion Extraction):** The system shall query `/api/user/promotions/active?section=offers` and return structured promotions including BOGO offers, discount percentages, coupon codes, and target brand slugs.

---

## 3. Non-Functional Requirements (NFR)

### 3.1 Performance & Latency
* **NFR-001 (Cache Latency):** All cache-hit requests shall resolve in under 10 milliseconds.
* **NFR-002 (Throughput & Network Timeout):** External HTTP requests shall adhere to a strict 15.0s timeout per attempt, backed by automated exponential retry logic.
* **NFR-003 (Pre-Warming at Startup):** The server shall execute `asyncio.gather(_catalog(), _offers())` at boot time to ensure the first user query experiences sub-second response times.

### 3.2 Reliability & Availability
* **NFR-004 (Graceful Degradation):** In the event of an upstream Joyory REST API outage or IP challenge, the system shall support transparent fallback to `BrowserJoyoryDataSource` (Playwright headless engine).
* **NFR-005 (Deterministic Testability):** The codebase shall maintain 100% test pass rate across unit, cache, normalization, and tool mock test suites without external network dependencies.

### 3.3 Security & Boundaries
* **NFR-006 (Zero Credential Exposure):** The connector shall require zero end-user passwords, tokens, or payment credentials.
* **NFR-007 (Network Egress Control):** Outbound network requests shall be strictly whitelisted to `joyory.com`, `beauty.joyory.com`, and `res.cloudinary.com`.

### 3.4 Operational & Platform Compatibility
* **NFR-008 (Cross-Platform Deployment):** The service shall bind to `127.0.0.1` in local development and dynamically bind to `0.0.0.0` when deployed in containerized cloud environments (e.g., Render, Docker) via `PORT` detection.
