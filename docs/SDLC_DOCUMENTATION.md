# SDLC Documentation
## Joyory MCP — Development Progress

**Version:** v1.0  
**Methodology:** Iterative / Hackathon Sprint  
**Last Updated:** September 2026  

---

## 1. Project Overview

Joyory MCP is a read-only Model Context Protocol server that connects Claude AI to Joyory's live product catalog. Built during a single-day hackathon sprint, it enables natural-language beauty product discovery without any new frontend — the customer simply chats with Claude.

---

## 2. Development Methodology

Iterative development in phases, validated at each step before moving forward:

```
Phase 1 → Infrastructure & Environment
Phase 2 → API Discovery (know what we're connecting to before building)
Phase 3 → Data Layer (adapters, normalization, models)
Phase 4 → Tool Layer (search, details)
Phase 5 → MCP Server
Phase 6 → Testing
Phase 7 → Integration (Claude + tunnel)
Phase 8 → Documentation
```

Key principle: **Discovery before code.** We did not assume Joyory had a standard REST API. We built tooling to find it first.

---

## 3. Requirement Analysis

### Identified constraints
- Joyory has no public API documentation
- Joyory is a React SPA — all URLs return HTML
- Must work within a single hackathon day
- Must be demonstrable to judges live

### Key decisions made during analysis
- Use MCP (not a custom chatbot) — lets us plug into Claude without building a UI
- Read-only only — no auth, no mutations, no legal risk
- Two tools only — keep the surface area minimal and reliable
- API discovery engine — don't guess, observe the browser

---

## 4. System Design

### Architecture decision: Adapter pattern
Separating the adapter (knows Joyory's API) from the normalizer (knows our schema) from the tools (knows neither) means any layer can change independently.

### Architecture decision: MCP 2.x Streamable HTTP
Chosen over stdio (not useful for remote Claude.ai) and SSE (being deprecated). Streamable HTTP is the current MCP standard and works with Claude.ai custom integrations.

### Architecture decision: In-memory cache only
No Redis, no SQLite. The hackathon prototype needs zero infrastructure beyond Python. A TTL dict is sufficient for demo-scale traffic.

---

## 5. Technology Selection

| Choice | Alternatives Considered | Reason Selected |
|---|---|---|
| Python 3.14 | Node.js | Already installed, MCP SDK available |
| MCP 2.x | REST API wrapper | Native AI integration, Claude.ai support |
| httpx | requests | Async-native, timeout control, retry support |
| Playwright | Selenium, Puppeteer | Best Python async browser automation |
| Cloudflare Tunnel | ngrok, localtunnel | No account needed, no interstitial page |
| Pydantic v2 | dataclasses | Validation, serialization, IDE support |
| Rich | print() | Readable demo output for judges |

---

## 6. Development Log

### Phase 1 — Infrastructure
- Created project structure (`src/`, `tests/`, `scripts/`, `docs/`, `artifacts/`)
- Wrote `pyproject.toml` — hit Python 3.14 incompatibility with `setuptools.backends.legacy`, fixed to `setuptools.build_meta`
- Set up `.env.example`, `.gitignore`, config files

### Phase 2 — API Discovery
- Built Playwright discovery engine (`scripts/discover_joyory.py`)
- Built scoring system (`discovery/scoring.py`) — scores API candidates 0–100 based on JSON content, field richness, search trigger correlation
- **First discovery attempt:** All 16 guessed REST endpoints returned HTML — Joyory is a catch-all SPA
- **Breakthrough:** JS bundle analysis (`scripts/extract_api_from_js.py`) found 102 API paths in the 2.5MB bundle at `/assets/index-CLdj6JPs.js`
- **Key finding:** Real API host is `beauty.joyory.com` (a separate subdomain, not `joyory.com`)
- Probed `beauty.joyory.com` directly — `/api/user/products/all` returned real product JSON immediately
- Mapped full product schema via `scripts/inspect_api_schema.py`
- Wrote `config/joyory_source.json` with confidence scores: Search 97/100, Detail 95/100

### Phase 3 — Data Layer
- Wrote `models.py` — `ProductSummary`, `ProductDetail`, `VariantInfo`, `SearchResponse`
- Wrote `normalize.py` — 20+ field alias mappings, Joyory-specific extraction:
  - `_id` as primary ID (MongoDB ObjectId)
  - `discountedPrice` as primary price
  - `brand.name` from nested object
  - `variants[].images` for product images
  - `howToUse` array → single joined string
  - Stock derived from `variants[].status` on detail endpoint
- Built `adapters/api.py` — REST adapter with retry, timeout, URL validation
- Built `adapters/browser.py`, `graphql.py`, `html.py` — fallback chain
- Wrote `cache.py` — TTL dict with search and detail key builders
- Wrote `errors.py` — typed error classes with user-facing messages

### Phase 4 — Tool Layer
- Wrote `tools/search.py` — cache → adapter → normalize → return
- Wrote `tools/details.py` — cache → adapter → normalize → return
- Both tools catch all exceptions and return structured error dicts

### Phase 5 — MCP Server
- **First attempt:** Used `FastMCP` — failed. MCP SDK v2.2 renamed it to `MCPServer`
- Discovered actual v2 API by inspecting installed package directly
- **Second attempt:** `path=` kwarg — failed. Correct param is `streamable_http_path=`
- **Third attempt:** Host validation error `421 Misdirected Request` — Cloudflare Tunnel sends public domain as `Host` header, MCP's DNS rebinding protection rejects it
- Fixed with `TransportSecuritySettings(enable_dns_rebinding_protection=False)`
- Server running on `http://127.0.0.1:8000/mcp`

### Phase 6 — Testing
- 69 unit tests across 5 test files
- Tests cover: normalization, cache, tool contracts, error handling, response shape
- All tests run without network — mocked adapters only
- Smoke test (`scripts/test_joyory_source.py`) runs real queries against live Joyory API

### Phase 7 — Integration
- **Tunnel attempt 1 — ngrok:** Auth token issues, then domain config error (`ERR_NGROK_15013`), then human-verification interstitial blocked all Claude requests
- **Tunnel attempt 2 — localtunnel:** No account needed but localtunnel's interstitial returned 503/404 to Claude
- **Tunnel attempt 3 — Cloudflare Tunnel:** Single exe download, one command, clean HTTPS URL, no interstitial. Working immediately.
- Added to Claude.ai as custom integration with `No sign-in` authentication
- End-to-end test: Claude → MCP → Joyory API → real products ✅

### Phase 8 — Documentation
- `README.md` — technical overview and setup guide
- `docs/PRD.md` — product requirements
- `docs/SRS.md` — software requirements
- `docs/SDLC_DOCUMENTATION.md` — this file
- `docs/TESTING_DOCUMENTATION.md` — test cases and results
- `pitch.html` — visual pitch document for judges

---

## 7. Feature Development Tracker

| ID | Feature / Task | Status | Priority | Notes |
|---|---|---|---|---|
| MCP-001 | Project scaffold and environment | ✅ Complete | High | pyproject.toml, dirs, .env |
| MCP-002 | API discovery engine (Playwright) | ✅ Complete | High | Scores 102 API candidates |
| MCP-003 | beauty.joyory.com API identified | ✅ Complete | High | Search + detail endpoints confirmed |
| MCP-004 | Product models (Pydantic) | ✅ Complete | High | ProductSummary, ProductDetail |
| MCP-005 | Normalization layer | ✅ Complete | High | Handles Joyory's schema |
| MCP-006 | REST API adapter | ✅ Complete | High | Retry, timeout, URL validation |
| MCP-007 | Browser fallback adapter | ✅ Complete | Medium | Playwright-based fallback |
| MCP-008 | In-memory TTL cache | ✅ Complete | High | 10-min TTL, configurable |
| MCP-009 | Error handling layer | ✅ Complete | High | Typed errors, user messages |
| MCP-010 | search_products tool | ✅ Complete | High | Query, limit, price, brand |
| MCP-011 | get_product_details tool | ✅ Complete | High | Full product data |
| MCP-012 | MCP 2.x server (MCPServer) | ✅ Complete | High | Streamable HTTP on :8000/mcp |
| MCP-013 | Unit tests (69 tests) | ✅ Complete | High | All passing |
| MCP-014 | Real smoke test | ✅ Complete | High | Live Joyory data confirmed |
| MCP-015 | Cloudflare Tunnel integration | ✅ Complete | High | Clean HTTPS, no interstitial |
| MCP-016 | Claude.ai custom integration | ✅ Complete | High | Working end-to-end |
| MCP-017 | PRD / SRS / SDLC documentation | ✅ Complete | Medium | Full docs folder |
| MCP-018 | Pitch document (HTML/PDF) | ✅ Complete | Medium | Judge-facing one-pager |
| MCP-019 | list_categories tool | ⏳ Pending | Low | Future enhancement |
| MCP-020 | list_brands tool | ⏳ Pending | Low | Future enhancement |
| MCP-021 | compare_products tool | ⏳ Pending | Low | Future enhancement |
| MCP-022 | Skin profile filtering | ⏳ Pending | Low | Future enhancement |
| MCP-023 | Persistent user context | ⏳ Pending | Low | Future enhancement |

---

## 8. Bug Tracker

| ID | Bug Description | Status | Severity | Resolution |
|---|---|---|---|---|
| BUG-001 | `setuptools.backends.legacy` not found on Python 3.14 | ✅ Fixed | High | Changed to `setuptools.build_meta` in pyproject.toml |
| BUG-002 | `FastMCP` import error — MCP SDK v2 renamed it | ✅ Fixed | High | Switched to `MCPServer` from `mcp.server.mcpserver` |
| BUG-003 | `path=` kwarg rejected by `MCPServer.run()` | ✅ Fixed | High | Changed to `streamable_http_path=` |
| BUG-004 | `421 Misdirected Request` from Cloudflare Tunnel | ✅ Fixed | High | Added `TransportSecuritySettings(enable_dns_rebinding_protection=False)` |
| BUG-005 | ngrok interstitial blocking Claude requests | ✅ Fixed | High | Replaced ngrok with Cloudflare Tunnel |
| BUG-006 | localtunnel 503/404 errors from Claude | ✅ Fixed | High | Replaced localtunnel with Cloudflare Tunnel |
| BUG-007 | Detail endpoint showing "In Stock: Unknown" | ✅ Fixed | Medium | Added variant-based stock derivation in normalizer |
| BUG-008 | Port 8000 already in use on restart | ✅ Fixed | Low | Kill process with `taskkill /PID` before restart |
| BUG-009 | Cache bleeding across tests — wrong adapter used | ✅ Fixed | Medium | Added `cache.clear()` in affected test setUp |
| BUG-010 | `_make_mock_adapter` returning results even when `search_error` set | ✅ Fixed | Medium | Fixed conditional logic in test helper |

---

## 9. Integration Testing

| Integration | Test | Result |
|---|---|---|
| MCP Server ↔ httpx client | POST /mcp with MCP headers | ✅ Pass |
| MCP Server ↔ Cloudflare Tunnel | External HTTPS request | ✅ Pass |
| MCP Server ↔ Claude.ai | Claude calls search_products | ✅ Pass |
| Adapter ↔ beauty.joyory.com | Real search query | ✅ Pass |
| Adapter ↔ beauty.joyory.com | Real detail query | ✅ Pass |
| Normalizer ↔ Joyory schema | All fields mapped correctly | ✅ Pass |
| Cache ↔ repeated queries | Second call from cache | ✅ Pass |
| Error handling ↔ invalid ID | Graceful error returned | ✅ Pass |
| Error handling ↔ empty search | Graceful empty response | ✅ Pass |

---

## 10. Deployment

### Local (current)

```powershell
# Terminal 1 — MCP Server
cd C:\Users\thefu\Downloads\Hackathon\joyory-mcp
python server.py

# Terminal 2 — Cloudflare Tunnel
C:\Users\thefu\cloudflared.exe tunnel --url http://127.0.0.1:8000
```

Claude connector URL: `https://YOUR-TUNNEL.trycloudflare.com/mcp`

### Requirements
- Python 3.11+
- All pip dependencies installed
- `config/joyory_source.json` present (run `discover_joyory.py` if missing)
- Cloudflare Tunnel exe at `C:\Users\thefu\cloudflared.exe`

---

## 11. Current Project Status

**Status: ✅ Demo-Ready**

The system is fully functional end-to-end. Claude can search Joyory products, retrieve full product details, compare products, and handle errors gracefully — all from natural language conversation.

### What works
- Natural language product search
- Price and brand filtering
- Full ingredient / how-to-use detail retrieval
- Multi-turn conversation (Claude maintains context)
- Product comparison
- Error handling for invalid queries and IDs
- 69 unit tests passing
- Live demo via Claude.ai custom integration

### Known limitations
- Ratings show as `—` for newer products (Joyory API returns `avgRating: 0` for products with no reviews — accurate data, not a bug)
- Cloudflare Tunnel URL changes every restart (free tier)
- No persistent deployment — requires both server and tunnel to be running locally

---

## 12. Version History

| Version | Date | Changes |
|---|---|---|
| v0.1 | Sep 2026 | Initial scaffold, discovery engine |
| v0.2 | Sep 2026 | API identified, adapter + normalizer built |
| v0.3 | Sep 2026 | MCP server, tools, 69 tests passing |
| v0.4 | Sep 2026 | Cloudflare Tunnel fix, Claude integration working |
| v1.0 | Sep 2026 | Full documentation, pitch deck, demo-ready |
