import cv2
import numpy as np
import os
import math
import time
from config.preprocessing_config import (
    CLAHE_CLIP_LIMIT, CLAHE_GRID_SIZE, DENOISE_H, DENOISE_TEMPLATE_WINDOW_SIZE,
    DENOISE_SEARCH_WINDOW_SIZE, ADAPTIVE_BLOCK_SIZE, ADAPTIVE_C, MAX_SKEW_ANGLE,
    SHARPEN_KERNEL, MORPH_KERNEL_SIZE, DEBUG_OUTPUT_DIR
)

def deskew_image(image):
    """
    Detects and corrects skew in the image.
    Returns the corrected image, the estimated angle, and processing time.
    """
    start_time = time.time()
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=150, maxLineGap=10)
    
    angles = []
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
            if -45 < angle < 45:
                angles.append(angle)
                
    median_angle = np.median(angles) if angles else 0.0
    
    if abs(median_angle) > 0.5 and abs(median_angle) <= MAX_SKEW_ANGLE:
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        
        cos = np.abs(M[0, 0])
        sin = np.abs(M[0, 1])
        new_w = int((h * sin) + (w * cos))
        new_h = int((h * cos) + (w * sin))
        
        M[0, 2] += (new_w / 2) - center[0]
        M[1, 2] += (new_h / 2) - center[1]
        
        rotated = cv2.warpAffine(
            image, M, (new_w, new_h), 
            flags=cv2.INTER_CUBIC, 
            borderMode=cv2.BORDER_CONSTANT, 
            borderValue=(255, 255, 255)
        )
        elapsed = time.time() - start_time
        return rotated, median_angle, elapsed
        
    elapsed = time.time() - start_time
    return image.copy(), median_angle, elapsed

def _save_debug(img, name, page_num):
    base_dir = os.path.abspath(os.path.dirname(__file__))
    pages_dir = os.path.join(base_dir, "..", DEBUG_OUTPUT_DIR, "pages")
    os.makedirs(pages_dir, exist_ok=True)
    cv2.imwrite(os.path.join(pages_dir, f"page_{page_num}_{name}.png"), img)

def generate_ocr_versions(image, page_num):
    """
    Generates OCR Version 1 (Printed Text Optimized) and OCR Version 2 (Handwritten Marks Optimized).
    Saves outputs and returns timings and paths.
    """
    timings = {}
    versions = {}
    base_dir = os.path.abspath(os.path.dirname(__file__))
    pages_dir = os.path.join(base_dir, "..", DEBUG_OUTPUT_DIR, "pages")
    os.makedirs(pages_dir, exist_ok=True)

    img_copy = image.copy()

    # Step 1: Grayscale (Shared)
    t0 = time.time()
    gray = cv2.cvtColor(img_copy, cv2.COLOR_BGR2GRAY)
    timings['grayscale'] = time.time() - t0
    _save_debug(gray, "gray", page_num)

    # Step 2: CLAHE (Shared)
    t0 = time.time()
    clahe_obj = cv2.createCLAHE(clipLimit=CLAHE_CLIP_LIMIT, tileGridSize=CLAHE_GRID_SIZE)
    clahe = clahe_obj.apply(gray)
    timings['clahe'] = time.time() - t0
    _save_debug(clahe, "clahe", page_num)

    # --- LAYOUT OPTIMIZED VERSION ---
    # Bilateral Filter -> Adaptive Threshold(11,2) -> Morph Closing
    t0 = time.time()
    bilateral = cv2.bilateralFilter(clahe, 9, 75, 75)
    timings['bilateral_layout'] = time.time() - t0
    
    t0 = time.time()
    layout_thresh = cv2.adaptiveThreshold(
        bilateral, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    timings['adaptive_thresh_layout'] = time.time() - t0
    
    t0 = time.time()
    layout_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    layout_morph = cv2.morphologyEx(layout_thresh, cv2.MORPH_CLOSE, layout_kernel)
    timings['morph_layout'] = time.time() - t0
    
    layout_path = os.path.join(pages_dir, f"page_{page_num}_layout.png")
    cv2.imwrite(layout_path, layout_morph)
    versions['layout'] = layout_path

    # --- OCR VERSION 1 (Printed Text Optimized) ---
    # Denoise
    t0 = time.time()
    denoised = cv2.fastNlMeansDenoising(clahe, None, DENOISE_H, DENOISE_TEMPLATE_WINDOW_SIZE, DENOISE_SEARCH_WINDOW_SIZE)
    timings['denoise_v1'] = time.time() - t0
    
    # Adaptive Threshold
    t0 = time.time()
    adaptive_thresh = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, ADAPTIVE_BLOCK_SIZE, ADAPTIVE_C
    )
    timings['adaptive_thresh_v1'] = time.time() - t0
    
    v1_path = os.path.join(pages_dir, f"page_{page_num}_ocr_printed.png")
    cv2.imwrite(v1_path, denoised)
    versions['printed'] = v1_path

    # --- OCR VERSION 2 (Handwritten Marks Optimized) ---
    # Otsu Threshold
    t0 = time.time()
    _, otsu_thresh = cv2.threshold(clahe, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    timings['otsu_thresh_v2'] = time.time() - t0

    # Morphological Closing
    t0 = time.time()
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, MORPH_KERNEL_SIZE)
    morph = cv2.morphologyEx(otsu_thresh, cv2.MORPH_CLOSE, kernel)
    timings['morph_v2'] = time.time() - t0

    # Sharpen
    t0 = time.time()
    sharpened = cv2.filter2D(morph, -1, SHARPEN_KERNEL)
    timings['sharpen_v2'] = time.time() - t0

    v2_path = os.path.join(pages_dir, f"page_{page_num}_ocr_handwritten.png")
    cv2.imwrite(v2_path, sharpened)
    versions['handwritten'] = v2_path

    print("DEBUG: generate_ocr_versions() returning:", versions)
    return versions, timings

def preprocess_image_v2(image, page_num):
    """
    Central preprocessing function. Applies deskew, then generates OCR versions.
    """
    total_timings = {}
    
    # 1. Deskew
    deskewed, angle, d_time = deskew_image(image)
    total_timings['deskew'] = d_time
    _save_debug(deskewed, "deskew", page_num)
    
    # 2. Generate versions
    versions, v_timings = generate_ocr_versions(deskewed, page_num)
    total_timings.update(v_timings)
    
    return versions, angle, total_timings

def assess_image_quality(image, original_image, dpi):
    """
    Calculates metrics and returns status, warnings, and recommendations.
    """
    height, width = image.shape[:2]
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
    contrast_score = gray.std()
    
    status = "GOOD"
    warnings = []
    recommendations = []
    
    if blur_score < 100:
        status = "POOR"
        warnings.append(f"High blur detected (score: {blur_score:.1f})")
        recommendations.append("Ensure scan is sharply focused or apply sharpening")
        
    if contrast_score < 40:
        if status == "GOOD": status = "ACCEPTABLE"
        warnings.append(f"Low contrast detected (score: {contrast_score:.1f})")
        recommendations.append("Apply contrast stretching or CLAHE")
        
    if dpi < 300:
        status = "POOR"
        warnings.append(f"Low DPI ({dpi})")
        recommendations.append("Increase scanning resolution to at least 300 DPI")
        
    return {
        "width": width,
        "height": height,
        "dpi": dpi,
        "blur_score": round(blur_score, 2),
        "contrast_score": round(contrast_score, 2),
        "status": status,
        "warnings": warnings,
        "recommendations": recommendations
    }
