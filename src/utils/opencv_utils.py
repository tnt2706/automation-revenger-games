import cv2
import numpy as np


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
