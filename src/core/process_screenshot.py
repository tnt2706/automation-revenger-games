import cv2
import time
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple
from utils.logger import write_log
from utils.paths import TEMPLATE_DIR, get_output_path
from utils.opencv_utils import enhanced_template_matching, convert_numpy_types
from utils.mapping_utils import map_mode_check_display


TEMPLATE_THRESHOLDS = {
    "high": 0.85,
    "medium": 0.70,
    "low": 0.55,
    "display_min": 0.50,
}

def get_confidence_level(confidence: float) -> str:
    """Determine confidence level based on threshold values"""
    if confidence >= TEMPLATE_THRESHOLDS["high"]:
        return "high"
    elif confidence >= TEMPLATE_THRESHOLDS["medium"]:
        return "medium"
    elif confidence >= TEMPLATE_THRESHOLDS["low"]:
        return "low"
    else:
        return "very_low"
    
def convert_numpy_types(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(i) for i in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_types(i) for i in obj)
    return obj


def enhanced_template_matching(screen_img, template_img, scales=None):
    if scales is None:
        scales = [0.5, 0.7, 0.8, 0.9, 1.0, 1.1, 1.25, 1.5, 1.75, 2.0]

    methods = [
        ("TM_CCOEFF_NORMED", cv2.TM_CCOEFF_NORMED),
        ("TM_CCORR_NORMED", cv2.TM_CCORR_NORMED),
        ("TM_SQDIFF_NORMED", cv2.TM_SQDIFF_NORMED),
    ]

    best_results = []
    t_h, t_w = template_img.shape[:2]

    for method_name, method in methods:
        for scale in scales:
            scaled_template = cv2.resize(
                template_img, (int(t_w * scale), int(t_h * scale))
            )
            if (
                scaled_template.shape[0] > screen_img.shape[0]
                or scaled_template.shape[1] > screen_img.shape[1]
            ):
                continue
            res = cv2.matchTemplate(screen_img, scaled_template, method)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            if method == cv2.TM_SQDIFF_NORMED:
                match_val = 1 - min_val
                match_loc = min_loc
            else:
                match_val = max_val
                match_loc = max_loc
            best_results.append(
                {
                    "method": method_name,
                    "scale": scale,
                    "confidence": match_val,
                    "location": match_loc,
                    "template_size": scaled_template.shape[:2],
                }
            )
    best_results.sort(key=lambda x: x["confidence"], reverse=True)
    return best_results[0] if best_results else None



def get_confidence_color(confidence: float) -> Tuple[int, int, int]:
    """Get BGR color based on confidence level"""
    if confidence >= TEMPLATE_THRESHOLDS["high"]:
        return (0, 255, 0)  # Green - High confidence
    elif confidence >= TEMPLATE_THRESHOLDS["medium"]:
        return (0, 255, 255)  # Yellow - Medium confidence
    elif confidence >= TEMPLATE_THRESHOLDS["low"]:
        return (0, 165, 255)  # Orange - Low confidence
    else:
        return (0, 0, 255)  # Red - Very low confidence


def load_all_templates(oc: str, modes: List[str]) -> Dict[str, List[Dict]]:
    """Load and pre-process all templates once at startup for maximum performance"""
    templates_cache = {}

    write_log("🔄 Loading and pre-processing all templates into memory...")
    start_time = time.time()

    for mode in modes:
        try:
            template_dir = TEMPLATE_DIR / oc / mode
            template_files = list(template_dir.glob("*.png"))

            loaded_templates = []
            for template_path in template_files:
                template_img = cv2.imread(str(template_path))
                if template_img is not None:
                    template_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)

                    h, w = template_gray.shape[:2]
                    template_area = h * w

                    loaded_templates.append(
                        {
                            "path": template_path,
                            "gray": template_gray,
                            "name": template_path.name,
                            "original": template_img,
                            "size": (w, h),
                            "area": template_area,
                        }
                    )

            loaded_templates.sort(key=lambda x: x["area"])

            templates_cache[mode] = loaded_templates
            write_log(
                f"✅ Pre-processed {len(loaded_templates)} templates for mode: {mode}"
            )

        except Exception as e:
            write_log(f"⚠️ Error loading templates for mode {mode}: {str(e)}")
            templates_cache[mode] = []

    elapsed = time.time() - start_time
    total_templates = sum(len(templates) for templates in templates_cache.values())
    write_log(
        f"✅ All templates pre-processed! Total: {total_templates} templates in {elapsed:.2f}s"
    )

    return templates_cache


def mark_final_matches(img, templates, display_threshold=None, debug=True):
    """Mark matches on image with confidence-based colors and thresholds"""
    if display_threshold is None:
        display_threshold = TEMPLATE_THRESHOLDS["display_min"]

    result_img = img.copy()
    final_matches = []

    # Filter templates based on display threshold
    displayable_templates = [
        t for t in templates if t["similarity"] >= display_threshold
    ]

    for i, template in enumerate(displayable_templates, 1):
        top_left, bottom_right, center = (
            template["top_left"],
            template["bottom_right"],
            template["center"],
        )
        similarity, template_name = template["similarity"], template["template_name"]
        mode = template.get("mode", "")
        confidence_level = get_confidence_level(similarity)

        # Get color based on confidence
        color = get_confidence_color(similarity)

        # Draw rectangle with confidence-based color
        cv2.rectangle(
            result_img,
            (top_left[0] - 5, top_left[1] - 5),
            (bottom_right[0] + 5, bottom_right[1] + 5),
            color,
            4,
        )

        # Draw center point
        cv2.circle(result_img, center, 8, color, -1)
        cv2.circle(result_img, center, 12, (255, 255, 255), 2)

        # Enhanced label with confidence info
        label = (
            f"{mode} ({confidence_level})"
            if mode
            else f"TEMPLATE #{i} ({confidence_level})"
        )
        confidence_text = f"{similarity:.3f}"

        # Draw label background for better readability
        label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        conf_size = cv2.getTextSize(confidence_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[
            0
        ]

        # Label background
        cv2.rectangle(
            result_img,
            (top_left[0], top_left[1] - 45),
            (top_left[0] + max(label_size[0], conf_size[0]) + 10, top_left[1] - 5),
            (0, 0, 0),
            -1,
        )

        # Draw label text
        cv2.putText(
            result_img,
            label,
            (top_left[0] + 5, top_left[1] - 25),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )

        # Draw confidence value
        cv2.putText(
            result_img,
            confidence_text,
            (top_left[0] + 5, top_left[1] - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            color,
            2,
        )

        final_matches.append(
            {
                "type": "TEMPLATE",
                "id": i,
                "name": template_name,
                "center": center,
                "confidence": similarity,
                "confidence_level": confidence_level,
                "bbox": (
                    top_left[0],
                    top_left[1],
                    bottom_right[0] - top_left[0],
                    bottom_right[1] - top_left[1],
                ),
                "mode": mode,
            }
        )

    return result_img, final_matches


def process_screenshot_batch(
    game,
    token,
    language,
    screen_path,
    templates,
    modes,
    template_threshold=None,
    display_threshold=None,
    debug=False,
):
    """Process screenshot with enhanced thresholding system"""
    if template_threshold is None:
        template_threshold = TEMPLATE_THRESHOLDS["medium"]

    if display_threshold is None:
        display_threshold = TEMPLATE_THRESHOLDS["display_min"]

    game_code = game.get("code") if isinstance(game, dict) else str(game)

    screen_img = cv2.imread(str(screen_path))
    if screen_img is None:
        write_log(f"❌ Cannot read screenshot: {screen_path}")
        return {}

    screen_gray = cv2.cvtColor(screen_img, cv2.COLOR_BGR2GRAY)
    dict_result: dict = {}
    all_templates_found = []

    for mode in modes:
        loaded_templates = templates.get(mode, [])
        mode_display = map_mode_check_display(mode)

        if not loaded_templates:
            write_log(f"⚠️ No templates found for mode={mode}")
            dict_result[mode] = {
                "mode": mode_display,
                "final_matches": [],
                "templates_matched": 0,
                "confidence_stats": {},
            }
            continue

        templates_found = []
        best_confidence = 0.0
        confidence_stats = {"high": 0, "medium": 0, "low": 0, "very_low": 0}

        for template_data in loaded_templates:
            # Early termination optimization
            if best_confidence > 0.95:
                break

            match_result = enhanced_template_matching(
                screen_gray, template_data["gray"]
            )

            if match_result and match_result["confidence"] >= display_threshold:
                confidence = match_result["confidence"]
                confidence_level = get_confidence_level(confidence)
                confidence_stats[confidence_level.lower()] += 1

                if confidence > best_confidence:
                    best_confidence = confidence

                x, y = match_result["location"]
                h, w = match_result["template_size"]

                template_match = {
                    "template_name": template_data["name"],
                    "similarity": confidence,
                    "confidence_level": confidence_level,
                    "method": match_result["method"],
                    "scale": match_result["scale"],
                    "top_left": (x, y),
                    "bottom_right": (x + w, y + h),
                    "center": (x + w // 2, y + h // 2),
                    "label": mode,
                    "mode": mode_display,
                    "meets_threshold": confidence >= template_threshold,
                }

                templates_found.append(template_match)

        # Keep only the best match for each mode
        if templates_found:
            templates_found = [max(templates_found, key=lambda t: t["similarity"])]
            all_templates_found.extend(templates_found)

        # Count only matches that meet the main threshold for accuracy
        reliable_matches = [t for t in templates_found if t["meets_threshold"]]

        dict_result[mode] = {
            "mode": mode_display,
            "final_matches": templates_found,  # All displayable matches
            "reliable_matches": reliable_matches,  # Only reliable matches
            "templates_matched": len(reliable_matches),  # Count reliable matches
            "total_displayed": len(templates_found),  # Total displayed matches
            "confidence_stats": confidence_stats,
            "thresholds": {
                "template_threshold": template_threshold,
                "display_threshold": display_threshold,
            },
        }

    # Save screenshot with all displayable matches
    if all_templates_found:
        result_img, final_matches = mark_final_matches(
            screen_img, all_templates_found, display_threshold, debug
        )

        # Add threshold info to the image
        threshold_text = (
            f"Template: {template_threshold:.3f} | Display: {display_threshold:.3f}"
        )
        cv2.putText(
            result_img,
            threshold_text,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
        )

        output_path = get_output_path(token, game_code, language) / "screenshot.jpg"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        success = cv2.imwrite(str(output_path), result_img)

        if not success:
            write_log(f"❌ Failed to write combined image to {output_path}")
        else:
            write_log(f"✅ Combined image saved: {output_path}")

        # Log summary statistics
        reliable_count = sum(
            len(mode_data["reliable_matches"]) for mode_data in dict_result.values()
        )
        total_displayed = sum(
            len(mode_data["final_matches"]) for mode_data in dict_result.values()
        )
        write_log(
            f"📊 Summary: {reliable_count} reliable matches, {total_displayed} total displayed"
        )

    return dict_result


def process_screenshot(
    game,
    token,
    language,
    screen_path,
    loaded_templates,
    template_threshold=None,
    display_threshold=None,
    debug=True,
):
    """Enhanced single screenshot processing with dual threshold system"""
    if template_threshold is None:
        template_threshold = TEMPLATE_THRESHOLDS["medium"]

    if display_threshold is None:
        display_threshold = TEMPLATE_THRESHOLDS["display_min"]

    screen_img = cv2.imread(str(screen_path))
    if screen_img is None:
        msg = f"❌ Cannot read screenshot: {screen_path}"
        write_log(msg)
        return {
            "screen_path": screen_path,
            "final_matches": [],
            "templates_matched": 0,
            "error": msg,
        }

    screen_gray = cv2.cvtColor(screen_img, cv2.COLOR_BGR2GRAY)
    templates = []
    best_confidence = 0.0
    confidence_stats = {"high": 0, "medium": 0, "low": 0, "very_low": 0}

    game_code = game.get("code")

    write_log(
        f"🎯 Processing with template_threshold: {template_threshold:.3f}, display_threshold: {display_threshold:.3f}"
    )

    for template_data in loaded_templates:
        # Early termination optimization
        if best_confidence > 0.95:
            break

        match_result = enhanced_template_matching(screen_gray, template_data["gray"])

        if match_result and match_result["confidence"] >= display_threshold:
            x, y = match_result["location"]
            h, w = match_result["template_size"]

            confidence = match_result["confidence"]
            confidence_level = get_confidence_level(confidence)
            confidence_stats[confidence_level.lower()] += 1

            if confidence > best_confidence:
                best_confidence = confidence

            templates.append(
                {
                    "template_name": template_data["name"],
                    "similarity": confidence,
                    "confidence_level": confidence_level,
                    "method": match_result["method"],
                    "scale": match_result["scale"],
                    "top_left": (x, y),
                    "bottom_right": (x + w, y + h),
                    "center": (x + w // 2, y + h // 2),
                    "meets_threshold": confidence >= template_threshold,
                }
            )

    # Keep only the best match
    if templates:
        templates = [max(templates, key=lambda x: x["similarity"])]

    result_img, final_matches = mark_final_matches(
        screen_img, templates, display_threshold, debug
    )

    # Add threshold information to image
    threshold_text = (
        f"Template: {template_threshold:.3f} | Display: {display_threshold:.3f}"
    )
    cv2.putText(
        result_img,
        threshold_text,
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2,
    )

    output_path = get_output_path(token, game_code, language)
    if templates:
        action_name = templates[0]["template_name"].split(".")[0]
        action_display = map_mode_check_display(action_name)
        confidence = templates[0]["similarity"]
        meets_threshold = templates[0]["meets_threshold"]

        # Include confidence and threshold status in filename
        filename = f"match_{action_display}_{confidence:.3f}{'_OK' if meets_threshold else '_LOW'}.jpg"
        output_path = output_path / filename

        output_path.parent.mkdir(parents=True, exist_ok=True)
        success = cv2.imwrite(str(output_path), result_img)
        if not success:
            write_log(f"❌ Failed to write image to {output_path}")
        else:
            write_log(f"✅ Image saved: {output_path}")

    # Count only reliable matches
    reliable_matches = [t for t in templates if t["meets_threshold"]]

    return {
        "screen_path": screen_path,
        "final_matches": final_matches,
        "templates_matched": len(reliable_matches),  # Only reliable matches
        "total_displayed": len(templates),  # All displayed matches
        "confidence_stats": confidence_stats,
        "best_confidence": best_confidence,
        "thresholds": {
            "template_threshold": template_threshold,
            "display_threshold": display_threshold,
        },
    }
