import sys
import os
import cv2

sys.path.append(os.path.abspath('backend'))
from utils.table_detector import detect_table, detect_horizontal_lines, detect_vertical_lines, build_table_grid, detect_table_cells, filter_cells

filepath = 'backend/uploads/Rubrics_Sample_File.pdf'
from services.pdf_service import pdf_to_images
from utils.image_utils import preprocess_image
temp_path = pdf_to_images(filepath)[0]
processed_path = preprocess_image(temp_path, "temp_processed.png")

image, gray = detect_table(processed_path)
binary, horizontal = detect_horizontal_lines(gray)
vertical = detect_vertical_lines(gray)
grid = build_table_grid(horizontal, vertical)
contours = detect_table_cells(grid)

print(f"Total contours: {len(contours)}")

for i, contour in enumerate(contours):
    x, y, w, h = cv2.boundingRect(contour)
    if w >= 20 and h >= 20: # ignore tiny noise
        if h > 100:
            print(f"TALL CELL: h={h}, w={w}, x={x}, y={y}")
        if w > 400:
            print(f"WIDE CELL: h={h}, w={w}, x={x}, y={y}")

filtered = filter_cells(contours)
print(f"Total after filter: {len(filtered)}")
