# End-to-End System Workflows
## Project: Joyory Conversational Commerce MCP Connector
**Document Version:** 2.0  
**Architectural Flow:** Intent → Protocol → Gateway → Normalization → Synthesis  

---

## 1. High-Level Transaction Lifecycle

Every interaction through Joyory MCP adheres to a disciplined, multi-stage pipeline:

```
[ User Intent ]
       │
       ▼
[ AI Host (Claude / ChatGPT) ]
       │   1. Tool Selection & JSON-RPC Construction
       ▼
[ MCP Streamable HTTP Layer (/mcp) ]
       │   2. Parameter Parsing & Pydantic Schema Validation
       ▼
[ Tool Business Logic Handler ]
       │   3. Cache Evaluation (TTLCache 10-Min)
      ┌┴────────────────────────┐
 [Cache Hit]               [Cache Miss]
      │                         │
      │ 4a. Return Cached JSON  │ 4b. Forward to ApiJoyoryDataSource
      │                         ▼
      │             [ Upstream HTTP Call (beauty.joyory.com) ]
      │                         │
      │                         ▼
      │             [ Normalization, Cleaning & Scoring ]
      │                         │
      │                         ▼
      │             [ Update TTLCache Singleton ]
      └─────────────────────────┬┘
                                │
                                ▼
                   [ MCP Response Serialization ]
                                │
                                ▼
            [ AI Host Synthesizes Card Presentation ]
                                │
                                ▼
                       [ User Presentation ]
```

---

## 2. Boot-Time Pre-Warming Workflow

To prevent the cold-start latency penalty common in serverless or newly spawned services, `server.py` executes an asynchronous warm-up routine prior to accepting client traffic:

```mermaid
sequenceDiagram
    autonumber
    participant App as server.py (main)
    participant Prewarm as _prewarm()
    participant Catalog as tools/catalog.py
    participant Offers as tools/offers.py
    participant Upstream as beauty.joyory.com
    participant Cache as TTLCache

    App->>Prewarm: asyncio.run(_prewarm())
    par Fetch Categories & Brands
        Prewarm->>Catalog: get_catalog_overview()
        Catalog->>Upstream: GET /api/user/categories/tree
        Catalog->>Upstream: GET /api/user/brands
        Upstream-->>Catalog: 200 OK (Category Tree & Brands)
        Catalog->>Cache: set("catalog:overview:v2", catalog_data)
    and Fetch Active Promotions
        Prewarm->>Offers: get_offers()
        Offers->>Upstream: GET /api/user/promotions/active?section=offers
        Upstream-->>Offers: 200 OK (Active Offers & BOGOs)
        Offers->>Cache: set("offers:v2", offers_data)
    end
    Prewarm-->>App: Pre-warm Complete (Logged)
    App->>App: mcp.run(transport="streamable-http", host, port)
```

---

## 3. Conversational Multi-Tool Consultation Workflow

The following diagram illustrates an end-to-end multi-turn customer session, showcasing how the AI host orchestrates multiple discrete MCP tools to solve an ambiguous shopping request:

```mermaid
sequenceDiagram
    autonumber
    actor User as Consumer
    participant AI as Claude / ChatGPT
    participant MCP as Joyory MCP Server
    participant Joyory as Joyory Beauty Backend

    User->>AI: "I need a full AM routine under ₹1,000 using any active offers."
    
    Note over AI: Rule 1: Call catalog overview & offers concurrently
    par Session Start Initialization
        AI->>MCP: POST /mcp [get_catalog_overview()]
        MCP-->>AI: {categories: [...], brands: [...]}
    and Active Deals Discovery
        AI->>MCP: POST /mcp [get_offers()]
        MCP-->>AI: {offers: [{brand: "aqualogica", type: "bogo", code: "GLOW"}]}
    end

    Note over AI: User wants deals + routine under ₹1,000. Target Aqualogica BOGO.
    AI->>MCP: POST /mcp [search_products(brand="aqualogica", query="sunscreen", limit=5)]
    MCP->>Joyory: GET /api/user/products/all?brandIds=aqualogica&search=sunscreen
    Joyory-->>MCP: Raw Products List
    MCP-->>AI: Normalized ProductSummary list with verified URLs

    AI->>MCP: POST /mcp [get_product_details(product_ids=["6a6..."])]
    MCP->>Joyory: GET /api/user/products/6a6...
    Joyory-->>MCP: Raw Product Detail (INCI, SPF, variants)
    MCP-->>AI: Normalized ProductDetail (SPF 50, Fragrance-Free)

    AI-->>User: Presents complete curated routine with active coupon code GLOW and direct purchase links.
```

---

## 4. Cache Invalidation & TTL Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Uncached: Service Start / Cold Key
    Uncached --> InFlight: First Client Invocation
    InFlight --> Cached: Upstream 200 OK (Stored with timestamp)
    
    state Cached {
        [*] --> Valid: age < 600 seconds
        Valid --> Valid: Hit within 10 minutes (0 network calls)
        Valid --> Stale: age >= 600 seconds
    }

    Stale --> InFlight: Next Client Invocation triggers refresh
    Cached --> Uncached: Explicit cache.clear() in tests
```
