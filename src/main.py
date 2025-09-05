import asyncio
import time
from typing import Any, Dict, List
from core.process_screenshot import (
    load_all_templates,
    process_screenshot_batch,
)
from utils.paths import (
    CAPTURE_DIR,
    init_workspace,
    get_report_path,
    get_output_path,
    clear_outputs,
)
from config import Config
from utils.logger import write_log, print_banner, set_log_path
from actions.game_actions import (
    capture_game_screenshot,
    click_by_coord,
    click_multiple_times,
    capture_screenshot,
)
from core.browser_manager import BrowserManager
from utils.csv_logger import write_csv_log
from cli.prompts import (
    ask_environment,
    ask_games,
    ask_execution_mode,
    ask_confirmation,
    ask_check_modes,
    ask_delete_output,
    ask_currency,
    ask_language,
)
from utils.statistics import GameStatistics
from utils.mapping_utils import (
    reverse_mode_check,
    map_mode_check_display,
    is_mode_add_or_sub,
)
from utils.metadata_utils import (
    get_all_providers,
    get_all_currencies,
    get_all_languages,
)

from utils.response_tracker import set_current_mode, set_game_info

from utils.http_utils import get_token_by_operator_target, fetch_games_data
from rich.markup import escape
from rich.console import Console

TEMPLATE_THRESHOLD = 0.5
LOG_DIVIDER = "=" * 80
PROGRESS_DIVIDER = "[dim]" + "=" * 60 + "[/dim]"


def get_user_configurations(
    providers: Dict[str, Any], languages: Dict[str, Any], currencies: List[str]
):

    if not providers or not languages or not currencies:
        write_log("⚠️ No input available, exiting.")
        return None, None, None, None, None, None, None

    output_deletion = ask_delete_output()

    # Ask user for environment
    env = ask_environment()
    if not env:
        write_log("⚠️ No environment selected, exiting.")
        return None, None, None, None, None, None, None
    write_log(f"🌍 Selected environment: {env}")

    # Ask user for games
    oc = ask_games(providers)
    if not oc:
        write_log("⚠️ No games selected, exiting.")
        return None, None, None, None, None, None, None
    write_log(f"🎮 Selected games: {oc}")

    # Ask user for language
    language = ask_language(languages)
    if not language:
        write_log("⚠️ No language selected, exiting.")
        return None, None, None, None, None, None, None
    write_log(f"🎮 Selected language: {language}")

    # Ask user for currency
    currency = ask_currency(currencies)
    if not currency:
        write_log("⚠️ No currencies selected, exiting.")
        return None, None, None, None, None, None, None
    write_log(f"🎮 Selected currency: {currency}")

    # Ask user for execution mode
    execution_mode = ask_execution_mode()
    if not execution_mode:
        write_log("⚠️ No execution mode selected, exiting.")
        return None, None, None, None, None, None, None
    write_log(f"⚙️ Selected execution mode: {execution_mode}")

    # Ask user for check modes
    check_modes = ask_check_modes()
    if not check_modes:
        write_log("⚠️ No check modes selected, exiting.")
        return None, None, None, None, None, None, None

    modes = reverse_mode_check(check_modes)
    write_log(f"🔍 Selected check modes: {', '.join(modes)}")
    write_log(LOG_DIVIDER)

    return output_deletion, env, oc, execution_mode, modes, language, currency


async def screenshot_game(token, language, page, game, url_templates, oc):
    game_code = game.get("code")
    if not game_code:
        raise ValueError("Game code is missing")

    url_pp_template = url_templates.get("pp")
    if not url_pp_template:
        raise ValueError("PP URL template is missing")

    try:
        game_url = url_pp_template.format(
            gameCode=game_code, oc=oc, token=token, language=language
        )

        game_data = {
            "gameCode": game_code,
            "language": language,
            "gameUrl": game_url,
        }

        screenshot_path = await capture_game_screenshot(page, game_data, CAPTURE_DIR)
        return screenshot_path

    except Exception as e:
        write_log(f"❌ Error capturing game {game_code}: {str(e)}")
        raise


async def _capture_stage_screenshot(
    token, game_code, language, mode_display, stage, page
):
    try:
        file_name = f"capture_{stage}.jpg"
        output_path = (
            get_output_path(token, game_code, language) / mode_display / file_name
        )

        await asyncio.sleep(0.5)

        await capture_screenshot(page, output_path, f"{mode_display}_{stage}")
        return True

    except Exception as e:
        write_log(
            f"⚠️ Screenshot capture failed at stage '{stage}' for mode {mode_display}: {str(e)}"
        )
        return False


async def execute_click(token, language, game_code, mode, result_dict, page):
    mode_display = map_mode_check_display(mode)
    screenshot_captured = False

    try:
        is_add_or_sub = is_mode_add_or_sub(mode)
        result = result_dict.get(mode)
        if not result:
            return f"No result found for mode: {mode}"

        matches = result.get("final_matches", [])
        if not matches:
            return "No matches found"

        position = matches[0]["center"]

        screenshot_captured = await _capture_stage_screenshot(
            token, game_code, language, mode_display, "before_click", page
        )

        async def do_click(pos, multiple=False):
            click_fn = click_multiple_times if multiple else click_by_coord
            click_result = await click_fn(page, pos)
            if click_result != "success":
                raise RuntimeError(f"Click failed at {pos}: {click_result}")

        if is_add_or_sub:
            await do_click(position, multiple=True)

            await _capture_stage_screenshot(
                token, game_code, language, mode_display, mode_display, page
            )

            result_spin = result_dict.get("btn_spin")
            if not result_spin or not result_spin.get("final_matches"):
                return f"Spin button not found after clicking {position}"

            spin_position = result_spin["final_matches"][0]["center"]
            await do_click(spin_position)

            await _capture_stage_screenshot(
                token, game_code, language, mode_display, "after_spin", page
            )

        else:
            await do_click(position)
            await _capture_stage_screenshot(
                token, game_code, language, mode_display, "after_click", page
            )

        return "success"

    except Exception as e:
        write_log(f"❌ Error in execute_click: {str(e)}")
        return f"Unexpected error: {e}"

    finally:
        if not screenshot_captured:
            try:
                write_log(f"🔄 Attempting fallback screenshot for mode {mode_display}")
                await _capture_stage_screenshot(
                    token, game_code, language, mode_display, "fallback", page
                )
            except Exception as e:
                write_log(
                    f"❌ Fallback screenshot also failed for mode {mode_display}: {str(e)}"
                )


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
    game_code = game.get("code")
    game_name = game.get("name")

    try:
        write_log(LOG_DIVIDER)
        report_path = get_report_path(token, language)

        if execution_mode == "manual":
            if not await _handle_manual_confirmation(game_code):
                return

        console.print(
            f"[bold yellow]🎮 Running Game: {game_name} ({game_code})[/bold yellow]"
        )

        game_start_time = time.time()

        write_log(f"Running Game: {game_name} - code: {game_code}")

        screenshot_path = await _capture_screenshot_with_retry(
            token, language, page, game, url_templates, oc
        )

        if not screenshot_path:
            write_log(f"❌ Failed to capture screenshot for game {game_code}")
            _record_failed_results(
                report_path, game, modes, stats, "Screenshot capture failed"
            )
            return

        set_game_info(
            game_code, 
            game_name,
            language,
            token,
            page
        )

        await _process_capture_screenshot(
            token, language, page, game, modes, templates_cache, screenshot_path, stats
        )

        _show_game_completion(console, game_name, game_code, game_start_time)

    except Exception as e:
        write_log(f"❌ Critical error processing game {game_code}: {str(e)}")
        console.print(f"[red]❌ Critical error in game {game_code}: {str(e)}[/red]")
        _record_failed_results(
            report_path, game, modes, stats, f"Critical game error: {str(e)}"
        )


async def _handle_manual_confirmation(game_code: str) -> bool:
    try:
        proceed = await ask_confirmation(
            f"\nDo you want to run game {game_code}?", timeout=5
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
    for attempt in range(max_retries):
        try:
            write_log(
                f"📸 Capturing screenshot for game {game.get('code')} (attempt {attempt + 1})"
            )
            return await screenshot_game(token, language, page, game, url_templates, oc)
        except Exception as e:
            if attempt == max_retries - 1:  # Last attempt
                write_log(
                    f"❌ Final screenshot capture failed for {game.get('code')}: {str(e)}"
                )
                return None
            write_log(f"⚠️ Screenshot attempt {attempt + 1} failed, retrying: {str(e)}")
            await asyncio.sleep(1)  # Brief delay before retry


async def _process_capture_screenshot(
    token, language, page, game, modes, templates_cache, screenshot_path, stats
):
    report_path = get_report_path(token, language)
    game_code = game.get("code")

    write_log(f"🔍 Processing screenshot for game {game_code} with {len(modes)} modes")

    result_dict = process_screenshot_batch(
        game,
        token,
        language,
        screenshot_path,
        templates_cache,
        modes,
        template_threshold=TEMPLATE_THRESHOLD,
        debug=True,
    )

    write_log(f"✅ Screenshot processing completed for game {game_code}")

    for mode in modes:
        await _handle_single_mode_result(
            token, language, game, mode, result_dict, page, stats, report_path
        )


async def _handle_single_mode_result(
    token, language, game, mode, result_dict, page, stats, report_path
):
    """Handle processing result for a single mode"""
    try:
        game_code = game.get("code")
        mode_display = map_mode_check_display(mode)

        set_current_mode(mode_display)

        result = result_dict.get(mode)
        if result is None:
            write_log(f"⚠️ No result returned for mode {mode_display}, skipping...")
            stats.add_result(mode, "skipped")
            write_csv_log(
                report_path,
                game,
                mode_display,
                "⚠️",
                "No result returned",
            )
            return

        click_result = await execute_click(
            token, language, game_code, mode, result_dict, page
        )
        icon, status, error_msg = _process_game_result(click_result)

        stats.add_result(mode, status)
        write_csv_log(report_path, game, mode_display, icon, error_msg)
        write_log(f"{icon} Game {game_code} (mode={mode_display}): {click_result}")

    except Exception as e:
        error_message = f"Mode processing error: {str(e)}"
        write_log(
            f"❌ Error processing mode {mode} for game {game.get('code')}: {str(e)}"
        )
        stats.add_result(mode, "failed")
        write_csv_log(
            report_path,
            game,
            map_mode_check_display(mode),
            "❌",
            error_message,
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
    for mode in modes:
        stats.add_result(mode, "failed")
        write_csv_log(
            report_path, game, map_mode_check_display(mode), "❌", error_message
        )

def _show_game_completion(console, game_name, game_code, start_time):
    elapsed = time.time() - start_time
    minutes, seconds = divmod(int(elapsed), 60)
    console.print(
        f"🏁 [green]Completed Game:[/green] [bold yellow]{game_name}[/bold yellow] "
        f"([cyan]{game_code}[/cyan]) (Runtime: [magenta]{minutes:02d}:{seconds:02d}[/magenta])"
    )
    console.print(PROGRESS_DIVIDER)


async def run_all_games(
    env, token, language, oc, modes, execution_mode, games, url_templates
):
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

        # await page.set_viewport_size({"width": 1280, "height": 720})

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
            if i < 5:
                continue
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

        console.print(
            f"\n[bold green]📊 Processing Summary: {completed_games}/{total_games} games processed"
        )
        if failed_games > 0:
            console.print(
                f"[bold red]⚠️ {failed_games} games had critical errors[/bold red]"
            )
        console.print("[/bold green]")

    except Exception as e:
        write_log(f"❌ Critical error in run_all_games: {str(e)}")
        # console.print(f"[red]❌ Critical system error: {str(e)}[/red]")

    finally:
        await _cleanup_resources(browser_manager)

    try:
        stats.print_final_summary(console)
    except Exception as e:
        write_log(f"⚠️ Error printing final summary: {str(e)}")


async def _cleanup_resources(browser_manager):
    cleanup_tasks = []

    if browser_manager:
        cleanup_tasks.append(_close_browser(browser_manager))
    
    if cleanup_tasks:
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)


async def _close_browser(browser_manager):
    try:
        await browser_manager.close()
        write_log("✅ Browser closed successfully")
    except Exception as e:
        write_log(f"⚠️ Error closing browser: {str(e)}")

def validate_configuration(
    env, oc, modes, game_config, url_templates
):
    validations = [
        (env and oc and modes, "Missing basic configuration"),
        (game_config, "No game config found"),
        (game_config.get("operatorTarget"), "No operatorTarget found in game config"),
        (url_templates.get("pp"), "No PP URL template found in game config"),
    ]

    for condition, error_msg in validations:
        if not condition:
            write_log(f"⚠️ {error_msg}")
            return False
    return True


def _get_meta_data():
    providers = get_all_providers()
    if not providers:
        write_log("⚠️ No providers available!")
        return None, None, None

    languages = get_all_languages()
    if not languages:
        write_log("⚠️ No languages available!")
        return None, None, None

    currencies = get_all_currencies()
    if not currencies:
        write_log("⚠️ No currencies available!")
        return None, None, None

    return providers, languages, currencies


def main():
    console = Console()

    try:
        # Initialize workspace
        init_workspace()
        write_log("✅ Workspace initialized successfully")

        # Get from metadata
        providers, languages, currencies = _get_meta_data()
        if not all([providers, languages, currencies]):
            return

        # Get user configurations
        output_deletion, env, oc, execution_mode, modes, language, currency = (
            get_user_configurations(providers, languages, currencies)
        )

        if not all([env, oc, modes, language, currency]):
            return

        # Clear all data in dir _output_report
        if output_deletion is True:
            clear_outputs()

        # Load config with selected e nv
        Config.load(env)
        write_log(f"✅ Loaded config for ENV={env}")

        game_config = Config.get("game")

        # Get token
        operator_target = game_config.get("operatorTarget")
        token = get_token_by_operator_target(
            operator_target=operator_target,
            currency=currency,
            language=language,
        )
        
        if not token:
            write_log("⚠️ Failed to obtain player token!")
            return

        set_log_path(token, language)
        
        sevice_game_client_target = game_config.get('serviceGameClientTarget')
        games = fetch_games_data(sevice_game_client_target, oc)

        url_templates = game_config.get("urlTemplates", {})

        if not validate_configuration(
            env, oc, modes, game_config, url_templates
        ):
            return

        # Run optimized game processing
        asyncio.run(
            run_all_games(
                env,
                token,
                language,
                oc,
                modes,
                execution_mode,
                games,
                url_templates,
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


if __name__ == "__main__":
    main()
