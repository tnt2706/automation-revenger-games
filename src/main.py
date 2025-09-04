import asyncio
import time
from typing import Any, Dict
from core.process_screenshot import load_all_templates, process_screenshot
from utils.paths import (
    CAPTURE_DIR,
    init_workspace,
    get_report_path
)
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
from utils.mapping_utils import reverse_mode_check, map_mode_check_display
from utils.metadata_utils import get_all_providers, get_code_prefix
from utils.db_utils import get_all_game_by_code
from utils.http_utils import get_token_by_operator_target
from rich.markup import escape
from rich.console import Console



# Configuration constants
GAMES = ["vs5luckyphnly", "vs20fruitsw", "vs20sugarrush", "vs20olympx"]
TEMPLATE_THRESHOLD = 0.5
TOKEN = "gzu7mw8cke69dd1dpp8h9iu4"
LANGUAGE = "en"

# Performance optimization: Pre-compile frequently used strings
LOG_DIVIDER = "=" * 80
PROGRESS_DIVIDER = "[dim]" + "=" * 60 + "[/dim]"


def get_user_configurations(providers: Dict[str, Any]):
    """Get all user configurations through CLI prompts with optimized logging"""

    # Early validation to avoid unnecessary processing
    if not providers:
        write_log("⚠️ No providers available, exiting.")
        return None, None, None, None

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
    write_log(LOG_DIVIDER)

    return env, oc, execution_mode, modes


async def capture_game_for_mode(token, language, page, game, url_templates, oc):
    """Optimized game URL preparation and screenshot capture"""
    game_code = game.get("code")
    if not game_code:
        raise ValueError("Game code is missing")

    # Pre-validate required template
    url_pp_template = url_templates.get("pp")
    if not url_pp_template:
        raise ValueError("PP URL template is missing")

    try:
        # Use f-string formatting for better performance
        game_url = url_pp_template.format(
            gameCode=game_code, oc=oc, token=token, language=language
        )

        # Create minimal game data object
        game_data = {
            "gameCode": game_code,
            "language": LANGUAGE,
            "gameUrl": game_url,
        }

        screenshot_path = await capture_game_screenshot(page, game_data, CAPTURE_DIR)
        return screenshot_path

    except Exception as e:
        write_log(f"❌ Error capturing game {game_code}: {str(e)}")
        raise  # Re-raise to let caller handle


async def run_game(game, token, language, page, loaded_templates, screenshot_path):
    """Optimized game runner using pre-loaded templates"""
    try:
        # Use optimized processing with pre-loaded templates
        result = process_screenshot(
            game,
            token,
            language,
            screenshot_path,
            loaded_templates,
            template_threshold=TEMPLATE_THRESHOLD,
            debug=True,
        )

        matches = result.get("final_matches", [])
        if not matches:
            return "No matches found"

        # Get first match position
        position = matches[0]["center"]
        click_result = await click_by_coord(page, position)

        if click_result != "success":
            return f"Click failed at {position}: {click_result}"

        return "success"

    except Exception as e:
        write_log(f"❌ Error in run_game: {str(e)}")
        return f"Unexpected error: {e}"


async def process_single_game(
    token,
    language,
    page,
    game,
    url_templates,
    oc,
    modes,
    stats,
    console,
    execution_mode,
    templates_cache,
):
    """Optimized single game processing with better error handling and performance"""
    game_code = game.get("code")
    game_name = game.get("name")

    try:
        write_log(LOG_DIVIDER)
        report_path = get_report_path(token, language )

        # Manual confirmation optimization
        if execution_mode == "manual":
            if not await _handle_manual_confirmation(game_code):
                return

        console.print(
            f"[bold yellow]🎮 Running Game: {game_name} ({game_code})[/bold yellow]"
        )
        game_start_time = time.time()

        screenshot_path = await _capture_screenshot_with_retry(
            token, language, page, game, url_templates, oc
        )

        if not screenshot_path:
            write_log(f"❌ Failed to capture screenshot for game {game_code}")
            _record_failed_results(report_path, game, modes, stats, "Screenshot capture failed")
            return

        # Process each mode efficiently
        await _process_modes_for_game(
            token, language, page, game, modes, templates_cache, screenshot_path, stats
        )

        # Show completion with optimized time formatting
        _show_game_completion(console, game_name, game_code, game_start_time)

    except Exception as e:
        write_log(f"❌ Critical error processing game {game_code}: {str(e)}")
        console.print(f"[red]❌ Critical error in game {game_code}: {str(e)}[/red]")
        _record_failed_results(report_path, game, modes, stats, f"Critical game error: {str(e)}")


async def _handle_manual_confirmation(game_code: str) -> bool:
    """Handle manual confirmation with timeout"""
    try:
        proceed = await ask_confirmation(
            f"Do you want to run game {game_code}?", timeout=5
        )
        if not proceed:
            write_log(f"⏭️ Skipping game {game_code} as per user choice.")
            return False
        return True
    except Exception as e:
        write_log(
            f"⚠️ Error in manual confirmation for {game_code}: {e}, proceeding automatically"
        )
        return True


async def _capture_screenshot_with_retry(
    token, language, page, game, url_templates, oc, max_retries=2
):
    """Capture screenshot with retry logic"""
    for attempt in range(max_retries):
        try:
            return await capture_game_for_mode(
                token, language, page, game, url_templates, oc
            )
        except Exception as e:
            if attempt == max_retries - 1:  # Last attempt
                write_log(
                    f"❌ Final screenshot capture failed for {game.get('code')}: {str(e)}"
                )
                return None
            write_log(f"⚠️ Screenshot attempt {attempt + 1} failed, retrying: {str(e)}")
            await asyncio.sleep(1)  # Brief delay before retry


async def _process_modes_for_game(
    token, language, page, game, modes, templates_cache, screenshot_path, stats
):
    
    
    report_path = get_report_path(token, language )
    
    for mode in modes:
        try:
            loaded_templates = templates_cache.get(mode, [])

            if not loaded_templates:
                write_log(f"⚠️ No templates found for mode={mode}")
                stats.add_result(mode, "failed")
                write_csv_log(
                    report_path, game, map_mode_check_display(mode), "⚠️", "No templates found"
                )
                continue

            result = await run_game(
                game, token, language, page, loaded_templates, screenshot_path
            )

            icon, status, message_error = _process_game_result(result)

            stats.add_result(mode, status)
            write_csv_log(report_path, game, map_mode_check_display(mode), icon, message_error)
            write_log(
                f"{icon} Game {game.get('code')} (mode={map_mode_check_display(mode)}): {result}"
            )

        except Exception as e:
            write_log(
                f"❌ Error processing mode {mode} for game {game.get('code')}: {str(e)}"
            )
            stats.add_result(mode, "failed")
            write_csv_log(
                report_path,
                game,
                map_mode_check_display(mode),
                "❌",
                f"Mode processing error: {str(e)}",
            )


def _process_game_result(result: str) -> tuple:
    """Process game result and return status indicators"""
    if result == "success":
        return "✅", "success", ""
    elif result.startswith("No matches") or result.startswith("Failed"):
        return "⚠️", "failed", result
    else:
        return "❌", "failed", result


def _record_failed_results(report_path, game, modes, stats, error_message):
    """Record failed results for all modes"""
    for mode in modes:
        stats.add_result(mode, "failed")
        write_csv_log(report_path, game, map_mode_check_display(mode), "❌", error_message)


def _show_game_completion(console, game_name, game_code, start_time):
    """Show game completion with optimized formatting"""
    elapsed = time.time() - start_time
    minutes, seconds = divmod(int(elapsed), 60)
    console.print(
        f"🏁 [green]Completed Game:[/green] [bold yellow]{game_name}[/bold yellow] "
        f"([cyan]{game_code}[/cyan]) (Runtime: [magenta]{minutes:02d}:{seconds:02d}[/magenta])"
    )
    console.print(PROGRESS_DIVIDER)


async def run_all_games_optimized(
    env, token, language, oc, modes, execution_mode, games, url_templates, conn
):
    """Optimized main game runner with better resource management"""
    console = Console()
    stats = GameStatistics()

    browser_manager = None
    browser = None
    page = None

    try:
        templates_cache = load_all_templates(oc, modes)
        if not any(templates_cache.values()):
            write_log("❌ No templates loaded for any mode, exiting")
            return

        browser_manager = BrowserManager(headless=False)
        browser = await browser_manager.launch()
        page = await browser.new_page()

        await page.set_viewport_size({"width": 1280, "height": 720})

        print("\n")
        print_banner(
            console,
            f"🎮✨ Starting Game Checks in [bold green]{escape(env.upper())}[/bold green] environment "
            f"for OC: [bold cyan]{escape(oc)}[/bold cyan] "
            f"and token: [bold magenta]{escape(token)}[/bold magenta]",
            width=10,
        )
        print("\n")

        total_games = len(games)
        console.print(
            f"[bold cyan]📊 Total games to process: {total_games}[/bold cyan]"
        )

        completed_games = 0
        failed_games = 0

        for i, game in enumerate(games, 1):
            try:
                console.print(
                    f"\n[bold blue]📋 Progress: {i}/{total_games}[/bold blue]"
                )

                await process_single_game(
                    token,
                    language,
                    page,
                    game,
                    url_templates,
                    oc,
                    modes,
                    stats,
                    console,
                    execution_mode,
                    templates_cache,
                )
                completed_games += 1

            except Exception as e:
                game_code = game.get("code", "unknown")
                write_log(f"❌ Unhandled error processing game {game_code}: {str(e)}")
                console.print(
                    f"[red]❌ Unhandled error in game {game_code}, continuing...[/red]"
                )
                failed_games += 1
                continue

        # Enhanced completion summary
        console.print(
            f"\n[bold green]📊 Processing Summary: {completed_games}/{total_games} games processed"
        )
        if failed_games > 0:
            console.print(
                f"[bold red]⚠️ {failed_games} games had critical errors[/bold red]"
            )
        console.print("[/bold green]")

    except Exception as e:
        write_log(f"❌ Critical error in run_all_games_optimized: {str(e)}")
        console.print(f"[red]❌ Critical system error: {str(e)}[/red]")

    finally:
        await _cleanup_resources(browser_manager, conn)

    try:
        stats.print_final_summary(console)
    except Exception as e:
        write_log(f"⚠️ Error printing final summary: {str(e)}")


async def _cleanup_resources(browser_manager, conn):
    cleanup_tasks = []

    if browser_manager:
        cleanup_tasks.append(_close_browser(browser_manager))

    if conn:
        cleanup_tasks.append(_close_db_connection(conn))

    if cleanup_tasks:
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)


async def _close_browser(browser_manager):
    try:
        await browser_manager.close()
        write_log("✅ Browser closed successfully")
    except Exception as e:
        write_log(f"⚠️ Error closing browser: {str(e)}")


async def _close_db_connection(conn):
    """Close DB connection asynchronously"""
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, conn.close)
        write_log("✅ DB connection closed")
        write_log("🎮 Game Checks Completed Successfully !!!")
    except Exception as e:
        write_log(f"⚠️ Error closing DB connection: {str(e)}")


def validate_configuration(
    env, oc, modes, db_config, game_config, games, url_templates
):
    """Validate all configuration before processing"""
    validations = [
        (env and oc and modes, "Missing basic configuration"),
        (db_config, "No DB config found"),
        (game_config, "No game config found"),
        (game_config.get("operatorTarget"), "No operatorTarget found in game config"),
        (url_templates.get("pp"), "No PP URL template found in game config"),
    ]

    for condition, error_msg in validations:
        if not condition:
            write_log(f"⚠️ {error_msg}")
            return False
    return True


def main():
    """Optimized main function with better error handling and validation"""
    console = Console()

    try:
        # Initialize workspace
        init_workspace()
        write_log("✅ Workspace initialized successfully")

        # Get all providers from metadata
        providers = get_all_providers()
        if not providers:
            write_log("⚠️ No providers available!")
            return

        # Get user configurations
        env, oc, execution_mode, modes = get_user_configurations(providers)
        if not all([env, oc, modes]):
            return

        # Load config with selected env
        Config.load(env)
        write_log(f"✅ Loaded config for ENV={env}")

        # Get configurations with validation
        db_config = Config.get("db")
        game_config = Config.get("game")

        # Get database connection
        conn = get_db_connection(db_config)
        if not conn:
            write_log("⚠️ Failed to connect to DB!")
            return

        # Get token
        operator_target = game_config.get("operatorTarget")
        token = get_token_by_operator_target(
            operator_target=operator_target,
            currency="USD",
            language="en",
        )

        if not token:
            write_log("⚠️ Failed to obtain player token!")
            return

        language = LANGUAGE
        if not language:
            write_log("⚠️ Language not set, defaulting to 'en'")
            return

        # Get games
        code_prefix = get_code_prefix(providers, oc)
        games = get_all_game_by_code(code_prefix, db_config)

        url_templates = game_config.get("urlTemplates", {})

        # Final validation
        if not validate_configuration(
            env, oc, modes, db_config, game_config, games, url_templates
        ):
            return

        #

        # Run optimized game processing
        asyncio.run(
            run_all_games_optimized(
                env,
                token,
                language,
                oc,
                modes,
                execution_mode,
                games,
                url_templates,
                conn,
            )
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
