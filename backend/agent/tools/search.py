import re
from urllib.parse import quote_plus
from playwright.async_api import async_playwright


async def search_parts(query: str, appliance_filter: str) -> dict:
    browser = None
    try:
        normalized = appliance_filter.strip().lower()
        if normalized not in ("refrigerator", "dishwasher"):
            return {"error": "appliance_filter must be refrigerator or dishwasher"}

        encoded_query = quote_plus(query)
        if normalized == "refrigerator":
            url = f"https://www.partselect.com/Refrigerator-Parts.htm?SearchTerm={encoded_query}"
        else:
            url = f"https://www.partselect.com/Dishwasher-Parts.htm?SearchTerm={encoded_query}"

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
            page = await context.new_page()
            await page.goto(url)
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(3000)

            cards = await page.locator("div.nf__part.mb-3").all()
            results = []

            for card in cards[:8]:
                title = ""
                part_url = ""
                part_number = ""
                price = ""

                try:
                    title = await card.locator("a.nf__part__detail__title").first.inner_text()
                    title = title.strip()
                except Exception:
                    pass

                try:
                    href = await card.locator("a.nf__part__detail__title").first.get_attribute("href") or ""
                    if href.startswith("http"):
                        part_url = href
                    elif href.startswith("/"):
                        part_url = f"https://www.partselect.com{href}"
                    else:
                        part_url = href

                    match = re.search(r'PS\d+', href)
                    part_number = match.group(0) if match else ""
                except Exception:
                    pass

                try:
                    price_text = await card.locator("div.mt-sm-2.price").first.inner_text(timeout=2000)
                    price = price_text.replace("$", "").strip()
                except Exception:
                    price = ""

                results.append({
                    "title": title,
                    "url": part_url,
                    "part_number": part_number,
                    "price": price,
                })

            await browser.close()
            browser = None

            return {
                "results": results,
                "count": len(results),
                "query": query,
                "appliance": appliance_filter,
            }
    except Exception as e:
        if browser:
            try:
                await browser.close()
            except Exception:
                pass
        return {"error": str(e)}
