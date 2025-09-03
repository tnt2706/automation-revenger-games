from pathlib import Path
import shutil

BASE_DIR = Path(__file__).parent.parent.parent
TEMPLATE_DIR = BASE_DIR / "templates"
SCREEN_DIR = BASE_DIR / "screenshots"
CAPTURE_DIR = BASE_DIR / "captures"
OUTPUT_DIR = BASE_DIR / "_output-reports"
LOG_FILE = BASE_DIR / "_output-reports" / "report.log"
LOG_DIR = BASE_DIR / "logs"


def init_workspace():
    """
    Clean old data in logs, screenshots, output
    and recreate folders if missing.
    """

    for folder in [SCREEN_DIR, OUTPUT_DIR, CAPTURE_DIR, LOG_DIR]:
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True, exist_ok=True)


def ensure_dirs():
    for folder in [TEMPLATE_DIR, SCREEN_DIR, OUTPUT_DIR, CAPTURE_DIR, LOG_FILE.parent]:
        folder.mkdir(parents=True, exist_ok=True)
