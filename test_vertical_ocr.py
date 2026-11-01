import sys
import os
import cv2
import easyocr
import re

sys.path.append(os.path.abspath('backend'))
from utils.table_detector import detect_table, detect_horizontal_lines, detect_vertical_lines, build_table_grid, detect_table_cells, filter_cells, sort_cells_by_rows, crop_table_cells
from utils.image_utils import preprocess_image
from services.pdf_service import pdf_to_images
from services.ocr_service import extract_cell_text

reader = easyocr.Reader(["en"], gpu=False)

filepath = 'backend/uploads/37579-iUBT427_Examiner_s_Assessment_Form_v1.pdf'
temp_path = pdf_to_images(filepath)[0]
processed_path = preprocess_image(temp_path, "temp_processed.png")

image, gray = detect_table(processed_path)
binary, horizontal = detect_horizontal_lines(gray)
vertical = detect_vertical_lines(gray)
grid = build_table_grid(horizontal, vertical)
contours = detect_table_cells(grid)
filtered = filter_cells(contours)
rows = sort_cells_by_rows(filtered)
cropped_rows = crop_table_cells(image, rows)

# Find the row with tall cells (should be row index 1 or 2)
for i, row in enumerate(cropped_rows):
    if len(row) > 10:
        h, w = row[5].shape[:2]
        if h > 200:
            print(f"Testing OCR on row {i}, cell 5 (shape: {h}x{w})")
            cell = row[5]
            
            res_normal = reader.readtext(cell, detail=0, paragraph=True)
            print("Normal text:", " ".join(res_normal))
            
            rot_cw = cv2.rotate(cell, cv2.ROTATE_90_CLOCKWISE)
            res_cw = reader.readtext(rot_cw, detail=0, paragraph=True)
            print("Rotated CW text:", " ".join(res_cw))
            
            rot_ccw = cv2.rotate(cell, cv2.ROTATE_90_COUNTERCLOCKWISE)
            res_ccw = reader.readtext(rot_ccw, detail=0, paragraph=True)
            print("Rotated CCW text:", " ".join(res_ccw))
            
            final = extract_cell_text(reader, cell)
            print("Final extracted:", final)
            
            # test another cell
            print("---")
            print("Testing OCR on row", i, "cell 6")
            cell = row[6]
            print("Final extracted:", extract_cell_text(reader, cell))
            break
