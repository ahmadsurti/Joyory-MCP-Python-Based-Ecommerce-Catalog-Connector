# Release Notes: Joyory MCP v2.0.0
## Release Tag: v2.0.0-hackathon-production
**Release Date:** September 21, 2026  
**Status:** Certified Stable Prototype  

---

## 1. Summary of Release

Version 2.0.0 represents the complete, production-hardened release of the **Joyory MCP Connector**. Evolving from an initial 2-tool proof-of-concept, v2.0.0 delivers a full suite of **6 deterministic MCP tools**, automated reverse-engineering discovery tooling, robust brand slug normalization, active promotional campaign scraping, and sub-3-second full test execution.

---

## 2. Key Capabilities & New Features

* **Full 6-Tool MCP Suite:**
  * `search_products`: Parametric keyword catalog search with relevance scoring and price bounding.
  * `get_product_details`: Concurrent multi-product detail lookup (INCI, variants, attributes).
  * `get_catalog_overview`: Complete non-sampled category tree and brand directory.
  * `get_reviews`: Customer reviews and sentiment aggregation.
  * `get_similar_products`: Algorithmic cheaper "dupe" discovery.
  * `get_offers`: Real-time BOGO and coupon code discovery (e.g., Aqualogica `GLOW`).
* **Startup Cache Pre-Warming:** `_prewarm()` fires catalog and offer fetching concurrently at server launch, ensuring sub-100ms first-query response times.
* **Streamable HTTP MCP 2.x:** Full compliance with the latest Model Context Protocol specification over HTTP (`/mcp`), enabling seamless cloud hosting on Render.
* **Production-Grade Data Normalization:** Robust extraction of package sizes (`ml`, `g`), calculated unit prices (`price_per_100ml`), and clinical attributes (`fragrance_free`, `spf`, `skin_types`).

---

## 3. Bug Fixes & Refactoring Completed

* **Fix 1 (Brand Slug Punctuation):** Resolved apostrophe and ampersand normalization so brands like `"Dr Sheth's"` and `"DOT & KEY"` map accurately to Joyory's API parameters (`dr-sheth-s`, `dot-key`).
* **Fix 2 (Category Routing):** Configured upstream adapter to route category filtering to `categoryIds`, unlocking accurate catalog filtering across secondary tags.
* **Fix 3 (Pagination Ceiling Raised):** Raised `JOYORY_MAX_RESULTS` from 20 to 100, allowing full brand catalog browsing (e.g., all 29 Kiro Beauty products returned cleanly).
* **Fix 4 (Unrestricted Image Stripping):** Fixed image URL stripping logic so visual cards render reliably on all products when requested.
* **Fix 5 (Dead Weight Pruned):** Removed ~850 lines of unused scrapers and pruned heavy dependencies (`beautifulsoup4`, `lxml`) in favor of direct JSON microservices.
* **Fix 6 (Logfire Warning Suppression):** Cleaned up third-party Pydantic plugin warnings to maintain pristine terminal outputs during test and server runs.

---

## 4. Verification & Health

* **Test Suite:** **69 / 69 Tests Passing (100%)** in ~2.6 seconds.
* **Smoke Testing:** Live verification against `beauty.joyory.com` confirmed healthy.
* **Cloud Readiness:** Environment-driven port and host binding configured for instant Render deployment.
