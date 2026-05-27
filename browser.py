"""
Browser automation layer for ShopWay Concierge.
Navigates the Shop_way storefront at localhost:8080.
"""

import asyncio
import json
import re
from playwright.async_api import async_playwright, Page, Browser

SITE_URL = "http://localhost:8080"


class FurnitureBrowser:
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.playwright = None
        self.browser: Browser = None
        self.page: Page = None

    async def start(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=["--start-maximized"],
        )
        context = await self.browser.new_context(
            viewport={"width": 1440, "height": 900},
        )
        self.page = await context.new_page()
        # Load the storefront and wait for products
        await self.page.goto(SITE_URL, wait_until="domcontentloaded")
        await self.page.wait_for_function("typeof window.__shopway !== 'undefined'", timeout=10000)

    async def stop(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def search_products(self, query: str = "", style: str = None, max_price: float = None):
        """Search and filter products on the Shop_way storefront."""
        # Only navigate if not already on the site (avoids wiping the cart)
        if SITE_URL not in self.page.url:
            await self.page.goto(SITE_URL, wait_until="domcontentloaded")
            await self.page.wait_for_function("typeof window.__shopway !== 'undefined'", timeout=10000)

        # Use the JS API to filter — fast and reliable
        results = await self.page.evaluate(
            """
            ({ query, style, maxPrice }) => {
                const sw = window.__shopway;
                let products = sw.getProducts();

                if (style && style !== 'all') {
                    products = products.filter(p => p.style.toLowerCase().includes(style.toLowerCase()));
                }
                if (query) {
                    const q = query.toLowerCase();
                    products = products.filter(p =>
                        p.name.toLowerCase().includes(q) ||
                        p.style.toLowerCase().includes(q) ||
                        p.category.toLowerCase().includes(q) ||
                        p.material.toLowerCase().includes(q) ||
                        p.colors.some(c => c.toLowerCase().includes(q)) ||
                        p.description.toLowerCase().includes(q)
                    );
                }
                if (maxPrice) {
                    products = products.filter(p => p.price <= maxPrice);
                }

                return products.map(p => ({
                    id: p.id,
                    name: p.name,
                    category: p.category,
                    style: p.style,
                    price: p.price,
                    colors: p.colors,
                    dimensions: p.dimensions,
                    material: p.material,
                    rating: p.rating,
                    reviews: p.reviews,
                    in_stock: p.in_stock,
                    assembly: p.assembly,
                    highlights: p.highlights,
                    description: p.description,
                }));
            }
            """,
            {"query": query or "", "style": style or "", "maxPrice": max_price or 0},
        )

        # Also update the visible UI so the demo looks good
        if query:
            await self.page.evaluate(f"window.__shopway.search({json.dumps(query)})")

        return results

    async def _ensure_page(self):
        """Reopen the storefront if the page was closed."""
        try:
            await self.page.title()  # cheap alive-check
        except Exception:
            context = await self.browser.new_context(viewport={"width": 1440, "height": 900})
            self.page = await context.new_page()
            await self.page.goto(SITE_URL, wait_until="domcontentloaded")
            await self.page.wait_for_function("typeof window.__shopway !== 'undefined'", timeout=10000)

    async def get_product_details(self, product_id: str):
        """Open a product modal and return full specs."""
        await self._ensure_page()
        # Open the product in the UI (visible to audience)
        await self.page.evaluate(f"window.__shopway.openProductById({json.dumps(product_id)})")
        await self.page.wait_for_timeout(600)

        # Get data directly from the JS store
        product = await self.page.evaluate(
            """
            (id) => {
                const products = window.__shopway.getProducts();
                return products.find(p => p.id === id) || null;
            }
            """,
            product_id,
        )
        return product

    async def add_to_cart(self, product_id: str, color: str = None):
        """Add item to cart — visible in UI."""
        await self._ensure_page()
        # Open modal first so audience sees the product
        await self.page.evaluate(f"window.__shopway.openProductById({json.dumps(product_id)})")
        await self.page.wait_for_timeout(800)

        # Click the Add to Cart button in the modal
        try:
            btn = await self.page.wait_for_selector(".add-to-cart-btn", timeout=3000)
            if btn:
                # Select color if specified
                if color:
                    color_opts = await self.page.query_selector_all(".color-opt")
                    for opt in color_opts:
                        text = await opt.inner_text()
                        if color.lower() in text.lower():
                            await opt.click()
                            await self.page.wait_for_timeout(200)
                            break
                await btn.click()
                await self.page.wait_for_timeout(800)
        except Exception:
            pass

        # Also call JS directly to ensure cart state is set
        success = await self.page.evaluate(
            "([id, color]) => window.__shopway.addToCartById(id, color)",
            [product_id, color],
        )

        # Open cart sidebar to show it was added
        await self.page.evaluate("document.getElementById('cart-sidebar').classList.add('open')")
        await self.page.wait_for_timeout(500)

        cart = await self.page.evaluate("() => window.__shopway.getCart()")
        return {
            "success": bool(success),
            "cart_items": len(cart),
            "cart": [{"name": c["name"], "price": c["price"], "color": c.get("color")} for c in cart],
        }
