from playwright.async_api import async_playwright


async def get_part_details(part_number: str) -> dict:
    """Get detailed information about a specific PartSelect part.
    
    Args:
        part_number: The PS part number (e.g. PS11752778)
    
    Returns:
        dict with part_name, price, availability, symptoms, 
        image_url, video_url and other part details
    """
    browser = None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
            page = await context.new_page()
            await page.goto(f"https://www.partselect.com/api/search/?searchterm={part_number}")
            await page.wait_for_selector('h1', timeout=20000)
            await page.wait_for_timeout(3000)

            # wait for product details section to fully render
            try:
                await page.wait_for_selector('div.pd__wrap', timeout=10000)
                await page.wait_for_timeout(1000)
            except Exception:
                pass

            part_name = ""
            try:
                part_name = await page.locator("h1").first.inner_text()
            except Exception:
                pass

            part_id = ""
            try:
                part_id = await page.locator("span[itemprop='productID']").first.inner_text()
            except Exception:
                pass

            mpn = ""
            try:
                mpn = await page.locator("span[itemprop='mpn']").first.inner_text()
            except Exception:
                pass

            price = ""
            try:
                price = await page.locator("span.js-partPrice").first.inner_text()
            except Exception:
                pass

            availability = ""
            try:
                availability = await page.locator("span[itemprop='availability']").first.inner_text()
            except Exception:
                pass

            brand = ""
            try:
                brand = await page.locator("span[itemprop='brand'] span[itemprop='name']").first.inner_text()
            except Exception:
                pass

            description = ""
            try:
                description = await page.locator('div.pd__wrap').nth(0).locator('div[itemprop="description"]').first.text_content(timeout=5000)
                description = description.strip()
            except Exception:
                pass

            install_difficulty = ""
            try:
                install_difficulty = await page.locator("div.d-flex p").nth(0).inner_text()
            except Exception:
                pass

            install_time = ""
            try:
                install_time = await page.locator("div.d-flex p").nth(1).inner_text()
            except Exception:
                pass

            symptoms = []
            try:
                sections = await page.locator('div.pd__wrap div.col-md-6.mt-3').all()
                for section in sections:
                    heading = await section.locator('div.bold.mb-1').first.text_content(timeout=2000)
                    if 'fixes the following symptoms' in heading.lower():
                        items = await section.locator('li.mb-1').all_text_contents()
                        symptoms = [s.strip() for s in items if s.strip()]
                        break
            except Exception:
                pass

            product_types = []
            try:
                sections = await page.locator('div.pd__wrap div.col-md-6.mt-3').all()
                for section in sections:
                    heading = await section.locator('div.bold.mb-1').first.text_content(timeout=2000)
                    if 'works with the following products' in heading.lower():
                        items = await section.locator('li.mb-1').all_text_contents()
                        product_types = [s.strip() for s in items if s.strip()]
                        break
            except Exception:
                pass

            image_url = ""
            try:
                image_url = await page.locator("img[itemprop=image]").first.get_attribute("src") or ""
            except Exception:
                pass

            video_id = ""
            try:
                video_id = await page.locator("div[data-yt-init]").first.get_attribute("data-yt-init") or ""
            except Exception:
                pass

            video_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else ""
            video_thumbnail_url = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg" if video_id else ""
            product_url = page.url

            await browser.close()
            browser = None

            return {
                "part_name": part_name.strip(),
                "part_id": part_id.strip(),
                "mpn": mpn.strip(),
                "price": price.strip(),
                "availability": availability.strip(),
                "brand": brand.strip(),
                "description": description,
                "install_difficulty": install_difficulty.strip(),
                "install_time": install_time.strip(),
                "symptoms": symptoms,
                "product_types": product_types,
                "image_url": image_url.strip(),
                "video_id": video_id.strip(),
                "video_url": video_url,
                "video_thumbnail_url": video_thumbnail_url,
                "product_url": product_url,
            }
    except Exception as e:
        if browser:
            try:
                await browser.close()
            except Exception:
                pass
        return {"error": str(e)}
