import asyncio
import json
from playwright.async_api import async_playwright
from core.settings import ROOT


async def main():
    session = json.loads((ROOT / "runtime/smoke-session.json").read_text())
    folder = ROOT / "docs/images"
    folder.mkdir(exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        context = await browser.new_context(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        page = await context.new_page()
        await page.add_init_script(
            'localStorage.setItem("gigbid-token",' + json.dumps(session["token"].removeprefix("Bearer ")) + ");"
        )
        await page.goto("http://127.0.0.1:8000/inbox")
        await page.get_by_role("heading", name="Good work starts with a good fit.").wait_for()
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(folder / "inbox-desktop.png"), full_page=False)
        await page.goto("http://127.0.0.1:8000/studio/" + session["run_id"])
        await page.get_by_role("heading", name="A proposal you can stand behind.").wait_for()
        await page.wait_for_timeout(1000)
        await page.screenshot(path=str(folder / "studio-desktop.png"), full_page=False)
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.goto("http://127.0.0.1:8000/inbox")
        await page.wait_for_timeout(700)
        await page.screenshot(path=str(folder / "inbox-mobile.png"), full_page=False)
        await browser.close()
    print("Saved desktop, mobile and proposal-studio screenshots.")


if __name__ == "__main__":
    asyncio.run(main())
