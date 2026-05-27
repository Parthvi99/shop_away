#!/usr/bin/env python3
"""
ShopWay Concierge — Entry point.

Usage:
    python main.py                  # Interactive mode
    python main.py --demo           # Run the hackathon demo script
"""

import asyncio
import sys
import os
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown

load_dotenv()

console = Console()

BANNER = """
╔══════════════════════════════════════════════════════════╗
║          ShopWay Concierge  •  AI Furniture Shopper      ║
║          Powered by Claude claude-sonnet-4-6 + Playwright          ║
╚══════════════════════════════════════════════════════════╝
"""

DEMO_SCRIPT = [
    "I need a mid-century modern sofa in gray or blue, budget is $900, for a living room that's about 12 feet wide.",
    "yes, add it to cart",
]

HELP_TEXT = """
**Tips:**
- Describe your style: *mid-century modern, farmhouse, Scandinavian, industrial...*
- Mention your budget: *under $500, around $1200...*
- Describe your space: *12x14 room, small apartment, studio...*
- Confirm a purchase: *yes / add it / buy it*
- Type **quit** or **exit** to end the session
"""


async def run_interactive():
    from concierge import ShopWayConcierge

    console.print(BANNER, style="bold cyan")
    console.print(Markdown(HELP_TEXT))

    agent = ShopWayConcierge()

    console.print("[dim]Starting browser...[/dim]")
    await agent.start()

    try:
        while True:
            try:
                user_input = Prompt.ask("\n[bold green]You[/bold green]")
            except (EOFError, KeyboardInterrupt):
                break

            if user_input.lower() in ("quit", "exit", "q", "bye"):
                break

            if not user_input.strip():
                continue

            response = await agent.chat(user_input)
            console.print(f"\n[bold blue]Concierge:[/bold blue]")
            console.print(Panel(Markdown(response), border_style="blue", padding=(1, 2)))

    finally:
        console.print("\n[dim]Closing browser...[/dim]")
        await agent.stop()
        console.print("[bold cyan]Thanks for shopping with ShopWay Concierge![/bold cyan]")


async def run_demo():
    """Scripted demo for the hackathon presentation."""
    from concierge import ShopWayConcierge

    console.print(BANNER, style="bold cyan")
    console.print(
        Panel(
            "[bold]HACKATHON DEMO[/bold] — Watch the agent browse Wayfair live",
            border_style="yellow",
        )
    )

    agent = ShopWayConcierge()
    console.print("[dim]Starting browser (visible for demo)...[/dim]")
    await agent.start()

    try:
        for i, message in enumerate(DEMO_SCRIPT):
            console.print(f"\n[bold green]You:[/bold green] {message}")
            await asyncio.sleep(1)  # Dramatic pause for demo

            response = await agent.chat(message)
            console.print(f"\n[bold blue]Concierge:[/bold blue]")
            console.print(Panel(Markdown(response), border_style="blue", padding=(1, 2)))

            if i < len(DEMO_SCRIPT) - 1:
                input("\n[Press Enter for next step...]")

    finally:
        input("\n[Demo complete — Press Enter to close browser]")
        await agent.stop()


if __name__ == "__main__":
    if not os.getenv("GROQ_API_KEY"):
        console.print("[bold red]Error:[/bold red] GROQ_API_KEY not set.")
        console.print("Create a .env file with: GROQ_API_KEY=your_key_here")
        sys.exit(1)

    if "--demo" in sys.argv:
        asyncio.run(run_demo())
    else:
        asyncio.run(run_interactive())
