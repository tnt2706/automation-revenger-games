import asyncio
from pathlib import Path
from typing import Optional
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from utils.logger import write_log
from utils.response_tracker import on_response


async def capture_game_screenshot(
    page: Page, game: dict, save_dir: Path
) -> Path | None:
    """Capture game screenshot with basic error handling"""
    try:
        write_log(f"🌐 Loading game page: {game['gameUrl']}")

        response = await page.goto(
            game["gameUrl"], wait_until="networkidle", timeout=100_000
        )

        if response is None:
            write_log("⚠️ No response received")
            return None

        if response.status not in (200, 301, 302):
            write_log(f"⚠️ Bad response status: {response.status}")
            return None

        try:
            await page.wait_for_selector("body", timeout=15_000)
            await asyncio.sleep(2)  # Give game time to load
        except Exception:
            write_log("⚠️ Timeout waiting for content, proceeding anyway")

        save_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = save_dir / f"{game['gameCode']}_{game['language']}.png"

        await page.screenshot(path=str(screenshot_path), full_page=True)

        if screenshot_path.exists() and screenshot_path.stat().st_size > 1000:
            write_log(f"📸 Screenshot saved: {screenshot_path}")
            return screenshot_path
        else:
            write_log("❌ Screenshot failed or too small")
            return None

    except Exception as e:
        write_log(f"❌ Failed to capture screenshot: {str(e)}")
        return None


async def click_by_coord(
    page: Page,
    position: tuple[int, int],
    max_attempts: int = 5,
    idle_timeout: int = 2000,  # milliseconds
    response_timeout: int = 5000,  # milliseconds
    settle_delay: float = 4.0,
    number_click: int = 3,
    click_delay: float = 0.2,  # seconds between clicks
) -> str:
    x, y = position

    if not hasattr(page, "_response_tracked"):
        try:
            if "on_response" in globals():
                page.on("response", on_response)
            page._response_tracked = True

        except Exception as e:
            write_log(f"⚠️ Failed to enable response tracking: {e}")

    for attempt in range(1, max_attempts + 1):
        try:
            for i in range(number_click):
                await page.mouse.click(x, y)
                if click_delay > 0 and i < number_click - 1:
                    await asyncio.sleep(click_delay)

            await asyncio.wait_for(
                page.wait_for_load_state("networkidle", timeout=idle_timeout / 1000),
                timeout=response_timeout / 1000,
            )

            await asyncio.sleep(settle_delay)
            return "success"

        except asyncio.TimeoutError:
            write_log(
                f"⏳ Attempt {attempt}/{max_attempts}: no response within {response_timeout}ms at ({x},{y})"
            )
        except Exception as e:
            write_log(f"⚠️ Attempt {attempt}/{max_attempts} failed: {e}")

    return (
        f"Max attempts reached ({max_attempts}) without successful click at ({x},{y})"
    )


async def click_multiple_times(
    page: Page,
    position: tuple[int, int],
    times: int = 30,
    delay: float = 0.2,
) -> str:
    x, y = position

    for i in range(times):
        try:
            await page.mouse.click(x, y)
            if delay > 0:
                await asyncio.sleep(delay)
        except Exception as e:
            return f"Error during click #{i+1} at ({x},{y}): {e}"

    return "success"


async def capture_screenshot(page: Page, output_path: Path, mode: str) -> Path | None:
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(output_path), full_page=True)

        return output_path

    except Exception as e:
        write_log(f"❌ Failed to capture screenshot: {e}")
        return None
