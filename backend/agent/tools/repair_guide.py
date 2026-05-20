from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from data.vector_store import search_repair_guides

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
AI_DISCLAIMER = "⚠️ Repair guidance provided by AI. Please use discretion and consult a qualified technician for complex repairs."


async def get_repair_guide(symptom: str, appliance_type: str) -> dict:
    browser = None
    try:
        normalized = appliance_type.strip().lower()
        if normalized not in ("refrigerator", "dishwasher"):
            return {"error": "appliance_type must be refrigerator or dishwasher"}

        if normalized == "refrigerator":
            listing_url = "https://www.partselect.com/Repair/Refrigerator/"
        else:
            listing_url = "https://www.partselect.com/Repair/Dishwasher/"

        # STEP 2 — ChromaDB lookup
        guide_url = ""
        symptom_matched = ""
        symptom_description = ""
        percentage = ""
        source = "live"

        results = search_repair_guides(symptom, normalized, n_results=3)
        if results and results[0]["distance"] < 1.3:
            best = results[0]
            guide_url = best["guide_url"]
            symptom_matched = best["symptom_name"]
            symptom_description = best["description"]
            percentage = best["percentage"]
            source = "vector_db"

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(user_agent=USER_AGENT)
            page = await context.new_page()
            await Stealth().apply_stealth_async(page)

            # STEP 3 — Live fallback if no ChromaDB match
            if source == "live":
                await page.goto(listing_url)
                await page.wait_for_load_state("domcontentloaded")
                await page.wait_for_timeout(3000)

                symptom_links = await page.locator(".symptom-list a").all()
                scraped_symptoms = []
                for link in symptom_links:
                    name = ""
                    desc = ""
                    pct = ""
                    href = ""
                    try:
                        name = await link.locator("h3.title-md").first.inner_text()
                        name = name.strip()
                    except Exception:
                        pass
                    try:
                        desc = await link.locator("p").first.inner_text()
                        desc = desc.strip()
                    except Exception:
                        pass
                    try:
                        spans = await link.locator(".symptom-list__reported-by span").all()
                        if spans:
                            pct = await spans[-1].inner_text()
                            pct = pct.strip()
                    except Exception:
                        pass
                    try:
                        href_raw = await link.get_attribute("href") or ""
                        if href_raw.startswith("/"):
                            href = f"https://www.partselect.com{href_raw}"
                        else:
                            href = href_raw
                    except Exception:
                        pass
                    if name:
                        scraped_symptoms.append({
                            "name": name,
                            "description": desc,
                            "percentage": pct,
                            "href": href,
                        })

                matched = None
                symptom_lower = symptom.strip().lower()
                for s in scraped_symptoms:
                    name_lower = s["name"].lower()
                    if symptom_lower in name_lower or name_lower in symptom_lower:
                        matched = s
                        break

                if matched is None:
                    await browser.close()
                    browser = None
                    return {
                        "matched": False,
                        "message": "Could not find a matching symptom. Available symptoms:",
                        "all_symptoms": [s["name"] for s in scraped_symptoms],
                        "appliance": appliance_type,
                        "guide_url": listing_url,
                    }

                guide_url = matched["href"]
                symptom_matched = matched["name"]
                symptom_description = matched["description"]
                percentage = matched["percentage"]

            # STEP 4 — Scrape the guide page
            await page.goto(guide_url)
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(3000)

            title = ""
            try:
                title = await page.locator("h1").first.inner_text()
                title = title.strip()
            except Exception:
                pass

            parts = []
            try:
                part_links = await page.locator("div.repair__intro a.js-scrollTrigger").all()
                for link in part_links:
                    part_name = ""
                    part_href = ""
                    try:
                        part_name = await link.inner_text()
                        part_name = part_name.strip()
                    except Exception:
                        pass
                    try:
                        part_href = await link.get_attribute("href") or ""
                        if part_href.startswith("/"):
                            part_href = f"https://www.partselect.com{part_href}"
                    except Exception:
                        pass
                    parts.append({"name": part_name, "href": part_href})
            except Exception:
                pass

            video_id = ""
            try:
                video_id = await page.locator("div[data-yt-init]").first.get_attribute("data-yt-init") or ""
            except Exception:
                pass

            video_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else ""
            video_thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg" if video_id else ""
            final_guide_url = page.url

            await browser.close()
            browser = None

            return {
                "symptom_matched": symptom_matched,
                "symptom_description": symptom_description,
                "percentage": percentage,
                "appliance": appliance_type,
                "title": title,
                "parts": parts,
                "video_id": video_id,
                "video_url": video_url,
                "video_thumbnail_url": video_thumbnail_url,
                "guide_url": final_guide_url,
                "source": source,
                "ai_generated": True,
                "ai_disclaimer": AI_DISCLAIMER,
            }
    except Exception as e:
        if browser:
            try:
                await browser.close()
            except Exception:
                pass
        return {"error": str(e)}
