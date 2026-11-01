import os
import cv2

def build_document_representation(page_num, page_image_path, rows_with_text, table_regions):
    """
    Packages the output from OpenCV table detection and PaddleOCR text extraction
    into a structured, machine-readable JSON format for the Vision LLM to consume.
    Crops the page image to the specific table regions to save LLM context window.
    """
    # Load the full page image
    image = cv2.imread(page_image_path)
    base_dir = os.path.dirname(page_image_path)
    
    tables = []
    
    # Process each table region
    for idx, region in enumerate(table_regions):
        x1, y1, x2, y2 = [int(v) for v in region]
        
        # Add a small padding to the crop (so borders are visible)
        pad = 20
        h, w = image.shape[:2]
        cy1, cy2 = max(0, y1 - pad), min(h, y2 + pad)
        cx1, cx2 = max(0, x1 - pad), min(w, x2 + pad)
        
        # Crop the table image
        table_crop = image[cy1:cy2, cx1:cx2]
        
        # Save the cropped image
        crop_filename = f"table_crop_p{page_num}_{idx}.png"
        crop_path = os.path.join(base_dir, crop_filename)
        cv2.imwrite(crop_path, table_crop)
        
        # Filter cells that belong to this table region
        table_cells = []
        for r_idx, row in enumerate(rows_with_text):
            for c_idx, cell in enumerate(row):
                cx = int(cell["x"])
                cy = int(cell["y"])
                cw = int(cell["w"])
                ch = int(cell["h"])
                
                # Check if cell center is inside this table region
                center_x = cx + cw / 2
                center_y = cy + ch / 2
                
                if x1 <= center_x <= x2 and y1 <= center_y <= y2:
                    text = cell.get("text", "").strip()
                    confidence = float(cell.get("confidence", 1.0))
                    
                    # Convert absolute coords to be relative to the cropped image!
                    # This helps the LLM easily map the JSON bbox to what it sees in the image crop.
                    rel_x = max(0, cx - cx1)
                    rel_y = max(0, cy - cy1)
                    
                    table_cells.append({
                        "row": r_idx,
                        "column": c_idx,
                        "bbox": [rel_x, rel_y, rel_x + cw, rel_y + ch],
                        "text": text,
                        "confidence": confidence
                    })
                    
        tables.append({
            "image": crop_path,
            "cells": table_cells
        })
        
    document_data = {
        "page": page_num,
        "tables": tables
    }
    
    return document_data
