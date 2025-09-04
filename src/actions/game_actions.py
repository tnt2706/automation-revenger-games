import asyncio
from pathlib import Path
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from utils.logger import write_log


async def capture_game_screenshot(
    page: Page, game: dict, save_dir: Path
) -> Path | None:
    try:
        write_log(f"🌐 Loading game page: {game['gameUrl']}")

        response = await page.goto(
            game["gameUrl"], wait_until="networkidle", timeout=100_000
        )

        if response is None or response.status not in (200, 301, 302):
            write_log(
                f"⚠️ Unexpected response status: {response.status if response else 'No Response'}"
            )
            return None

        try:
            await page.wait_for_selector(
                "#game-canvas, .game-wrapper, body", timeout=15_000
            )
        except:
            write_log("⚠️ Selector not found, proceeding anyway")

        save_dir.mkdir(parents=True, exist_ok=True)

        screenshot_path = save_dir / f"{game['gameCode']}_{game['language']}.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        write_log(f"📸 Screenshot saved: {screenshot_path}")

        return screenshot_path

    except Exception as e:
        print(f"❌ Failed to capture screenshot: {e}")
        return None


async def click_by_coord(
    page: Page,
    position: tuple[int, int],
    max_attempts: int = 5,
    idle_timeout: int = 2000,
    response_timeout: int = 5000,
    settle_delay: float = 4.0,
) -> str:
    x, y = position

    for attempt in range(1, max_attempts + 1):
        try:
            await page.mouse.click(x, y)
        except Exception as e:
            continue

        try:
            # await asyncio.wait_for(
            #     page.wait_for_load_state("networkidle", timeout=idle_timeout),
            #     timeout=response_timeout / 1000,
            # )
            await asyncio.sleep(settle_delay)
            return "success"
        except asyncio.TimeoutError:
            if attempt == max_attempts:
                return f"No network response within {response_timeout}ms after {max_attempts} attempts at ({x},{y})"

    return (
        f"Max attempts reached ({max_attempts}) without successful click at ({x},{y})"
    )


async def click_multiple_times(
    page: Page,
    position: tuple[int, int],
    times: int = 80,
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
        write_log(f"📸 capture_{mode}: {output_path}")

        return output_path

    except Exception as e:
        write_log(f"❌ Failed to capture screenshot: {e}")
        return None
