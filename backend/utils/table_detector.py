import cv2
import numpy as np
import os


def detect_table(image_path):

    image = cv2.imread(image_path)

    if image is None:
        raise Exception("Cannot load image")

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    return image, gray


def detect_horizontal_lines(gray):

    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        15,
        5
    )

    horizontal_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (25, 1)
    )

    horizontal = cv2.morphologyEx(
        binary,
        cv2.MORPH_OPEN,
        horizontal_kernel,
        iterations=1
    )

    return binary, horizontal


def detect_vertical_lines(gray):

    binary = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        15,
        5
    )

    vertical_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (1, 25)
    )

    vertical = cv2.morphologyEx(
        binary,
        cv2.MORPH_OPEN,
        vertical_kernel,
        iterations=1
    )

    return vertical


def build_table_grid(horizontal, vertical):
    """
    Combine horizontal and vertical lines to create
    the complete table grid.
    """

    grid = cv2.add(horizontal, vertical)
    
    # Dilate the grid to close any small gaps between intersecting lines
    # This prevents cells from merging if a line was faintly scanned
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    grid = cv2.dilate(grid, kernel, iterations=1)

    return grid


def detect_table_cells(grid):

    contours, hierarchy = cv2.findContours(
        grid,
        cv2.RETR_TREE,
        cv2.CHAIN_APPROX_SIMPLE
    )

    return contours


def draw_detected_cells(image, contours):

    output = image.copy()

    for contour in contours:

        x, y, w, h = cv2.boundingRect(contour)

        # Ignore tiny noise
        if w < 20 or h < 20:
            continue

        cv2.rectangle(
            output,
            (x, y),
            (x + w, y + h),
            (0, 255, 0),
            2
        )

    return output


def filter_cells(contours):

    filtered = []

    for contour in contours:

        x, y, w, h = cv2.boundingRect(contour)

        # Ignore tiny contours
        if w < 20 or h < 20:
            continue

        # Ignore huge merged page-bounding boxes but KEEP wide header rows
        if h > 1200:
            continue

        filtered.append((x, y, w, h))

    return filtered


def sort_cells_by_rows(filtered_cells, row_tolerance=15):
    """
    Group detected cells into rows using
    the vertical center of each cell.
    """

    filtered_cells = sorted(
        filtered_cells,
        key=lambda cell: cell[1] + cell[3] // 2
    )

    rows = []

    current_row = []

    current_center = None

    for cell in filtered_cells:

        x, y, w, h = cell

        center = y + h // 2

        if current_center is None:

            current_center = center

            current_row.append(cell)

        elif abs(center - current_center) <= row_tolerance:

            current_row.append(cell)

        else:

            rows.append(current_row)

            current_row = [cell]

            current_center = center

    if current_row:

        rows.append(current_row)

    # Sort every row from left to right
    for row in rows:
        row.sort(key=lambda cell: cell[0])

    return rows


def crop_table_cells(image, rows):
    """
    Crop every detected cell from the original image.

    Returns:
        [
            [cell_img, cell_img, ...],   # Row 1
            [cell_img, cell_img, ...],   # Row 2
            ...
        ]
    """

    cropped_rows = []

    for row in rows:

        cropped_cells = []

        for (x, y, w, h) in row:

            cell = image[y:y+h, x:x+w]

            cropped_cells.append(cell)

        cropped_rows.append(cropped_cells)

    return cropped_rows

def detect_table_regions(image):
    """
    Detects the outer bounding boxes of all table regions in an image.
    Uses morphological operations to find horizontal and vertical lines,
    combines them, and extracts the external contours.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 1. Binarize
    block_size = 51 if min(gray.shape[:2]) > 1000 else 15
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, block_size, 5
    )
    
    # 2. Extract Horizontal Lines
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel, iterations=2)
    
    # 3. Extract Vertical Lines
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel, iterations=2)
    
    # 4. Combine and dilate
    table_mask = cv2.add(horizontal, vertical)
    dilate_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    table_mask = cv2.dilate(table_mask, dilate_kernel, iterations=3)
    
    # 5. Find external contours
    contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 6. Filter contours
    tables = []
    debug_img = image.copy()
    (img_h, img_w) = image.shape[:2]
    
    table_id = 1
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        
        # Filtering criteria:
        # - Ignore very small contours (less than 10% of image width or very short)
        if w < (img_w * 0.1) or h < 50:
            continue
            
        # Ignore huge contours that are the size of the whole page (border noise)
        if w > (img_w * 0.95) and h > (img_h * 0.95):
            continue
            
        # Add padding to capture missing outer borders (e.g. Serial Numbers)
        pad = 40
        x = max(0, x - pad)
        y = max(0, y - pad)
        w = min(img_w - x, w + 2 * pad)
        h = min(img_h - y, h + 2 * pad)
            
        tables.append({
            "table_id": table_id,
            "bbox": [x, y, x + w, y + h],
            "width": w,
            "height": h,
            "area": area
        })
        
        # Draw for debug
        cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 0, 255), 3)
        cv2.putText(debug_img, f"Table {table_id}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
        table_id += 1
        
    # If no nested tables were found (e.g. image is already a cropped table or full-page grid), fallback to full image
    if not tables:
        tables.append({
            "table_id": 1,
            "bbox": [0, 0, img_w, img_h],
            "width": img_w,
            "height": img_h,
            "area": img_w * img_h
        })
        cv2.rectangle(debug_img, (0, 0), (img_w, img_h), (0, 0, 255), 3)
        cv2.putText(debug_img, "Table 1 (Full Image)", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

    # 7. Sort from top to bottom based on y-coordinate

    tables = sorted(tables, key=lambda t: t["bbox"][1])
    
    # Re-assign sequential IDs after sorting
    for idx, t in enumerate(tables):
        t["table_id"] = idx + 1
        
    # 8. Save debug outputs
    base_dir = os.path.abspath(os.path.dirname(__file__))
    debug_folder = os.path.join(base_dir, "..", "debug")
    os.makedirs(debug_folder, exist_ok=True)
    
    cv2.imwrite(os.path.join(debug_folder, "horizontal_lines.png"), horizontal)
    cv2.imwrite(os.path.join(debug_folder, "vertical_lines.png"), vertical)
    cv2.imwrite(os.path.join(debug_folder, "table_mask.png"), table_mask)
    cv2.imwrite(os.path.join(debug_folder, "table_regions.png"), debug_img)
    
    return tables

def crop_table_regions(image, detected_tables, page_num=1, padding=10):
    """
    Crops every detected table from the original high-resolution image into an independent image, 
    preserving its exact geometry.
    Applies a small padding to ensure outer borders are not clipped.
    """
    cropped_results = []
    
    (img_h, img_w) = image.shape[:2]
    
    base_dir = os.path.abspath(os.path.dirname(__file__))
    debug_folder = os.path.join(base_dir, "..", "debug")
    os.makedirs(debug_folder, exist_ok=True)
    
    for table in detected_tables:
        x1, y1, x2, y2 = table["bbox"]
        
        # Apply padding while ensuring we don't go out of image bounds
        crop_y1 = max(0, y1 - padding)
        crop_y2 = min(img_h, y2 + padding)
        crop_x1 = max(0, x1 - padding)
        crop_x2 = min(img_w, x2 + padding)
        
        # Crop the image
        table_crop = image[crop_y1:crop_y2, crop_x1:crop_x2]
        
        # Save crop
        table_id = table["table_id"]
        crop_filename = f"table_crop_p{page_num}_{table_id}.png"
        crop_path = os.path.join(debug_folder, crop_filename)
        cv2.imwrite(crop_path, table_crop)
        
        # Record structured data
        cropped_results.append({
            "table_id": table_id,
            "image_path": crop_path,
            "bbox": [crop_x1, crop_y1, crop_x2, crop_y2],
            "width": crop_x2 - crop_x1,
            "height": crop_y2 - crop_y1
        })
        
    return cropped_results

def detect_grid_lines(table_crop, table_id="1"):
    import cv2
    import numpy as np

    if table_crop is None:
        raise ValueError(f"Could not load image")

    gray = cv2.cvtColor(table_crop, cv2.COLOR_BGR2GRAY)
    
    unique_vals = np.unique(gray)
    if len(unique_vals) > 2 or (0 not in unique_vals and 255 not in unique_vals):
        block_size = 51 if min(table_crop.shape[:2]) > 1000 else 15
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, block_size, 5
        )
    else:
        binary = (gray == 0).astype(np.uint8) * 255

    img_h, img_w = table_crop.shape[:2]

    # Text destruction - tuned for high resolution
    h_open_size = max(40, img_w // 40)
    v_open_size = max(60, img_h // 40)

    h_open_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_open_size, 1))
    v_open_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, v_open_size))

    h_iso = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_open_kernel)
    v_iso = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_open_kernel)

    # Gap bridging (must be < row_height/col_width to avoid bridging text)
    h_close_size = max(30, img_w // 20)
    v_close_size = max(30, img_h // 20)

    h_close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (h_close_size, 5))
    v_close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, v_close_size))

    h_mask = cv2.morphologyEx(h_iso, cv2.MORPH_CLOSE, h_close_kernel)
    v_mask = cv2.morphologyEx(v_iso, cv2.MORPH_CLOSE, v_close_kernel)

    # Extract horizontal lines (keep lines > 5% of width)
    h_contours, _ = cv2.findContours(h_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    horizontal_lines = []
    for cnt in h_contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w > img_w * 0.05:
            horizontal_lines.append({
                "x_start": x, "y_start": y, "length": w, "thickness": h,
                "center_y": y + h // 2, "center_x": x + w // 2
            })

    # Extract vertical lines (keep lines > 5% of height)
    v_contours, _ = cv2.findContours(v_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    vertical_lines = []
    for cnt in v_contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if h > img_h * 0.05:
            vertical_lines.append({
                "x_start": x, "y_start": y, "length": h, "thickness": w,
                "center_x": x + w // 2, "center_y": y + h // 2
            })

    return {
        "horizontal_lines": horizontal_lines,
        "vertical_lines": vertical_lines,
        "table_id": table_id,
        "overlay_img": table_crop,
        "h_mask": h_mask,
        "v_mask": v_mask
    }

def cluster_coordinates(coords, tolerance=20):
    if not coords:
        return []
    coords = sorted(coords)
    clusters = []
    current_cluster = [coords[0]]
    for c in coords[1:]:
        if c - current_cluster[-1] <= tolerance:
            current_cluster.append(c)
        else:
            clusters.append(int(np.mean(current_cluster)))
            current_cluster = [c]
    clusters.append(int(np.mean(current_cluster)))
    return clusters

def reconstruct_grid(grid_model):
    horizontal_lines = grid_model["horizontal_lines"]
    vertical_lines = grid_model["vertical_lines"]
    
    raw_y = [h["center_y"] for h in horizontal_lines]
    raw_x = [v["center_x"] for v in vertical_lines]
    
    canonical_y = cluster_coordinates(raw_y, tolerance=15)
    canonical_x = cluster_coordinates(raw_x, tolerance=15)
    
    # Intersection Validation (Grid Validation)
    valid_x = []
    for cx in canonical_x:
        inters = 0
        for h in horizontal_lines:
            if h["x_start"] - 20 <= cx <= h["x_start"] + h["length"] + 20:
                inters += 1
        if inters >= len(horizontal_lines) * 0.3:
            valid_x.append(cx)
            
    valid_y = []
    for cy in canonical_y:
        inters = 0
        for v in vertical_lines:
            if v["y_start"] - 20 <= cy <= v["y_start"] + v["length"] + 20:
                inters += 1
        if inters >= len(vertical_lines) * 0.3:
            valid_y.append(cy)
            
    # Force outer borders if they are missing
    if "overlay_img" in grid_model:
        img_h, img_w = grid_model["overlay_img"].shape[:2]
        if valid_x and valid_x[0] > 50:
            valid_x.insert(0, 5)
        if valid_x and valid_x[-1] < img_w - 50:
            valid_x.append(img_w - 5)
        if valid_y and valid_y[0] > 50:
            valid_y.insert(0, 5)
        if valid_y and valid_y[-1] < img_h - 50:
            valid_y.append(img_h - 5)
            
        # Detect abnormally wide columns in valid_y and split them
        # (This fixes the merged Final Mark and Comment columns)
        if len(valid_y) > 3:
            widths = [valid_y[i+1] - valid_y[i] for i in range(1, len(valid_y)-1)]
            if widths:
                median_w = sorted(widths)[len(widths)//2]
                new_valid_y = [valid_y[0]]
                for i in range(len(valid_y)-1):
                    new_valid_y.append(valid_y[i+1])
                    width = valid_y[i+1] - valid_y[i]
                    # Split if it's much wider than median AND it's not the first column (Learner Name)
                    if i > 1 and width > median_w * 1.8:
                        new_valid_y.insert(-1, valid_y[i] + width // 2)
                        print(f"[INFO] Split merged column at Y={valid_y[i] + width // 2}")
                valid_y = new_valid_y
            
    # Draw diagnostic artifact
    if "overlay_img" in grid_model:
        import os
        import cv2
        overlay = grid_model["overlay_img"].copy()
        for cx in valid_x:
            cv2.line(overlay, (cx, 0), (cx, overlay.shape[0]), (255, 0, 0), 2)
        for cy in valid_y:
            cv2.line(overlay, (0, cy), (overlay.shape[1], cy), (0, 0, 255), 2)
            
        debug_dir = "c:/Users/spoor/EXCEL works/Project1/backend/debug/latest"
        os.makedirs(debug_dir, exist_ok=True)
        cv2.imwrite(os.path.join(debug_dir, "08_locked_grid_overlay.png"), overlay)
        
    grid_model["valid_x"] = valid_x
    grid_model["valid_y"] = valid_y
    
    # Dynamic Grid Validation
    num_cols = len(valid_y) - 1
    num_rows = len(valid_x) - 1
    print(f"[INFO] Detected Grid: {num_rows} rows x {num_cols} columns")
    if num_cols < 5 or num_cols > 30:
        print(f"[WARNING] Unlikely number of columns detected: {num_cols}. The grid may be malformed.")
    if num_rows < 5 or num_rows > 100:
        print(f"[WARNING] Unlikely number of rows detected: {num_rows}. The grid may be malformed.")
        
    return grid_model

def extract_cells_from_grid(grid_model, overlay_img=None):
    valid_x = grid_model["valid_x"]
    valid_y = grid_model["valid_y"]
    
    cells = []
    cell_id = 1
    
    for r in range(len(valid_y) - 1):
        for c in range(len(valid_x) - 1):
            x1, x2 = valid_x[c], valid_x[c+1]
            y1, y2 = valid_y[r], valid_y[r+1]
            
            cells.append({
                "cell_id": cell_id,
                "row": r,
                "column": c,
                "bbox": [x1, y1, x2, y2],
                "width": x2 - x1,
                "height": y2 - y1,
                "colspan": 1,
                "rowspan": 1
            })
            cell_id += 1
            
    grid_model["cells"] = cells
    return grid_model

def build_cell_matrix(grid_model, table_id="1", overlay_img=None):
    cells = grid_model["cells"]
    
    num_rows = len(grid_model["valid_y"]) - 1
    num_cols = len(grid_model["valid_x"]) - 1
    
    # Check if table is physically sideways in the image
    # In a sideways table, cells are physically taller than they are wide.
    aspect_ratios = []
    for cell in cells:
        if cell["height"] > 0:
            aspect_ratios.append(cell["width"] / cell["height"])
            
    is_transposed = False
    if aspect_ratios:
        aspect_ratios.sort()
        median_ar = aspect_ratios[len(aspect_ratios)//2]
        # If the median cell is taller than it is wide (e.g. W/H < 0.8), the table is sideways
        is_transposed = median_ar < 0.8
        print(f"[INFO] Median cell aspect ratio (W/H): {median_ar:.3f}. Transpose needed? {is_transposed}")
    
    if is_transposed:
        print(f"[INFO] Table appears transposed (cols={num_cols}, rows={num_rows}). Transposing DOM.")
        rows_dict = {}
        for cell in cells:
            r = cell["column"]
            c = cell["row"]
            if r not in rows_dict: rows_dict[r] = []
            new_cell = cell.copy()
            new_cell["row"] = r
            new_cell["column"] = c
            rows_dict[r].append(new_cell)
    else:
        rows_dict = {}
        for cell in cells:
            r = cell["row"]
            if r not in rows_dict: rows_dict[r] = []
            rows_dict[r].append(cell)
            
    rows = []
    max_cols = 0
    for r in sorted(rows_dict.keys()):
        row_cells = sorted(rows_dict[r], key=lambda c: c["column"])
        rows.append({
            "index": r,
            "cells": row_cells
        })
        max_cols = max(max_cols, len(row_cells))
        
    output = {
        "table_id": table_id,
        "rows": rows,
        "dimensions": {
            "rows": len(rows),
            "columns": max_cols
        },
        "matrix": [[c for c in r["cells"]] for r in rows]
    }
    return output

def detect_merged_cells(matrix_model, overlay_img=None):
    return matrix_model

def detect_metadata_regions(page_image, detected_tables):
    """
    Detects non-table document regions containing metadata (headers, footers, notes).
    Uses geometric morphological clustering, completely masking out detected tables.
    """
    import json
    import os
    import cv2
    import numpy as np
    
    gray = cv2.cvtColor(page_image, cv2.COLOR_BGR2GRAY)
    (img_h, img_w) = gray.shape[:2]
    
    # 1. Binarize the entire page
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 5
    )
    
    # 2. Mask out all detected tables so they are completely ignored
    for table in detected_tables:
        x1, y1, x2, y2 = table["bbox"]
        # Expand mask slightly to cover table borders safely
        pad = 5
        cv2.rectangle(binary, (max(0, x1-pad), max(0, y1-pad)), 
                      (min(img_w, x2+pad), min(img_h, y2+pad)), 0, -1)
                      
    # 3. Morphological dilation to group nearby text into solid region blocks
    # A wide kernel connects words into lines, a tall kernel stacks lines into paragraphs
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 15))
    dilated = cv2.dilate(binary, kernel, iterations=2)
    
    # 4. Find external contours of these grouped text blocks
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    metadata_regions = []
    region_id = 1
    
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        
        # Ignore tiny noise artifacts
        if w < 30 or h < 10:
            continue
            
        # 5. Geometric Classification Heuristics
        center_x = x + w // 2
        center_y = y + h // 2
        
        region_type = "unknown"
        
        if center_y < img_h * 0.15:
            # Top 15% is usually Header or Title
            if w > img_w * 0.4 and (img_w * 0.3 < center_x < img_w * 0.7):
                region_type = "title"
            else:
                region_type = "header"
        elif center_y > img_h * 0.85:
            # Bottom 15%
            region_type = "footer"
            if w < img_w * 0.4 and h > 30:
                # Often signatures are smaller blocks in corners at the bottom
                region_type = "signature"
        elif y > (img_h * 0.5) and (x > img_w * 0.7 or x < img_w * 0.3) and h > 50:
            # Side notes or signatures lower down the page
            region_type = "signature"
        else:
            region_type = "notes"
            
        metadata_regions.append({
            "region_id": region_id,
            "type": region_type,
            "bbox": [x, y, x + w, y + h]
        })
        region_id += 1
        
    # Sort metadata top-to-bottom
    metadata_regions.sort(key=lambda r: r["bbox"][1])
    for idx, r in enumerate(metadata_regions):
        r["region_id"] = idx + 1
        
    # 6. Save Debug Outputs
    base_dir = os.path.abspath(os.path.dirname(__file__))
    debug_folder = os.path.join(base_dir, "..", "debug")
    os.makedirs(debug_folder, exist_ok=True)
    
    with open(os.path.join(debug_folder, "metadata_regions.json"), "w") as f:
        json.dump({"metadata_regions": metadata_regions}, f, indent=4)
        
    vis_img = page_image.copy()
    for r in metadata_regions:
        x1, y1, x2, y2 = r["bbox"]
        cv2.rectangle(vis_img, (x1, y1), (x2, y2), (255, 0, 0), 3) # Blue rectangle
        label = f"{r['type'].upper()} ({r['region_id']})"
        cv2.putText(vis_img, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
        
    cv2.imwrite(os.path.join(debug_folder, "metadata_regions.png"), vis_img)
    
    return {"metadata_regions": metadata_regions}

def build_layout_object(page_image, metadata_regions, tables_data, page_num=1, dpi=400):
    """
    Creates the final Layout Object representing the complete physical structure of the document.
    This serves as the definitive structural input for Stage 2 (OCR).
    """
    import json
    import os
    import logging
    
    (img_h, img_w) = page_image.shape[:2]
    orientation = "landscape" if img_w > img_h else "portrait"
    
    # 1. Assemble Document Info
    document_info = {
        "page": page_num,
        "dpi": dpi,
        "width": img_w,
        "height": img_h,
        "orientation": orientation
    }
    
    # 2. Validate everything is present
    if not isinstance(metadata_regions, list):
        raise ValueError("metadata_regions must be a list")
    
    for table in tables_data:
        required_keys = ["table_id", "image_path", "bbox", "dimensions", "matrix", "merged_regions", "statistics"]
        for key in required_keys:
            if key not in table:
                raise ValueError(f"Table {table.get('table_id', 'unknown')} is missing required key: {key}")
                
        # 2b. Validate logical structural integrity (Total slots == Rows * Columns)
        rows = table["dimensions"]["rows"]
        cols = table["dimensions"]["columns"]
        expected_slots = rows * cols
        
        covered_slots = 0
        for row in table["matrix"]:
            for cell in row:
                covered_slots += cell.get("rowspan", 1) * cell.get("colspan", 1)
                
        if covered_slots != expected_slots:
            logging.warning(f"Structural Validation Warning (Table {table['table_id']}): "
                            f"Grid covers {covered_slots} slots, but Dimensions expect {expected_slots} ({rows}x{cols}). "
                            f"This indicates a broken matrix mapping or missing cells.")
                
    # 3. Assemble Layout Object
    layout_object = {
        "document_info": document_info,
        "metadata_regions": metadata_regions,
        "tables": tables_data
    }
    
    # 4. Save Debug Output
    base_dir = os.path.abspath(os.path.dirname(__file__))
    debug_folder = os.path.join(base_dir, "..", "debug")
    os.makedirs(debug_folder, exist_ok=True)
    
    layout_path = os.path.join(debug_folder, "layout_object.json")
    with open(layout_path, "w") as f:
        json.dump(layout_object, f, indent=4)
        
    return layout_object