import re
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


async def get_model_parts(model_number: str) -> dict:
    """Get all parts for a specific appliance model number.
    
    Args:
        model_number: The appliance model number (e.g. WDT780SAEM1)
    
    Returns:
        dict with model_name, parts list, count, and model_url
    """
    browser = None
    model_url = f"https://www.partselect.com/Models/{model_number}/Parts/"
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(user_agent=USER_AGENT)
            page = await context.new_page()
            await Stealth().apply_stealth_async(page)

            await page.goto(model_url)
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(3000)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(3000)

            model_name = ""
            try:
                model_name = await page.locator("h1").first.inner_text()
                model_name = model_name.strip()
            except Exception:
                pass

            cards = await page.locator("div.mega-m__part").all()
            parts = []

            for card in cards[:12]:
                title = ""
                url = ""
                part_number = ""
                price = ""
                availability = ""

                try:
                    title = await card.locator("a.mega-m__part__name").first.inner_text()
                    title = title.strip()
                except Exception:
                    pass

                try:
                    href = await card.locator("a.mega-m__part__img").first.get_attribute("href") or ""
                    if href.startswith("/"):
                        href = f"https://www.partselect.com{href}"
                    url = href.split("?")[0]
                    match = re.search(r"PS\d+", href)
                    part_number = match.group(0) if match else ""
                except Exception:
                    pass

                try:
                    price_text = await card.locator("div.mega-m__part__price").first.inner_text(timeout=2000)
                    price = price_text.replace("$", "").strip()
                except Exception:
                    pass

                try:
                    availability = await card.locator("div.mega-m__part__avlbl span").first.inner_text(timeout=2000)
                    availability = availability.strip()
                except Exception:
                    pass

                parts.append({
                    "title": title,
                    "url": url,
                    "part_number": part_number,
                    "price": price,
                    "availability": availability,
                })

            await browser.close()
            browser = None

            return {
                "model_number": model_number,
                "model_name": model_name,
                "parts": parts,
                "count": len(parts),
                "model_url": model_url,
            }
    except Exception as e:
        if browser:
            try:
                await browser.close()
            except Exception:
                pass
        return {"error": str(e)}
