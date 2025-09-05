from typing import Dict, Any
from pathlib import Path
import json

METADATA_FILE = Path(__file__).parent.parent / "config" / "metadata.json"
_METADATA_CACHE: Dict[str, Any] = {}


def _get_metadata() -> Dict[str, Any]:
    global _METADATA_CACHE
    if _METADATA_CACHE:
        return _METADATA_CACHE
    if not METADATA_FILE.exists():
        raise FileNotFoundError(f"Metadata file not found: {METADATA_FILE}")
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        _METADATA_CACHE = json.load(f)
    return _METADATA_CACHE


def get_all_providers() -> Dict[str, Any]:
    metadata = _get_metadata()
    return {p.get("oc"): p for p in metadata.get("providers", [])}


def is_currency_supported(metadata: Dict[str, Any], currency: str) -> bool:
    return currency in metadata.get("currencies", [])


def get_all_currencies():
    metadata = _get_metadata()
    return metadata.get("currencies", [])


def get_all_languages() -> Dict[str, Any]:
    metadata = _get_metadata()
    return {p.get("code"): p for p in metadata.get("languages", [])}


def get_languages(metadata: Dict[str, Any], code: str) -> Dict[str, Any]:
    for p in metadata.get("languages", []):
        if p.get("code") == code:
            return p
    return {}
