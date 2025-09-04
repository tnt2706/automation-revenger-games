from pathlib import Path
import shutil
from typing import Optional

BASE_DIR = Path(__file__).parent.parent.parent
TEMPLATE_DIR = BASE_DIR / "templates"
SCREEN_DIR = BASE_DIR / "screenshots"
CAPTURE_DIR = BASE_DIR / "captures"
OUTPUT_DIR = BASE_DIR / "_output-reports"
LOG_DIR = BASE_DIR / "logs"


def init_workspace():
    dirs = [SCREEN_DIR, CAPTURE_DIR, LOG_DIR]

    for folder in dirs:
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True, exist_ok=True)

def get_output_path(token: str, game_code: str, language: Optional[str] = "en") -> Path:
    return OUTPUT_DIR / token / (language if language else "en") / game_code


def get_report_path(token: str, language: Optional[str] = "en") -> Path:
    return OUTPUT_DIR / token / (language if language else "en") / "report.log"


def clear_captures():
    shutil.rmtree(CAPTURE_DIR)


def clear_outputs():
    shutil.rmtree(OUTPUT_DIR)