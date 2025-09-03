from utils.opencv_utils import screenshot_to_cv2, find_button_position
from utils.sleep import sleep
from utils.logger import write_log
from pathlib import Path
import cv2

TEMPLATE_DIR = Path("templates/btn_spin")

async def click_template(page, template_name, retries=5):
    """Click button in game page based on template image"""
    
    template_path = TEMPLATE_DIR / template_name
    for i in range(retries):
        screenshot = await screenshot_to_cv2(page)
        pos = find_button_position(screenshot, template_path)
        print(f"Attempt {i+1}/{retries}: Looking for {template_name}, found at {pos}")
        if pos:
            await page.mouse.click(pos["x"], pos["y"])
            return True
        await sleep(1000)
    raise Exception(f"Button not found after {retries} retries: {template_name}")


async def capture_game_screenshot(page, game, screenshot_dir: Path):
    """
    Capture screenshot for 1 game and save to screenshot_dir.
    Return Path to screenshot.
    """

    game_code = game["gameCode"]
    game_url = game["gameUrl"]
    language = game["language"]

    screenshot_name = f"game_{game_code}_{language}.png"
    screenshot_path = screenshot_dir / screenshot_name

    if screenshot_path.exists():
        write_log(f"🖼 Screenshot exists: {screenshot_name}, skipping capture")
        return screenshot_path

    try:
        await page.goto(game_url, wait_until="networkidle", timeout=60000)
        print(f"Navigated to {game_url}")
        await sleep(3000)
        await click_template(page, "btn_spin.png")
        screenshot = await screenshot_to_cv2(page)
        cv2.imwrite(str(screenshot_path), screenshot)
        write_log(f"✅ Screenshot captured: {screenshot_name}")
        return screenshot_path
    except Exception as e:
        await write_log(f"❌ NG: {game_code}, {language}, URL: {game_url}, error: {e}")
        return None
