# Known System Limitations
## Project: Joyory Conversational Commerce MCP Connector
**Document Version:** 2.0  
**Transparency Classification:** Full Engineering Disclosure  

---

## 1. Upstream Catalog & Taxonomy Asymmetries

### 1.1 Category Assignment Inconsistencies
* **Observation:** In Joyory’s upstream product catalog, certain child categories do not inherit products assigned to their parent category. For example, under the parent category `Eye Care` (`skin-eye-care`), there are 9 active products including two explicit serums (`5% Caffeine Under Eye Serum` and `Hydro Burst Under Eye Serum Roll On`). However, only 3 products (all creams) are tagged with the child slug `skin-eye-care-eye-cream-and-serums`.
* **Impact:** If an AI model queries strictly by the child subcategory slug rather than the parent category or general search, it will only see the 3 creams.
* **Mitigation Implemented:** `normalize.py` populates `tags` with all category memberships from raw data, and `api.py` searches across category names, slugs, and secondary tags.

### 1.2 Upstream Text Search Tokenization
* **Observation:** Joyory’s backend search (`/api/user/products/all?search=...`) uses lexical substring and keyword matching rather than dense semantic vector embeddings.
* **Impact:** Multi-word queries with filler terms (e.g., *"give me a cream for that"*) return low-relevance results compared to concise keywords (*"retinol cream"*).
* **Mitigation Implemented:** MCP system instructions explicitly instruct the AI: *"search_products is KEYWORD search, not semantic. Use exact words likely in product names."*

---

## 2. Transactional & E-Commerce Boundaries

### 2.1 Absence of Shareable Cart Deep-Links
* **Observation:** Joyory’s e-commerce architecture utilizes a client-side shopping cart stored in browser LocalStorage and gated behind user OTP phone authentication. There is no public REST API to construct a server-side pre-filled cart URL (`joyory.com/cart?add=...`).
* **Impact:** The MCP server cannot generate a direct one-click checkout link containing all recommended products.
* **Mitigation Implemented:** The system returns canonical, SEO-friendly product URLs (`url`) for every item, allowing shoppers to click through directly to the product detail page and add items with one tap.

### 2.2 Read-Only Scope by Design
* **Observation:** The connector provides zero order placement, customer account login, or payment processing tools.
* **Impact:** Transactions must be finalized on the official Joyory website.
* **Rationale:** Deliberate security and regulatory decision for a hackathon prototype to eliminate PCI-DSS compliance scope, customer data liability, and payment fraud risks.

---

## 3. Runtime & Architectural Constraints

### 3.1 In-Memory Cache Volatility
* **Observation:** `TTLCache` is maintained in Python process heap memory rather than an external Redis cluster.
* **Impact:** Restarting the server container (e.g. during a code redeploy or Render cold-start) invalidates the cache.
* **Mitigation Implemented:** The `_prewarm()` startup routine automatically warms the category tree and active promotions cache before serving user traffic.

### 3.2 Product Detail Batch Cap (5 Items)
* **Observation:** `get_product_details` enforces a maximum ceiling of 5 product IDs per invocation.
* **Impact:** AI clients cannot inspect 20 products simultaneously in a single call.
* **Rationale:** Protects token context limits and prevents API latency spikes caused by launching dozens of parallel upstream HTTP requests.

### 3.3 Client-Dependent UI Visualization
* **Observation:** Interactive, horizontal swipeable carousels with native buttons (as seen in ChatGPT shopping actions) depend entirely on the host client's UI engine.
* **Impact:** Claude.ai renders rich vertical Markdown cards with images and links, but cannot display interactive JavaScript carousels due to Claude's Markdown-only architecture.
