from pathlib import Path

# ---------------------------
# Base directories
# ---------------------------
BASE_DIR = Path(__file__).parent.parent.parent
TEMPLATE_DIR = BASE_DIR / "templates"
SCREEN_DIR = BASE_DIR / "screenshots"
OUTPUT_DIR = BASE_DIR / "output"
LOG_FILE = BASE_DIR / "result.log"

# ---------------------------
# Helper functions
# ---------------------------
def ensure_dirs():
    """Create necessary directories if they don't exist."""
    for folder in [TEMPLATE_DIR, SCREEN_DIR, OUTPUT_DIR]:
        folder.mkdir(parents=True, exist_ok=True)

def get_screenshot_path(filename: str) -> Path:
    """Return full path for a screenshot file inside SCREEN_DIR."""
    return SCREEN_DIR / filename

def get_output_path(filename: str) -> Path:
    """Return full path for an output file inside OUTPUT_DIR."""
    return OUTPUT_DIR / filename

def log_message(message: str):
    """Append a message to the log file."""
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{message}\n")
