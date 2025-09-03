import asyncio
import time
from typing import Any, Dict, List, Optional
from core.process_screenshot import process_screenshot
from utils.paths import TEMPLATE_DIR, CAPTURE_DIR, init_workspace, ensure_dirs
from config import Config
from utils.logger import write_log, print_banner
from utils.db_utils import get_db_connection
from actions.game_actions import capture_game_screenshot, click_by_coord
from core.browser_manager import BrowserManager
from utils.csv_logger import write_csv_log
from cli.prompts import (
    ask_environment,
    ask_games,
    ask_execution_mode,
    ask_confirmation,
    ask_check_modes,
)
from utils.statistics import GameStatistics
from rich.console import Console
from utils.mapping_utils import reverse_mode_check, map_mode_check_display
from utils.metadata_utils import get_all_providers, get_code_prefix
from utils.db_utils import get_all_game_by_code
from utils.http_utils import get_token_by_operator_target


GAMES = ["vs5luckyphnly", "vs20fruitsw", "vs20sugarrush", "vs20olympx"]
# GAMES =['vs20sugarrush', 'vs20olympx']
TEMPLATE_THRESHOLD = 0.5
TOKEN = "gzu7mw8cke69dd1dpp8h9iu4"
LANGUAGE = "en"


def load_all_templates(oc: str, modes: List[str]) -> Dict[str, List]:
    """Load all templates once at startup for all modes"""
    templates_cache = {}
    
    write_log("🔄 Loading all templates into memory...")
    start_time = time.time()
    
    for mode in modes:
        try:
            template_dir = TEMPLATE_DIR / oc / mode
            templates = list(template_dir.glob("*.png"))
            templates_cache[mode] = templates
            write_log(f"✅ Loaded {len(templates)} templates for mode: {mode}")
        except Exception as e:
            write_log(f"⚠️ Error loading templates for mode {mode}: {str(e)}")
            templates_cache[mode] = []
    
    elapsed = time.time() - start_time
    total_templates = sum(len(templates) for templates in templates_cache.values())
    write_log(f"✅ All templates loaded! Total: {total_templates} templates in {elapsed:.2f}s")
    
    return templates_cache


def get_user_configurations(providers: Dict[str, Any]):
    """Get all user configurations through CLI prompts"""

    # Ask user for environment
    env = ask_environment()
    if not env:
        write_log("⚠️ No environment selected, exiting.")
        return None, None, None, None
    write_log(f"🌍 Selected environment: {env}")

    # Ask user for games
    oc = ask_games(providers)
    if not oc:
        write_log("⚠️ No games selected, exiting.")
        return None, None, None, None
    write_log(f"🎮 Selected games: {oc}")

    # Ask user for execution mode
    execution_mode = ask_execution_mode()
    if not execution_mode:
        write_log("⚠️ No execution mode selected, exiting.")
        return None, None, None, None
    write_log(f"⚙️ Selected execution mode: {execution_mode}")

    # Ask user for check modes
    check_modes = ask_check_modes()
    if not check_modes:
        write_log("⚠️ No check modes selected, exiting.")
        return None, None, None, None

    modes = reverse_mode_check(check_modes)
    write_log(f"🔍 Selected check modes: {', '.join(modes)}")

    write_log("=" * 80)

    return env, oc, execution_mode, modes


async def capture_game_for_mode(page, game, game_config, oc):
    """Prepare game URL and capture screenshot for a specific mode."""
    try:
        game_code = game["code"]
        game_name = game["name"]

        url_pp_template = game_config.get("urlTemplates", {}).get("pp", "")
        game_url = url_pp_template.format(
            gameCode=game_code, oc=oc, token=TOKEN, language=LANGUAGE
        )

        game_data = {
            "gameCode": game_code,
            "language": LANGUAGE,
            "gameUrl": game_url,
        }

        screenshot_path = await capture_game_screenshot(page, game_data, CAPTURE_DIR)
        return screenshot_path

    except Exception as e:
        write_log(f"❌ Error capturing game {game.get('code', 'unknown')}: {str(e)}")
        return None


async def run_game(page, templates, screenshot_path):
    """Run checks for one game with given screenshot and templates."""
    try:
        result = process_screenshot(
            screenshot_path,
            templates,
            template_threshold=TEMPLATE_THRESHOLD,
            debug=True,
        )
        match = result.get("final_matches", [])
        if not match:
            return "No matches found"

        position = match[0]["center"]
        click_result = await click_by_coord(page, position)
        if click_result != "success":
            return f"Click failed at {position}: {click_result}"

        return "success"

    except Exception as e:
        write_log(f"❌ Error in run_game: {str(e)}")
        return f"Unexpected error: {e}"


async def process_single_game(
    page, game, game_config, oc, modes, stats, console, execution_mode, templates_cache
):
    """Process a single game with comprehensive error handling and cached templates"""
    game_code = game.get("code", "unknown")
    game_name = game.get("name", "unknown")

    try:
        write_log("=" * 80)

        if game_code == "unknown":
            write_log("⚠️ Game code is None or missing, skipping...")
            for mode in modes:
                stats.add_result(mode, "failed")
                write_csv_log(
                    game, map_mode_check_display(mode), "❌", "Game code missing"
                )
            return

        if game_name == "unknown":
            write_log(f"⚠️ Game name is None for code {game_code}, using code as name")
            game_name = game_code

        if execution_mode == "manual":
            try:
                proceed = await ask_confirmation(
                    f"Do you want to run game {game_code}?", timeout=5
                )
                if not proceed:
                    write_log(f"⏭️ Skipping game {game_code} as per user choice.")
                    return
            except Exception as e:
                write_log(
                    f"⚠️ Error in manual confirmation for {game_code}: {e}, proceeding automatically"
                )

        console.print(
            f"[bold yellow]🎮 Running Game: {game_name} ({game_code})[/bold yellow]"
        )
        game_start_time = time.time()

        screenshot_path = None
        try:
            screenshot_path = await capture_game_for_mode(page, game, game_config, oc)
        except Exception as e:
            write_log(
                f"❌ Critical error capturing screenshot for {game_code}: {str(e)}"
            )
            screenshot_path = None

        if not screenshot_path:
            write_log(f"❌ Failed to capture screenshot for game {game_code}")
            for mode in modes:
                stats.add_result(mode, "failed")
                write_csv_log(
                    game,
                    map_mode_check_display(mode),
                    "❌",
                    "Screenshot capture failed",
                )
            return

        # Process each mode with individual error handling using cached templates
        for mode in modes:
            try:
                # Get templates from cache instead of loading from disk
                templates = templates_cache.get(mode, [])

                if not templates:
                    write_log(f"⚠️ No templates found for mode={mode}")
                    stats.add_result(mode, "failed")
                    write_csv_log(
                        game, map_mode_check_display(mode), "⚠️", "No templates found"
                    )
                    continue

                result = await run_game(page, templates, screenshot_path)

                message_error = ""
                if result == "success":
                    icon = "✅"
                    status = "success"
                elif result.startswith("No matches") or result.startswith("Failed"):
                    icon = "⚠️"
                    status = "failed"
                    message_error = result
                else:
                    icon = "❌"
                    status = "failed"
                    message_error = result

                stats.add_result(mode, status)
                write_csv_log(game, map_mode_check_display(mode), icon, message_error)
                write_log(
                    f"{icon} Game {game_code} (mode={map_mode_check_display(mode)}): {result}"
                )

            except Exception as e:
                write_log(
                    f"❌ Error processing mode {mode} for game {game_code}: {str(e)}"
                )
                stats.add_result(mode, "failed")
                write_csv_log(
                    game,
                    map_mode_check_display(mode),
                    "❌",
                    f"Mode processing error: {str(e)}",
                )

        # Show game completion with elapsed time
        game_elapsed = time.time() - game_start_time
        minutes, seconds = divmod(int(game_elapsed), 60)
        console.print(
            f"[green]Completed Game: {game_name} ({game_code}) (Runtime: {minutes:02d}:{seconds:02d})[/green]"
        )
        console.print("[dim]" + "=" * 60 + "[/dim]")

    except Exception as e:
        write_log(f"❌ Critical error processing game {game_code}: {str(e)}")
        console.print(f"[red]❌ Critical error in game {game_code}: {str(e)}[/red]")
        # Still log failed results for all modes
        for mode in modes:
            stats.add_result(mode, "failed")
            write_csv_log(
                game,
                map_mode_check_display(mode),
                "❌",
                f"Critical game error: {str(e)}",
            )


async def run_all_games(env, oc, modes, execution_mode, games, game_config, conn):
    console = Console()
    stats = GameStatistics()

    browser_manager = None
    browser = None
    page = None

    try:
        # Load all templates once at the beginning
        templates_cache = load_all_templates(oc, modes)
        
        browser_manager = BrowserManager(headless=False)
        browser = await browser_manager.launch()
        page = await browser.new_page()
        print("\n")
        print_banner(
            console,
            f"🎮✨ Starting Game Checks in {env.upper()} environment for OC: {oc}",
            width=10,
        )

        total_games = len(games)
        console.print(
            f"[bold cyan]📊 Total games to process: {total_games}[/bold cyan]"
        )

        completed_games = 0

        for i, game in enumerate(games, 1):
            try:
                console.print(
                    f"\n[bold blue]📋 Progress: {i}/{total_games}[/bold blue]"
                )
                await process_single_game(
                    page, game, game_config, oc, modes, stats, console, execution_mode, templates_cache
                )
                completed_games += 1

            except Exception as e:
                game_code = game.get("code", "unknown")
                write_log(f"❌ Unhandled error processing game {game_code}: {str(e)}")
                console.print(
                    f"[red]❌ Unhandled error in game {game_code}, continuing with next game...[/red]"
                )
                continue

        console.print(
            f"\n[bold green]📊 Processing Summary: {completed_games}/{total_games} games processed[/bold green]"
        )

    except Exception as e:
        write_log(f"❌ Critical error in run_all_games: {str(e)}")
        console.print(f"[red]❌ Critical system error: {str(e)}[/red]")

    finally:
        # Cleanup resources safely
        try:
            if browser_manager:
                await browser_manager.close()
                write_log("✅ Browser closed successfully")
        except Exception as e:
            write_log(f"⚠️ Error closing browser: {str(e)}")

        try:
            if conn:
                conn.close()
                write_log("✅ DB connection closed")
        except Exception as e:
            write_log(f"⚠️ Error closing DB connection: {str(e)}")

    # Print final summary by mode
    try:
        stats.print_final_summary(console)
    except Exception as e:
        write_log(f"⚠️ Error printing final summary: {str(e)}")


def main():
    console = Console()

    try:
        # Initialize workspace
        init_workspace()
        ensure_dirs()
        write_log("✅ Workspace initialized successfully")

        # Get player token from operator API
        token = get_token_by_operator_target(
            operator_target="https://operator-demo.dev.revenge-games.com",
            currency="USD",
            language="en",
        )

        # Get all providers from metadata
        providers = get_all_providers()

        # Get user configurations
        env, oc, execution_mode, modes = get_user_configurations(providers)
        if not all([env, oc, modes]):
            return

        # Load config with selected env
        Config.load(env)
        write_log(f"✅ Loaded config for ENV={env}")

        db_config = Config.get("db")
        if not db_config:
            write_log("⚠️ No DB config found!")
            return

        game_config = Config.get("game")
        if not game_config:
            write_log("⚠️ No game config found!")
            return

        conn = get_db_connection(db_config)

        code_prefix = get_code_prefix(providers, oc)
        games = get_all_game_by_code(code_prefix, db_config)

        if not games:
            write_log("⚠️ No games found to process!")
            return

        asyncio.run(
            run_all_games(env, oc, modes, execution_mode, games, game_config, conn)
        )

        console.print(
            "\n[bold green]✅ All checks completed![/bold green] 🚀 Exiting... 👋"
        )

    except KeyboardInterrupt:
        write_log("🛑 Process interrupted by user")
        console.print("\n[yellow]🛑 Process interrupted by user[/yellow]")

    except Exception as e:
        write_log(f"❌ Critical error in main: {str(e)}")
        console.print(f"[red]❌ Critical system error: {str(e)}[/red]")


if __name__ == "__main__":
    main()