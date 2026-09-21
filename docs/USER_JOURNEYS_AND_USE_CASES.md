# User Journeys & Use Cases
## Project: Joyory Conversational Commerce MCP Connector
**Document Version:** 2.0  
**Target Audience:** Product Managers, QA Engineers, Hackathon Judges  

---

## 1. User Personas

### Persona 1: Ananya (The Skincare Specialist)
* **Demographics:** 26, Bengaluru. Knowledgeable about active ingredients (AHA/BHA, Niacinamide, Retinol).
* **Goals:** Finds targeted treatments matching her combination/acne-prone skin; validates full ingredient lists before buying.
* **Frustrations:** Brand marketing hides full INCI formulas behind generic buzzwords.

### Persona 2: Rohan (The Deal-Seeking Groomer)
* **Demographics:** 21, Pune. College student with budget constraints.
* **Goals:** Builds complete morning grooming kit under ₹1,000 using active coupon codes and BOGO promotions.
* **Frustrations:** Misses out on valid coupon codes buried in promotional emails.

### Persona 3: Meera (The Visual Makeup Shopper)
* **Demographics:** 30, Delhi. Shopper looking for specific lipstick and concealer shades for an upcoming wedding.
* **Goals:** Sees exact shade swatches, hex codes, and in-stock variants side-by-side.
* **Frustrations:** Product search returns foundation bottles when she is looking for liquid concealers.

---

## 2. Structured Use Cases

### UC-001: Intent-Driven Skincare Routine Consultation
* **Primary Persona:** Ananya
* **Mapped Tools:** `get_catalog_overview`, `search_products`, `get_product_details`
* **Preconditions:** AI Host has connected to Joyory MCP.
* **Main Flow:**
  1. Ananya prompts: *"I have combination skin and dark spots. Build me an AM routine under ₹1,200 with Vitamin C and SPF."*
  2. AI calls `get_catalog_overview()` to resolve categories `skin-serums-and-essences-serum` and `skin-sunscreen`.
  3. AI calls `search_products(query='vitamin c serum', max_price=600)` and `search_products(query='sunscreen', max_price=600)`.
  4. AI calls `get_product_details()` on the top serum to confirm it is fragrance-free.
  5. AI formats recommendations as visual cards with prices, ratings, and purchase links.
* **Alternative Flow (Stock-Out):** If the top serum is out of stock, AI invokes `get_similar_products(cheaper=True)` to replace it with an in-stock alternative.
* **Expected Outcome:** Ananya receives a medically sound, in-stock 2-step routine under ₹1,200 with direct Joyory links.

---

### UC-002: BOGO Deal Discovery & Routine Optimization
* **Primary Persona:** Rohan
* **Mapped Tools:** `get_offers`, `search_products`
* **Preconditions:** Joyory has active brand promotions.
* **Main Flow:**
  1. Rohan prompts: *"Are there any Buy 1 Get 1 Free deals active right now? What products can I get?"*
  2. AI calls `get_offers()`.
  3. AI discovers active BOGO for brand `aqualogica` with coupon code `GLOW`.
  4. AI executes `search_products(brand='aqualogica', limit=10)`.
  5. AI presents eligible Aqualogica products and explains how applying code `GLOW` at checkout gives the second item free.
* **Failure Flow:** If no BOGOs are active, AI falls back to price-capped collection deals (e.g. *"Under ₹799 Deals"*).
* **Expected Outcome:** Rohan discovers verified savings without hunting for third-party coupon codes.

---

### UC-003: Cosmetic Shade & Variant Verification
* **Primary Persona:** Meera
* **Mapped Tools:** `search_products`, `get_product_details`
* **Preconditions:** Product has multiple cosmetic shades.
* **Main Flow:**
  1. Meera asks: *"What shades are available for Swiss Beauty Liquid Concealer, and which ones are in stock?"*
  2. AI executes `search_products(query='Swiss Beauty Liquid Concealer')`.
  3. AI takes the returned product ID and invokes `get_product_details(product_ids=[id])`.
  4. Server extracts the `variants` list containing shade names, hex codes, and live inventory.
  5. AI displays each shade name with hex color indicator and stock availability.
* **Expected Outcome:** Meera sees exactly which shades are purchasable without loading a heavy web application.

---

### UC-004: Cheaper Alternative / "Dupe" Discovery
* **Primary Persona:** Rohan / Ananya
* **Mapped Tools:** `get_similar_products`, `get_reviews`
* **Preconditions:** Shopper finds an expensive product and desires a budget equivalent.
* **Main Flow:**
  1. User prompts: *"I like the Plum 15% Vitamin C serum at ₹583. Is there a cheaper option that still has good reviews?"*
  2. AI calls `get_similar_products(product_id='...', cheaper=True)`.
  3. Server locates items in category `skin-serums-and-essences-serum` with `price < 583`.
  4. AI checks `get_reviews()` on the candidate to verify customer satisfaction.
  5. AI presents the alternative product highlighting cost savings.
* **Expected Outcome:** Immediate discovery of an authentic, lower-priced alternative.

---

### UC-005: Clinical Ingredient Cross-Examination
* **Primary Persona:** Ananya
* **Mapped Tools:** `get_product_details`
* **Preconditions:** User has specific allergen restrictions (e.g., essential oils, synthetic dyes).
* **Main Flow:**
  1. Ananya prompts: *"Does the Dot & Key Retinol Eye Cream contain synthetic fragrance or parabens?"*
  2. AI executes `get_product_details()` for the product.
  3. Tool returns parsed `inci_complete` and boolean `fragrance_free` flags.
  4. AI parses the full chemical formula and answers with 100% factual accuracy.
* **Expected Outcome:** Zero clinical hallucinations; customer avoids an allergic reaction.

---

### UC-006: Brand Catalog Pagination & Discovery
* **Primary Persona:** General Shopper
* **Mapped Tools:** `search_products`
* **Main Flow:**
  1. User prompts: *"Show me all products made by Kiro Beauty on Joyory."*
  2. AI executes `search_products(brand='kiro-beauty', limit=50)`.
  3. Server passes `brandIds=kiro-beauty` to Joyory backend.
  4. Server returns complete list of all 29 Kiro Beauty catalog items with `has_more=false`.
* **Expected Outcome:** Full catalog transparency without 20-item arbitrary truncation.
