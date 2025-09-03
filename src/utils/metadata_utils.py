from typing import Dict, Any
from config.metadata import get_metadata


def get_all_providers() -> Dict[str, Any]:
    metadata = get_metadata()
    return {p.get("oc"): p for p in metadata.get("providers", [])}


def get_provider(metadata: Dict[str, Any], oc: str) -> Dict[str, Any]:
    for p in metadata.get("providers", []):
        if p.get("oc") == oc:
            return p
    return {}


def get_code_prefix(provider: Dict[str, Any], oc: str) -> str:
    oc_data = provider.get(oc)
    if oc_data:
        return oc_data.get("codePrefix", "")
    return ""


def is_currency_supported(metadata: Dict[str, Any], currency: str) -> bool:
    return currency in metadata.get("currencies", [])
