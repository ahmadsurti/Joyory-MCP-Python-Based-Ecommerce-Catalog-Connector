"""
scripts/discover_joyory.py
==========================
Launch Playwright, browse Joyory, capture network traffic,
score API candidates, and write config/joyory_source.json.

Usage:
    python scripts/discover_joyory.py
    python scripts/discover_joyory.py --visible   # show browser window
"""

import sys
import asyncio
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from joyory_mcp.discovery.discover import run_discovery, print_discovery_report
from joyory_mcp.discovery.scoring import rank_candidates
from joyory_mcp import config as cfg


async def main(visible: bool = False):
    headless = not visible

    print("\n" + "=" * 60)
    print("  JOYORY API DISCOVERY")
    print("=" * 60)
    print(f"  Target: {cfg.BASE_URL}")
    print(f"  Browser: {'visible' if visible else 'headless'}")
    print("  This will take ~60 seconds...")
    print("=" * 60 + "\n")

    source_config = await run_discovery(headless=headless)

    # Load ranked candidates for the report
    import json
    candidates_path = Path("artifacts/discovery/api_candidates.json")
    ranked = []
    if candidates_path.exists():
        candidates = json.loads(candidates_path.read_text())
        # Re-score with response bodies from json_responses/
        ranked = candidates  # already ranked (no bodies in slim format)

    # Print report
    print_discovery_report(source_config, ranked)

    # Save config
    cfg.save_source_config(source_config)

    adapter = source_config.get("adapter", "api")
    confidence_search = source_config.get("confidence", {}).get("search", 0)

    if confidence_search >= 50:
        print(f"\n✅ Discovery succeeded! Adapter: {adapter}")
        print("   Run: python scripts/test_joyory_source.py")
    elif confidence_search >= 20:
        print(f"\n⚠️  Low-confidence discovery. Adapter: {adapter}")
        print("   Will use browser fallback for live queries.")
        print("   Run: python scripts/test_joyory_source.py")
    else:
        print("\n⚠️  No clean API found. Using browser fallback adapter.")
        print("   This is slower but should still work.")
        print("   Run: python scripts/test_joyory_source.py")

    return source_config


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--visible", action="store_true", help="Show browser window")
    args = parser.parse_args()

    asyncio.run(main(visible=args.visible))
