"""
scripts/test_joyory_source.py
==============================
Real smoke test that calls the discovered Joyory data source directly.

Usage:
    python scripts/test_joyory_source.py
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint

console = Console()


async def main():
    from joyory_mcp import config as cfg
    from joyory_mcp.tools.search import search_products
    from joyory_mcp.tools.details import get_product_details

    source_config = cfg.load_source_config()

    if not source_config:
        console.print("[bold red]ERROR:[/bold red] No config/joyory_source.json found.")
        console.print("Run: python scripts/discover_joyory.py")
        sys.exit(1)

    adapter_type = source_config.get("adapter", "api")
    console.print(f"\n[bold cyan]Joyory Source Test[/bold cyan]  adapter=[bold]{adapter_type}[/bold]")

    # ── Initialize adapter ────────────────────────────────────────────────────
    if adapter_type == "graphql":
        from joyory_mcp.adapters.graphql import GraphQLJoyoryDataSource
        adapter = GraphQLJoyoryDataSource(source_config)
    elif adapter_type == "browser":
        from joyory_mcp.adapters.browser import BrowserJoyoryDataSource
        adapter = BrowserJoyoryDataSource(source_config)
    else:
        from joyory_mcp.adapters.api import ApiJoyoryDataSource
        adapter = ApiJoyoryDataSource(source_config)

    test_queries = ["lipstick", "serum", "foundation"]
    first_id = None
    all_passed = True

    for query in test_queries:
        console.print(f"\n[bold]SEARCH:[/bold] '{query}' (limit=3)")
        result = await search_products(query, limit=3, adapter=adapter)

        if result.get("error"):
            console.print(f"[red]  ✗ Error: {result['error']}[/red]")
            all_passed = False
            continue

        count = result.get("count", 0)
        results = result.get("results", [])

        if count == 0:
            console.print(f"[yellow]  ⚠ No results for '{query}'[/yellow]")
            continue

        console.print(f"[green]  ✓ {count} result(s) returned[/green]")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", width=20, overflow="fold")
        table.add_column("Name", width=30, overflow="fold")
        table.add_column("Brand", width=15)
        table.add_column("Price ₹", width=10)
        table.add_column("Rating", width=8)
        table.add_column("Stock", width=7)

        for p in results:
            pid = p.get("id", "")
            if not first_id and pid and pid != "unknown":
                first_id = pid
            table.add_row(
                pid[:20],
                (p.get("name") or "")[:30],
                (p.get("brand") or "-")[:15],
                str(p.get("price") or "-"),
                str(p.get("rating") or "-"),
                "✓" if p.get("in_stock") else "?" if p.get("in_stock") is None else "✗",
            )
        console.print(table)

    # ── Detail test ───────────────────────────────────────────────────────────
    if first_id:
        console.print(f"\n[bold]DETAIL:[/bold] '{first_id}'")
        detail = await get_product_details(first_id, adapter=adapter)

        if detail.get("error"):
            console.print(f"[red]  ✗ Detail error: {detail['error']}[/red]")
            all_passed = False
        else:
            console.print(f"[green]  ✓ Detail retrieved[/green]")
            console.print(f"  Name:        {detail.get('name')}")
            console.print(f"  Brand:       {detail.get('brand')}")
            console.print(f"  Price:       ₹{detail.get('price')}")
            console.print(f"  Description: {str(detail.get('description') or '')[:80]}...")
            console.print(f"  Ingredients: {len(detail.get('ingredients', []))} items")
            console.print(f"  Images:      {len(detail.get('images', []))}")
            console.print(f"  Variants:    {len(detail.get('variant_information', []))}")
    else:
        console.print("\n[yellow]⚠ No product ID found to test detail endpoint.[/yellow]")

    # ── Invalid ID test ───────────────────────────────────────────────────────
    console.print("\n[bold]INVALID ID TEST:[/bold] 'this-product-does-not-exist-12345'")
    bad = await get_product_details("this-product-does-not-exist-12345", adapter=adapter)
    if bad.get("error"):
        console.print(f"[green]  ✓ Graceful error: {bad['error'][:60]}[/green]")
    else:
        console.print("[yellow]  ⚠ No error returned for invalid ID[/yellow]")

    # ── Empty search test ─────────────────────────────────────────────────────
    console.print("\n[bold]EMPTY SEARCH TEST:[/bold] 'zzzznonexistentproductxxx999'")
    empty = await search_products("zzzznonexistentproductxxx999", limit=3, adapter=adapter)
    if empty.get("count", 1) == 0 or empty.get("error") or empty.get("message"):
        console.print(f"[green]  ✓ Handled gracefully[/green]")
    else:
        console.print("[yellow]  ⚠ Unexpected results for nonsense query[/yellow]")

    await adapter.close()

    # ── Summary ───────────────────────────────────────────────────────────────
    console.print()
    if all_passed:
        console.print(Panel.fit(
            "[bold green]✅ SMOKE TEST PASSED[/bold green]\n"
            "Joyory data source is working.\n"
            "Next: python server.py",
            border_style="green",
        ))
    else:
        console.print(Panel.fit(
            "[bold yellow]⚠ PARTIAL RESULTS[/bold yellow]\n"
            "Some tests had issues. Check the output above.\n"
            "You may need to rerun: python scripts/discover_joyory.py",
            border_style="yellow",
        ))


if __name__ == "__main__":
    asyncio.run(main())
