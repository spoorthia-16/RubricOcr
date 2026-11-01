import os
import cv2
import json
import sys

# Add current dir to path to import services/utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.pdf_service import pdf_to_images
from utils.image_utils import preprocess_image, correct_page_orientation
from utils.table_detector import (
    detect_table_regions,
    crop_table_regions,
    detect_grid_lines,
    reconstruct_grid,
    extract_cells_from_grid,
    build_cell_matrix,
    detect_merged_cells,
    detect_metadata_regions,
    build_layout_object
)

def test_pipeline():
    pdf_path = os.path.join("uploads", "DOC_1.pdf")
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return

    print(f"1. Converting PDF to images: {pdf_path}")
    image_paths = pdf_to_images(pdf_path)
    if not image_paths:
        print("No images generated.")
        return
        
    img_path = image_paths[0]
    print(f"Processing page 1: {img_path}")
    
    print("2. Stage 1.2: Preprocessing")
    processed_path = os.path.join("temp", "processed_test.png")
    preprocess_image(img_path, processed_path)
    
    print("3. Stage 1.3: Orientation")
    image = cv2.imread(processed_path)
    corrected_img, angle = correct_page_orientation(image)
    print(f"Detected Skew: {angle} degrees")
    
    print("4. Stage 1.4: Table Detection")
    tables = detect_table_regions(corrected_img)
    print(f"Detected {len(tables)} table(s)")
    
    print("5. Stage 1.5: Table Cropping")
    cropped_tables = crop_table_regions(corrected_img, tables)
    
    tables_data = []
    
    for c_table in cropped_tables:
        t_id = c_table["table_id"]
        t_img = cv2.imread(c_table["image_path"])
        
        print(f"6. Stage 1.6: Grid Lines (Table {t_id})")
        grid_model = detect_grid_lines(t_img, table_id=t_id)
        # Pass table ID to grid model manually since our function adds it
        grid_model["table_id"] = t_id
        
        print(f"7. Stage 1.7: Reconstruct Grid (Table {t_id})")
        recon_model = reconstruct_grid(grid_model)
        recon_model["table_id"] = t_id
        
        print(f"8. Stage 1.8: Cell Extraction (Table {t_id})")
        cells = extract_cells_from_grid(recon_model, overlay_img=t_img)
        
        print(f"9. Stage 1.9: Cell Matrix (Table {t_id})")
        matrix_data = build_cell_matrix(cells, table_id=t_id, overlay_img=t_img)
        
        print(f"10. Stage 1.10: Merged Cell Analysis (Table {t_id})")
        final_matrix = detect_merged_cells(matrix_data, overlay_img=t_img)
        
        tables_data.append({
            "table_id": t_id,
            "image_path": c_table["image_path"],
            "bbox": c_table["bbox"],
            "dimensions": final_matrix.get("dimensions", matrix_data["dimensions"]),
            "matrix": final_matrix["matrix"],
            "merged_regions": final_matrix["merged_regions"],
            "statistics": matrix_data["statistics"]
        })
        
    print("11. Stage 1.11: Metadata Detection")
    metadata_res = detect_metadata_regions(corrected_img, tables)
    metadata = metadata_res["metadata_regions"]
    
    print("12. Stage 1.12: Layout Object Generation")
    layout = build_layout_object(corrected_img, metadata, tables_data, page_num=1)
    
    print("\n--- Pipeline Completed Successfully ---")
    print(f"Output saved to: backend/debug/layout_object.json")
    print(f"Found {len(tables_data)} tables, {len(metadata)} metadata regions.")

if __name__ == "__main__":
    test_pipeline()
