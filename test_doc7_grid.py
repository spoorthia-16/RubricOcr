import cv2
import os
import sys

# Ensure backend is in path
sys.path.append('c:/Users/spoor/EXCEL works/Project1/backend')
from utils.table_detector import detect_table_regions, crop_table_regions, detect_grid_lines, reconstruct_grid
from services.pdf_service import pdf_to_images

pdf_path = "c:/Users/spoor/EXCEL works/Project1/backend/uploads/37579-iUBT427_Examiner_s_Assessment_Form_v1.pdf"
image_paths = pdf_to_images(pdf_path)

img = cv2.imread(image_paths[0])
regions = detect_table_regions(img)

cropped_results = crop_table_regions(img, regions)

if cropped_results:
    largest_region = max(cropped_results, key=lambda r: r['width'] * r['height'])
    table_crop = cv2.imread(largest_region['image_path'])
    
    grid_lines = detect_grid_lines(table_crop)
    grid_model = reconstruct_grid(grid_lines)
    
    valid_x = grid_model["valid_x"]
    valid_y = grid_model["valid_y"]
    print(f"Detected {len(valid_x) - 1} columns and {len(valid_y) - 1} rows.")
    
    cv2.imwrite("c:/Users/spoor/EXCEL works/Project1/backend/debug/doc7_overlay.png", grid_model["overlay_img"])
    
    print("Coordinates of X (Columns):", valid_x)
