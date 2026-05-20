import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from data.vector_store import add_repair_guides

PAGES = [
    ("https://www.partselect.com/Repair/Refrigerator/", "refrigerator"),
    ("https://www.partselect.com/Repair/Dishwasher/", "dishwasher"),
]

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


async def scrape_symptoms(page, url: str, appliance_type: str) -> list[dict]:
    await page.goto(url)
    await page.wait_for_load_state("domcontentloaded")
    await page.wait_for_timeout(3000)

    links = await page.locator(".symptom-list a").all()
    guides = []

    for link in links:
        symptom_name = ""
        description = ""
        percentage = ""
        guide_url = ""

        try:
            symptom_name = await link.locator("h3.title-md").first.inner_text()
            symptom_name = symptom_name.strip()
        except Exception:
            pass

        try:
            description = await link.locator("p").first.inner_text()
            description = description.strip()
        except Exception:
            pass

        try:
            spans = await link.locator(".symptom-list__reported-by span").all()
            if spans:
                percentage = await spans[-1].inner_text()
                percentage = percentage.strip()
        except Exception:
            pass

        try:
            href = await link.get_attribute("href") or ""
            if href.startswith("/"):
                guide_url = f"https://www.partselect.com{href}"
            else:
                guide_url = href
        except Exception:
            pass

        if symptom_name:
            guides.append({
                "symptom_name": symptom_name,
                "description": description,
                "percentage": percentage,
                "guide_url": guide_url,
                "appliance_type": appliance_type,
            })

    return guides


async def seed():
    all_guides = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(user_agent=USER_AGENT)
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)

        for url, appliance_type in PAGES:
            guides = await scrape_symptoms(page, url, appliance_type)
            all_guides.extend(guides)

        await browser.close()

    add_repair_guides(all_guides)

    refrigerator_count = sum(1 for g in all_guides if g["appliance_type"] == "refrigerator")
    dishwasher_count = sum(1 for g in all_guides if g["appliance_type"] == "dishwasher")
    print(f"Seeded {len(all_guides)} repair guides ({refrigerator_count} refrigerator, {dishwasher_count} dishwasher)")


if __name__ == "__main__":
    asyncio.run(seed())
