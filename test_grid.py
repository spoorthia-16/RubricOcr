import cv2
import json
import os
import sys

sys.path.append('c:/Users/spoor/EXCEL works/Project1/backend')
from utils.table_detector import detect_table_regions, detect_grid_lines

image_path = "c:/Users/spoor/EXCEL works/Project1/backend/debug/DOC_5/01_original_page.png"
if not os.path.exists(image_path):
    print("Image not found:", image_path)
    sys.exit(1)

image = cv2.imread(image_path)
print("Original shape:", image.shape)

def custom_detect_grid(table_crop):
    gray = cv2.cvtColor(table_crop, cv2.COLOR_BGR2GRAY)
    block_size = 51 if min(table_crop.shape[:2]) > 1000 else 15
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, block_size, 5)
    img_h, img_w = table_crop.shape[:2]
    
    h_open_size = max(40, img_w // 40)
    v_open_size = max(60, img_h // 40)
    h_open_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_open_size, 1))
    v_open_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_open_size))
    
    h_iso = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_open_kernel)
    v_iso = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_open_kernel)
    
    h_close_size = max(30, img_w // 20)
    v_close_size = max(30, img_h // 20)
    h_close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_close_size, 5))
    v_close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, v_close_size))
    
    h_mask = cv2.morphologyEx(h_iso, cv2.MORPH_CLOSE, h_close_kernel)
    v_mask = cv2.morphologyEx(v_iso, cv2.MORPH_CLOSE, v_close_kernel)
    
    h_contours, _ = cv2.findContours(h_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    horizontal_lines = []
    for cnt in h_contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w > img_w * 0.05:
            horizontal_lines.append({"center_y": y + h // 2, "center_x": x + w // 2})
            
    v_contours, _ = cv2.findContours(v_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    vertical_lines = []
    for cnt in v_contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if h > img_h * 0.05:
            vertical_lines.append({"center_x": x + w // 2, "center_y": y + h // 2})
            
    return {"horizontal_lines": horizontal_lines, "vertical_lines": vertical_lines}

def custom_detect_table(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    block_size = 51 if min(gray.shape[:2]) > 1000 else 15
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, block_size, 5)
    
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel, iterations=2)
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel, iterations=2)
    
    table_mask = cv2.add(horizontal, vertical)
    dilate_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    table_mask = cv2.dilate(table_mask, dilate_kernel, iterations=3)
    
    contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    img_h, img_w = image.shape[:2]
    
    tables = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w < (img_w * 0.1) or h < 50:
            continue
        if w > (img_w * 0.95) and h > (img_h * 0.95):
            continue
        # Add padding to ensure serial numbers and outer edges are captured
        pad = 40
        x = max(0, x - pad)
        y = max(0, y - pad)
        w = min(img_w - x, w + 2 * pad)
        h = min(img_h - y, h + 2 * pad)
        tables.append({"bbox": [x, y, x + w, y + h]})
    return tables

tables = custom_detect_table(image)
if not tables:
    print("No tables found!")
    sys.exit(1)

t = tables[0]
print("New Table bbox:", t['bbox'])
x, y, x2, y2 = t['bbox']
table_crop = image[y:y2, x:x2]

grid = custom_detect_grid(table_crop)
horizontal_lines = grid["horizontal_lines"]
vertical_lines = grid["vertical_lines"]
raw_y = [h["center_y"] for h in horizontal_lines]
from utils.table_detector import cluster_coordinates, reconstruct_grid
canonical_y = cluster_coordinates(raw_y, tolerance=15)
skipped_y = []
for cy in canonical_y:
    inters = 0
    for v in vertical_lines:
        if v["center_y"] - 20 <= cy <= v["center_y"] + v["center_y"] + 20: # wait, y_start and length is not there!
            pass
            
# Let's just print canonical_y!
print("All canonical Ys:", canonical_y)
v_centers = [line["center_x"] for line in grid['vertical_lines']]
h_clusters = cluster_coordinates(h_centers, tolerance=15)
v_clusters = cluster_coordinates(v_centers, tolerance=15)
valid_x = v_clusters
valid_y = h_clusters
img_h, img_w = table_crop.shape[:2]

if valid_x and valid_x[0] > 50:
    valid_x.insert(0, 5)
if valid_x and valid_x[-1] < img_w - 50:
    valid_x.append(img_w - 5)
    
if valid_y and valid_y[0] > 50:
    valid_y.insert(0, 5)
if valid_y and valid_y[-1] < img_h - 50:
    valid_y.append(img_h - 5)
    
print("h_clusters (valid_y):", len(valid_y))
print("v_clusters (valid_x):", len(valid_x))
print("valid_x:", valid_x)
print("valid_y:", valid_y)
