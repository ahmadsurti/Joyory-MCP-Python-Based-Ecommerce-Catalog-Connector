"""
Core discovery logic — launched by scripts/discover_joyory.py.

Uses Playwright to browse Joyory, captures all network requests,
scores them, and writes config/joyory_source.json.
"""

from __future__ import annotations
import asyncio
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, parse_qs

from joyory_mcp.discovery.scoring import (
    rank_candidates,
    detect_product_count,
    infer_query_params,
    classify_endpoint,
)
from joyory_mcp import config as cfg

log = logging.getLogger(__name__)

BASE_URL = cfg.BASE_URL
ARTIFACT_DIR = Path("artifacts/discovery")
JSON_DIR = ARTIFACT_DIR / "json_responses"
SCREENSHOT_DIR = ARTIFACT_DIR / "screenshots"

TEST_QUERIES = ["lipstick", "vitamin c serum", "foundation"]
CATEGORY_URLS = [
    f"{BASE_URL}/category/makeup/face",
    f"{BASE_URL}/category/skin",
    f"{BASE_URL}/Products/category/fragrances",
]


async def run_discovery(headless: bool = True) -> dict:
    """
    Full discovery run. Returns a joyory_source config dict.
    """
    from playwright.async_api import async_playwright

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    all_candidates: list[dict] = []
    network_log: list[dict] = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=headless,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )

        # ── STEP 1: Homepage ──────────────────────────────────────────────────
        log.info("Opening Joyory homepage...")
        page = await context.new_page()
        candidates_from_page: list[dict] = []

        def make_response_handler(trigger_name: str):
            async def handler(response):
                try:
                    await _capture_response(
                        response, trigger_name,
                        candidates_from_page, network_log,
                    )
                except Exception:
                    pass
            return handler

        page.on("response", make_response_handler("pageload"))

        try:
            await page.goto(BASE_URL, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            await page.screenshot(path=str(SCREENSHOT_DIR / "01_homepage.png"))
            log.info("Homepage loaded")
        except Exception as e:
            log.warning(f"Homepage load error: {e}")

        all_candidates.extend(candidates_from_page)
        candidates_from_page.clear()

        # ── STEP 2: Category pages ────────────────────────────────────────────
        for i, cat_url in enumerate(CATEGORY_URLS):
            page.on("response", make_response_handler("category"))
            log.info(f"Visiting category: {cat_url}")
            try:
                await page.goto(cat_url, timeout=20000, wait_until="domcontentloaded")
                await page.wait_for_timeout(3000)
                await page.screenshot(path=str(SCREENSHOT_DIR / f"02_category_{i}.png"))
            except Exception as e:
                log.warning(f"Category error {cat_url}: {e}")
            all_candidates.extend(candidates_from_page)
            candidates_from_page.clear()

        # ── STEP 3: Search queries ────────────────────────────────────────────
        for qi, query in enumerate(TEST_QUERIES):
            log.info(f"Searching for: {query}")
            page.on("response", make_response_handler("search"))

            try:
                # Try search box first
                await page.goto(BASE_URL, timeout=20000, wait_until="domcontentloaded")
                await page.wait_for_timeout(1500)

                search_selectors = [
                    'input[type="search"]',
                    'input[placeholder*="Search" i]',
                    'input[name="search"]',
                    'input[name="q"]',
                    '#search',
                    '.search-input',
                    '[data-testid*="search" i]',
                    'input[type="text"]',
                ]

                typed = False
                for sel in search_selectors:
                    try:
                        el = page.locator(sel).first
                        if await el.is_visible(timeout=2000):
                            await el.click()
                            await el.fill(query)
                            await page.keyboard.press("Enter")
                            await page.wait_for_timeout(4000)
                            typed = True
                            break
                    except Exception:
                        continue

                if not typed:
                    # Fall back to direct URL
                    for search_url in [
                        f"{BASE_URL}/search?q={query.replace(' ', '+')}",
                        f"{BASE_URL}/search?query={query.replace(' ', '+')}",
                        f"{BASE_URL}/search/{query.replace(' ', '+')}",
                    ]:
                        try:
                            await page.goto(search_url, timeout=15000, wait_until="domcontentloaded")
                            await page.wait_for_timeout(3000)
                            if candidates_from_page:
                                break
                        except Exception:
                            continue

                await page.screenshot(path=str(SCREENSHOT_DIR / f"03_search_{qi}_{query.replace(' ', '_')}.png"))

            except Exception as e:
                log.warning(f"Search error for '{query}': {e}")

            all_candidates.extend(candidates_from_page)
            candidates_from_page.clear()

        # ── STEP 4: Click a product ───────────────────────────────────────────
        log.info("Attempting to click a product...")
        page.on("response", make_response_handler("product"))
        try:
            product_link_selectors = [
                "a[href*='/product/']",
                "a[href*='/products/']",
                "a[href*='/p/']",
                "[class*='product-card'] a",
                "[class*='ProductCard'] a",
                "[data-product-id] a",
            ]
            clicked = False
            for sel in product_link_selectors:
                try:
                    el = page.locator(sel).first
                    if await el.is_visible(timeout=2000):
                        href = await el.get_attribute("href")
                        if href:
                            product_url = href if href.startswith("http") else BASE_URL + href
                            await page.goto(product_url, timeout=15000, wait_until="domcontentloaded")
                            await page.wait_for_timeout(3000)
                            await page.screenshot(path=str(SCREENSHOT_DIR / "04_product.png"))
                            clicked = True
                            break
                except Exception:
                    continue

            if not clicked:
                log.info("Could not click a product automatically")

        except Exception as e:
            log.warning(f"Product click error: {e}")

        all_candidates.extend(candidates_from_page)
        candidates_from_page.clear()

        await browser.close()

    # ── Score and rank ────────────────────────────────────────────────────────
    ranked = rank_candidates(all_candidates)

    # Save artifacts
    _save_network_log(network_log)
    _save_candidates(ranked)

    # Save individual JSON responses
    for i, c in enumerate(ranked[:30]):
        body = c.get("response_body")
        if body:
            fname = JSON_DIR / f"candidate_{i:02d}_{c['score']}.json"
            try:
                fname.write_text(json.dumps(body, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception:
                pass

    # ── Build source config ───────────────────────────────────────────────────
    source_config = _build_source_config(ranked)

    return source_config


async def _capture_response(
    response,
    trigger: str,
    candidates: list,
    network_log: list,
) -> None:
    url = response.url
    method = response.request.method
    status = response.status
    content_type = response.headers.get("content-type", "")

    # Skip obvious non-data requests
    skip_extensions = (".css", ".js", ".woff", ".woff2", ".ttf", ".png", ".jpg",
                       ".jpeg", ".gif", ".svg", ".ico", ".map", ".webp")
    url_lower = url.lower()
    if any(url_lower.endswith(ext) or f"{ext}?" in url_lower for ext in skip_extensions):
        return

    skip_keywords = ["analytics", "telemetry", "/gtm", "googletagmanager",
                     "facebook.com", "hotjar", "clarity.ms", "doubleclick"]
    if any(k in url_lower for k in skip_keywords):
        return

    # Log everything
    log_entry = {
        "url": url,
        "method": method,
        "status": status,
        "content_type": content_type,
        "trigger": trigger,
    }

    # Only parse JSON for XHR/fetch (not navigations)
    response_body = None
    if "json" in content_type and status == 200:
        try:
            response_body = await response.json()
            log_entry["has_json"] = True
        except Exception:
            pass

    network_log.append(log_entry)

    # Only add to candidates if potentially useful
    if "json" in content_type or any(k in url_lower for k in ["api", "product", "search", "catalog"]):
        # Extract query params
        parsed = urlparse(url)
        params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        path = parsed.path

        candidate = {
            "url": url,
            "path": path,
            "method": method,
            "status": status,
            "content_type": content_type,
            "trigger": trigger,
            "params": params,
            "response_body": response_body,
        }
        candidates.append(candidate)


def _save_network_log(network_log: list) -> None:
    log_path = ARTIFACT_DIR / "network.log"
    with open(log_path, "w", encoding="utf-8") as f:
        for entry in network_log:
            f.write(json.dumps(entry) + "\n")
    log.info(f"Network log saved: {log_path} ({len(network_log)} entries)")


def _save_candidates(ranked: list) -> None:
    # Strip large response bodies for the summary file
    slim = []
    for c in ranked:
        body = c.get("response_body")
        product_count = detect_product_count(body) if body else 0
        slim.append({
            "url": c["url"],
            "method": c["method"],
            "status": c["status"],
            "trigger": c["trigger"],
            "score": c["score"],
            "product_count": product_count,
            "content_type": c.get("content_type", ""),
            "params": c.get("params", {}),
        })
    path = ARTIFACT_DIR / "api_candidates.json"
    path.write_text(json.dumps(slim, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info(f"Candidates saved: {path}")


def _build_source_config(ranked: list[dict]) -> dict:
    """Build joyory_source.json from the best-ranked candidates."""
    from joyory_mcp.normalize import extract_products_from_response

    search_candidate = None
    detail_candidate = None

    for c in ranked:
        if c["score"] < 20:
            continue
        endpoint_type = classify_endpoint(c)
        body = c.get("response_body")

        if endpoint_type == "search" and search_candidate is None:
            search_candidate = c
        elif endpoint_type == "detail" and detail_candidate is None:
            detail_candidate = c

        if search_candidate and detail_candidate:
            break

    # Fallback: top 2 by score for each role
    if not search_candidate and ranked:
        for c in ranked:
            if c["score"] > 0:
                search_candidate = c
                break

    # ── Build config dict ─────────────────────────────────────────────────────
    config: dict = {
        "base_url": BASE_URL,
        "adapter": "api",
        "discovered_at": datetime.now(timezone.utc).isoformat(),
        "confidence": {
            "search": search_candidate["score"] if search_candidate else 0,
            "product": detail_candidate["score"] if detail_candidate else 0,
        },
    }

    if search_candidate:
        parsed = urlparse(search_candidate["url"])
        params = search_candidate.get("params", {})
        qp_map = infer_query_params(search_candidate["url"], params)
        config["search"] = {
            "method": search_candidate["method"],
            "url": parsed.path,
            "query_parameters": qp_map or {"query": "q", "limit": "limit"},
            "_full_url_example": search_candidate["url"],
        }
    else:
        # Safe default
        config["search"] = {
            "method": "GET",
            "url": "/search",
            "query_parameters": {"query": "q", "limit": "limit"},
        }
        config["adapter"] = "browser"  # Fall back to browser

    if detail_candidate:
        parsed = urlparse(detail_candidate["url"])
        # Try to generalize the URL template
        path = _generalize_product_path(parsed.path)
        config["product_details"] = {
            "method": detail_candidate["method"],
            "url_template": path,
            "_example_url": detail_candidate["url"],
        }
    else:
        config["product_details"] = {
            "method": "GET",
            "url_template": "/product/{id}",
        }

    return config


def _generalize_product_path(path: str) -> str:
    """Replace the last path segment (assumed to be the product ID) with {id}."""
    parts = path.rstrip("/").split("/")
    if len(parts) > 1:
        # If last segment looks like an ID or slug
        last = parts[-1]
        if re.search(r"\d", last) or "-" in last or "_" in last:
            parts[-1] = "{id}"
    return "/".join(parts)


def print_discovery_report(source_config: dict, ranked: list[dict]) -> None:
    """Print a human-readable discovery report to stdout."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()

    console.print()
    console.print(Panel.fit(
        "[bold cyan]JOYORY API DISCOVERY[/bold cyan]",
        border_style="cyan",
    ))

    # Top candidates table
    table = Table(title="Top API Candidates", show_lines=True)
    table.add_column("Rank", style="bold", width=5)
    table.add_column("Score", style="cyan", width=7)
    table.add_column("Trigger", width=10)
    table.add_column("Method", width=7)
    table.add_column("Products", width=9)
    table.add_column("URL", overflow="fold")

    from joyory_mcp.normalize import extract_products_from_response
    for i, c in enumerate(ranked[:10]):
        body = c.get("response_body")
        pc = detect_product_count(body) if body else 0
        table.add_row(
            str(i + 1),
            str(c["score"]),
            c.get("trigger", ""),
            c.get("method", ""),
            str(pc),
            c["url"][:80],
        )
    console.print(table)

    # Recommendations
    console.print()
    console.print("[bold green]RECOMMENDED CONFIGURATION[/bold green]")

    search_cfg = source_config.get("search", {})
    detail_cfg = source_config.get("product_details", {})
    conf = source_config.get("confidence", {})
    adapter = source_config.get("adapter", "browser")

    console.print(f"\nAdapter:        [bold]{adapter}[/bold]")
    console.print(f"Search endpoint: {search_cfg.get('method')} {search_cfg.get('_full_url_example', search_cfg.get('url'))}")
    console.print(f"Search confidence: [bold]{conf.get('search', 0)}/100[/bold]")
    console.print(f"Detail endpoint: {detail_cfg.get('method')} {detail_cfg.get('url_template')}")
    console.print(f"Detail confidence: [bold]{conf.get('product', 0)}/100[/bold]")

    console.print()
    console.print("[bold yellow]Saved:[/bold yellow]  config/joyory_source.json")
    console.print("[bold yellow]Logs:[/bold yellow]   artifacts/discovery/")
    console.print()
    console.print("[bold]Next step:[/bold]")
    console.print("  python scripts/test_joyory_source.py")
    console.print()
