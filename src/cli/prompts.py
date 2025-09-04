from typing import Any, Dict, Literal, Optional, List
import questionary
import asyncio


def ask_environment() -> str:
    """Ask user which environment to run tests."""
    return questionary.select(
        "Please select environment to run tests:",
        choices=["dev", "sandbox", "production"],
        default="sandbox",
    ).ask()


def ask_games(
    providers: Dict[str, Any], default_game: Optional[str] = None
) -> Optional[str]:
    if not providers:
        return None

    choices = [
        {"name": f"{p['gameName']} (oc: {oc}) ", "value": oc}
        for oc, p in providers.items()
    ]

    return questionary.select(
        "Select OC game to run:", choices=choices, default=choices[0]
    ).ask()


def ask_execution_mode() -> Literal["auto", "manual"]:
    choices = [
        questionary.Choice(
            title="🤖 Automatic (run all selected games sequentially)", value="auto"
        ),
        questionary.Choice(title="🕹️ Manual (choose game one by one)", value="manual"),
    ]

    return questionary.select(
        "How do you want to run the games?", choices=choices, default="auto"
    ).ask()


async def ask_confirmation(
    message: str, default: bool = True, timeout: int = 5
) -> bool:
    """
    Ask yes/no confirmation from user.
    If no response within `timeout` seconds, return default.
    """
    try:
        loop = asyncio.get_running_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(
                None, lambda: questionary.confirm(message, default=default).ask()
            ),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        return default


def ask_check_modes() -> List[str]:
    """Ask user to pick one or more check modes (e.g., spin, setting, add/sub bet, ...)."""
    selected = questionary.checkbox(
        "Which checks do you want to run?",
        choices=[
            {"name": "📋 All checks", "value": "all", "checked": True},
            {"name": "🎯 Spin check", "value": "spin"},
            {"name": "⚙️ Settings check", "value": "setting"},
            {"name": "➕ Increase bet value", "value": "bet_add"},
            {"name": "➖ Decrease bet value", "value": "bet_sub"},
        ],
    ).ask()

    if not selected:
        return ["spin", "setting", "bet_add", "bet_sub"]

    if "all" in selected:
        return ["all"]

    if ("bet_add" in selected or "bet_sub" in selected) and "spin" not in selected:
        selected = ["spin"] + selected

    return selected


def ask_delete_output() -> bool:
    """Ask user whether to delete previous output data (Yes/No)."""
    return (
        questionary.select(
            "Do you want to delete all previous output data before running?",
            choices=["Yes", "No"],
            default="Yes",
        ).ask()
        == "Yes"
    )
