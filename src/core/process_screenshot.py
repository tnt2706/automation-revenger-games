from pathlib import Path
import cv2
import json
from typing import List, Dict, Any, Optional

from utils.logger import write_log
from utils.opencv_utils import enhanced_template_matching, mark_final_matches, convert_numpy_types
from utils.paths import OUTPUT_DIR
from config import Config

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def process_screenshot(
    screen_path: Path,
    template_paths: List[Path],
    template_threshold: float = 0.5,
    debug: bool = True
) -> Optional[Dict[str, Any]]:
    """
    Process a screenshot and match templates.

    Args:
        screen_path (Path): Path to screenshot image
        template_paths (List[Path]): List of template image paths
        template_threshold (float): Minimum confidence threshold
        debug (bool): Draw rectangles/circles on matches if True

    Returns:
        Dict[str, Any]: Dictionary with processed info and output paths
    """
    # Load screenshot
    screen_img = cv2.imread(str(screen_path))
    if screen_img is None:
        write_log(f"❌ Cannot read screenshot: {screen_path}")
        return None

    screen_gray = cv2.cvtColor(screen_img, cv2.COLOR_BGR2GRAY)
    matches: List[Dict[str, Any]] = []

    # Process each template
    for template_path in template_paths:
        if not template_path.exists():
            write_log(f"⚠️ Template not found: {template_path}")
            continue

        template_img = cv2.imread(str(template_path))
        template_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)

        match_result = enhanced_template_matching(screen_gray, template_gray)
        if match_result and match_result['confidence'] >= template_threshold:
            x, y = match_result['location']
            h, w = match_result['template_size']
            matches.append({
                "template_name": template_path.name,
                "similarity": match_result['confidence'],
                "method": match_result['method'],
                "scale": match_result['scale'],
                "top_left": (x, y),
                "bottom_right": (x + w, y + h),
                "center": (x + w // 2, y + h // 2)
            })

    # Keep only the most confident match
    if matches:
        matches = [max(matches, key=lambda x: x['similarity'])]

    # Draw matches and prepare output
    result_img, final_matches = mark_final_matches(screen_img, matches, template_threshold, debug)
    output_img_path = OUTPUT_DIR / f"MATCHES_{screen_path.stem}.jpg"
    cv2.imwrite(str(output_img_path), result_img)

    # Prepare JSON output
    json_path = OUTPUT_DIR / f"matches_{screen_path.stem}.json"
    json_data = {
        "screen_file": screen_path.name,
        "total_matches": len(final_matches),
        "matches": final_matches,
        "db_connection": Config.get("db") 
    }
    json_data = convert_numpy_types(json_data)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    write_log(f"✅ Processed {screen_path.name}: {len(final_matches)} template matches")

    return {
        "screen_path": screen_path,
        "output_img_path": output_img_path,
        "json_path": json_path,
        "final_matches": final_matches
    }
