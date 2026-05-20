from playwright.async_api import async_playwright


async def check_compatibility(part_number: str, model_number: str) -> dict:
    """Check if a part is compatible with a specific appliance model.
    
    Args:
        part_number: The PS part number (e.g. PS11752778)
        model_number: The appliance model number (e.g. WDT780SAEM1)
    
    Returns:
        dict with compatible bool, message, model_name, model_url
    """
    browser = None
    model_url = f"https://www.partselect.com/Models/{model_number}/Parts/"
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
            page = await context.new_page()
            await page.goto(model_url)
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(3000)

            model_name = ""
            try:
                model_name = await page.locator("h1").first.inner_text()
                model_name = model_name.strip()
            except Exception:
                pass

            if not model_name:
                await browser.close()
                browser = None
                return {"error": f"Could not load model page for {model_number}"}

            page_content = await page.content()

            await browser.close()
            browser = None

            compatible = part_number in page_content

            if compatible:
                message = f"Part {part_number} is compatible with model {model_number}"
            else:
                message = f"Part {part_number} is not compatible with model {model_number}"

            return {
                "compatible": compatible,
                "part_number": part_number,
                "model_number": model_number,
                "model_name": model_name,
                "message": message,
                "model_url": model_url,
            }
    except Exception as e:
        if browser:
            try:
                await browser.close()
            except Exception:
                pass
        return {"error": str(e)}
