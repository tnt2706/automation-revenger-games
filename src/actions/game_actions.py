import asyncio
from pathlib import Path
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from utils.logger import write_log


async def capture_game_screenshot(
    page: Page, game: dict, save_dir: Path
) -> Path | None:
    """
    Capture a screenshot immediately after the page loads successfully.
    `game` should include 'gameCode', 'gameUrl', 'language'
    """
    try:
        write_log(f"🌐 Loading game page: {game['gameUrl']}")
        await page.goto(game["gameUrl"], wait_until="networkidle", timeout=100_000)
        await page.wait_for_load_state("networkidle", timeout=2_000)

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
    """
    Click at the given (x, y) coordinates repeatedly until network idle is detected.

    Returns:
      - "success" if the click succeeds and network becomes idle
      - error string describing the failure if timeout or unexpected error occurs
    """
    x, y = position
    attempt = 0

    while attempt < max_attempts:
        attempt += 1
        try:
            await page.mouse.click(x, y)

            try:
                await asyncio.wait_for(
                    page.wait_for_load_state("networkidle", timeout=idle_timeout),
                    timeout=response_timeout / 1000,
                )

                await asyncio.sleep(settle_delay)
                return "success"

            except asyncio.TimeoutError:
                return (
                    f"No network response within {response_timeout}ms "
                    f"after click #{attempt} at ({x},{y})"
                )

        except Exception as e:
            return f"Unexpected error during click #{attempt} at ({x},{y}): {e}"

    return f"Max attempts reached ({max_attempts}) without network idle at ({x},{y})"
