from pathlib import Path
from datetime import datetime, timezone
from rich.console import Console
import shutil
from utils.paths import TEMP_DIR, OUTPUT_DIR

_LOGGER_STATE = {
    "token": None,
    "language": None,
    "folder": Path(TEMP_DIR),
    "file": Path(TEMP_DIR) / "log_activity.log",
}

_LOGGER_STATE["folder"].mkdir(parents=True, exist_ok=True)


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def set_log_path(token: str, language: str):
    new_folder = Path(OUTPUT_DIR) / f"{token}_{language}"
    new_folder.mkdir(parents=True, exist_ok=True)

    old_folder = _LOGGER_STATE["folder"]
    if old_folder.exists():
        for item in old_folder.iterdir():
            dest = new_folder / item.name
            if item.is_file():
                shutil.copy2(item, dest)
            elif item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
        shutil.rmtree(old_folder)

    _LOGGER_STATE["token"] = token
    _LOGGER_STATE["language"] = language
    _LOGGER_STATE["folder"] = new_folder
    _LOGGER_STATE["file"] = new_folder / "log_activity.log"


def write_log(message: str):
    folder = _LOGGER_STATE["folder"]
    folder.mkdir(parents=True, exist_ok=True)
    log_file = _LOGGER_STATE["file"]
    with log_file.open("a", encoding="utf-8") as f:
        f.write(f"[{now_utc_iso()}] {message}\n")


def print_banner(console, message: str, width: int = 80):
    """Print a banner line with message centered"""
    if console is None:
        console = Console()

    msg_len = len(message)
    if msg_len >= width:
        console.print(f"[dim]{message}[/dim]")
        return

    half_len = (width - msg_len) // 2
    line = "=" * half_len + f" {message} " + "=" * half_len
    if len(line) < width:
        line += "="
    console.print(f"[dim]{line}[/dim]")
