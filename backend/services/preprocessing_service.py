import os
import json
import time
import cv2

from utils.pdf_utils import validate_pdf, render_pdf
from utils.preprocessing_utils import preprocess_image_v2, assess_image_quality
from config.preprocessing_config import PDF_DPI, DEBUG_OUTPUT_DIR

def process_document_phase1(file_path):
    """
    Phase 1 Orchestrator: Input & Image Processing.
    """
    overall_start = time.time()
    
    print("[Phase 1] Validating PDF...")
    val_result = validate_pdf(file_path)
    if not val_result["valid"]:
        raise ValueError(f"PDF Validation failed: {val_result['errors']}")
    print("[Phase 1] PDF validation completed.")

    print(f"[Phase 1] Rendering {val_result['pages']} pages...")
    try:
        images = render_pdf(file_path)
    except Exception as e:
        raise ValueError(f"PDF Rendering failed: {e}")
    print("[Phase 1] Rendering completed.")

    base_dir = os.path.abspath(os.path.dirname(__file__))
    quality_dir = os.path.join(base_dir, "..", DEBUG_OUTPUT_DIR, "quality")
    metadata_dir = os.path.join(base_dir, "..", DEBUG_OUTPUT_DIR, "metadata")
    os.makedirs(quality_dir, exist_ok=True)
    os.makedirs(metadata_dir, exist_ok=True)

    results = []

    for idx, pil_img in enumerate(images, start=1):
        print(f"[Phase 1] Enhancing image {idx}...")
        
        # Convert PIL to CV2 format (BGR)
        import numpy as np
        open_cv_image = np.array(pil_img)
        # Convert RGB to BGR 
        img_bgr = open_cv_image[:, :, ::-1].copy()
        
        versions, angle, timings = preprocess_image_v2(img_bgr, idx)
        print("[Phase 1] Image preprocessing completed.")
        
        print(f"[Phase 1] Assessing image quality for page {idx}...")
        quality_report = assess_image_quality(img_bgr, img_bgr, PDF_DPI)
        quality_report["skew_angle"] = round(angle, 2)
        
        q_path = os.path.join(quality_dir, f"quality_report_{idx}.json")
        with open(q_path, "w") as f:
            json.dump(quality_report, f, indent=4)
        print(f"[Phase 1] Quality: {quality_report['status']}")
        
        total_time_page = time.time() - overall_start
        
        metadata = {
            "page": idx,
            "dpi": PDF_DPI,
            "operations": list(timings.keys()),
            "timings": timings,
            "processing_time": round(total_time_page, 2)
        }
        
        m_path = os.path.join(metadata_dir, f"preprocessing_metadata_{idx}.json")
        with open(m_path, "w") as f:
            json.dump(metadata, f, indent=4)
            
        results.append({
            "page_number": idx,
            "original_image": os.path.abspath(os.path.join(base_dir, "..", DEBUG_OUTPUT_DIR, "pages", f"page_{idx}_original.png")),
            "versions": versions,
            "dpi": PDF_DPI,
            "width": quality_report["width"],
            "height": quality_report["height"],
            "quality": quality_report
        })
        
    return results
