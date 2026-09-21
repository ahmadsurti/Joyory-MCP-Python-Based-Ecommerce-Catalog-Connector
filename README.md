# Joyory-MCP-Python-Based-Ecommerce-Catalog-Connector

![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![Protocol](https://img.shields.io/badge/MCP-2.x%20Streamable%20HTTP-orange)
![Validation](https://img.shields.io/badge/Validation-Pydantic%20V2-brightgreen)
![Client](https://img.shields.io/badge/HTTP%20Client-HTTPX-blueviolet)
![Testing](https://img.shields.io/badge/Tests-69%20Passed-success)
![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)

A high-performance, read-only Model Context Protocol (MCP) server that connects frontier conversational AI clients—including Anthropic Claude and OpenAI ChatGPT—directly to Joyory's live beauty, personal care, and wellness catalog.

Built on the MCP 2.x Streamable HTTP specification, this connector allows AI assistants to execute parametric product searches, extract complete INCI ingredient formulas, inspect cosmetic shade variants, identify active store promotions (BOGOs), and recommend cheaper alternatives in real time without human data fabrication.

> **Full Documentation Package:** Detailed engineering, business, and architecture documents are available in the [`docs/`](docs/INDEX.md) directory.

---

## Features

| Module / Tool | Implementation File | What it does |
|---|---|---|
| **`search_products`** | [`src/joyory_mcp/tools/search.py`](src/joyory_mcp/tools/search.py) | Parametric keyword catalog search with price bounding (INR), brand and category slug filtering, live in-stock verification, relevance scoring, and offset pagination. |
| **`get_product_details`** | [`src/joyory_mcp/tools/details.py`](src/joyory_mcp/tools/details.py) | Concurrent batch lookup for 1–5 products, extracting full INCI ingredients, usage directions, dermatological attributes (SPF, fragrance-free), and variant shade/size inventories. |
| **`get_catalog_overview`** | [`src/joyory_mcp/tools/catalog.py`](src/joyory_mcp/tools/catalog.py) | Retrieves Joyory's complete, non-sampled category taxonomy tree and all active brand directories with live product counts. |
| **`get_reviews`** | [`src/joyory_mcp/tools/reviews.py`](src/joyory_mcp/tools/reviews.py) | Fetches authentic customer reviews, star ratings, and verified buyer commentary for product qualification. |
| **`get_similar_products`** | [`src/joyory_mcp/tools/similar.py`](src/joyory_mcp/tools/similar.py) | Algorithmic "dupe" discovery locating comparable or cheaper in-stock alternatives within the same product category. |
| **`get_offers`** | [`src/joyory_mcp/tools/offers.py`](src/joyory_mcp/tools/offers.py) | Ingests active merchandising campaigns, price-capped collections, and promotional discount codes (e.g. Aqualogica BOGO `GLOW`). |
| **`TTLCache`** | [`src/joyory_mcp/cache.py`](src/joyory_mcp/cache.py) | Thread-safe in-memory caching engine with a 10-minute (600s) TTL, eliminating redundant upstream network traffic. |
| **`ApiJoyoryDataSource`** | [`src/joyory_mcp/adapters/api.py`](src/joyory_mcp/adapters/api.py) | Resilient asynchronous REST adapter with automatic retries, exponential backoff, and domain error sanitization. |
| **`JoyoryApiDiscoverer`** | [`src/joyory_mcp/discovery/discover.py`](src/joyory_mcp/discovery/discover.py) | Playwright-based network interception engine capable of dynamically reverse-engineering undocumented e-commerce APIs. |

---

## Prerequisites

* **Python:** Version 3.10, 3.11, 3.12, or 3.13 installed.
* **Package Manager:** `pip` installed.
* **Network Access:** Outbound HTTPS access to `beauty.joyory.com`, `joyory.com`, and `res.cloudinary.com`.

Verify your local Python installation:
```bash
python --version
pip --version
```

---

## Setup from Scratch

### 1. Clone the Repository
```bash
git clone https://github.com/ahmadsurti/Joyory-MCP-Python-Based-Ecommerce-Catalog-Connector.git
cd Joyory-MCP-Python-Based-Ecommerce-Catalog-Connector
```

### 2. Create and Activate a Virtual Environment
```bash
# Windows (PowerShell):
python -m venv .venv
.venv\Scripts\Activate.ps1

# Linux / macOS:
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies in Development Mode
```bash
pip install -e .
```

### 4. Run the Automated Test Suite
Verify that all 69 unit, cache, normalization, and tool tests pass cleanly:
```bash
python -m pytest
```

---

## Configuration / Environment Variables

The application operates with sensible production defaults out-of-the-box, but can be customized via a `.env` file in the project root:

```bash
cp .env.example .env
```

Expected `.env` structure:
```env
# Canonical web storefront
JOYORY_BASE_URL=https://joyory.com

# HTTP Client Timeout (seconds)
JOYORY_TIMEOUT_SECONDS=20

# In-Memory Cache Validity (seconds)
JOYORY_CACHE_TTL_SECONDS=600

# Upper bound on search ingestion
JOYORY_MAX_RESULTS=100

# Server Binding
MCP_HOST=127.0.0.1
MCP_PORT=8000
```
> **Security Note:** The `.env` file is explicitly ignored in `.gitignore` and must never be committed to version control.

---

## How to Use

### 1. Start the Server Locally
```bash
python server.py
```
Upon launch, the server pre-warms the catalog tree and active promotions cache, then starts the Streamable HTTP transport:
```
[INFO] Joyory MCP on http://127.0.0.1:8000/mcp
```

### 2. Connect an AI Client (Claude Desktop Example)
Add the server definition to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "joyory": {
      "command": "python",
      "args": ["-m", "joyory_mcp.server"],
      "cwd": "C:\\path\\to\\Joyory-MCP-Python-Based-Ecommerce-Catalog-Connector"
    }
  }
}
```

### 3. Perform Conversational Shopping
In Claude or ChatGPT, execute natural-language queries:
* *"I have combination, acne-prone skin. Recommend two fragrance-free sunscreens from The Derma Co under ₹500 with pictures and links."*
* *"Compare the full INCI ingredients and active percentages of those two products."*
* *"Are there any Buy 1 Get 1 Free offers active right now, and what coupon code do I need?"*
* *"Find me a cheaper in-stock alternative for the top sunscreen you showed."*

---

## Project Structure

```
Joyory-MCP-Python-Based-Ecommerce-Catalog-Connector/
├── .env.example              # Template environment configuration
├── .gitignore                # Git exclusion rules (caches, virtual environments)
├── LICENSE                   # Apache License 2.0
├── NOTICE                    # Project attribution notice
├── README.md                 # Master repository documentation
├── pitch.html                # Interactive marketing & slide presentation
├── pyproject.toml            # Build metadata, packaging, and test dependencies
├── server.py                 # Root application entrypoint
├── config/
│   └── joyory_source.json    # Reverse-engineered API endpoint signatures
├── docs/                     # Comprehensive 22-document engineering & product package
│   ├── INDEX.md              # Master documentation index & glossary
│   ├── BRD.md                # Business Requirements Document
│   ├── PRD.md                # Product Requirements Document
│   ├── SRS.md                # Software Requirements Specification
│   ├── SYSTEM_ARCHITECTURE.md# C4 Architecture & Sequence Diagrams
│   ├── TECHNICAL_DESIGN.md   # Implementation design & Pydantic models
│   ├── MCP_SPECIFICATION.md  # Formal JSON-RPC tool contracts
│   ├── DEMO_GUIDE.md         # Live judge presentation script
│   └── TESTING.md            # Test case specifications & results
├── scripts/
│   ├── demo.py               # Interactive CLI tool demonstration script
│   ├── discover_joyory.py    # Automated API discovery trigger script
│   └── test_joyory_source.py # Live network smoke verification suite
├── src/
│   └── joyory_mcp/           # Core application package
│       ├── config.py         # 12-factor configuration & host resolution
│       ├── server.py         # MCPServer initialization & tool registration
│       ├── models.py         # Pydantic V2 data contracts (ProductSummary, ProductDetail)
│       ├── normalize.py      # Normalization, HTML stripping, relevance scoring
│       ├── cache.py          # In-memory thread-safe TTLCache singleton
│       ├── errors.py         # Typed domain exceptions & sanitized error messages
│       ├── adapters/         # Data ingestion adapters (REST API & Playwright)
│       ├── discovery/        # Network interception & heuristic scoring engine
│       └── tools/            # Discrete MCP tool business logic
└── tests/                    # Hermetic Pytest test suite (69 tests)
```

---

## Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `JOYORY_BASE_URL` | `https://joyory.com` | Base storefront URL used for generating canonical product links. |
| `JOYORY_TIMEOUT_SECONDS` | `20.0` | Maximum network timeout for upstream HTTP calls. |
| `JOYORY_CACHE_TTL_SECONDS`| `600` | In-memory cache time-to-live in seconds (10 minutes). |
| `JOYORY_MAX_RESULTS` | `100` | Maximum products retrieved per query to bound memory consumption. |
| `MCP_HOST` | `127.0.0.1` | Host interface. Automatically binds to `0.0.0.0` when `PORT` or `RENDER` is set. |
| `MCP_PORT` | `8000` | HTTP port for Streamable HTTP transport. Overridden by cloud `PORT` env var. |

---

## Deployment

The connector is configured for cloud deployment to **Render** Web Services:

* **Platform:** Render Web Service (Python 3)
* **Build Command:** `pip install -e .`
* **Start Command:** `python server.py`
* **Health Check Path:** `/mcp`

The service automatically detects cloud container environments. In `src/joyory_mcp/config.py`, when Render injects the dynamic `PORT` environment variable, `MCP_HOST` binds to `0.0.0.0:${PORT}` automatically, requiring zero manual configuration.

---

## Troubleshooting

| Problem | Root Cause | Solution |
|---|---|---|
| `[Errno 11002] getaddrinfo failed` | Local workstation DNS resolution timeout (`WSATRY_AGAIN`). | Verify internet connectivity or configure system DNS to `1.1.1.1` / `8.8.8.8`. |
| Port `8000` already in use | Previous instance of `server.py` running in background. | Terminate previous Python PID: `Stop-Process -Name python` or set `MCP_PORT=8001`. |
| Zero products for brand query | Special characters or spaces in brand name. | Brand normalizer resolves strings like `Dr Sheth's` to `dr-sheth-s`. Validate slug via `get_catalog_overview()`. |
| Product shows `rating=null` | Catalog item is newly added with zero customer reviews. | Normal e-commerce state; `rating=null` indicates an unreviewed item, not a low rating. |

---

## What I Learned from Building This

Building this connector provided several deep software engineering insights into agentic commerce, protocol design, and reverse-engineering real-world web applications:

1. **Protocol Over Proprietary UIs:** Moving away from heavy, custom web chat widgets to an open standard (MCP 2.x) demonstrated that meeting users inside their primary AI client (Claude/ChatGPT) provides a superior user experience with zero frontend maintenance costs.
2. **"Discovery Before Code":** E-commerce platforms rarely publish public developer APIs. Instead of attempting brittle HTML DOM scraping, writing a Playwright-based network interceptor (`discover.py`) allowed us to uncover Joyory's underlying JSON microservices (`beauty.joyory.com`), reducing codebase size and latency by an order of magnitude.
3. **Defensive Normalization at the Boundary:** Real-world e-commerce data is chaotic: numbers stored as strings, unescaped HTML description tags, missing category keys, and inconsistent punctuation (`DOT & KEY` vs `dot-key`). Enforcing strict Pydantic V2 schemas at the ingestion boundary ensured that downstream AI reasoning never crashed on malformed payloads.
4. **Intentional Minimalism (The "Ponytail" Approach):** Pruning unnecessary dependencies (`beautifulsoup4`, `lxml`) and implementing a clean in-memory thread-safe `TTLCache` avoided the operational overhead of external Redis infrastructure while maintaining sub-5ms cached response times.
5. **Client-Side Bounding Over Blind Trust:** We discovered that upstream search APIs frequently ignore parameter bounds like `minPrice` or return broad keyword OR matches. Applying client-side bounding and TF-IDF relevance scoring in Python proved essential for delivering 100% accurate results.

> **Biggest Takeaway:** In conversational commerce, the bottleneck is rarely the intelligence of the LLM—it is the quality, structure, and latency of the context provided to it. A fast, deterministic MCP server that sanitizes data, resolves pricing, and injects verified promotions transforms an AI from a generic chatbot into an authoritative shopping advisor.

---

## License

This project is licensed under the **Apache License 2.0**. See the [`LICENSE`](LICENSE) file for details.
