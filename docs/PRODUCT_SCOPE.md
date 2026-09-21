# Product Scope & MVP Boundaries
## Project: Joyory Conversational Commerce MCP Connector
**Document Version:** 2.0  
**Status:** Hackathon Working Prototype Audit  

---

## 1. Implemented Features (100% Complete & Verified)

* **MCP 2.x Streamable HTTP Server:** Fully compliant `/mcp` HTTP endpoint supporting bidirectional JSON-RPC.
* **`search_products` Tool:** Parametric keyword search with price bounding (INR), brand and category slug filtering, in-stock filtering, relevance scoring, and pagination offset.
* **`get_product_details` Tool:** Concurrent batch lookup for 1–5 products, extracting full INCI ingredients, usage steps, shades/hex colors, attributes, and unit pricing.
* **`get_catalog_overview` Tool:** Hierarchical category tree mapping with subcategory counts and full brand directory with live item counts.
* **`get_reviews` Tool:** Social proof extraction retrieving star ratings, review text, author names, and verified buyer flags.
* **`get_similar_products` Tool:** Algorithmic dupe and budget alternative finder with `cheaper=True` bounding.
* **`get_offers` Tool:** Active promotional scraping surfacing BOGOs, price-capped collections, and coupon codes (e.g. `GLOW`).
* **High-Performance In-Memory Cache:** Thread-safe `TTLCache` (600s TTL) eliminating redundant upstream network traffic.
* **Resilient Brand Normalization:** Regex slugifier mapping special characters, spaces, and punctuation (`Dr Sheth's` → `dr-sheth-s`, `DOT & KEY` → `dot-key`).
* **Automated API Discovery Engine:** Playwright-based network interception script capable of reverse-engineering undocumented API endpoints.

---

## 2. Partially Implemented Features (Scaffolded / Limited Scope)

* **Browser Fallback Adapter (`adapters/browser.py`):** Fully scaffolded Playwright browser crawler; intended as secondary failover if Joyory blocks direct REST requests.
* **GraphQL Adapter (`adapters/graphql.py`):** Stub architecture demonstrating how alternative enterprise data sources plug into the unified `JoyoryDataSource` interface.
* **Client-Side Card Styling:** Instructions provided to LLM for rich Markdown cards; full interactive React widgets depend on host client UI support (e.g., ChatGPT Actions).

---

## 3. Planned Features (Future Roadmap)

* **Dense Semantic Vector Search:** Integration of vector embeddings for mood- and concept-based queries ("glass skin", "clean girl makeup").
* **Distributed Redis Caching:** Multi-replica cache persistence for high-concurrency cloud scaling.
* **Persistent Shopper Profiles:** MCP Resources storing customer skin profiles, sensitivity flags, and favorite brands across chat sessions.
* **Automated Re-Order Triggers:** Cron-based replenishment reminders for consumable beauty products.

---

## 4. Explicit Non-Goals (Out of Scope by Design)

* **User Authentication & Passwords:** We do not collect or store user credentials.
* **Payment & Order Finalization:** We do not handle credit cards, UPI, or financial transactions. All purchases occur directly on Joyory's secure web store.
* **Custom Chat Frontend Web App:** We do not build a proprietary chat widget; we leverage open AI platforms (Claude, ChatGPT).
* **Inventory Mutations / Admin Operations:** The connector is strictly read-only; no catalog altering or administrative endpoints exist.
