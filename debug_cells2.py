import sys
import os
import cv2

sys.path.append(os.path.abspath('backend'))
from utils.table_detector import detect_table, detect_horizontal_lines, detect_vertical_lines, build_table_grid, detect_table_cells, filter_cells, sort_cells_by_rows, crop_table_cells
from utils.image_utils import preprocess_image
from services.pdf_service import pdf_to_images

filepath = 'backend/uploads/37579-iUBT427_Examiner_s_Assessment_Form_v1.pdf'
image_paths = pdf_to_images(filepath)
temp_path = image_paths[0]
directory, filename = os.path.split(temp_path)
processed_path = os.path.join(directory, f"processed_{filename}")
processed_path = preprocess_image(temp_path, processed_path)

image, gray = detect_table(processed_path)
binary, horizontal = detect_horizontal_lines(gray)
vertical = detect_vertical_lines(gray)
contours = detect_table_cells(grid)
print(f"Total contours: {len(contours)}")
for c in contours:
    x, y, w, h = cv2.boundingRect(c)
    if h > 150 and w > 20:
        print(f"Tall contour detected: h={h}, w={w}, x={x}, y={y}")

filtered = filter_cells(contours)
rows = sort_cells_by_rows(filtered)
cropped = crop_table_cells(image, rows)

print(f"Total rows: {len(cropped)}")
for i, row in enumerate(cropped):
    print(f"Row {i+1} has {len(row)} cells")
    if i in [0, 1, 2, 3]: # Check the first few rows
        for j, cell in enumerate(row):
            h, w = cell.shape[:2]
            print(f"  Cell {j+1}: h={h}, w={w}")
