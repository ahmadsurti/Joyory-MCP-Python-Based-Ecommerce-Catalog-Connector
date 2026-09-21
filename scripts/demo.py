"""
scripts/demo.py
================
Beautiful demo script for showing the MCP server in action.

Performs:
  1. search_products("lipstick", 3)
  2. get_product_details(first_result_id)

Usage:
    python scripts/demo.py
    python scripts/demo.py --query "vitamin c serum" --limit 3
"""

import sys
import asyncio
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule
from rich.text import Text
from rich import box

console = Console(width=90)


async def run_demo(query: str = "lipstick", limit: int = 3):
    from joyory_mcp import config as cfg
    from joyory_mcp.tools.search import search_products
    from joyory_mcp.tools.details import get_product_details

    source_config = cfg.load_source_config()
    if not source_config:
        console.print("[bold red]No config/joyory_source.json. Run discover_joyory.py first.[/bold red]")
        sys.exit(1)

    adapter_type = source_config.get("adapter", "api")
    if adapter_type == "graphql":
        from joyory_mcp.adapters.graphql import GraphQLJoyoryDataSource
        adapter = GraphQLJoyoryDataSource(source_config)
    elif adapter_type == "browser":
        from joyory_mcp.adapters.browser import BrowserJoyoryDataSource
        adapter = BrowserJoyoryDataSource(source_config)
    else:
        from joyory_mcp.adapters.api import ApiJoyoryDataSource
        adapter = ApiJoyoryDataSource(source_config)

    # ── Header ────────────────────────────────────────────────────────────────
    console.print()
    console.print(Panel.fit(
        "[bold magenta]✨  JOYORY MCP DEMO  ✨[/bold magenta]\n"
        "[dim]Powered by Joyory Product MCP Server[/dim]",
        border_style="magenta",
    ))

    # ── Search ────────────────────────────────────────────────────────────────
    console.print()
    console.rule(f"[bold cyan]SEARCH: '{query}'  (limit={limit})[/bold cyan]")
    console.print()

    search_result = await search_products(query, limit=limit, adapter=adapter)

    if search_result.get("error"):
        console.print(f"[bold red]Search failed:[/bold red] {search_result['error']}")
        await adapter.close()
        return

    results = search_result.get("results", [])
    count = search_result.get("count", 0)

    if count == 0:
        console.print(f"[yellow]No results found for '{query}'.[/yellow]")
        await adapter.close()
        return

    console.print(f"[green]Found {count} product(s):[/green]\n")

    table = Table(
        show_header=True,
        header_style="bold white on dark_magenta",
        box=box.ROUNDED,
        show_lines=True,
    )
    table.add_column("#", width=3)
    table.add_column("Product Name", width=32, overflow="fold")
    table.add_column("Brand", width=18, overflow="fold")
    table.add_column("Price (₹)", width=10, justify="right")
    table.add_column("Rating", width=8, justify="center")
    table.add_column("In Stock", width=9, justify="center")

    for i, p in enumerate(results, 1):
        price = f"₹{p.get('price'):,.0f}" if p.get('price') else "N/A"
        rating = f"⭐ {p.get('rating')}" if p.get('rating') else "—"
        stock_val = p.get('in_stock')
        stock = "[green]Yes[/green]" if stock_val is True else "[red]No[/red]" if stock_val is False else "[dim]?[/dim]"
        table.add_row(
            str(i),
            p.get("name", "Unknown")[:32],
            p.get("brand") or "—",
            price,
            rating,
            stock,
        )

    console.print(table)

    # Print URLs
    console.print()
    for i, p in enumerate(results, 1):
        url = p.get("url") or "No URL"
        console.print(f"  [dim]{i}.[/dim] {url}")

    # ── Detail ────────────────────────────────────────────────────────────────
    first = results[0] if results else None
    if not first:
        await adapter.close()
        return

    first_id = first.get("id")
    if not first_id or first_id == "unknown":
        console.print("\n[yellow]No stable ID available for detail lookup.[/yellow]")
        await adapter.close()
        return

    console.print()
    console.rule(f"[bold cyan]PRODUCT DETAIL: #{first_id}[/bold cyan]")
    console.print()

    detail = await get_product_details(first_id, adapter=adapter)

    if detail.get("error"):
        console.print(f"[bold red]Detail failed:[/bold red] {detail['error']}")
    else:
        info_table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
        info_table.add_column("Field", style="bold cyan", width=15)
        info_table.add_column("Value", overflow="fold")

        def row(label, value):
            if value:
                info_table.add_row(label, str(value))

        row("Name", detail.get("name"))
        row("Brand", detail.get("brand"))
        row("Price", f"₹{detail.get('price'):,.0f}" if detail.get('price') else None)
        row("Rating", f"{detail.get('rating')} ({detail.get('rating_count')} reviews)" if detail.get('rating') else None)
        row("In Stock", "Yes" if detail.get('in_stock') else "No" if detail.get('in_stock') is False else "Unknown")
        row("Category", detail.get("category"))

        desc = detail.get("description") or ""
        row("Description", desc[:120] + ("..." if len(desc) > 120 else ""))

        how = detail.get("how_to_use") or ""
        row("How To Use", how[:100] + ("..." if len(how) > 100 else ""))

        ingredients = detail.get("ingredients", [])
        if ingredients:
            row("Ingredients", ", ".join(ingredients[:5]) + (f" +{len(ingredients)-5} more" if len(ingredients) > 5 else ""))

        variants = detail.get("variant_information", [])
        if variants:
            row("Variants", f"{len(variants)} variant(s): " + ", ".join(v.get("name", "") for v in variants[:3]))

        images = detail.get("images", [])
        row("Images", f"{len(images)} image(s)" if images else None)
        row("URL", detail.get("url"))

        console.print(info_table)

    await adapter.close()

    # ── Footer ────────────────────────────────────────────────────────────────
    console.print()
    console.print(Panel.fit(
        "[bold green]✅  Demo complete[/bold green]\n"
        "[dim]Start server: python server.py\n"
        "Inspector:    npx -y @modelcontextprotocol/inspector\n"
        "Connect to:   http://127.0.0.1:8000/mcp[/dim]",
        border_style="green",
    ))
    console.print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Joyory MCP Demo")
    parser.add_argument("--query", default="lipstick", help="Search query")
    parser.add_argument("--limit", type=int, default=3, help="Result limit")
    args = parser.parse_args()

    asyncio.run(run_demo(query=args.query, limit=args.limit))
