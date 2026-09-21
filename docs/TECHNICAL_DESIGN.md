# Technical Design Document
## Project: Joyory Conversational Commerce MCP Connector
**Document Version:** 2.0  
**Target Codebase:** `src/joyory_mcp/`  
**Language & Runtime:** Python 3.10+ / Pydantic V2 / MCP SDK 2.x  

---

## 1. Module Structure & File Responsibilities

The codebase follows a modular design separating protocol exposition, tool orchestration, domain normalization, and upstream transport:

```
src/joyory_mcp/
├── __init__.py            # Package initialization & version metadata
├── config.py              # Centralized environment variables, URLs, and headers
├── server.py              # MCPServer initialization, startup prewarm, and tool routing
├── models.py              # Pydantic V2 data contracts (ProductSummary, ProductDetail, Variant)
├── normalize.py           # Data normalization, HTML stripping, size/price parsing, relevance scoring
├── cache.py               # In-memory thread-safe TTLCache with parameterized keys
├── errors.py              # Typed domain exceptions and user-friendly error translation
├── adapters/
│   ├── base.py            # JoyoryDataSource abstract base class
│   ├── api.py             # ApiJoyoryDataSource (primary HTTP REST client)
│   ├── browser.py         # BrowserJoyoryDataSource (Playwright headless browser fallback)
│   └── graphql.py         # GraphQLJoyoryDataSource (stub/alternative transport)
├── discovery/
│   ├── discover.py        # Automated network discovery & probe engine
│   └── scoring.py         # API candidate heuristic scoring
└── tools/
    ├── search.py          # search_products tool implementation
    ├── details.py         # get_product_details tool implementation
    ├── catalog.py         # get_catalog_overview tool implementation
    ├── reviews.py         # get_reviews tool implementation
    ├── similar.py         # get_similar_products tool implementation
    └── offers.py          # get_offers tool implementation
```

---

## 2. Core Modules & Implementation Details

### 2.1 Configuration Management (`src/joyory_mcp/config.py`)
* **Purpose:** Provides centralized, 12-factor environment configuration.
* **Environment Variables:**
  * `JOYORY_BASE_URL` (default: `"https://joyory.com"`): Canonical web storefront URL.
  * `JOYORY_TIMEOUT_SECONDS` (default: `20.0`): Maximum client timeout for upstream requests.
  * `JOYORY_CACHE_TTL_SECONDS` (default: `600`): Cache expiration duration (10 minutes).
  * `JOYORY_MAX_RESULTS` (default: `100`): Upper bound for search result retrieval to protect memory.
  * `MCP_HOST` (default: `0.0.0.0` if `PORT` or `RENDER` env var is present, else `127.0.0.1`).
  * `MCP_PORT` (default: `int(os.getenv("PORT", "8000"))`).
* **Upstream Constants:**
  * `BEAUTY_BASE_URL = "https://beauty.joyory.com"`: Upstream microservice host.
  * `BEAUTY_HEADERS`: Standard browser headers including `User-Agent`, `Accept: application/json`, and mandatory `Referer: https://joyory.com/`.
  * `ALLOWED_HOSTS = {"joyory.com", "www.joyory.com", "beauty.joyory.com", "res.cloudinary.com"}`.

### 2.2 Domain Models (`src/joyory_mcp/models.py`)
Built with **Pydantic V2** for high-performance schema validation, serialization, and type safety:

```python
class ProductSummary(BaseModel):
    id: str
    name: str
    brand: str | None = None
    category: str | None = None
    category_slug: str | None = None
    price: float | None = None
    mrp: float | None = None
    currency: str = "INR"
    rating: float | None = None
    rating_count: int | None = None
    in_stock: bool = True
    image_url: str | None = None
    url: str
    size: str | None = None
    price_per_100ml: float | None = None
    match: str | None = None  # "exact" | "high" | "partial" | "weak"
    tags: list[str] = Field(default_factory=list)

class Variant(BaseModel):
    id: str
    sku: str | None = None
    name: str
    shade: str | None = None
    hex_code: str | None = None
    price: float
    mrp: float | None = None
    in_stock: bool = True
    images: list[str] = Field(default_factory=list)
    size: str | None = None

class ProductDetail(ProductSummary):
    short_description: str | None = None
    description: str | None = None
    ingredients: list[str] = Field(default_factory=list)
    how_to_use: list[str] = Field(default_factory=list)
    attributes: dict = Field(default_factory=dict)
    images: list[str] = Field(default_factory=list)
    variants: list[Variant] = Field(default_factory=list)

    @computed_field
    @property
    def variant_information(self) -> list[dict]:
        """Provides backward-compatible dictionary serialization for variants."""
        return [v.model_dump(exclude_none=True) for v in self.variants]
```

### 2.3 Data Normalization & Enrichment (`src/joyory_mcp/normalize.py`)
* **Brand Slug Normalization (`_to_brand_slug`):** Normalizes brand names with ampersands, apostrophes, and casing to match Joyory's API parameters:
  * `"DOT & KEY"` → `"dot-key"`
  * `"Dr Sheth's"` → `"dr-sheth-s"`
  * `"Swiss Beauty"` → `"swiss-beauty"`
* **Size & Unit Price Calculation (`_extract_size` & `_calc_unit_price`):**
  * Uses regex to identify milliliter (`ml`), gram (`g`), and liter (`l`) values with strict word boundaries to avoid false positives (e.g. matching 'l' in 'oil').
  * Computes standard `price_per_100ml` or `price_per_100g` to enable consumer value comparisons.
* **Relevance Scoring (`score_relevance`):**
  * Evaluates match quality against query tokens.
  * Assigns confidence tier: `"exact"` (1.0), `"high"` (≥0.8), `"partial"` (≥0.4), or `"weak"` (<0.4).
  * Considers primary product title, brand identity, and secondary category tags.

### 2.4 High-Performance Caching (`src/joyory_mcp/cache.py`)
* **Thread-Safe In-Memory TTLCache:**
  * Uses `threading.Lock()` to prevent race conditions during concurrent tool calls.
  * Automatically purges stale keys when `time.monotonic() - timestamp > ttl`.
  * Exposes helper methods: `search_key()`, `detail_key()`, `clear()`, `delete()`, and `size()`.
  * Backwards-compatible signature supports legacy 4-argument and modern 9-argument search invocations.

---

## 3. Upstream Integration & Adapter Layer

### 3.1 Primary REST Adapter (`src/joyory_mcp/adapters/api.py`)
* **Endpoint:** `GET https://beauty.joyory.com/api/user/products/all`
* **Query Parameter Resolution:**
  * Query text: `search` (only injected when `query.strip()` is non-empty to avoid overriding brand browsing).
  * Brand filter: `brandIds` (uses `_to_brand_slug`).
  * Category filter: `categoryIds` (accepts hierarchical category slugs).
  * Pagination: `limit` (capped at `cfg.MAX_RESULTS = 100`).
* **Resilient Error Recovery:**
  * Catches `httpx.HTTPError` and network timeouts.
  * Automatically retries with exponential backoff (up to 2 retries).
  * Maps upstream 404s and empty data arrays to domain exceptions (`JoyoryNoResultsError`, `JoyoryProductNotFoundError`).

### 3.2 Playwright Browser Fallback (`src/joyory_mcp/adapters/browser.py`)
* **Purpose:** Executes headless Chromium via Playwright if direct HTTP endpoints are challenged or blocked.
* **Mechanism:** Navigates directly to `https://joyory.com`, executes DOM query evaluations, intercepts in-flight client network responses, and extracts hydrated React application states.

---

## 4. Error Handling Architecture (`src/joyory_mcp/errors.py`)

The system eliminates raw stack traces and unhandled 500 errors by funneling all upstream anomalies into clean, user-friendly messages:

| Exception Class | Cause | Output to MCP Host |
|---|---|---|
| `JoyoryUnavailableError` | DNS failure (`WSATRY_AGAIN`), TCP timeout, or upstream 503 | *"Joyory appears to be temporarily unavailable. Please try again in a moment."* |
| `JoyoryNoResultsError` | Zero products matched the search criteria | Returns empty list with actionable catalog guidance hint. |
| `JoyoryProductNotFoundError` | Invalid or deleted product ID requested | *"Product '{id}' was not found on Joyory."* |
| `JoyoryRateLimitError` | Upstream HTTP 429 received | *"Joyory is currently receiving high traffic. Please wait a moment before trying again."* |
| `JoyoryAPIChangedError` | Upstream JSON structure altered unexpectedly | Triggers safe fallback and alerts server logs. |
