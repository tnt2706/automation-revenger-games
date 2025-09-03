from pathlib import Path
import json
from typing import Dict, Any

METADATA_FILE = Path(__file__).parent / "metadata.json"
_METADATA_CACHE: Dict[str, Any] = {}


def get_metadata() -> Dict[str, Any]:
    global _METADATA_CACHE
    if _METADATA_CACHE:
        return _METADATA_CACHE
    if not METADATA_FILE.exists():
        raise FileNotFoundError(f"Metadata file not found: {METADATA_FILE}")
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        _METADATA_CACHE = json.load(f)
    return _METADATA_CACHE
