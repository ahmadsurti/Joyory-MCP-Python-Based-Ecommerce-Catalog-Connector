# Business Requirements Document (BRD)
## Project: Joyory Conversational Commerce MCP Connector
**Document Version:** 2.0  
**Project Status:** Working Hackathon Prototype  
**Date:** September 2026  
**Target Audience:** Hackathon Judges, Business Stakeholders, Product Leadership  

---

## 1. Executive Summary

Joyory (https://joyory.com) is an Indian e-commerce retailer specializing in beauty, personal care, and wellness products. In modern digital commerce, beauty shopping exhibits uniquely high cognitive overhead: consumers do not merely search for "shampoo" or "lipstick"; they seek tailored solutions addressing specific skin concerns (e.g., hyperpigmentation, acne-prone skin), ingredient safety (e.g., fragrance-free, niacinamide, SPF coverage), price-to-volume valuation, and active promotional benefits (BOGOs).

The **Joyory Model Context Protocol (MCP) Connector** is a lightweight, read-only integration layer that bridges conversational AI agents (such as Anthropic Claude and OpenAI ChatGPT) directly with Joyory’s live product catalog. By implementing the open standard Model Context Protocol (MCP 2.x Streamable HTTP), the system transforms static e-commerce catalog data into an interactive, conversational shopping assistant. Shoppers can perform natural-language queries, cross-examine ingredient formulations, compare alternatives, and unlock real-time promotional discounts without manual website navigation.

---

## 2. Business Problem & Market Need

### 2.1 The Current E-Commerce Friction
Traditional e-commerce discovery relies on rigid keyword search and static faceted filters. In beauty e-commerce, this creates significant friction:
1. **Search Disconnect:** A user searching for *"something soothing for irritated barrier with ceramides under ₹500"* is typically met with empty search results or irrelevant keyword hits on conventional retail storefronts.
2. **High Cognitive Overhead:** Customers must manually open 5–10 browser tabs, cross-reference INCI ingredient lists, calculate price-per-ml, and verify whether a product is currently in stock.
3. **Cart Abandonment:** Customers frequently abandon sessions due to choice paralysis and uncertainty over product compatibility with their skin type.
4. **Opaque Promotions:** Active brand promotions, price-capped collections, and "Buy 1 Get 1 Free" (BOGO) deals are often buried on banner carousels, failing to influence purchase decisions at the moment of discovery.

### 2.2 The AI Assistant Problem (The "Blind Assistant")
Modern consumers increasingly turn to AI assistants like Claude and ChatGPT for personalized skincare advice and product recommendations. However, general-purpose LLMs suffer from critical limitations:
* **Zero Real-Time Catalog Visibility:** LLMs have no access to live inventory, current Indian Rupee (INR) pricing, or variant stock levels.
* **Hallucination Risk:** When asked for specific products, standard LLMs frequently fabricate nonexistent shades, discontinued formulations, or wrong prices.
* **Broken Conversion Funnel:** Even when recommendations are accurate, the AI cannot provide verified direct purchase links to active inventory.

---

## 3. Market Opportunity

By positioning Joyory as a first-class tool provider within the Model Context Protocol ecosystem:
* **First-Mover Advantage in Agentic Commerce:** As consumers shift from web browsing to conversational AI interfaces, brands offering native MCP endpoints become the default recommendation destination.
* **Zero Frontend Cost:** Leverages existing AI client interfaces (Claude Desktop, Claude.ai, ChatGPT) without requiring Joyory to develop, host, or maintain custom chat UI infrastructure.
* **Higher Conversion Intent:** Conversational product discovery delivers pre-qualified buyers directly to product detail pages with verified pricing and clear promotional codes.

---

## 4. Stakeholders & Personas

### 4.1 Key Stakeholders
| Stakeholder Group | Interest & Expectations |
|---|---|
| **E-Commerce Operations** | Zero impact on backend database loads; read-only operations with strict caching; zero checkout risk. |
| **Marketing & Merchandising** | Accurate promotion dissemination (active coupon codes, BOGOs); brand fidelity; verified product URLs. |
| **End Consumers** | Instant, trustworthy, personalized product discovery without manual filtering across dozens of pages. |
| **Hackathon Evaluation Panel** | Clear engineering discipline, architectural adherence to MCP standards, commercial viability, and functional prototype. |

### 4.2 Target Personas

#### Persona A: The Solution-Oriented Shopper ("Skincare Enthusiast Ananya")
* **Profile:** 26-year-old professional with sensitive, combination skin.
* **Behavior:** Researches active ingredients (salicylic acid, centella), checks SPF ratings, and seeks cruelty-free options.
* **Pain Point:** Exhausted by reading 20-ingredient chemical lists across multiple product detail pages.
* **Desired Experience:** *"Recommend a fragrance-free daily moisturizer under ₹600 that works well with vitamin C."*

#### Persona B: The Budget Deal Hunter ("College Student Rohan")
* **Profile:** 21-year-old looking for grooming essentials under a strict monthly budget.
* **Behavior:** Maximizes volume and active promotions; looks for Buy-1-Get-1 offers and bundle deals.
* **Pain Point:** Misses out on coupon codes and struggles to compare unit costs (price per 100ml).
* **Desired Experience:** *"What active BOGO offers exist right now, and what are the cheapest face washes I can get?"*

---

## 5. Business Goals & Objectives

| ID | Business Goal | Metric / Target |
|---|---|---|
| **BG-01** | **Eliminate AI Hallucination in Catalog Search** | 100% of returned products, prices, and stock statuses must originate from live Joyory data. |
| **BG-02** | **Streamline Product Evaluation** | Reduce time required to evaluate multi-product ingredient compatibility from ~15 minutes to under 30 seconds. |
| **BG-03** | **Promote Active Merchandising Campaigns** | Automatically inject valid promotional codes (e.g., Aqualogica BOGO `GLOW`) into conversational buying journeys. |
| **BG-04** | **Zero Operational Footprint on Host Systems** | Employ edge TTL caching to ensure repeated conversational queries do not overload Joyory's primary backend. |
| **BG-05** | **Frictionless Integration** | Zero proprietary client apps required; 100% compatibility with standard MCP hosts via Streamable HTTP. |

---

## 6. Business Requirements

### 6.1 Core Discovery Requirements
* **BR-001 (Natural Language Product Discovery):** The system shall allow AI agents to translate consumer intent into structured product queries across Joyory's skincare, makeup, haircare, and wellness categories.
* **BR-002 (Parametric Filtering):** The business must support filtering by price ceilings/floors (INR), brand identity (slug-normalized), category classification, and live stock availability.
* **BR-003 (Catalog Transparency):** The AI assistant must have access to Joyory's complete, non-sampled category tree and brand directory to prevent false claims regarding product availability.

### 6.2 Product Intelligence Requirements
* **BR-004 (Formulation & Attribute Transparency):** The system shall expose structured skincare attributes—including full INCI ingredients, SPF ratings, fragrance-free flags, and skin-type suitability—to satisfy clinical consumer queries.
* **BR-005 (Variant & Shade Visibility):** For cosmetic products, the system shall expose complete variant records, including shade names, hex swatches, size configurations, and per-variant stock.
* **BR-006 (Social Proof Integration):** The system shall surface verified customer review counts and sentiment to assist the AI in qualifying product recommendations.
* **BR-007 (Budget Dupes & Alternatives):** The system shall enable automated discovery of similar or lower-priced alternative items within the same category to combat stock-outs and price resistance.

### 6.3 Commercial & Merchandising Requirements
* **BR-008 (Live Promotion Injection):** The system shall dynamically expose active brand promotions, price-capped collections (e.g., Under ₹799), and coupon codes directly to conversational agents.
* **BR-009 (Direct Conversion Linkage):** Every product returned must supply an authenticated canonical Joyory web URL to transition the conversational user directly into the Joyory purchase flow.
* **BR-010 (Client-Side Rendering Support):** The data contract must supply direct image URLs to support inline product card visualization within supporting AI clients.

---

## 7. Assumptions, Constraints & Risks

### 7.1 Assumptions
1. **Public Catalog Access:** Joyory's public catalog endpoints (`beauty.joyory.com`) remain accessible over HTTPS without requiring end-user authentication.
2. **Read-Only Scope:** Commercial purchases will continue to be executed on Joyory’s web storefront; no payment or personal data is collected or handled by this connector.
3. **Transport Protocol:** MCP hosts support the standard Model Context Protocol Streamable HTTP transport specification.

### 7.2 Constraints
1. **No Proprietary Database:** The system must function strictly as an in-flight gateway/adapter, maintaining no persistent consumer database to ensure compliance with privacy and data residency standards.
2. **Rate Limiting & Politeness:** Upstream calls to Joyory must be rate-conscious, employing in-memory TTL caching (10-minute validity) to prevent IP throttling.
3. **Cart Architecture:** Joyory’s shopping cart is client-side and authentication-gated; therefore, direct cart injection is out of scope. Direct canonical product links are mandatory.

### 7.3 Risk Assessment & Mitigation
| Risk | Impact | Likelihood | Mitigation Strategy |
|---|---|---|---|
| Upstream Joyory API schema changes | High | Low | Automated API discovery engine and resilient defensive normalization fallbacks. |
| Host client rate limits / IP blocks | Medium | Low | Centralized caching (`TTLCache`), batch detail fetching, and browser fallback adapter. |
| AI client renders plain text instead of cards | Low | Medium | Enhanced tool descriptions directing Claude/ChatGPT to utilize native product card presentation. |

---

## 8. Non-Goals (Explicit Out-of-Scope)
* **User Authentication & Payment Processing:** No storage of credit cards, UPI, or personal customer profiles.
* **Direct Order Creation:** All checkouts occur through Joyory’s official secure storefront.
* **Independent Chat Frontend:** The project will not build a custom React/Vue chatbot; it is designed purely as an open MCP backend for existing AI platforms.
