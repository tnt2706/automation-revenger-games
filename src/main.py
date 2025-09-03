import asyncio
from pathlib import Path
from core.process_screenshot import process_screenshot
from utils.paths import TEMPLATE_DIR, SCREEN_DIR
from config import Config
from utils.logger import write_log
from utils.db_utils import get_db_connection
from actions.game_actions import capture_game_screenshot
from core.browser_manager import BrowserManager

COMMAND_TEST_CASE = 'btn_spin'
GAMES = ["vs5luckyphnly"]
TEMPLATE_THRESHOLD = 0.5

async def run_game(game_code, templates):
    browser_manager = BrowserManager(headless=False)
    browser = await browser_manager.launch()
    page = await browser.new_page()

    url_pp_teamplate = Config.get("urlTemplates", {}).get("pp")
    gameUrl = url_pp_teamplate.format(gameCode=game_code)

    game = {
        "gameCode": game_code,
        "language": "en",
        "gameUrl": gameUrl
    }

    screenshot_path = await capture_game_screenshot(page, game, SCREEN_DIR)
    if screenshot_path:
        process_screenshot(
            screenshot_path,
            templates,
            template_threshold=TEMPLATE_THRESHOLD,
            debug=True,
        )

    await browser_manager.close()


def main():
    Config.load()
    write_log(f"✅ Loaded config for ENV={Config.get('env', 'dev')}")

    db_config = Config.get("db")
    if not db_config:
        write_log("⚠️ No DB config found!")
        return

    conn = get_db_connection(db_config)

    template_dir = TEMPLATE_DIR / COMMAND_TEST_CASE

    templates = list(template_dir.glob("*.png"))
    if not templates:
        write_log("⚠️ No templates found!")
        return

    async def run_all_games():
        for game_code in GAMES:
            await run_game(game_code, templates)

    try:
        asyncio.run(run_all_games())

    finally:
        conn.close()
        write_log("✅ DB connection closed")


if __name__ == "__main__":
    main()
