import cv2
import numpy as np
from pathlib import Path
from .logger import write_log

def convert_numpy_types(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_numpy_types(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_numpy_types(item) for item in obj)
    return obj

def enhanced_template_matching(screen_img, template_img, scales=None):
    if scales is None:
        scales = [0.5,0.7,0.8,0.9,1.0,1.1,1.25,1.5,1.75,2.0]
    methods = [
        ('TM_CCOEFF_NORMED', cv2.TM_CCOEFF_NORMED),
        ('TM_CCORR_NORMED', cv2.TM_CCORR_NORMED),
        ('TM_SQDIFF_NORMED', cv2.TM_SQDIFF_NORMED)
    ]
    best_results = []
    t_h, t_w = template_img.shape[:2]
    for method_name, method in methods:
        for scale in scales:
            try:
                scaled_template = cv2.resize(template_img, (int(t_w*scale), int(t_h*scale)))
                if scaled_template.shape[0] > screen_img.shape[0] or scaled_template.shape[1] > screen_img.shape[1]:
                    continue
                res = cv2.matchTemplate(screen_img, scaled_template, method)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
                if method == cv2.TM_SQDIFF_NORMED:
                    match_val = 1 - min_val
                    match_loc = min_loc
                else:
                    match_val = max_val
                    match_loc = max_loc
                best_results.append({
                    'method': method_name,
                    'scale': scale,
                    'confidence': match_val,
                    'location': match_loc,
                    'template_size': scaled_template.shape[:2]
                })
            except Exception:
                continue
    best_results.sort(key=lambda x: x['confidence'], reverse=True)
    return best_results[0] if best_results else None

def mark_final_matches(img, templates, template_threshold=0.6, debug=True):
    """
    Mark all templates with confidence >= threshold on the image.
    Returns image with drawn boxes and a list of all final matches.
    """
    result_img = img.copy()
    final_matches = []

    # Keep templates above threshold
    filtered_templates = [t for t in templates if t['similarity'] >= template_threshold]

    for match_count, template in enumerate(filtered_templates, start=1):
        top_left = template['top_left']
        bottom_right = template['bottom_right']
        center = template['center']
        similarity = template['similarity']
        template_name = template['template_name']

        # Draw rectangle and center circle
        cv2.rectangle(result_img, (top_left[0]-5, top_left[1]-5), 
                      (bottom_right[0]+5, bottom_right[1]+5), (0,0,255), 4)
        cv2.circle(result_img, center, 8, (0,0,255), -1)
        cv2.circle(result_img, center, 12, (255,255,255), 2)

        # Label
        label = f"TEMPLATE MATCH #{match_count}"
        label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
        cv2.rectangle(result_img, (top_left[0], top_left[1]-35), 
                      (top_left[0]+label_size[0]+10, top_left[1]-5), (0,0,255), -1)
        cv2.putText(result_img, label, (top_left[0]+5, top_left[1]-15), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255,255,255), 2)

        # Record match
        final_matches.append({
            'type':'TEMPLATE',
            'id':match_count,
            'name':template_name,
            'center':center,
            'confidence':similarity,
            'bbox':(top_left[0], top_left[1], bottom_right[0]-top_left[0], bottom_right[1]-top_left[1])
        })

        if debug:
            write_log(f"✅ TEMPLATE MATCH #{match_count}: {template_name} at {center}, confidence={similarity:.3f}")

    return result_img, final_matches
