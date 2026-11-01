import os
import cv2
os.environ["FLAGS_enable_pir_api"] = "0"

from paddleocr import PaddleOCR
import threading
import concurrent.futures

paddle_reader = PaddleOCR(use_angle_cls=False, lang='en', enable_mkldnn=False)
trocr_processor = None
trocr_model = None
trocr_lock = threading.Lock()

def get_trocr():
    global trocr_processor, trocr_model
    if trocr_processor is None:
        with trocr_lock:
            if trocr_processor is None:
                try:
                    from transformers import TrOCRProcessor, VisionEncoderDecoderModel
                    print("Loading TrOCR model into memory (this happens once)...")
                    trocr_processor = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
                    trocr_model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")
                except Exception as e:
                    print(f"Failed to initialize TrOCR: {e}")
                    trocr_processor = False
                    trocr_model = False
    return trocr_processor, trocr_model

from utils.table_detector import (
    detect_table,
    detect_horizontal_lines,
    detect_vertical_lines,
    build_table_grid,
    detect_table_cells,
    draw_detected_cells,
    filter_cells,
    sort_cells_by_rows,
    crop_table_cells
)
from services.pdf_service import pdf_to_images
from utils.image_utils import preprocess_image
from config import TEMP_FOLDER

def detect_header_and_col_types(rows_with_text):
    import difflib
    
    col_types = {}
    header_row_idx = 0
    
    # Check up to the first 5 rows to find the true header
    for r_idx, row in enumerate(rows_with_text[:5]):
        row_texts = [cell["text"].lower() for cell in row]
            
        combined_text = " ".join(row_texts)
        words = combined_text.replace(".", "").split()
        
        # Fuzzy match to identify if this is the header row
        has_learner = difflib.get_close_matches("learner", words, n=1, cutoff=0.6)
        has_student = difflib.get_close_matches("student", words, n=1, cutoff=0.6)
        
        if has_learner or has_student:
            header_row_idx = r_idx
            # Map column types based on cell text
            for c_idx, text in enumerate(row_texts):
                ctype = "score" # default
                cell_words = text.replace(".", "").split()
                
                if difflib.get_close_matches("name", cell_words, n=1, cutoff=0.6) or \
                   difflib.get_close_matches("learner", cell_words, n=1, cutoff=0.6):
                    ctype = "name"
                elif difflib.get_close_matches("student", cell_words, n=1, cutoff=0.6) or \
                     difflib.get_close_matches("id", cell_words, n=1, cutoff=0.6) or \
                     difflib.get_close_matches("no", cell_words, n=1, cutoff=0.7):
                    ctype = "id"
                    
                col_types[c_idx] = ctype
            break # Stop searching after finding the header
            
    return header_row_idx, col_types

def extract_cell_text(cell, col_type="score"):
    global trocr_processor, trocr_model
    import cv2
    import re
    import numpy as np
    from PIL import Image
    
    # 0. Fast Empty Cell Detection (Prevents 10-minute hangs on blank cells)
    gray = cv2.cvtColor(cell, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 220, 255, cv2.THRESH_BINARY_INV)
    ink_pixels = cv2.countNonZero(binary)
    total_pixels = binary.size
    
    if ink_pixels < (total_pixels * 0.005):
        return ""
        
    # 1. Preprocess the cell image for better OCR
    h_c, w_c = cell.shape[:2]
    scaled_cell = cv2.resize(cell, (w_c * 2, h_c * 2), interpolation=cv2.INTER_CUBIC)
    
    # Step 8: Rotate vertical headers clockwise before OCR
    if h_c > w_c * 1.1:
        scaled_cell = cv2.rotate(scaled_cell, cv2.ROTATE_90_CLOCKWISE)
    
    if col_type == "score":
        # Process score using PaddleOCR only, completely removing the slow/buggy TrOCR
        result = paddle_reader.ocr(scaled_cell)
        paddle_text = ""
        if result and result[0]:
            lines = [line[1][0] for line in result[0] if line]
            paddle_text = " ".join(lines)
            
        paddle_clean = re.sub(r'[^0-9Xx/\-]', '', paddle_text)
        return paddle_clean.strip()
    else:
        # PaddleOCR for printed text
        result = paddle_reader.ocr(scaled_cell)
        text_normal = ""
        if result and result[0]:
            lines = [line[1][0] for line in result[0] if line]
            text_normal = " ".join(lines)
            
        # Simple Character Filtering
        if col_type == "name":
            # Keep letters, spaces, hyphens, apostrophes
            text_normal = re.sub(r"[^a-zA-Z\s\-']", '', text_normal)
        elif col_type == "id":
            # Keep only alphanumeric
            text_normal = re.sub(r'[^a-zA-Z0-9]', '', text_normal)
            
        return text_normal.strip()

def extract_text(filepath):
    """
    Extracts text from a PDF or image file and maps it directly into a 2D matrix
    representing the table grid structure.
    """

    all_cell_data = []

    extension = os.path.splitext(filepath)[1].lower()

    # -------------------------
    # PDF OCR
    # -------------------------

    if extension == ".pdf":

        image_paths = pdf_to_images(filepath)

        for temp_path_idx, temp_path in enumerate(image_paths):

            import time
            start = time.time()
            print("Starting OCR for PDF...")
            
            directory, filename = os.path.split(temp_path)
            processed_path = os.path.join(directory, f"processed_{filename}")

            processed_path = preprocess_image(temp_path, processed_path)
            print(f"Preprocessing completed: {time.time() - start:.2f}s")

            image, gray = detect_table(processed_path)
            print(image.shape)

            binary, horizontal = detect_horizontal_lines(gray)
            vertical = detect_vertical_lines(gray)
            
            grid = build_table_grid(
                horizontal,
                vertical
            )

            contours = detect_table_cells(grid)

            print("\n========== TABLE DETECTION ==========")
            print(f"Total contours found: {len(contours)}")
            print("=====================================\n")

            detected_cells = draw_detected_cells(
                image,
                contours
            )

            filtered_cells = filter_cells(contours)

            print("\n========== CELL FILTER ==========")
            print(f"Contours Found : {len(contours)}")
            print(f"Filtered Cells : {len(filtered_cells)}")
            print("=================================\n")

            # 1. Sort cells into rows
            rows = sort_cells_by_rows(filtered_cells)
            
            print(f"Table detection completed: {time.time() - start:.2f}s")
            
            # Run Full Page OCR once
            print("Running Full Page OCR on PDF page...")
            
            # Scale down large images to prevent 20-minute CPU hangs
            max_dim = 1000
            h, w = image.shape[:2]
            scale = 1.0
            if max(h, w) > max_dim:
                scale = max_dim / max(h, w)
                scaled_image = cv2.resize(image, (0, 0), fx=scale, fy=scale)
            else:
                scaled_image = image
                
            print("Image Shape:", scaled_image.shape)
            print("Image Type:", scaled_image.dtype)
            
            import time
            t = time.time()
            
            print("Calling paddle_reader.ocr()...")
            
            result = paddle_reader.ocr(scaled_image)
            
            print("Returned from paddle_reader.ocr()")
            print(f"OCR Time: {time.time()-t:.2f} sec")
            
            paddle_boxes = []
            if result and isinstance(result[0], dict) and 'rec_polys' in result[0]:
                for poly, txt, conf in zip(result[0]['rec_polys'], result[0]['rec_texts'], result[0]['rec_scores'] if 'rec_scores' in result[0] else [1.0]*len(result[0]['rec_texts'])):
                    paddle_boxes.append((poly, txt, conf))
            elif result and isinstance(result[0], list):
                for item in result[0]:
                    if isinstance(item[1], (tuple, list)) and len(item[1]) >= 2:
                        paddle_boxes.append((item[0], item[1][0], float(item[1][1])))
                    else:
                        paddle_boxes.append((item[0], item[1][0], 1.0))
            
            # Map text to cells using Maximum Intersection Area (IoU logic)
            cell_texts = { (r, c): {"text": "", "confidence": 1.0} for r in range(len(rows)) for c in range(len(rows[r])) }
            
            for box, txt, conf in paddle_boxes:
                bx1 = min(p[0] for p in box) / scale
                by1 = min(p[1] for p in box) / scale
                bx2 = max(p[0] for p in box) / scale
                by2 = max(p[1] for p in box) / scale
                
                max_overlap = 0
                best_cell = None
                
                for r_idx, row in enumerate(rows):
                    for c_idx, (x, y, w, h) in enumerate(row):
                        ix1 = max(bx1, x)
                        iy1 = max(by1, y)
                        ix2 = min(bx2, x + w)
                        iy2 = min(by2, y + h)
                        
                        if ix1 < ix2 and iy1 < iy2:
                            inter_area = (ix2 - ix1) * (iy2 - iy1)
                            if inter_area > max_overlap:
                                max_overlap = inter_area
                                best_cell = (r_idx, c_idx)
                                
                if best_cell:
                    current = cell_texts[best_cell]
                    current["text"] += str(txt) + " "
                    # If multiple texts land in one cell, average or take lowest confidence. We'll take min to be safe.
                    current["confidence"] = min(current["confidence"], conf)
            
            rows_with_text = []
            for r_idx, row in enumerate(rows):
                row_cells = []
                for c_idx, (x, y, w, h) in enumerate(row):
                    cell_info = cell_texts[(r_idx, c_idx)]
                    text = cell_info["text"].strip()
                    confidence = cell_info["confidence"]
                    row_cells.append({"x": x, "y": y, "w": w, "h": h, "text": text, "confidence": round(confidence, 3)})
                rows_with_text.append(row_cells)
                
            # --- START FALLBACK & VERTICAL OCR ---
            print("Running Fallback & Vertical OCR on problem cells...")
            fallback_count = 0
            
            import json
            import difflib
            header_vocab = []
            try:
                vocab_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "header_vocab.json")
                with open(vocab_path, "r", encoding="utf-8") as f:
                    vocab_data = json.load(f)
                    header_vocab = vocab_data.get("default", [])
            except Exception as e:
                print("Could not load header_vocab.json:", e)
                
            for r_idx, row in enumerate(rows_with_text):
                is_header_row = (r_idx < 4)
                
                for c_idx, cell in enumerate(row):
                    x, y, w, h = cell['x'], cell['y'], cell['w'], cell['h']
                    old_text = cell['text']
                    old_confidence = cell['confidence']
                    
                    needs_fallback = False
                    rotate_needed = False
                    
                    if not old_text.strip():
                        needs_fallback = True
                    elif is_header_row and h > w * 1.2:
                        needs_fallback = True
                        rotate_needed = True
                        
                    if needs_fallback:
                        crop = image[y:y+h, x:x+w]
                        if crop.size == 0: continue
                        
                        pad = 10
                        crop = cv2.copyMakeBorder(crop, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=[255, 255, 255])
                        
                        if rotate_needed:
                            crop = cv2.rotate(crop, cv2.ROTATE_90_CLOCKWISE)
                            
                        import logging
                        logging.getLogger('ppocr').setLevel(logging.ERROR)
                        fallback_result = paddle_reader.ocr(crop)
                        
                        new_text = ""
                        new_conf = 0.0
                        if fallback_result and isinstance(fallback_result[0], dict) and 'rec_texts' in fallback_result[0]:
                            texts = fallback_result[0]['rec_texts']
                            confs = fallback_result[0]['rec_scores'] if 'rec_scores' in fallback_result[0] else [1.0]*len(texts)
                            new_text = " ".join([str(t).strip() for t in texts if str(t).strip()])
                            if confs:
                                new_conf = sum(confs) / len(confs)
                        elif fallback_result and fallback_result[0] and isinstance(fallback_result[0], list):
                            texts = []
                            confs = []
                            for item in fallback_result[0]:
                                if isinstance(item, (tuple, list)) and len(item) > 1:
                                    if isinstance(item[1], (tuple, list)) and len(item[1]) >= 2:
                                        texts.append(str(item[1][0]).strip())
                                        confs.append(float(item[1][1]))
                                    else:
                                        texts.append(str(item[1]).strip())
                                        confs.append(1.0)
                            new_text = " ".join([t for t in texts if t])
                            if confs:
                                new_conf = sum(confs) / len(confs)
                                
                        new_text = new_text.strip()
                        matches = []
                        
                        if rotate_needed and new_text:
                            # Fuzzy matching for vertical headers
                            matches = difflib.get_close_matches(new_text, header_vocab, n=1, cutoff=0.5)
                            if matches:
                                new_text = matches[0]
                                new_conf = 1.0 # high confidence if it matched vocab
                                
                        if new_text:
                            if not old_text.strip():
                                cell['text'] = new_text
                                cell['confidence'] = round(new_conf, 3)
                                fallback_count += 1
                            elif rotate_needed and (new_conf > 0.40 or matches):
                                cell['text'] = new_text
                                cell['confidence'] = round(new_conf, 3)
                                fallback_count += 1
                            elif new_conf > old_confidence:
                                cell['text'] = new_text
                                cell['confidence'] = round(new_conf, 3)
                                fallback_count += 1

            print(f"Fallback & Vertical OCR updated {fallback_count} cells.")
            # --- END FALLBACK & VERTICAL OCR ---
            table_regions = []
            if rows_with_text:
                all_x = []
                all_y = []
                all_xw = []
                all_yh = []
                for row in rows_with_text:
                    for cell in row:
                        all_x.append(cell['x'])
                        all_y.append(cell['y'])
                        all_xw.append(cell['x'] + cell['w'])
                        all_yh.append(cell['y'] + cell['h'])
                
                if all_x:
                    table_regions.append([min(all_x), min(all_y), max(all_xw), max(all_yh)])
                    
            print(f"OCR mapping completed: {time.time() - start:.2f}s")
            
            # Phase 4.1: Return structured intermediate representation
            return {
                "rows": rows_with_text,
                "table_regions": table_regions,
                "page_image": processed_path
            }

    # -------------------------
    # Image OCR
    # -------------------------

    else:

        import time
        start = time.time()
        print("Starting OCR for Image...")

        directory, filename = os.path.split(filepath)
        processed_path = os.path.join(TEMP_FOLDER, f"processed_{filename}")

        processed_path = preprocess_image(filepath, processed_path)
        print(f"Preprocessing completed: {time.time() - start:.2f}s")

        image, gray = detect_table(processed_path)
        print(image.shape)

        binary, horizontal = detect_horizontal_lines(gray)
        vertical = detect_vertical_lines(gray)

        grid = build_table_grid(
            horizontal,
            vertical
        )

        contours = detect_table_cells(grid)

        print("\n========== TABLE DETECTION ==========")
        print(f"Total contours found: {len(contours)}")
        print("=====================================\n")

        detected_cells = draw_detected_cells(
            image,
            contours
        )

        filtered_cells = filter_cells(contours)

        print("\n========== CELL FILTER ==========")
        print(f"Contours Found : {len(contours)}")
        print(f"Filtered Cells : {len(filtered_cells)}")
        print("=================================\n")

        # 1. Sort cells into rows
        rows = sort_cells_by_rows(filtered_cells)
        
        print(f"Table detection completed: {time.time() - start:.2f}s")
        
        # Run Full Page OCR once
        print("Running Full Page OCR on image...")
        
        # Scale down large images to prevent 20-minute CPU hangs
        max_dim = 1000
        h, w = image.shape[:2]
        scale = 1.0
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            scaled_image = cv2.resize(image, (0, 0), fx=scale, fy=scale)
        else:
            scaled_image = image
            
        print("Image Shape:", scaled_image.shape)
        print("Image Type:", scaled_image.dtype)
        
        import time
        t = time.time()
        
        print("Calling paddle_reader.ocr()...")
        
        result = paddle_reader.ocr(scaled_image)
        
        print("Returned from paddle_reader.ocr()")
        print(f"OCR Time: {time.time()-t:.2f} sec")
        
        paddle_boxes = []
        if result and isinstance(result[0], dict) and 'rec_polys' in result[0]:
            for poly, txt, conf in zip(result[0]['rec_polys'], result[0]['rec_texts'], result[0]['rec_scores'] if 'rec_scores' in result[0] else [1.0]*len(result[0]['rec_texts'])):
                paddle_boxes.append((poly, txt, conf))
        elif result and isinstance(result[0], list):
            for item in result[0]:
                if isinstance(item[1], (tuple, list)) and len(item[1]) >= 2:
                    paddle_boxes.append((item[0], item[1][0], float(item[1][1])))
                else:
                    paddle_boxes.append((item[0], item[1][0], 1.0))
        
        # Map text to cells using Maximum Intersection Area (IoU logic)
        cell_texts = { (r, c): {"text": "", "confidence": 1.0} for r in range(len(rows)) for c in range(len(rows[r])) }
        
        for box, txt, conf in paddle_boxes:
            bx1 = min(p[0] for p in box) / scale
            by1 = min(p[1] for p in box) / scale
            bx2 = max(p[0] for p in box) / scale
            by2 = max(p[1] for p in box) / scale
            
            max_overlap = 0
            best_cell = None
            
            for r_idx, row in enumerate(rows):
                for c_idx, (x, y, w, h) in enumerate(row):
                    ix1 = max(bx1, x)
                    iy1 = max(by1, y)
                    ix2 = min(bx2, x + w)
                    iy2 = min(by2, y + h)
                    
                    if ix1 < ix2 and iy1 < iy2:
                        inter_area = (ix2 - ix1) * (iy2 - iy1)
                        if inter_area > max_overlap:
                            max_overlap = inter_area
                            best_cell = (r_idx, c_idx)
                            
            if best_cell:
                current = cell_texts[best_cell]
                current["text"] += str(txt) + " "
                current["confidence"] = min(current["confidence"], conf)
        
        rows_with_text = []
        for r_idx, row in enumerate(rows):
            row_cells = []
            for c_idx, (x, y, w, h) in enumerate(row):
                cell_info = cell_texts[(r_idx, c_idx)]
                text = cell_info["text"].strip()
                confidence = cell_info["confidence"]
                row_cells.append({"x": x, "y": y, "w": w, "h": h, "text": text, "confidence": round(confidence, 3)})
            rows_with_text.append(row_cells)
            
        table_regions = []
        if rows_with_text:
            all_x = []
            all_y = []
            all_xw = []
            all_yh = []
            for row in rows_with_text:
                for cell in row:
                    all_x.append(cell['x'])
                    all_y.append(cell['y'])
                    all_xw.append(cell['x'] + cell['w'])
                    all_yh.append(cell['y'] + cell['h'])
            
            if all_x:
                table_regions.append([min(all_x), min(all_y), max(all_xw), max(all_yh)])
                
        print(f"OCR mapping completed: {time.time() - start:.2f}s")
        
        # Phase 4.1: Return structured intermediate representation
        return {
            "rows": rows_with_text,
            "table_regions": table_regions,
            "page_image": processed_path
        }

def recognize_image(image_path):
    """
    Stage 2.3 - Targeted OCR Engine
    Performs text recognition on a single cropped image (cell or metadata).
    Completely independent of layout.
    """
    import time
    import json
    
    print(f"[OCR] recognize_image() entered: {image_path}")
    start_time = time.time()
    
    # Initialize default enterprise response
    response = {
        "engine": "PaddleOCR",
        "text": "",
        "confidence": 0.0,
        "processing_time_ms": 0,
        "image_size": [0, 0],
        "empty": True,
        "needs_review": False
    }
    
    if not os.path.exists(image_path):
        response["text"] = "[FILE NOT FOUND]"
        response["needs_review"] = True
        return response
        
    image = cv2.imread(image_path)
    if image is None:
        response["text"] = "[UNREADABLE IMAGE]"
        response["needs_review"] = True
        return response
        
    h, w = image.shape[:2]
    response["image_size"] = [w, h]
    
    # Fast Empty Check
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 220, 255, cv2.THRESH_BINARY_INV)
    ink_pixels = cv2.countNonZero(binary)
    total_pixels = binary.size
    
    # If less than 0.5% of the crop has ink, it's effectively blank
    if ink_pixels < (total_pixels * 0.005):
        response["processing_time_ms"] = int((time.time() - start_time) * 1000)
        return response
        
    response["empty"] = False
    
    try:
        # Perform OCR
        print("[OCR] Calling PaddleOCR...")
        paddle_start = time.time()
        result = paddle_reader.ocr(image)
        paddle_end = time.time()
        print("[OCR] PaddleOCR returned")
        print(f"[OCR] Execution time: {paddle_end - paddle_start:.4f}s")
        
        extracted_texts = []
        confidences = []
        
        if result and isinstance(result[0], list):
            for item in result[0]:
                if isinstance(item[1], (tuple, list)) and len(item[1]) >= 2:
                    extracted_texts.append(str(item[1][0]))
                    confidences.append(float(item[1][1]))
                else:
                    extracted_texts.append(str(item[1][0]))
                    confidences.append(1.0)
                    
        if extracted_texts:
            response["text"] = " ".join(extracted_texts).strip()
            # Calculate average confidence across all words in this crop
            response["confidence"] = round(sum(confidences) / len(confidences), 3)
            if response["confidence"] < 0.80:
                response["needs_review"] = True
                
    except Exception as e:
        print(f"OCR Error on {image_path}: {e}")
        response["text"] = "[OCR FAILED]"
        response["needs_review"] = True
        
    response["processing_time_ms"] = int((time.time() - start_time) * 1000)
    
    # Save Debug Output
    try:
        base_dir = os.path.abspath(os.path.dirname(__file__))
        debug_folder = os.path.join(base_dir, "..", "debug")
        os.makedirs(debug_folder, exist_ok=True)
        debug_path = os.path.join(debug_folder, "ocr_results.json")
        
        # We append to the JSON array to create a log of processed crops
        log_entry = {
            "image_path": image_path,
            "recognized_text": response["text"],
            "confidence": response["confidence"],
            "processing_time": response["processing_time_ms"]
        }
        
        existing_logs = []
        if os.path.exists(debug_path):
            try:
                with open(debug_path, "r") as f:
                    existing_logs = json.load(f)
            except json.JSONDecodeError:
                existing_logs = []
                
        existing_logs.append(log_entry)
        
        with open(debug_path, "w") as f:
            json.dump(existing_logs, f, indent=4)
            
    except Exception as e:
        print(f"Warning: Failed to write debug ocr_results.json: {e}")
        
    return response

def integrate_ocr_results(layout_object):
    """
    Phase 3 - Table-Level OCR Milestone & Stage 2 Execution
    Runs PaddleOCR on page/table images, dumps raw_paddle_output.json, ocr_input.png,
    and maps OCR tokens into table cells.
    """
    import os
    import json
    import time
    import cv2

    ocr_versions = layout_object.get("ocr_versions", {})
    printed_img_path = ocr_versions.get("printed") or ocr_versions.get("layout")

    original_file = layout_object.get("document_info", {}).get("original_file", "")
    doc_name = os.path.splitext(os.path.basename(original_file))[0] if original_file else "document"

    base_dir = os.path.abspath(os.path.dirname(__file__))
    debug_folder = os.path.join(base_dir, "..", "debug")
    doc_debug_dir = os.path.join(debug_folder, doc_name)
    os.makedirs(debug_folder, exist_ok=True)
    os.makedirs(doc_debug_dir, exist_ok=True)

    printed_page_img = None
    if printed_img_path and os.path.exists(printed_img_path):
        printed_page_img = cv2.imread(printed_img_path)
    elif original_file and os.path.exists(original_file) and not original_file.lower().endswith(".pdf"):
        printed_page_img = cv2.imread(original_file)

    all_paddle_boxes = []

    for table in layout_object.get("tables", []):
        t_id = table.get("table_id")
        table_img_path = table.get("image_path")

        table_crop = None
        if printed_page_img is not None:
            tx1, ty1, tx2, ty2 = table.get("bbox", [0, 0, 0, 0])
            if tx2 > tx1 and ty2 > ty1:
                table_crop = printed_page_img[ty1:ty2, tx1:tx2]

        if table_crop is None and table_img_path and os.path.exists(table_img_path):
            table_crop = cv2.imread(table_img_path)

        if table_crop is None:
            print(f"[OCR WARN] Could not obtain image matrix for Table {t_id}")
            continue

        h, w = table_crop.shape[:2]
        c = table_crop.shape[2] if len(table_crop.shape) == 3 else 1
        print(f"\n[OCR] Image width: {w}, Image height: {h}, Channels: {c}")

        # Save ocr_input.png
        cv2.imwrite(os.path.join(debug_folder, "ocr_input.png"), table_crop)
        cv2.imwrite(os.path.join(doc_debug_dir, "ocr_input.png"), table_crop)

        print(f"Running PaddleOCR on Table {t_id}...")

        # Scale down large table crops to prevent CPU hangs
        scale = 1.0
        if w > 1024:
            scale = 1024 / w
            resized_crop = cv2.resize(table_crop, None, fx=scale, fy=scale)
            t0 = time.time()
            result = paddle_reader.ocr(resized_crop)
        else:
            t0 = time.time()
            result = paddle_reader.ocr(table_crop)

        print(f"PaddleOCR completed. Inference time: {time.time() - t0:.2f}s")

        table_tokens = 0
        if result:
            if hasattr(result[0], 'keys') and 'rec_texts' in result[0]:
                res_dict = result[0]
                polys = res_dict.get('dt_polys', [])
                texts = res_dict.get('rec_texts', [])
                scores = res_dict.get('rec_scores', [])

                for i in range(len(texts)):
                    box = polys[i] if i < len(polys) else []
                    txt = str(texts[i])
                    conf = float(scores[i]) if i < len(scores) else 1.0
                    scaled_box = [[float(p[0]) / scale, float(p[1]) / scale] for p in box]
                    all_paddle_boxes.append({"table_id": t_id, "box": scaled_box, "text": txt, "confidence": conf})
                    table_tokens += 1

            elif isinstance(result[0], list):
                for item in result[0]:
                    if isinstance(item[1], (tuple, list)) and len(item[1]) >= 2:
                        box = item[0]
                        txt = str(item[1][0])
                        conf = float(item[1][1])
                        scaled_box = [[float(p[0]) / scale, float(p[1]) / scale] for p in box]
                        all_paddle_boxes.append({"table_id": t_id, "box": scaled_box, "text": txt, "confidence": conf})
                        table_tokens += 1
                    else:
                        box = item[0]
                        txt = str(item[1][0])
                        scaled_box = [[float(p[0]) / scale, float(p[1]) / scale] for p in box]
                        all_paddle_boxes.append({"table_id": t_id, "box": scaled_box, "text": txt, "confidence": 1.0})
                        table_tokens += 1

        print(f"PaddleOCR completed. Detected tokens: {table_tokens}")
        
        # FIX: If PaddleOCR internally rotated the image by 90 degrees, it will return swapped coordinates.
        # We can detect this if the max X in PaddleOCR boxes exceeds the image width.
        if all_paddle_boxes:
            paddle_max_x = max(p[0] for pb in all_paddle_boxes if pb["table_id"] == t_id for p in pb["box"])
            if paddle_max_x > w * 1.2:
                print(f"[OCR INFO] PaddleOCR rotated coordinates detected (max_x={paddle_max_x} > w={w}). Swapping X and Y.")
                for pb in all_paddle_boxes:
                    if pb["table_id"] == t_id:
                        pb["box"] = [[p[1], p[0]] for p in pb["box"]]

    # Save raw_paddle_output.json
    raw_paddle_path1 = os.path.join(debug_folder, "raw_paddle_output.json")
    raw_paddle_path2 = os.path.join(doc_debug_dir, "raw_paddle_output.json")
    with open(raw_paddle_path1, "w", encoding="utf-8") as f:
        json.dump(all_paddle_boxes, f, indent=4)
    with open(raw_paddle_path2, "w", encoding="utf-8") as f:
        json.dump(all_paddle_boxes, f, indent=4)

    total_tokens = len(all_paddle_boxes)
    non_empty_tokens = [b for b in all_paddle_boxes if b["text"].strip() != ""]
    avg_conf = sum(b["confidence"] for b in non_empty_tokens) / len(non_empty_tokens) if non_empty_tokens else 0.0

    # Count total detected cells in matrix
    total_cells = sum(
        len(cell_list)
        for table in layout_object.get("tables", [])
        for row in table.get("matrix", [])
        for cell_list in ([row.get("cells", [])] if isinstance(row, dict) else [row])
    )

    print("\n=========================================")
    print("      STAGE 2 OCR EXTRACTION RESULTS     ")
    print("=========================================")
    print(f"Detected cells:         {total_cells}")
    print(f"OCR tokens:             {total_tokens}")
    print(f"Non-empty tokens:       {len(non_empty_tokens)}")
    print(f"Average confidence:     {avg_conf:.3f}")
    print(f"Raw output saved to:    {raw_paddle_path2}")
    print("=========================================\n")

    
    # ---------------------------------------------------------
    # PHASE 4: IoU Mapping
    # ---------------------------------------------------------
    print("[OCR] Starting Phase 4: IoU Mapping...")
    
    # 1. No shifting required - both cell['bbox'] and pbox['box'] are in table_crop local coordinates.
    # We just need to assign the pboxes directly for IoU mapping.
    local_paddle_boxes = []
    for pbox in all_paddle_boxes:
        t_id = pbox["table_id"]
        
        # pbox["box"] is a list of 4 points: [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
        # ALREADY relative to the table crop! No shift needed.
        local_box = [[p[0], p[1]] for p in pbox["box"]]
        
        local_paddle_boxes.append({
            "table_id": t_id,
            "box": local_box,
            "text": pbox["text"],
            "confidence": pbox["confidence"]
        })
        
    def get_bounding_box(polygon):
        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]
        return [min(xs), min(ys), max(xs), max(ys)]

    # 3. Map text into cells - Reversed approach: For each text box, find the BEST cell
    for table in layout_object.get("tables", []):
        t_id = table.get("table_id")
        table_paddle_boxes = [pb for pb in local_paddle_boxes if pb["table_id"] == t_id]
        
        # Initialize an empty list of texts for each cell
        for row in table.get("rows", table.get("matrix", [])):
            cells_list = row.get("cells", []) if isinstance(row, dict) else row
            for cell in cells_list:
                cell["assigned_texts"] = []
                
        for pb in table_paddle_boxes:
            pb_bbox = get_bounding_box(pb["box"])
            pbArea = (pb_bbox[2] - pb_bbox[0]) * (pb_bbox[3] - pb_bbox[1])
            if pbArea <= 0: continue
            
            pb_cx = (pb_bbox[0] + pb_bbox[2]) / 2
            pb_cy = (pb_bbox[1] + pb_bbox[3]) / 2
            
            best_cell = None
            max_inter = 0

            
            # 1. IoU Overlap Pass
            for row in table.get("rows", table.get("matrix", [])):
                cells_list = row.get("cells", []) if isinstance(row, dict) else row
                for cell in cells_list:
                    cell_bbox = cell.get("bbox")
                    xA = max(cell_bbox[0], pb_bbox[0])
                    yA = max(cell_bbox[1], pb_bbox[1])
                    xB = min(cell_bbox[2], pb_bbox[2])
                    yB = min(cell_bbox[3], pb_bbox[3])
                    
                    interArea = max(0, xB - xA) * max(0, yB - yA)
                    if interArea > max_inter:
                        max_inter = interArea
                        best_cell = cell

            # 2. Spatial Row/Col Fallback Pass (Fixes text in left margins / wide headers)
            if best_cell is None or max_inter == 0:
                valid_rows = [r.get("cells", []) if isinstance(r, dict) else r for r in table.get("rows", table.get("matrix", [])) if r]
                if valid_rows:
                    def get_row_cy(r):
                        y1 = min(c["bbox"][1] for c in r)
                        y2 = max(c["bbox"][3] for c in r)
                        return (y1 + y2) / 2
                    matching_row = min(valid_rows, key=lambda r: abs(pb_cy - get_row_cy(r)))
                    best_cell = min(matching_row, key=lambda c: abs(pb_cx - (c["bbox"][0] + c["bbox"][2]) / 2))

                    
            if best_cell is not None:
                # Store the text, confidence, and the center Y for sorting
                center_y = (pb_bbox[1] + pb_bbox[3]) / 2
                best_cell["assigned_texts"].append({
                    "text": pb["text"],
                    "confidence": pb["confidence"],
                    "y": center_y,
                    "x": pb_bbox[0]
                })

                
        # Now format the assigned texts into the final cell output
        for row in table.get("rows", table.get("matrix", [])):
            cells_list = row.get("cells", []) if isinstance(row, dict) else row
            for cell in cells_list:
                assigned = cell.pop("assigned_texts", [])
                
                if assigned:
                    # Sort by Y first, then X
                    assigned.sort(key=lambda t: (t["y"] // 15, t["x"]))
                    
                    formatted_text = ""
                    total_conf = 0
                    
                    for i, t in enumerate(assigned):
                        total_conf += t["confidence"]
                        if i == 0:
                            formatted_text += t["text"]
                        else:
                            # If significant Y difference, use newline, else space
                            if abs(t["y"] - assigned[i-1]["y"]) > 15:
                                formatted_text += "\n" + t["text"]
                            else:
                                formatted_text += " " + t["text"]
                                
                    cell["ocr"] = {
                        "raw_text": formatted_text,
                        "confidence": total_conf / len(assigned),
                        "status": "extracted"
                    }
                else:
                    cell["ocr"] = {
                        "raw_text": "",
                        "confidence": 1.0,
                        "status": "empty"
                    }

    print("[OCR] Completed IoU Mapping to Cells")

    layout_object["ocr_statistics"] = {
        "total_tokens": total_tokens,
        "non_empty_tokens": len(non_empty_tokens),
        "average_confidence": round(avg_conf, 3)
    }
    
    return layout_object