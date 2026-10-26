"""Configuration management for Joyory MCP server."""

import json
import os
import warnings
from pathlib import Path
from dotenv import load_dotenv

# Suppress opentelemetry/logfire version-mismatch warning that fires during pydantic import.
# logfire is a transitive dep — it fails to load its pydantic plugin when opentelemetry
# packages are on mismatched versions. This is harmless; we don't use logfire.
# ponytail: suppress here (earliest import) so it never reaches the terminal.
warnings.filterwarnings("ignore", message=".*logfire.*", category=UserWarning)
warnings.filterwarnings("ignore", message=".*ImportError.*", category=UserWarning)

load_dotenv()

# ── Environment-driven settings ──────────────────────────────────────────────

BASE_URL: str = os.getenv("JOYORY_BASE_URL", "https://joyory.com").rstrip("/")
TIMEOUT_SECONDS: float = float(os.getenv("JOYORY_TIMEOUT_SECONDS", "20"))
CACHE_TTL_SECONDS: int = int(os.getenv("JOYORY_CACHE_TTL_SECONDS", "600"))
MAX_RESULTS: int = int(os.getenv("JOYORY_MAX_RESULTS", "100"))
BROWSER_HEADLESS: bool = os.getenv("JOYORY_BROWSER_HEADLESS", "true").lower() == "true"
SOURCE_CONFIG_PATH: str = os.getenv("JOYORY_SOURCE_CONFIG", "config/joyory_source.json")
MCP_HOST: str = os.getenv("MCP_HOST", "0.0.0.0" if os.getenv("RENDER") or os.getenv("PORT") else "127.0.0.1")
# Render sets PORT; fall back to MCP_PORT for local dev.
MCP_PORT: int = int(os.getenv("PORT", os.getenv("MCP_PORT", "8000")))

# Beauty API — separate backend host for product/catalog/review/offer APIs
BEAUTY_BASE_URL: str = "https://beauty.joyory.com"
BEAUTY_HEADERS: dict = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, */*",
    "Referer": "https://joyory.com/",
}

# Allowed outbound hosts (security: restrict to joyory.com only)
ALLOWED_HOSTS: set[str] = {"joyory.com", "www.joyory.com", "beauty.joyory.com", "res.cloudinary.com"}

# Default source config used when config/joyory_source.json cannot be read from disk (e.g. serverless)
DEFAULT_SOURCE_CONFIG: dict = {
    "base_url": "https://beauty.joyory.com",
    "adapter": "api",
    "search": {
        "method": "GET",
        "url": "/api/user/products/all",
        "query_parameters": {
            "query": "search",
            "limit": "limit",
            "page": "cursor",
            "min_price": "minPrice",
            "max_price": "maxPrice",
            "brand": "brandIds",
            "category": "categoryIds",
        },
    },
    "product_details": {
        "method": "GET",
        "url_template": "/api/user/products/{id}",
    },
    "categories": {
        "method": "GET",
        "url": "/api/user/categories/tree",
    },
    "brands": {
        "method": "GET",
        "url": "/api/user/brands",
    },
    "reviews": {
        "method": "GET",
        "url_template": "/api/reviews/product/{id}",
        "query_parameters": {"limit": "limit", "page": "page"},
    },
    "promotions": {
        "method": "GET",
        "url": "/api/user/promotions/active",
        "query_parameters": {"section": "section"},
    },
}


def load_source_config() -> dict:
    """Load joyory_source.json if it exists, otherwise fall back to DEFAULT_SOURCE_CONFIG."""
    candidates = [
        Path(SOURCE_CONFIG_PATH),
        Path(__file__).parent.parent.parent / SOURCE_CONFIG_PATH,
        Path.cwd() / SOURCE_CONFIG_PATH,
        Path(__file__).parent.parent / SOURCE_CONFIG_PATH,
    ]
    for p in candidates:
        if p.exists():
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass
    return DEFAULT_SOURCE_CONFIG


def save_source_config(config: dict) -> None:
    """Save discovery results to joyory_source.json."""
    p = Path(SOURCE_CONFIG_PATH)
    if not p.is_absolute():
        project_root = Path(__file__).parent.parent.parent
        p = project_root / SOURCE_CONFIG_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
