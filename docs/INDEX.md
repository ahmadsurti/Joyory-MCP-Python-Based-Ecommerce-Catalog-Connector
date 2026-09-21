# Joyory MCP — Master Documentation Index
## Complete Software Engineering & Product Documentation Package
**Project Status:** Certified Working Prototype (v2.0.0)  
**Hackathon Target:** E-Commerce / Agentic AI Innovation  

Welcome to the official documentation suite for the **Joyory Conversational Commerce MCP Connector**. This package has been structured to provide complete visibility to software architects, product managers, security auditors, and hackathon judges.

---

## 📚 Document Navigation Map

```
┌────────────────────────────────────────────────────────────────────────┐
│                              docs/INDEX.md                             │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
       ┌────────────────────────────┼────────────────────────────┐
       ▼                            ▼                            ▼
┌──────────────┐             ┌──────────────┐             ┌──────────────┐
│  Business &  │             │Architecture &│             │   Testing,   │
│   Product    │             │ Engineering  │             │   Security & │
│              │             │              │             │  Operations  │
└──────────────┘             └──────────────┘             └──────────────┘
```

---

### 1. Business & Product Strategy
* 📄 **[BRD.md](BRD.md) — Business Requirements Document:** The business case, market opportunity, problem statements, customer personas, business goals, and ROI.
* 📄 **[PRD.md](PRD.md) — Product Requirements Document:** Functional product specifications, user stories, tool capabilities, and feature acceptance criteria.
* 📄 **[SALES_PITCH.md](SALES_PITCH.md) — Product & Commercial Pitch:** Commercialization strategy, monetization models (B2B SaaS, affiliate attribution), and value proposition.
* 📄 **[COMPETITIVE_AND_MARKET_CONTEXT.md](COMPETITIVE_AND_MARKET_CONTEXT.md) — Market Landscape:** Market analysis, comparison matrix against traditional chatbots and web scrapers, and strategic positioning.
* 📄 **[PRODUCT_SCOPE.md](PRODUCT_SCOPE.md) — Product Scope & MVP Boundaries:** Quick-scan matrix of implemented features, partially implemented components, and explicit non-goals.

---

### 2. Architecture & Technical Design
* 📄 **[SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) — System Architecture:** C4 context diagram, component architecture, request/response lifecycle, and sequence diagrams.
* 📄 **[TECHNICAL_DESIGN.md](TECHNICAL_DESIGN.md) — Technical Design:** Low-level implementation details, module responsibilities, Pydantic V2 schemas, normalization logic, and caching.
* 📄 **[SRS.md](SRS.md) — Software Requirements Specification:** Formal IEEE-compliant functional (`FR-001`..`FR-015`) and non-functional (`NFR-001`..`NFR-008`) requirements.
* 📄 **[WORKFLOW.md](WORKFLOW.md) — End-to-End System Workflows:** Detailed execution flow from user intent to upstream JSON-RPC responses, including boot-time pre-warming.
* 📄 **[ADR.md](ADR.md) — Architecture Decision Records:** Key architectural choices (`ADR-001` to `ADR-008`), trade-offs, and rejected alternatives.

---

### 3. MCP Technical Specification & User Journeys
* 📄 **[MCP_SPECIFICATION.md](MCP_SPECIFICATION.md) — Model Context Protocol Contract:** Technical interface contract for all 6 exposed tools, JSON schemas, examples, and error behaviors.
* 📄 **[USER_JOURNEYS_AND_USE_CASES.md](USER_JOURNEYS_AND_USE_CASES.md) — User Journeys & Use Cases:** Formal use cases (`UC-001` to `UC-006`), flows, preconditions, and mapped tools.

---

### 4. Quality, Verification & Traceability
* 📄 **[TESTING.md](TESTING.md) — Testing Strategy & Results:** Test architecture, 69 passing test cases (`TC-001` to `TC-015`), regression methodology, and live smoke tests.
* 📄 **[TRACEABILITY_MATRIX.md](TRACEABILITY_MATRIX.md) — Requirements Traceability Matrix:** Bidirectional traceability mapping `BR` → `PR` → `FR` → Code → MCP Tool → `TC`.
* 📄 **[KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) — Known System Limitations:** Professional engineering disclosure of upstream taxonomy quirks, cart limitations, and prototype boundaries.

---

### 5. Security, Deployment & Operations
* 📄 **[SECURITY.md](SECURITY.md) — Security Architecture & Threat Model:** STRIDE threat analysis, implemented security controls, egress whitelisting, and future hardening.
* 📄 **[DEPLOYMENT.md](DEPLOYMENT.md) — Deployment & Operations Guide:** Step-by-step local workstation installation, Claude Desktop configuration, and Render cloud deployment.

---

### 6. Hackathon Evaluation & Presentation
* 📄 **[HACKATHON_REQUIREMENT_MAPPING.md](HACKATHON_REQUIREMENT_MAPPING.md) — Rubric Alignment:** Direct line-by-line mapping of the repository deliverables to the hackathon judging criteria.
* 📄 **[DEMO_GUIDE.md](DEMO_GUIDE.md) — Live Demonstration Script:** Judge-facing 3-minute presentation script with exact prompts, live tool behaviors, and talking points.
* 📄 **[FUTURE_SCOPE.md](FUTURE_SCOPE.md) — Product Roadmap:** 3-tier roadmap spanning Near-Term, Medium-Term, and Long-Term commercial evolution.
* 📄 **[RELEASE_NOTES.md](RELEASE_NOTES.md) — Release Notes v2.0.0:** Production release summary highlighting new tools, bug fixes, and performance benchmarks.

---

## 📖 Master Glossary

| Term | Definition |
|---|---|
| **MCP** | Model Context Protocol — open standard introduced by Anthropic for connecting AI models to live external tools and contextual data sources. |
| **MCP Server** | The backend service (in this project, `joyory-product-mcp`) that publishes tools and responds to JSON-RPC requests over Streamable HTTP. |
| **MCP Host / Client**| The user-facing AI application (Claude Desktop, Claude.ai, ChatGPT) that orchestrates conversation and invokes MCP tools. |
| **Tool** | A callable function exposed by the MCP server with a defined JSON schema, inputs, outputs, and side-effect guarantees. |
| **Streamable HTTP** | The modern MCP transport protocol operating over standard HTTP (`/mcp`), enabling cloud hosting and remote AI client access. |
| **Adapter Pattern** | Object-oriented design pattern decoupling upstream transport mechanisms (`httpx` REST vs Playwright browser) from tool business logic. |
| **INCI** | International Nomenclature of Cosmetic Ingredients — standardized scientific naming convention for cosmetic ingredients. |
| **BOGO** | "Buy One, Get One" — retail promotional mechanism dynamically discovered and applied by `get_offers`. |
| **TTL Cache** | Time-To-Live cache — thread-safe memory storage automatically expiring cached items after 600 seconds (10 minutes). |
