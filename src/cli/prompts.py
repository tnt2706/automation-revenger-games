from typing import Any, Dict, Literal, Optional, List
import questionary
import asyncio
from questionary import Choice


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
        Choice(title=f"{p['gameName']} (oc: {oc})", value=oc)
        for oc, p in providers.items()
    ]

    valid_values = [c.value for c in choices]

    default_value = default_game if default_game in valid_values else choices[0].value

    return questionary.select(
        "Select OC game to run:", choices=choices, default=default_value
    ).ask()


def ask_language(
    language: Dict[str, Any], default_language: Optional[str] = "en"
) -> Optional[str]:
    if not language:
        return None

    choices = [Choice(title=p["name"], value=code) for code, p in language.items()]

    default_choice = next((c for c in choices if c.value == default_language), None)

    return questionary.select(
        "Select a language to run the game:", choices=choices, default=default_choice
    ).ask()


def ask_currency(currencies: List[str]) -> str:
    if not currencies:
        raise ValueError("No currencies available to choose from.")

    return questionary.select(
        "Select a currency:",
        choices=currencies,
        default=currencies[0],
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
    try:
        loop = asyncio.get_running_loop()

        choices = ["Yes", "No"]
        default_choice = "Yes" if default else "No"

        result = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                lambda: questionary.select(
                    message,
                    choices=choices,
                    default=default_choice,
                ).ask(),
            ),
            timeout=timeout,
        )

        return result == "Yes"

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
