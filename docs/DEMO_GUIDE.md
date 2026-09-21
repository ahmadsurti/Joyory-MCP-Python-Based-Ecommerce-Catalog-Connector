# Live Demonstration & Presentation Guide
## Project: Joyory Conversational Commerce MCP Connector
**Target Audience:** Hackathon Judges, Presenters, Evaluators  
**Estimated Demo Duration:** 3–5 Minutes  

---

## 1. Demo Objective

To demonstrate to judges that Joyory MCP is not a mock concept, but a **fully functioning, live Model Context Protocol server** connected directly to Joyory's live product database. The demo proves that an AI assistant (Claude/ChatGPT) can intelligently discover products, verify ingredients, compare shades, apply active coupons, and find cheaper alternatives in real time without human data fabrication.

---

## 2. Prerequisites & Setup

### Option A: Cloud / Remote Demo (Recommended)
1. Deploy to Render or use your active public tunnel URL: `https://your-service.onrender.com/mcp`
2. Connect to Claude.ai or Claude Desktop via Streamable HTTP.

### Option B: Local Workstation Demo
1. Terminal 1: Ensure server is running:
   ```bash
   python server.py
   ```
2. Verify log: `[INFO] Joyory MCP on http://127.0.0.1:8000/mcp`
3. Open Claude Desktop or your connected AI client.

---

## 3. Step-by-Step Live Demo Script

### Act 1: The Complex Clinical Inquiry (Ingredient & Price Bounding)
* **Goal:** Show that the AI doesn't hallucinate and accurately filters live inventory.
* **Presenter Action:** Paste the following prompt into Claude:
  ```text
  I have sensitive, acne-prone skin. Show me 2 fragrance-free sunscreens from The Derma Co under ₹500 with pictures and links.
  ```
* **Behind the Scenes:**
  * Claude calls `search_products(brand="the-derma-co", query="sunscreen", max_price=500, include_images=true)`.
  * MCP server filters out items above ₹500, validates brand slug `the-derma-co`, and returns live products with verified Cloudinary image URLs.
* **Talking Point for Judges:**
  > *"Notice how Claude didn't guess the price or recommend a random US brand. It queried Joyory's live catalog, enforced the ₹500 ceiling in Indian Rupees, and pulled real product URLs directly from the server."*

---

### Act 2: Clinical Ingredient Cross-Examination
* **Goal:** Show deep product attribute inspection (`get_product_details`).
* **Presenter Action:** Paste:
  ```text
  Compare the full ingredient lists and SPF ratings of those two side by side. Are they really 100% fragrance-free?
  ```
* **Behind the Scenes:**
  * Claude invokes `get_product_details(product_ids=[id1, id2])`.
  * MCP server returns complete INCI ingredient arrays and structured attribute flags.
* **Talking Point for Judges:**
  > *"Instead of hallucinating ingredients, the MCP server returned the actual clinical formula. The AI can confirm exact active percentages and verify fragrance-free claims from real packaging data."*

---

### Act 3: Deal Hunting & BOGO Orchestration
* **Goal:** Demonstrate commercial merchandising intelligence (`get_offers` + `search_products`).
* **Presenter Action:** Paste:
  ```text
  Are there any active Buy 1 Get 1 Free (BOGO) deals right now? If so, what is the coupon code and what products can I buy with it?
  ```
* **Behind the Scenes:**
  * Claude calls `get_offers()`.
  * Server returns active Aqualogica BOGO with coupon code `GLOW`.
  * Claude automatically chains `search_products(brand="aqualogica", limit=5)`.
* **Talking Point for Judges:**
  > *"The MCP server doesn't just search products—it is commercially aware. It queried Joyory's live promotions engine, retrieved coupon code GLOW, and chained a secondary search to present qualifying products."*

---

### Act 4: The Budget "Dupe" Finder
* **Goal:** Show automated alternative discovery (`get_similar_products`).
* **Presenter Action:** Paste:
  ```text
  Find me a cheaper in-stock alternative for the top sunscreen you showed earlier.
  ```
* **Behind the Scenes:**
  * Claude calls `get_similar_products(product_id="...", cheaper=true, in_stock_only=true)`.
  * Server locates items in the same category with `price < source_price`.
* **Talking Point for Judges:**
  > *"When a customer hits price resistance or a stock-out, the server algorithmically identifies relevant alternatives in the same category that cost less."*

---

## 4. Standalone Fallback Demonstration (Zero-Risk Backup)

If internet connectivity or conference Wi-Fi is compromised, you can execute the entire demonstration directly from the command line using the local offline verification script:

```bash
python scripts/demo.py
```
*This interactive script tests and displays live JSON responses, timing benchmarks, and colored output for all 6 MCP tools without needing an active Claude session.*
