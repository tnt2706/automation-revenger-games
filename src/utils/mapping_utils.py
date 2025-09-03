from typing import List
import re


MODE_CHECK_MAP = {"btn_spin": "spin", "btn_setting": "setting"}

MODE_CHECK_REGEX = {
    r"^btn_spin.*": "spin",
    r"^btn_setting.*": "setting",
}

reverse_map = {v: k for k, v in MODE_CHECK_MAP.items()}


def map_mode_check_display(original_name: str) -> str:
    """
    Map original_name (e.g. btn_spin_xxx) -> display mode (e.g. spin)
    using regex rules.
    """
    for pattern, mapped in MODE_CHECK_REGEX.items():
        if re.match(pattern, original_name):
            return mapped

    return original_name


def reverse_mode_check(mapped_names: List[str]) -> List[str]:
    result = []
    for mapped_name in mapped_names:
        if mapped_name == "all":
            return list(MODE_CHECK_MAP.keys())
        key = reverse_map.get(mapped_name, mapped_name)
        result.append(key)

    return result
