import csv
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict
from utils.paths import LOG_FILE

# Ensure log file uses .csv extension
LOG_CSV_FILE = LOG_FILE.with_suffix(".csv")


def now_utc_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def write_csv_log(
    game: Dict[str, str], mode_check: str, status: str, message: str = ""
):
    """
    Append a log entry into a CSV file with columns:
    timestamp, game_code, mode_check, status, message

    Args:
        game_code: The game identifier (e.g., 'vs5luckyphnly')
        mode_check: The check mode/type being performed
        status: Test result status (success/failed/warning)
        message: Optional error or additional message
    """

    game_code = game["code"]
    game_name = game["name"]

    csv_headers = [
        "Timestamp",
        "Game name" "Game code",
        "Mode check",
        "Status",
        "Message",
    ]
    is_new_file = not LOG_CSV_FILE.exists()

    with LOG_CSV_FILE.open("a", newline="", encoding="utf-8") as csv_file:
        csv_writer = csv.writer(csv_file)

        if is_new_file:
            csv_writer.writerow(csv_headers)

        csv_writer.writerow(
            [now_utc_iso(), game_name, game_code, mode_check, status.upper(), message]
        )


def read_csv_logs(status: str | None = None) -> list[dict]:
    """
    Read log entries from the CSV file.
    If `status` (SUCCESS, ERROR, FAILED, etc.) is provided, only return logs with that status.
    """

    if not LOG_CSV_FILE.exists():
        return []

    with LOG_CSV_FILE.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        logs = list(reader)

    if status:
        return [row for row in logs if row["status"] == status.upper()]
    return logs
