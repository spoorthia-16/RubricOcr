import os
import cv2
import json
import time
import shutil
import traceback
from datetime import datetime

# Importers for Stage 1
from services.pdf_service import pdf_to_images
from utils.image_utils import preprocess_image, correct_page_orientation
from services.preprocessing_service import process_document_phase1
from config.preprocessing_config import ENABLE_PHASE_1
from utils.table_detector import (
    detect_table_regions, crop_table_regions, detect_grid_lines,
    reconstruct_grid, extract_cells_from_grid, build_cell_matrix,
    detect_merged_cells, detect_metadata_regions, build_layout_object
)

# Importers for Stage 2
from utils.cell_cropper import generate_cell_images, generate_metadata_images
from services.ocr_service import integrate_ocr_results
from services.ocr_validator import validate_ocr_document, classify_ocr_regions, build_gpt_review_package

# Importers for Stage 3 (LLM Execution Engine & Validation)
from config import ENABLE_LLM_CORRECTION
from llm.correction_service import CorrectionService
from services.document_merger import merge_gpt_results
from services.validation_service import validate_document
from services.document_finalizer import build_final_document
from services.diagnostic_manager import DiagnosticManager



# Importers for Stage 4
from services.document_serializer import serialize_document
from services.workbook_builder import build_workbook
from services.worksheet_populator import populate_workbook
from services.merge_manager import apply_merges
from services.style_manager import apply_styles
from services.dimension_manager import adjust_dimensions
from services.excel_writer import write_excel

# Enterprise 1: State Machine
PIPELINE_STATES = [
    "UPLOAD",
    "LAYOUT",
    "OCR",
    "GPT",
    "VALIDATION",
    "SERIALIZATION",
    "EXCEL",
    "COMPLETED",
    "FAILED"
]

DEBUG_MODE = True

def _print_progress(step_num, total_steps, title):
    print(f"\n[{step_num}/{total_steps}] {title}")
    
def _cleanup_memory(context):
    if DEBUG_MODE:
        return
        
    print("Performing memory cleanup...")
    temp_dirs = ["temp/cells", "temp/metadata", "temp/processed_test.png"]
    
    for item in temp_dirs:
        path = os.path.join(os.path.dirname(__file__), "..", item)
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
        elif os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass

def process_document(input_file):
    """
    Phase 5 - Pipeline Orchestrator & System Integration
    Master orchestration engine to execute the complete document processing workflow.
    Ensures fault tolerance, clean data handoffs, and progression tracking.
    """
    overall_start = time.time()
    
    # Enterprise 3: Context Object & Diagnostic Manager
    context = {
        "input_file": input_file,
        "current_state": "UPLOAD",
        "timings": {},
        "page_image": None
    }
    
    base_dir = os.path.abspath(os.path.dirname(__file__))
    debug_folder = os.path.join(base_dir, "..", "debug")
    os.makedirs(debug_folder, exist_ok=True)
    
    diag = DiagnosticManager(os.path.basename(input_file))

    # ---------------------------------------------------------
    # STAGE 1: LAYOUT ANALYSIS
    # ---------------------------------------------------------
    try:
        context["current_state"] = "LAYOUT"
        print(f"\n[START] Stage 1/4: Layout Analysis")
        stage_start = time.time()
        
        if ENABLE_PHASE_1 and input_file.lower().endswith('.pdf'):
            phase1_results = process_document_phase1(input_file)

            first_page_res = phase1_results[0]
            
            # Use Layout Optimized version for layout detection
            img_path = first_page_res["versions"]["layout"]
            corrected_img = cv2.imread(img_path)
            
            # Since deskew was already applied in Phase 1, we just copy it
            angle = first_page_res["quality"]["skew_angle"]
            context["page_image"] = corrected_img
        else:
            if input_file.lower().endswith('.pdf'):
                image_paths = pdf_to_images(input_file)
                if not image_paths:
                    raise ValueError("PDF to Image conversion failed.")
                img_path = image_paths[0]
            else:
                img_path = input_file
                
            processed_path = os.path.join(base_dir, "..", "temp", "processed_test.png")
            os.makedirs(os.path.dirname(processed_path), exist_ok=True)
            
            preprocess_image(img_path, processed_path)
            image = cv2.imread(processed_path)
            
            corrected_img, angle = correct_page_orientation(image)
            context["page_image"] = corrected_img
        
        tables = detect_table_regions(corrected_img)
        cropped_tables = crop_table_regions(corrected_img, tables)
        
        tables_data = []
        for c_table in cropped_tables:
            t_id = c_table["table_id"]
            t_img = cv2.imread(c_table["image_path"])
            
            grid_model = detect_grid_lines(t_img, table_id=t_id)
            grid_model["table_id"] = t_id
            
            recon_model = reconstruct_grid(grid_model)
            recon_model["table_id"] = t_id
            
            cells = extract_cells_from_grid(recon_model, overlay_img=t_img)
            matrix_data = build_cell_matrix(cells, table_id=t_id, overlay_img=t_img)
            
            final_matrix = detect_merged_cells(matrix_data, overlay_img=t_img)
            
            tables_data.append({
                "table_id": t_id,
                "image_path": c_table["image_path"],
                "bbox": c_table["bbox"],
                "dimensions": final_matrix.get("dimensions", matrix_data.get("dimensions", {})),
                "matrix": final_matrix.get("matrix", []),
                "rows": final_matrix.get("rows", []),
                "merged_regions": final_matrix.get("merged_regions", []),
                "statistics": matrix_data.get("statistics", {})
            })
            
        metadata_res = detect_metadata_regions(corrected_img, tables)
        
        context["layout_object"] = build_layout_object(
            corrected_img, 
            metadata_res["metadata_regions"], 
            tables_data, 
            page_num=1
        )
        
        context["layout_object"]["document_info"]["original_file"] = input_file
        
        if ENABLE_PHASE_1 and input_file.lower().endswith('.pdf'):
            context["layout_object"]["ocr_versions"] = first_page_res["versions"]

            
        print("DEBUG: layout_object before returning from LAYOUT stage keys =", context["layout_object"].keys())
        print("DEBUG: ocr_versions at LAYOUT stage =", context["layout_object"].get("ocr_versions", "MISSING"))
        
        # Stage 1 Diagnostic Validation
        h_mask_path = os.path.join(debug_folder, "horizontal_lines.png")
        v_mask_path = os.path.join(debug_folder, "vertical_lines.png")
        grid_vis_path = os.path.join(debug_folder, "table1_reconstructed_grid.png")
        table_crop_path = cropped_tables[0]["image_path"] if cropped_tables else None

        h_mask = cv2.imread(h_mask_path) if os.path.exists(h_mask_path) else None
        v_mask = cv2.imread(v_mask_path) if os.path.exists(v_mask_path) else None
        grid_vis = cv2.imread(grid_vis_path) if os.path.exists(grid_vis_path) else None
        table_crop_img = cv2.imread(table_crop_path) if (table_crop_path and os.path.exists(table_crop_path)) else None

        stg1_report = diag.validate_stage1_layout(
            original_img=context["page_image"],
            horizontal_mask=h_mask,
            vertical_mask=v_mask,
            grid_overlay_img=grid_vis,
            table_crop_img=table_crop_img,
            layout_object=context["layout_object"]
        )

        if stg1_report.get("status") == "FAILED":
            print("STAGE 1 FAILED\nGrid reconstruction invalid")
            context["current_state"] = "FAILED"
            return {"status": "FAILED", "failed_stage": "LAYOUT", "reason": "STAGE 1 FAILED: Grid reconstruction invalid"}

        elapsed = time.time() - stage_start
        context["timings"]["layout_ms"] = int(elapsed * 1000)
        print(f"[OK] Completed Layout Analysis in {elapsed:.2f}s")
        
    except Exception as e:
        traceback.print_exc()
        context["current_state"] = "FAILED"
        return {"status": "FAILED", "failed_stage": "LAYOUT", "reason": str(e)}

    # ---------------------------------------------------------
    # STAGE 2: OCR PIPELINE
    # ---------------------------------------------------------
    try:
        context["current_state"] = "OCR"
        print(f"\n[START] Stage 2/4: OCR Pipeline")
        stage_start = time.time()
        
        temp_cells = os.path.join(base_dir, "..", "temp", "cells")
        temp_meta = os.path.join(base_dir, "..", "temp", "metadata")
        
        print("[OCR] Generating cell images...")
        t_cells = time.time()
        layout_with_cells = generate_cell_images(context["layout_object"], output_dir=temp_cells)
        print(f"[OCR] Cell images generated in {time.time() - t_cells:.2f} sec")
        
        print("[OCR] Generating metadata images...")
        t_meta = time.time()
        layout_with_meta = generate_metadata_images(layout_with_cells, context["page_image"], output_dir=temp_meta)
        print(f"[OCR] Metadata generated in {time.time() - t_meta:.2f} sec")
        
        print("[OCR] Starting OCR integration...")
        context["ocr_document"] = integrate_ocr_results(layout_with_meta)
        validate_ocr_document(context["ocr_document"])
        
        context["classified_document"] = classify_ocr_regions(context["ocr_document"])
        context["gpt_package"] = build_gpt_review_package(context["classified_document"])
        
        # Stage 2 Diagnostic Validation
        stg2_report = diag.validate_stage2_ocr(
            layout_with_cells=layout_with_cells,
            ocr_document=context["ocr_document"]
        )

        if stg2_report.get("status") == "FAILED":
            fail_reason = (
                "STAGE 2 FAILED\n\nReason:\nNo OCR tokens were produced.\n\n"
                "Possible causes:\n- OCR engine not executed\n- OCR model failed to initialize\n"
                "- Wrong image passed to OCR\n- Empty image\n- Incorrect OCR API call"
            )
            print(f"\n{fail_reason}\n")
            context["current_state"] = "FAILED"
            return {"status": "FAILED", "failed_stage": "OCR", "reason": fail_reason}

        elapsed = time.time() - stage_start
        print(f"[OK] Completed OCR Pipeline in {elapsed:.2f}s")

        
    except Exception as e:
        traceback.print_exc()
        context["current_state"] = "FAILED"
        return {"status": "FAILED", "failed_stage": "OCR", "reason": str(e)}

    # ---------------------------------------------------------
    # STAGE 3: LLM CORRECTION ENGINE & DOCUMENT FINALIZATION
    # ---------------------------------------------------------
    try:
        context["current_state"] = "GPT"
        print(f"\n[START] Stage 3/4: LLM Execution Engine")
        stage_start = time.time()
        
        ocr_doc = context["ocr_document"]
        
        if ENABLE_LLM_CORRECTION:
            print("[LLM Engine] ENABLE_LLM_CORRECTION is True. Executing LLM Execution Engine...")
            try:
                engine = CorrectionService()
                correction_result = engine.correct_document(ocr_doc)
                
                context["correction_result"] = correction_result
                context["corrected_ocr_document"] = correction_result.corrected_document
                context["gpt_status"] = "completed"
                
                print(f"[OK] LLM Execution Engine finished | "
                      f"Applied: {correction_result.accepted_patch_count} | "
                      f"Rejected: {correction_result.rejected_patch_count} | "
                      f"Latency: {correction_result.llm_latency:.2f}s")
            except Exception as llm_err:
                print(f"[WARN] LLM Execution Engine error: {llm_err}. Falling back to OCR document.")
                context["corrected_ocr_document"] = ocr_doc
                context["gpt_status"] = "failed"
        else:
            print("[LLM Engine] ENABLE_LLM_CORRECTION is False. Mode: OCR-Only.")
            context["corrected_ocr_document"] = ocr_doc
            context["gpt_status"] = "skipped"

        context["current_state"] = "VALIDATION"
        active_doc = context.get("corrected_ocr_document", ocr_doc)
        
        context["merged_document"] = merge_gpt_results(active_doc, {"results": []})
        context["validated_document"] = validate_document(context["merged_document"])
        
        context["validated_document"]["pipeline_status"] = {
            "layout": "completed",
            "ocr": "completed",
            "gpt_review": context["gpt_status"]
        }
        
        context["final_document"] = build_final_document(context["validated_document"])
        context["final_document"]["document_status"] = "READY_FOR_EXPORT"
            
        # Stage 3 Diagnostic Validation
        corr_res = context.get("correction_result")
        applied_p = corr_res.applied_patches if (corr_res and hasattr(corr_res, "applied_patches")) else []
        rejected_p = corr_res.rejected_patches if (corr_res and hasattr(corr_res, "rejected_patches")) else []

        stg3_report = diag.validate_stage3_ocr_document(
            ocr_doc=context["ocr_document"],
            corrected_doc=context.get("corrected_ocr_document", context["ocr_document"]),
            llm_patches=applied_p,
            rejected_patches=rejected_p
        )

        elapsed = time.time() - stage_start
        context["timings"]["gpt_ms"] = int(elapsed * 1000)
        print(f"[OK] Completed Stage 3 (LLM Execution Engine) in {elapsed:.2f}s")
        
    except Exception as e:
        traceback.print_exc()
        context["current_state"] = "FAILED"
        return {"status": "FAILED", "failed_stage": "GPT/VALIDATION", "reason": str(e)}

    # ---------------------------------------------------------
    # STAGE 4: EXCEL EXPORT
    # ---------------------------------------------------------
    try:
        context["current_state"] = "SERIALIZATION"
        print(f"\n[START] Stage 4/4: Excel Export")
        stage_start = time.time()
        
        context["serialized_document"] = serialize_document(context["final_document"])
        
        context["current_state"] = "EXCEL"
        wb_bundle = build_workbook(context["serialized_document"])
        wb_bundle = populate_workbook(wb_bundle, context["serialized_document"])
        wb_bundle = apply_merges(wb_bundle, context["serialized_document"])
        wb_bundle = apply_styles(wb_bundle, context["serialized_document"])
        wb_bundle = adjust_dimensions(wb_bundle)
        
        export_result = write_excel(wb_bundle, context["serialized_document"])
        
        if export_result.get("status") != "SUCCESS":
            raise ValueError(f"Excel Export failed: {export_result.get('error')}")
            
        context["excel_path"] = export_result.get("file_path")
        
        # Stage 4 Diagnostic Validation
        exp_rows = stg3_report.get("actual", {}).get("rows", 0)
        exp_cols = stg3_report.get("actual", {}).get("columns", 0)

        stg4_report = diag.validate_stage4_workbook(
            excel_path=context["excel_path"],
            expected_rows=exp_rows,
            expected_cols=exp_cols
        )

        elapsed = time.time() - stage_start
        context["timings"]["excel_ms"] = int(elapsed * 1000)
        print(f"[OK] Completed Excel Export in {elapsed:.2f}s")
        
    except Exception as e:
        traceback.print_exc()
        context["current_state"] = "FAILED"
        return {"status": "FAILED", "failed_stage": "EXCEL", "reason": str(e)}

        
    # ---------------------------------------------------------
    # CLEANUP & REPORTING
    # ---------------------------------------------------------
    context["current_state"] = "COMPLETED"
    context["timings"]["total_ms"] = int((time.time() - overall_start) * 1000)
    
    pipeline_report = {
        "pipeline": context["timings"]
    }
    
    pipeline_manifest = {
        "pipeline_version": "1.0",
        "input_file": input_file,
        "output_file": context["excel_path"],
        "status": "SUCCESS"
    }
    
    try:
        with open(os.path.join(debug_folder, "pipeline_report.json"), "w") as f:
            json.dump(pipeline_report, f, indent=4)
        with open(os.path.join(debug_folder, "pipeline_timeline.json"), "w") as f:
            json.dump(context["timings"], f, indent=4)
        with open(os.path.join(debug_folder, "pipeline_manifest.json"), "w") as f:
            json.dump(pipeline_manifest, f, indent=4)
    except Exception as e:
        print(f"Warning: Failed to write debug pipeline files: {e}")
        
    _cleanup_memory(context)
        
    return {
        "status": "SUCCESS",
        "excel_file": context["excel_path"],
        "processing_summary": pipeline_report
    }

if __name__ == "__main__":
    # Test execution block
    import sys
    if len(sys.argv) > 1:
        res = process_document(sys.argv[1])
        print(json.dumps(res, indent=4))
    else:
        print("Usage: python pipeline_orchestrator.py <path_to_pdf>")
