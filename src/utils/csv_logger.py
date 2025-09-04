import csv
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict


def now_utc_iso() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def write_csv_log(
    csv_file_path: str,game: Dict[str, str], mode_check: str, status: str, message: str = ""
):
    csv_file = csv_file_path.with_suffix(".csv")


    game_code = game["code"]
    game_name = game["name"]

    csv_headers = [
        "Timestamp",
        "Game name" "Game code",
        "Mode check",
        "Status",
        "Message",
    ]
    is_new_file = not csv_file.exists()

    with csv_file.open("a", newline="", encoding="utf-8") as csv_file:
        csv_writer = csv.writer(csv_file)

        if is_new_file:
            csv_writer.writerow(csv_headers)

        csv_writer.writerow(
            [now_utc_iso(), game_name, game_code, mode_check, status.upper(), message]
        )
