import pathlib
import json
from playwright.async_api import async_playwright

async def render_template(template_name: str, data: dict) -> bytes:
    tpl_path = pathlib.Path(__file__).parent.parent / "templates" / template_name
    async with async_playwright() as p:
        browser = await p.chromium.launch(args=["--no-sandbox"])
        page = await browser.new_page(viewport={"width": 800, "height": 450})
        await page.goto(f"file://{tpl_path.resolve()}")
        await page.evaluate(f"window.renderData({json.dumps(data)})")
        await page.wait_for_timeout(500) # Ждем загрузки шрифтов и картинок
        png_bytes = await page.screenshot()
        await browser.close()
        return png_bytes