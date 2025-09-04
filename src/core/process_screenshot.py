import cv2
import time
from pathlib import Path
from typing import List, Dict
from utils.logger import write_log
from utils.paths import TEMPLATE_DIR, get_output_path
from utils.opencv_utils import enhanced_template_matching, convert_numpy_types
from utils.mapping_utils import map_mode_check_display


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
                    loaded_templates.append(
                        {
                            "path": template_path,
                            "gray": template_gray,
                            "name": template_path.name,
                            "original": template_img,
                        }
                    )

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


def mark_final_matches(img, templates, template_threshold=0.6, debug=True):
    result_img = img.copy()
    final_matches = []

    best_templates = [t for t in templates if t["similarity"] >= template_threshold]

    for i, template in enumerate(best_templates, 1):
        top_left, bottom_right, center = (
            template["top_left"],
            template["bottom_right"],
            template["center"],
        )
        similarity, template_name = template["similarity"], template["template_name"]
        mode = template.get("mode", "")

        cv2.rectangle(
            result_img,
            (top_left[0] - 5, top_left[1] - 5),
            (bottom_right[0] + 5, bottom_right[1] + 5),
            (0, 0, 255),
            4,
        )
        cv2.circle(result_img, center, 8, (0, 0, 255), -1)
        cv2.circle(result_img, center, 12, (255, 255, 255), 2)

        label = f"{mode}" if mode else f"TEMPLATE #{i}"
        cv2.putText(
            result_img,
            label,
            (top_left[0] + 5, top_left[1] - 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
        )

        final_matches.append(
            {
                "type": "TEMPLATE",
                "id": i,
                "name": template_name,
                "center": center,
                "confidence": similarity,
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
    template_threshold=0.6,
    debug=False,
):
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
            }
            continue

        templates_found = []
        best_confidence = 0.0

        for template_data in loaded_templates:
            if best_confidence > 0.95:
                break

            match_result = enhanced_template_matching(
                screen_gray, template_data["gray"]
            )
            if match_result and match_result["confidence"] >= template_threshold:
                confidence = match_result["confidence"]
                if confidence > best_confidence:
                    best_confidence = confidence

                x, y = match_result["location"]
                h, w = match_result["template_size"]

                templates_found.append(
                    {
                        "template_name": template_data["name"],
                        "similarity": confidence,
                        "method": match_result["method"],
                        "scale": match_result["scale"],
                        "top_left": (x, y),
                        "bottom_right": (x + w, y + h),
                        "center": (x + w // 2, y + h // 2),
                        "label": mode,
                        "mode": mode_display,
                    }
                )

        if templates_found:
            templates_found = [max(templates_found, key=lambda t: t["similarity"])]
            all_templates_found.extend(templates_found)

        dict_result[mode] = {
            "mode": mode_display,
            "final_matches": templates_found,
            "templates_matched": len(templates_found),
        }

    if all_templates_found:
        result_img, _ = mark_final_matches(
            screen_img, all_templates_found, template_threshold, debug
        )
        output_path = get_output_path(token, game_code, language) / "screenshot.jpg"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        success = cv2.imwrite(str(output_path), result_img)
        if not success:
            write_log(f"❌ Failed to write combined image to {output_path}")
        else:
            write_log(f"✅ Combined image saved: {output_path}")

    return dict_result


def process_screenshot(
    game,
    token,
    language,
    screen_path,
    loaded_templates,
    template_threshold=0.6,
    debug=True,
):

    screen_img = cv2.imread(str(screen_path))
    if screen_img is None:
        msg = f"❌ Cannot read screenshot: {screen_path}"
        write_log(msg)
        return {
            "screen_path": screen_path,
            "final_matches": [],
            "templates_matched": 0,
        }

    screen_gray = cv2.cvtColor(screen_img, cv2.COLOR_BGR2GRAY)
    templates = []
    best_confidence = 0.0

    game_code = game.get("code")

    for template_data in loaded_templates:
        if best_confidence > 0.95:  # Early termination
            break

        match_result = enhanced_template_matching(screen_gray, template_data["gray"])

        if match_result and match_result["confidence"] >= template_threshold:
            x, y = match_result["location"]
            h, w = match_result["template_size"]

            confidence = match_result["confidence"]
            if confidence > best_confidence:
                best_confidence = confidence

            templates.append(
                {
                    "template_name": template_data["name"],
                    "similarity": confidence,
                    "method": match_result["method"],
                    "scale": match_result["scale"],
                    "top_left": (x, y),
                    "bottom_right": (x + w, y + h),
                    "center": (x + w // 2, y + h // 2),
                }
            )

    if templates:
        templates = [max(templates, key=lambda x: x["similarity"])]

    result_img, final_matches = mark_final_matches(
        screen_img, templates, template_threshold, debug
    )

    output_path = get_output_path(token, game_code, language)
    if templates:
        action_name = templates[0]["template_name"].split(".")[0]
        action_display = map_mode_check_display(action_name)
        output_path = output_path / f"match_{action_display}.jpg"

        output_path.parent.mkdir(parents=True, exist_ok=True)
        success = cv2.imwrite(str(output_path), result_img)
        if not success:
            write_log(f"❌ Failed to write image to {output_path}")

    return {
        "screen_path": screen_path,
        "final_matches": final_matches,
        "templates_matched": len(templates),
    }
