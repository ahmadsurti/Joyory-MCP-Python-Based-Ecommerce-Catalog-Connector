# Architecture Decision Records (ADR)
## Project: Joyory Conversational Commerce MCP Connector
**Document Version:** 2.0  
**Status:** Living Engineering Record  

---

### ADR-001: Model Context Protocol (MCP) vs. Custom Chat Web App
* **Status:** Accepted
* **Context:** Building an e-commerce assistant traditionally requires developing a full-stack web chat widget (React, WebSockets, LLM API orchestration, hosting).
* **Decision:** Implement an open-standard Model Context Protocol (MCP 2.x) server instead of a custom web application.
* **Reason:** Allows Joyory to seamlessly integrate into existing frontier AI clients (Claude Desktop, Claude.ai, ChatGPT) with zero frontend maintenance, zero LLM hosting costs, and native ecosystem adoption.
* **Consequences:** Presentation is governed by client markdown/card renderers; zero client-side UI code to maintain.
* **Alternatives Rejected:** Custom React chatbot iframe, LangChain standalone web app.

---

### ADR-002: Streamable HTTP Transport over Stdio and SSE
* **Status:** Accepted
* **Context:** MCP supports multiple transport bindings: stdio, Server-Sent Events (SSE), and Streamable HTTP.
* **Decision:** Adopt MCP 2.x Streamable HTTP (`transport="streamable-http"`, path `/mcp`).
* **Reason:** Stdio is limited strictly to local command-line processes and cannot be hosted in the cloud. SSE is being superseded in modern MCP revisions. Streamable HTTP works identically for local development and remote cloud deployments (e.g. Render).
* **Consequences:** Enables standard cloud hosting with HTTPS reverse-proxy support.
* **Alternatives Rejected:** Local-only stdio transport, legacy SSE transport.

---

### ADR-003: Adapter Pattern for Upstream Catalog Ingestion
* **Status:** Accepted
* **Context:** Joyory has no public developer portal; endpoints could change or require browser-based emulation if Cloudflare/bot protections are introduced.
* **Decision:** Implement an abstract `JoyoryDataSource` base class with concrete adapters: `ApiJoyoryDataSource` (primary HTTP client) and `BrowserJoyoryDataSource` (Playwright headless fallback).
* **Reason:** Isolates upstream transport mechanics from tool business logic and normalization layers.
* **Consequences:** If upstream APIs change, only `api.py` requires adjustment; tool contracts remain 100% stable.
* **Alternatives Rejected:** Hardcoding `httpx` calls directly inside tool functions.

---

### ADR-004: In-Memory Thread-Safe TTLCache vs. External Caching (Redis)
* **Status:** Accepted
* **Context:** Repeated conversational queries for popular items ("sunscreen", "lipstick") could generate unnecessary upstream load.
* **Decision:** Implement a lightweight, thread-safe in-memory `TTLCache` in Python with a 10-minute default TTL.
* **Reason:** Follows the "Ponytail" principle of intentional minimalism. Avoids operational overhead, cloud billing, and Docker dependency on Redis for a prototype.
* **Consequences:** Cache resets on server process restart (acceptable for read-only catalog data).
* **Alternatives Rejected:** Redis container, disk-based SQLite cache.

---

### ADR-005: Pydantic V2 Domain Contracts
* **Status:** Accepted
* **Context:** Raw e-commerce data contains missing fields, inconsistent data types (prices as strings, null ratings), and unescaped HTML.
* **Decision:** Enforce Pydantic V2 models (`ProductSummary`, `ProductDetail`, `Variant`) across all data pipelines.
* **Reason:** Provides C-speed validation via `pydantic-core`, automatic type coercion, and deterministic schema serialization.
* **Consequences:** Malformed upstream fields are trapped and sanitized at the boundary before reaching the LLM.
* **Alternatives Rejected:** Untyped Python dictionaries, legacy Marshmallow schemas.

---

### ADR-006: Hybrid Client-Side Filtering & Scoring
* **Status:** Accepted
* **Context:** Upstream Joyory search endpoints perform broad word-level matching and ignore certain query parameters (such as `minPrice` or specific category slugs).
* **Decision:** Ingest broad candidate pools from upstream API and apply client-side bounding (`min_price`, `max_price`, `brandIds`, `categoryIds`) and TF-IDF relevance scoring in Python.
* **Reason:** Guarantees 100% precision on price constraints and brand accuracy regardless of upstream server deficiencies.
* **Consequences:** Slightly higher payload ingestion (~20–40 items), offset by near-instant in-memory processing.
* **Alternatives Rejected:** Blindly trusting upstream server filtering.

---

### ADR-007: Elimination of Heavy Scraping Dependencies (`bs4`, `lxml`)
* **Status:** Accepted
* **Context:** The initial codebase included `beautifulsoup4` and `lxml` for HTML parsing, adding ~45MB of binary dependencies.
* **Decision:** Prune `bs4` and `lxml` completely from `pyproject.toml` after discovering dedicated JSON microservices (`beauty.joyory.com`).
* **Reason:** Pure JSON microservices eliminate the need for DOM parsing. Regex-based tag stripping handles inline description cleanup in zero extra dependencies.
* **Consequences:** Faster cold starts, smaller container images, and zero C-extension compile issues.
* **Alternatives Rejected:** Retaining legacy HTML scraping pipeline.

---

### ADR-008: Startup Cache Pre-Warming Routine
* **Status:** Accepted
* **Context:** First-time conversational queries experienced a 1.2s cold-start penalty while fetching category trees and active promotions.
* **Decision:** Execute `asyncio.gather(_catalog(), _offers())` at server initialization before binding the HTTP port.
* **Reason:** Guarantees that the first user interaction hits warm in-memory data, ensuring sub-100ms conversational responsiveness.
* **Consequences:** Negligible ~800ms one-time server boot overhead.
* **Alternatives Rejected:** Lazy loading on first client turn.
