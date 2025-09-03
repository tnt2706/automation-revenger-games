from pathlib import Path
from datetime import datetime, timezone

LOG_FILE = Path("logs/result.log")
LOG_FILE.parent.mkdir(exist_ok=True)

def now_utc_iso():
    return datetime.now(timezone.utc).isoformat()

def write_log(message):
    LOG_FILE.parent.mkdir(exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"[{now_utc_iso()}] {message}\n")