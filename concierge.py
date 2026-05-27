"""
ShopWay Concierge — AI furniture shopping agent.
Powered by Groq (free tier, no card needed) + Playwright browser automation.
Model: llama-3.3-70b-versatile — fast and supports tool use.
"""

import asyncio
import json
import os
from groq import Groq
from browser import FurnitureBrowser
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

console = Console()

SYSTEM_PROMPT = """/no_think
You are ShopWay Concierge, an AI furniture shopping assistant.

Steps: 1) call search_products 2) call get_product_details on top 2 results 3) recommend the best fit 4) if user says yes/add it, call add_to_cart.

Rules: check dimensions vs room size (1ft=12in). Be specific and opinionated. Pick one winner."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": (
                "Search and filter the Shop_way product catalog. "
                "Returns matching products with price, dimensions, rating, and style. "
                "Always call this first to find candidates."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keyword search by category or color — e.g. 'sofa', 'gray velvet', 'dining table'. Leave empty to get all products.",
                    },
                    "style": {
                        "type": "string",
                        "description": "Filter by style: 'mid-century modern', 'scandinavian', 'farmhouse', 'industrial', 'contemporary'",
                    },
                    "max_price": {
                        "type": "number",
                        "description": "Maximum price in USD",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_details",
            "description": (
                "Get full specs for a specific product: exact dimensions (width, depth, height), "
                "weight, material, available colors, assembly info, highlights, and description. "
                "Call this for your top 2-3 candidates before making a recommendation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "Product ID from search results (e.g. 'sw-001')",
                    },
                    "product_name": {
                        "type": "string",
                        "description": "Product name for display purposes",
                    },
                },
                "required": ["product_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_cart",
            "description": (
                "Add a product to the shopping cart. The cart slides open in the browser "
                "so everyone can see. ONLY call this when the user explicitly confirms "
                "they want to buy — e.g. 'yes', 'add it', 'buy it', 'looks good', 'add to cart'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "Product ID (e.g. 'sw-001')",
                    },
                    "product_name": {
                        "type": "string",
                        "description": "Product name",
                    },
                    "color": {
                        "type": "string",
                        "description": "Color variant to select (e.g. 'Slate Gray')",
                    },
                },
                "required": ["product_id", "product_name"],
            },
        },
    },
]


class ShopWayConcierge:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.browser = FurnitureBrowser(headless=False)
        self.messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    async def start(self):
        await self.browser.start()

    async def stop(self):
        await self.browser.stop()

    async def _execute_tool(self, tool_name: str, tool_input: dict) -> str:
        if tool_name == "search_products":
            label = tool_input.get("query") or tool_input.get("style") or "all products"
            budget = tool_input.get("max_price")
            budget_str = f" under ${budget:,.0f}" if budget else ""

            with Progress(
                SpinnerColumn(),
                TextColumn(f"[cyan]Browsing Shop_way: {label}{budget_str}...[/cyan]"),
                transient=True,
            ) as p:
                p.add_task("", total=None)
                results = await self.browser.search_products(
                    query=tool_input.get("query", ""),
                    style=tool_input.get("style"),
                    max_price=tool_input.get("max_price"),
                )

            if not results:
                return json.dumps({"results": [], "message": "No products matched the filters."})

            table = Table(title=f"Shop_way ({len(results)} results)", box=box.SIMPLE_HEAD)
            table.add_column("ID", style="dim", width=7)
            table.add_column("Product", style="white", max_width=34)
            table.add_column("Style", style="cyan", max_width=18)
            table.add_column("Price", style="green", width=8)
            table.add_column("W×D×H (in)", style="dim", width=14)
            table.add_column("Rating", style="yellow", width=10)
            for p in results:
                d = p.get("dimensions", {})
                dims = f"{d.get('width_in','')}×{d.get('depth_in','')}×{d.get('height_in','')}"
                table.add_row(
                    p["id"], p["name"][:33], p["style"],
                    f"${p['price']:,}", dims, f"★{p['rating']} ({p['reviews']})",
                )
            console.print(table)
            return json.dumps({"results": results, "count": len(results)})

        elif tool_name == "get_product_details":
            pid = tool_input["product_id"]
            name = tool_input.get("product_name", pid)
            with Progress(
                SpinnerColumn(),
                TextColumn(f"[cyan]Opening: {name}...[/cyan]"),
                transient=True,
            ) as p:
                p.add_task("", total=None)
                details = await self.browser.get_product_details(pid)

            if details:
                d = details.get("dimensions", {})
                console.print(
                    f"  [dim]→ {details['name']} | ${details['price']:,} | "
                    f"{d.get('width_in')}\"W × {d.get('depth_in')}\"D | "
                    f"★{details['rating']} ({details['reviews']} reviews)[/dim]"
                )
            return json.dumps(details)

        elif tool_name == "add_to_cart":
            pid = tool_input["product_id"]
            name = tool_input.get("product_name", pid)
            color = tool_input.get("color")
            console.print(f"\n[bold yellow]  → Adding: {name} ({color or 'default color'})...[/bold yellow]")
            result = await self.browser.add_to_cart(pid, color)
            if result["success"]:
                console.print(f"[bold green]  ✓ Added! Cart has {result['cart_items']} item(s)[/bold green]")
            else:
                console.print(f"[red]  ✗ Could not add to cart[/red]")
            return json.dumps(result)

        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    async def chat(self, user_message: str) -> str:
        """Send a message and run the agentic loop until a final response."""
        self.messages.append({"role": "user", "content": user_message})

        while True:
            for attempt in range(3):
                try:
                    response = self.client.chat.completions.create(
                model="qwen/qwen3-32b",
                messages=self.messages,
                tools=TOOLS,
                tool_choice="auto",
                parallel_tool_calls=False,
                        max_tokens=1024,
                    )
                    break
                except Exception as e:
                    if "429" in str(e) and attempt < 2:
                        import time; time.sleep(3)
                    else:
                        raise

            msg = response.choices[0].message

            # Serialize to plain dict so the API accepts it in subsequent turns
            assistant_turn = {"role": "assistant", "content": msg.content or ""}
            if msg.tool_calls:
                assistant_turn["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ]
            self.messages.append(assistant_turn)

            # No tool calls → final answer
            if not msg.tool_calls:
                return msg.content or ""

            # Print any leading text (thinking out loud)
            if msg.content:
                console.print(f"\n[bold blue]Concierge:[/bold blue] {msg.content}")

            # Execute each tool call and collect results
            for tc in msg.tool_calls:
                console.print(f"\n[dim]  → Tool: {tc.function.name}[/dim]")
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                result = await self._execute_tool(tc.function.name, args)
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
