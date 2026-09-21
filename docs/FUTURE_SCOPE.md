# Future Product Roadmap & Scope
## Project: Joyory Conversational Commerce MCP Connector
**Document Version:** 2.0  
**Planning Horizon:** Q4 2026 – Q4 2027  

---

## 1. Near-Term Horizon (1–3 Months)

### 1.1 Semantic Vector Embeddings for Product Search
* **Objective:** Augment keyword search with dense vector retrieval using open-source embeddings (e.g. `all-MiniLM-L6-v2` or BGE-small).
* **Benefit:** Enables conceptual queries such as *"glass skin finish"* or *"sunscreen that doesn't sting eyes"* without relying on literal keyword token matches.

### 1.2 Distributed Multi-Worker Caching (Redis)
* **Objective:** Replace in-memory `TTLCache` with a shared Redis instance when scaling to multi-replica cloud containers on Render.
* **Benefit:** Persistent cache across deployments, zero redundant upstream traffic across server instances.

### 1.3 Webhook-Driven Cache Invalidation
* **Objective:** Expose a secure webhook endpoint for Joyory's inventory management system to flush product detail caches instantly upon price changes or stock depletion.

---

## 2. Medium-Term Horizon (3–6 Months)

### 2.1 Personalized Skin Profiles via MCP Resources
* **Objective:** Implement the MCP `Resources` primitive to read and write persistent shopper preference files:
  `resource://joyory/user-profile/{user_id}`
* **Capabilities:** Stores skin type (dry/oily/sensitive), allergen flags (fragrance/parabens), and budget preferences across chat sessions.

### 2.2 Authenticated Cart Creation & Deep-Link Checkout
* **Objective:** Partner with Joyory engineering to build a server-to-server cart checkout token API.
* **Benefit:** Allows the AI to generate a single clickable checkout link containing all 3 routine products pre-populated into the shopper's Joyory basket.

### 2.3 Live Inventory Multi-Warehouse Routing
* **Objective:** Incorporate pincode-level inventory availability checks to ensure products recommended are available for fast local delivery.

---

## 3. Long-Term Horizon (6–12 Months)

### 3.1 Autonomous Regimen Refill Reminders
* **Objective:** Leverage scheduled background tasks to calculate when a 50ml serum will deplete (e.g., 60 days of twice-daily use) and prompt the shopper via conversational AI with one-tap reordering.

### 3.2 Visual AI Skin Diagnostics Integration
* **Objective:** Allow consumers to upload a selfie directly in Claude or ChatGPT, analyze skin redness/acne severity, and automatically trigger `search_products` for targeted clinical solutions.

### 3.3 Multi-Retailer Commercialization
* **Objective:** Package the discovery and adapter architecture into an enterprise "CommerceMCP" SDK capable of connecting any D2C beauty brand to the agentic AI ecosystem within 24 hours.
