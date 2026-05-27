# ShopWay Concierge 🛋️
### AI furniture shopping agent — Boston Tech Week Hackathon 2026

> Tell it what you need. It shops, compares, and adds to cart. Zero clicks.

---

## What it does

ShopWay Concierge takes a plain-English furniture request — style, budget, and room size — browses a live storefront, checks if products physically fit your space, and adds the best match to your cart, all without a single click.

**Example:**
```
You: I need a mid-century modern sofa in gray, budget $900, for a 12-foot wide room

Concierge: I recommend the Elliot Mid-Century Sofa at $799 — 84 inches wide,
           leaving 60 inches of walking space in your 12-foot room. ★4.7 (312 reviews)
           Shall I add it to cart?

You: yes

Concierge: ✓ Added to cart!
```

## How it works

1. **Search** — filters the catalog by style, color, and budget
2. **Compare** — opens each product, reads full specs
3. **Reason** — checks if dimensions fit your room (converts ft → inches)
4. **Recommend** — picks a winner with specific reasoning
5. **Purchase** — adds to cart on confirmation

## Stack

- **LLM:** Groq (`llama-3.3-70b-versatile`) with tool use
- **Browser:** Playwright (visible browser — audience sees it live)
- **Storefront:** Custom Shop_way site (HTML/JS/JSON)
- **Agent loop:** Python async with 3 tools: `search_products`, `get_product_details`, `add_to_cart`

## Run it

```bash
# 1. Install dependencies
pip install groq playwright rich python-dotenv
playwright install chromium

# 2. Add your Groq API key (free at console.groq.com)
echo "GROQ_API_KEY=your_key_here" > .env

# 3. Start the storefront
cd site && python3 -m http.server 8080

# 4. Run the agent (new terminal)
cd .. && python3 main.py
```

## Track

**Track 1 — Agents for Customers** (Wayfair / furniture discovery)
