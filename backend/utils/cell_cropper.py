import os
import cv2

def generate_cell_images(layout_object, output_dir="temp/cells", padding_mode="inside", padding=2):
    """
    Step 2.1 - Cell Image Generation
    Crops every cell from the tables defined in the layout_object into individual images.
    Supports configurable padding modes to avoid clipping handwriting or OCR border confusion.
    padding_mode: 'inside' (crops inwards), 'outside' (crops outwards), 'none' (strict bounds).
    Returns the mutated layout_object with cell image paths attached.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    for table in layout_object.get("tables", []):
        table_id = table["table_id"]
        table_img_path = table.get("image_path")
        
        if not table_img_path or not os.path.exists(table_img_path):
            print(f"Warning: Table image path not found for table {table_id}. Skipping cell crop.")
            continue
            
        table_img = cv2.imread(table_img_path)
        
        for row in table.get("matrix", []):
            for cell in row:
                cell_id = cell["cell_id"]
                x1, y1, x2, y2 = cell["bbox"]
                
                # Apply configurable padding
                h, w = table_img.shape[:2]
                
                if padding_mode == "inside":
                    cx1 = min(w, x1 + padding)
                    cy1 = min(h, y1 + padding)
                    cx2 = max(0, x2 - padding)
                    cy2 = max(0, y2 - padding)
                elif padding_mode == "outside":
                    cx1 = max(0, x1 - padding)
                    cy1 = max(0, y1 - padding)
                    cx2 = min(w, x2 + padding)
                    cy2 = min(h, y2 + padding)
                else:
                    cx1, cy1, cx2, cy2 = x1, y1, x2, y2
                    
                # Ensure width/height remain positive after padding
                if cx2 <= cx1 or cy2 <= cy1:
                    cx1, cy1, cx2, cy2 = x1, y1, x2, y2
                    
                cell_crop = table_img[cy1:cy2, cx1:cx2]
                
                # Save cell image
                cell_filename = f"table{table_id}_cell_{cell_id:04d}.png"
                cell_path = os.path.join(output_dir, cell_filename)
                
                cv2.imwrite(cell_path, cell_crop)
                
                # Attach path to the layout object
                cell["image_path"] = cell_path
                
    return layout_object

def generate_metadata_images(layout_object, page_image, output_dir="temp/metadata"):
    """
    Step 2.2 - Metadata Region Cropping
    Crops every metadata region from the original page image into independent images.
    Returns the mutated layout_object with metadata image paths attached.
    """
    import json
    
    os.makedirs(output_dir, exist_ok=True)
    
    metadata_index = []
    
    for region in layout_object.get("metadata_regions", []):
        region_id = region["region_id"]
        region_type = region["type"]
        x1, y1, x2, y2 = region["bbox"]
        
        # Ensure strict bounds
        h, w = page_image.shape[:2]
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w, x2)
        y2 = min(h, y2)
        
        if x2 > x1 and y2 > y1:
            region_crop = page_image[y1:y2, x1:x2]
            
            # Save metadata image
            filename = f"{region_type}_{region_id:03d}.png"
            image_path = os.path.join(output_dir, filename)
            cv2.imwrite(image_path, region_crop)
            
            region["image_path"] = image_path
            
            metadata_index.append({
                "region_id": region_id,
                "type": region_type,
                "image_path": image_path,
                "bbox": [x1, y1, x2, y2]
            })
            
    # Save metadata index
    base_dir = os.path.abspath(os.path.dirname(__file__))
    debug_folder = os.path.join(base_dir, "..", "debug")
    os.makedirs(debug_folder, exist_ok=True)
    
    with open(os.path.join(debug_folder, "metadata_index.json"), "w") as f:
        json.dump({"metadata_index": metadata_index}, f, indent=4)
        
    return layout_object
