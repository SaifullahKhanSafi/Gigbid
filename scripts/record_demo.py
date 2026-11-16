"""Three-minute edited capture of actual UI states, local open models, synthetic marketplace."""

import asyncio
import io
import json
import time
import uuid
import requests
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg
from playwright.async_api import async_playwright
from core.settings import ROOT
from core.security import mask


async def main():
    base = "http://127.0.0.1:8000"
    health = requests.get(base + "/api/health").json()
    if health["model_mode"] != "ollama":
        raise RuntimeError("Demo requires real open models, not test doubles")
    session = requests.Session()
    response = session.post(
        base + "/api/auth/register",
        json={"email": "demo-" + uuid.uuid4().hex + "@example.test", "password": uuid.uuid4().hex},
    )
    response.raise_for_status()
    auth = response.json()["access_token"]
    session.headers["Authorization"] = "Bearer " + auth
    folder = ROOT / "output/demo"
    folder.mkdir(parents=True, exist_ok=True)
    writer = imageio_ffmpeg.write_frames(
        str(folder / "gigbid-demo-3min.mp4"), (1280, 800), fps=4, codec="libx264", quality=7, macro_block_size=16
    )
    writer.send(None)
    samples = []
    count = 0
    run_ids = []
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 19)
    small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 13)
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome", headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        await page.add_init_script('localStorage.setItem("gigbid-token",' + json.dumps(auth) + ");")

        async def capture(seconds, title, caption):
            nonlocal count
            print(title, flush=True)
            for _ in range(seconds * 4):
                tick = time.monotonic()
                raw = await page.screenshot(type="jpeg", quality=82)
                img = Image.open(io.BytesIO(raw)).convert("RGB")
                draw = ImageDraw.Draw(img)
                draw.rectangle((0, 730, 1280, 800), fill="#173c2c")
                draw.text((26, 741), title, font=font, fill="#f4f7ec")
                draw.text((26, 771), caption, font=small, fill="#bdd1ad")
                draw.text((1050, 771), "LOCAL DEMO · SYNTHETIC DATA", font=small, fill="#bdd1ad")
                writer.send(img.tobytes())
                if count % 24 == 0:
                    samples.append(img.resize((960, 600)))
                count += 1
                await asyncio.sleep(max(0, 0.25 - (time.monotonic() - tick)))

        await page.goto(base + "/inbox")
        await page.get_by_role("heading", name="Good work starts with a good fit.").wait_for()
        await capture(
            15,
            "01 / An inbox with context",
            "Jobs and portfolios are fictional development fixtures. Historical pricing is derived from the attributed Kaggle snapshot.",
        )
        await page.goto(base + "/jobs/demo-ml-0001")
        await page.get_by_role("button", name="Analyze & draft").wait_for()
        await capture(
            15,
            "02 / Inspect the opportunity",
            "Read the client brief, budget and Connects cost before starting the agents. Analysis never submits anything.",
        )
        await page.get_by_role("button", name="Analyze & draft").click()
        await page.wait_for_url("**/studio/**")
        run_ids.append(page.url.rsplit("/", 1)[1])
        await capture(
            20,
            "03 / Watch the durable graph",
            "Analyst, risk and fit run in parallel. Qwen local models write/review; every node is saved and traced.",
        )
        await page.get_by_role("button", name="Approve proposal", exact=True).wait_for(timeout=120000)
        if not await page.get_by_role("button", name="Approve proposal", exact=True).is_enabled():
            raise RuntimeError("Real model draft did not reach approval; inspect the saved run")
        for summary in await page.locator("details.evidence summary").all():
            await summary.click()
            break
        await capture(
            20,
            "04 / Review claims and sources",
            "Exact portfolio facts carry evidence IDs. Unsupported assertions are removed before Critic and Compliance checks.",
        )
        await page.get_by_role("button", name="Approve proposal", exact=True).click()
        await page.wait_for_timeout(1500)
        await capture(
            15,
            "05 / Explicit approval, idempotent dispatch",
            "This recorded local test clicks approval in the UI. Only the synthetic simulator receives the approved proposal.",
        )
        await page.goto(base + "/messages")
        await page.get_by_role("button", name="Draft a reply").wait_for()
        await capture(
            15,
            "06 / A client reply enters the pipeline",
            "The local simulator sends a fixed labelled fixture reply. It is not evidence of real reply-rate effectiveness.",
        )
        await page.get_by_role("button", name="Draft a reply").click()
        await page.wait_for_url("**/studio/**")
        run_ids.append(page.url.rsplit("/", 1)[1])
        await page.get_by_role("button", name="Approve proposal", exact=True).wait_for(timeout=60000)
        await capture(
            20,
            "07 / Review the suggested response",
            "Conversation intent and tentative UTC calendar slots are prepared. Messages require a separate approval.",
        )
        await page.get_by_role("button", name="Approve proposal", exact=True).click()
        await page.wait_for_timeout(1000)
        await page.goto(base + "/jobs/demo-ml-0000")
        await page.get_by_role("button", name="Analyze & draft").click()
        await page.wait_for_url("**/studio/**")
        run_ids.append(page.url.rsplit("/", 1)[1])
        await page.wait_for_timeout(5000)
        await page.goto(base + "/jobs/demo-ml-0000")
        await capture(
            20,
            "08 / Scam and planted instruction caught",
            "Off-platform requests, unpaid trials and ignore-instructions text trigger risk flags. No proposal is sent.",
        )
        await page.goto(base + "/runs")
        await page.wait_for_timeout(500)
        await capture(
            20,
            "09 / Inspect the saved decision trail",
            "Runs and tool audits survive refreshes. Exact-content grants and atomic receipts prevent a retried debit from spending twice.",
        )
        await page.goto(base + "/settings")
        await page.wait_for_timeout(500)
        await capture(
            20,
            "10 / Set boundaries and review limitations",
            "Rates, Connects budgets, agency routing and memory stay visible. Official GigSim, human ratings and public hosting remain separate checks.",
        )
        await browser.close()
    writer.close()
    if len(samples) >= 30:
        samples = samples[:30]
    samples[0].save(
        ROOT / "docs/images/demo.gif", save_all=True, append_images=samples[1:], duration=1000, loop=0, optimize=True
    )
    (folder / "demo_manifest.json").write_text(
        json.dumps(
            {
                "video_seconds": count / 4,
                "fps": 4,
                "frames": count,
                "mode": health,
                "run_ids": run_ids,
                "recording": "Automated capture of real local UI/model executions, with labelled synthetic marketplace approval actions.",
            },
            indent=2,
        )
    )
    (ROOT / "runtime/smoke-session.json").write_text(json.dumps({"token": "Bearer " + auth, "run_id": run_ids[0]}))
    traces = ROOT / "docs/traces"
    traces.mkdir(exist_ok=True)
    for n, run_id in enumerate(run_ids):
        data = session.get(base + "/api/runs/" + run_id).json()
        audit = session.get(base + "/api/traces/" + run_id).json()
        (traces / f"demo-{n + 1}.json").write_text(json.dumps(mask({"run": data, "audit": audit}), indent=2))
    print("Saved 180-second MP4, 30-second GIF and sanitized local trace exports.", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
