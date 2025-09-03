from pathlib import Path
from datetime import datetime, timezone
from rich.console import Console


LOG_FILE = Path("logs/result.log")
LOG_FILE.parent.mkdir(exist_ok=True, parents=True)


def now_utc_iso():
    return datetime.now(timezone.utc).isoformat()


def write_log(message: str):
    with LOG_FILE.open("a", encoding="utf-8") as f:
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
