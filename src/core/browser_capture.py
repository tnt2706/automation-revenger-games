import asyncio
from actions.game_actions import capture_game_screenshot
from core.browser_manager import BrowserManager
from pathlib import Path
from utils.paths import SCREEN_DIR
from utils.logger import write_log

async def process_games_capture(games):
    """Capture screenshots for list of games"""
    
    browser_manager = BrowserManager(headless=True)
    browser = await browser_manager.launch()
    page = await browser.new_page()

    captured_screenshots = []

    for game in games:
        screenshot_path = await capture_game_screenshot(page, game, SCREEN_DIR)
        if screenshot_path:
            captured_screenshots.append(screenshot_path)

    await browser_manager.close()
    return captured_screenshots
