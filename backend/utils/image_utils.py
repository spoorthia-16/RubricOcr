import cv2
import os
import numpy as np
import math

def preprocess_image(
    image_path, 
    output_path,
    enable_clahe=True,
    enable_bilateral=True,
    enable_threshold=True,
    enable_morphology=True
):
    """
    Enhances table lines and document quality for downstream table detection 
    while preserving handwritten marks. Supports modular feature flags for easy experimentation.
    """
    image = cv2.imread(image_path)
    if image is None:
        raise Exception("Unable to read image.")

    # 1. Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    processed = gray

    # 2. Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
    if enable_clahe:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        processed = clahe.apply(processed)

    # 3. Apply a bilateral filter to reduce noise while preserving edges
    if enable_bilateral:
        processed = cv2.bilateralFilter(processed, 9, 75, 75)

    # 4. Apply adaptive thresholding to produce a clean binary image
    if enable_threshold:
        processed = cv2.adaptiveThreshold(
            processed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )

    # 5. Apply light morphological closing if needed
    if enable_morphology:
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        processed = cv2.morphologyEx(processed, cv2.MORPH_CLOSE, kernel)

    # Save to the requested output path (used by ocr_service.py)
    cv2.imwrite(output_path, processed)
    
    # Save a specific copy into the debug folder as requested
    base_dir = os.path.abspath(os.path.dirname(__file__))
    debug_folder = os.path.join(base_dir, "..", "debug")
    os.makedirs(debug_folder, exist_ok=True)
    debug_path = os.path.join(debug_folder, "processed_page.png")
    cv2.imwrite(debug_path, processed)

    return output_path

def correct_page_orientation(image):
    """
    Detects page skew angle using Hough Line Transform on long horizontal lines.
    If the skew is > 1 degree, rotates the image while expanding the boundaries 
    to prevent clipping any content.
    Returns the corrected image and the detected angle.
    """
    # 1. Internal processing to find lines (we don't modify the returned original image here)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    
    # 2. Detect long lines
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=150, maxLineGap=10)
    
    angles = []
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            # Calculate angle in degrees
            angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
            
            # We only care about roughly horizontal lines (tables) to determine skew
            if -45 < angle < 45:
                angles.append(angle)
                
    if not angles:
        return image, 0.0
        
    # Calculate median angle to ignore noisy outlier contours
    median_angle = np.median(angles)
    
    # 3. Check if rotation is necessary (> 1 degree)
    if abs(median_angle) > 1.0:
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        
        # Get rotation matrix
        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        
        # Calculate new bounding dimensions to avoid cropping corners
        cos = np.abs(M[0, 0])
        sin = np.abs(M[0, 1])
        new_w = int((h * sin) + (w * cos))
        new_h = int((h * cos) + (w * sin))
        
        # Adjust the rotation matrix translation
        M[0, 2] += (new_w / 2) - center[0]
        M[1, 2] += (new_h / 2) - center[1]
        
        # Perform rotation with white border padding
        rotated = cv2.warpAffine(
            image, 
            M, 
            (new_w, new_h), 
            flags=cv2.INTER_CUBIC, 
            borderMode=cv2.BORDER_CONSTANT, 
            borderValue=(255, 255, 255)
        )
        
        # 4. Save debug outputs
        base_dir = os.path.abspath(os.path.dirname(__file__))
        debug_folder = os.path.join(base_dir, "..", "debug")
        os.makedirs(debug_folder, exist_ok=True)
        cv2.imwrite(os.path.join(debug_folder, "original_orientation.png"), image)
        cv2.imwrite(os.path.join(debug_folder, "corrected_orientation.png"), rotated)
        
        return rotated, median_angle
        
    # Skew is insignificant, return original
    return image, median_angle
