import cv2
import json
from pathlib import Path
from utils.logger import write_log
from utils.paths import OUTPUT_DIR
from utils.opencv_utils import enhanced_template_matching, convert_numpy_types
from utils.mapping_utils import map_mode_check_display


def mark_final_matches(img, templates, template_threshold=0.6, debug=True):
    result_img = img.copy()
    final_matches = []
    best_templates = [t for t in templates if t["similarity"] >= template_threshold][:1]

    for i, template in enumerate(best_templates, 1):
        top_left, bottom_right, center = (
            template["top_left"],
            template["bottom_right"],
            template["center"],
        )
        similarity, template_name = template["similarity"], template["template_name"]

        cv2.rectangle(
            result_img,
            (top_left[0] - 5, top_left[1] - 5),
            (bottom_right[0] + 5, bottom_right[1] + 5),
            (0, 0, 255),
            4,
        )
        cv2.circle(result_img, center, 8, (0, 0, 255), -1)
        cv2.circle(result_img, center, 12, (255, 255, 255), 2)

        label = f"TEMPLATE MATCH #{i}"
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
            }
        )

    return result_img, final_matches


def process_screenshot(
    screen_path: Path, template_paths, template_threshold=0.6, debug=True
):
    screen_img = cv2.imread(str(screen_path))
    if screen_img is None:
        msg = f"❌ Cannot read screenshot: {screen_path}"
        write_log(msg)
        return None

    screen_gray = cv2.cvtColor(screen_img, cv2.COLOR_BGR2GRAY)
    templates = []

    for template_path in template_paths:
        template_img = cv2.imread(str(template_path))
        if template_img is None:
            continue
        template_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)
        match_result = enhanced_template_matching(screen_gray, template_gray)
        if match_result and match_result["confidence"] >= template_threshold:
            x, y = match_result["location"]
            h, w = match_result["template_size"]
            templates.append(
                {
                    "template_name": template_path.name,
                    "similarity": match_result["confidence"],
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

    action_name = map_mode_check_display(template_path.stem)
    output_path = OUTPUT_DIR / f"match_{screen_path.stem}_{action_name}.jpg"
    cv2.imwrite(str(output_path), result_img)

    return {
        "screen_path": screen_path,
        "output_path": output_path,
        "final_matches": final_matches,
        "templates_matched": len(templates),
    }
