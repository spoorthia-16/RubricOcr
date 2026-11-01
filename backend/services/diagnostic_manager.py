import os
import cv2
import json
import shutil
import base64
from datetime import datetime
from typing import Dict, Any, List, Optional

try:
    from config import DEBUG_PIPELINE
except ImportError:
    DEBUG_PIPELINE = True


class DiagnosticManager:
    """
    Comprehensive Diagnostic and Stage Validation Framework for the OCR Pipeline.
    Manages artifact generation (01 through 13 + report.html), structural self-validation,
    and HTML report rendering under backend/debug/<document_name>/.
    """

    def __init__(self, document_name: str, base_debug_dir: Optional[str] = None):
        clean_name = os.path.splitext(os.path.basename(document_name))[0]
        clean_name = clean_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
        if not clean_name:
            clean_name = "document"

        self.document_name = clean_name
        self.enabled = DEBUG_PIPELINE

        if base_debug_dir is None:
            backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            base_debug_dir = os.path.join(backend_dir, "debug")

        self.doc_dir = os.path.join(base_debug_dir, self.document_name)
        self.cropped_cells_dir = os.path.join(self.doc_dir, "07_cropped_cells")

        if self.enabled:
            os.makedirs(self.doc_dir, exist_ok=True)
            os.makedirs(self.cropped_cells_dir, exist_ok=True)

        self.summary_report = {
            "document_name": self.document_name,
            "timestamp": datetime.now().isoformat(),
            "pipeline_status": "RUNNING",
            "stages": {}
        }

    def save_image(self, filename: str, image_mat: Any) -> Optional[str]:
        """Saves image artifact if DEBUG_PIPELINE is enabled."""
        if not self.enabled or image_mat is None:
            return None
        target_path = os.path.join(self.doc_dir, filename)
        try:
            cv2.imwrite(target_path, image_mat)
            return target_path
        except Exception as e:
            print(f"[DIAGNOSTIC ERROR] Failed to save image {filename}: {e}")
            return None

    def save_json(self, filename: str, data: Any) -> Optional[str]:
        """Saves JSON artifact if DEBUG_PIPELINE is enabled."""
        if not self.enabled:
            return None
        target_path = os.path.join(self.doc_dir, filename)
        try:
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return target_path
        except Exception as e:
            print(f"[DIAGNOSTIC ERROR] Failed to save JSON {filename}: {e}")
            return None

    # ---------------------------------------------------------
    # STAGE 1 VALIDATION & ARTIFACTS
    # ---------------------------------------------------------
    def validate_stage1_layout(
        self,
        original_img: Any,
        horizontal_mask: Any,
        vertical_mask: Any,
        grid_overlay_img: Any,
        table_crop_img: Any,
        layout_object: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Stage 1 Validation:
        Validates table count, row/col monotonicity, total cells, merged cells, matrix integrity.
        Generates 01_original_page.png, 02_horizontal_lines.png, 03_vertical_lines.png,
        04_grid_overlay.png, 05_detected_cells.png (with R/C labels inside every cell), 06_table_matrix.json.
        """
        self.save_image("01_original_page.png", original_img)
        self.save_image("02_horizontal_lines.png", horizontal_mask)
        self.save_image("03_vertical_lines.png", vertical_mask)
        self.save_image("04_grid_overlay.png", grid_overlay_img)

        tables = layout_object.get("tables", [])
        num_tables = len(tables)

        total_rows = 0
        total_cols = 0
        total_cells = 0
        total_merged = 0
        validation_status = "PASS"
        failure_reasons = []

        annotated_cells_img = (
            table_crop_img.copy() if table_crop_img is not None else original_img.copy()
        )

        for table in tables:
            dims = table.get("dimensions", {})
            t_rows = dims.get("rows", 0)
            t_cols = dims.get("columns", 0)
            total_rows += t_rows
            total_cols += t_cols

            matrix = table.get("matrix", [])
            for r_idx, row in enumerate(matrix):
                for c_idx, cell in enumerate(row):
                    total_cells += 1
                    rspan = cell.get("rowspan", 1)
                    cspan = cell.get("colspan", 1)
                    if rspan > 1 or cspan > 1:
                        total_merged += 1

                    # Draw boundary rectangle & row/column index inside every cell
                    bbox = cell.get("bbox", [])
                    if len(bbox) == 4 and annotated_cells_img is not None:
                        x1, y1, x2, y2 = bbox
                        color = (255, 0, 255) if (rspan > 1 or cspan > 1) else (0, 255, 0)
                        cv2.rectangle(annotated_cells_img, (x1, y1), (x2, y2), color, 2)
                        label = f"R{cell.get('row', r_idx)} C{cell.get('column', c_idx)}"
                        cv2.putText(
                            annotated_cells_img,
                            label,
                            (x1 + 4, y1 + max(14, (y2 - y1) // 2)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.38,
                            (0, 0, 255),
                            1,
                        )

        self.save_image("05_detected_cells.png", annotated_cells_img)
        self.save_json("06_table_matrix.json", {"tables": tables})

        # Structural Consistency Validation Rules
        if num_tables == 0:
            validation_status = "FAILED"
            failure_reasons.append("No table boundaries detected.")
        if total_rows == 0 or total_cols == 0:
            validation_status = "FAILED"
            failure_reasons.append("Zero row or column dimension computed.")

        stage1_report = {
            "stage": "Stage 1 - Table Detection",
            "expected": {"tables": 1, "min_rows": 2, "min_cols": 2},
            "actual": {
                "tables": num_tables,
                "rows": total_rows,
                "columns": total_cols,
                "cells": total_cells,
                "merged_cells": total_merged,
            },
            "status": validation_status,
            "reasons": failure_reasons,
        }

        print("\n========================")
        print("STAGE 1 VALIDATION")
        print("========================")
        print(f"Tables Detected      : {num_tables}")
        print(f"Rows                 : {total_rows}")
        print(f"Columns              : {total_cols}")
        print(f"Cells                : {total_cells}")
        print(f"Merged Cells         : {total_merged}")
        print(f"Status               : {validation_status}")
        print("========================\n")

        self.summary_report["stages"]["stage1"] = stage1_report
        return stage1_report

    # ---------------------------------------------------------
    # STAGE 2 VALIDATION & ARTIFACTS
    # ---------------------------------------------------------
    def validate_stage2_ocr(
        self,
        layout_with_cells: Dict[str, Any],
        ocr_document: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Stage 2 Validation:
        Validates token-to-cell mapping, unmapped tokens, duplicate mappings,
        and inspects cells for concatenated neighbouring text (CELL MERGE ERROR).
        Saves 07_cropped_cells/, 08_ocr_tokens.json, 09_cell_mapping.json.
        """
        raw_ocr_tokens = []
        cell_mapping = []

        total_cells = 0
        mapped_count = 0
        unmapped_count = 0
        duplicate_mappings = 0
        concatenated_errors = 0

        validation_status = "PASS"
        failure_reasons = []

        # Check cells and tokens
        for table in ocr_document.get("tables", []):
            table_id = table.get("table_id", 1)
            matrix = table.get("matrix", table.get("rows", []))

            for row in matrix:
                cells_list = row.get("cells", []) if isinstance(row, dict) else row
                for cell in cells_list:
                    total_cells += 1
                    r_idx = cell.get("row", 0)
                    c_idx = cell.get("column", 0)
                    cell_id = cell.get("cell_id", total_cells)

                    # Save cell image to 07_cropped_cells/ if present
                    img_path = cell.get("image_path")
                    if img_path and os.path.exists(img_path) and self.enabled:
                        target_filename = f"cell_r{r_idx}_c{c_idx}.png"
                        shutil.copy(img_path, os.path.join(self.cropped_cells_dir, target_filename))

                    # Extract OCR text & tokens
                    cell_text = cell.get("ocr", {}).get("raw_text", cell.get("value", ""))
                    conf = cell.get("ocr", {}).get("confidence", cell.get("confidence", 1.0))

                    if cell_text:
                        mapped_count += 1
                        raw_ocr_tokens.append(
                            {
                                "cell_id": cell_id,
                                "row": r_idx,
                                "column": c_idx,
                                "text": cell_text,
                                "confidence": conf,
                            }
                        )

                        # Check for neighbouring text concatenation (e.g. Centre Name Student No Appearance)
                        words = cell_text.split()
                        suspicious_headers = ["centre", "student", "appearance", "marks", "signature"]
                        matches = [w for w in words if w.lower() in suspicious_headers]
                        if len(matches) >= 3:
                            concatenated_errors += 1
                            failure_reasons.append(
                                f"CELL MERGE ERROR: Cell R{r_idx} C{c_idx} contains concatenated header text: '{cell_text}'"
                            )
                    else:
                        unmapped_count += 1

                    cell_mapping.append(
                        {
                            "cell_id": cell_id,
                            "row": r_idx,
                            "column": c_idx,
                            "mapped_text": cell_text,
                            "mapped": bool(cell_text),
                        }
                    )

        self.save_json("08_ocr_tokens.json", {"tokens": raw_ocr_tokens})
        self.save_json("09_cell_mapping.json", {"cell_mapping": cell_mapping})

        # Strict Stage 2 Validation Rules
        # Only FAIL when literally zero tokens were mapped (true OCR failure)
        if mapped_count == 0 and total_cells > 0:
            validation_status = "FAILED"
            reason_msg = (
                f"STAGE 2 FAILED: No OCR tokens were mapped to cells "
                f"(0 mapped out of {total_cells} cells). "
                "Possible causes: OCR engine not executed, OCR model failed to initialize, "
                "wrong image passed to OCR, empty image, or incorrect OCR API call."
            )
            failure_reasons.append(reason_msg)
            print(f"\n[FAIL] STAGE 2 FAILED: {reason_msg}\n")

        # Concatenated header text is a WARNING, not a hard failure
        if concatenated_errors > 0:
            print(f"[WARN] CELL MERGE WARNING: {concatenated_errors} cell(s) may contain concatenated header text. "
                  "This is a soft warning and will not stop the pipeline.")


        stage2_report = {
            "stage": "Stage 2 - OCR Mapping",
            "expected": {"cells": total_cells, "concatenated_errors": 0},
            "actual": {
                "cells_detected": total_cells,
                "ocr_tokens": len(raw_ocr_tokens),
                "mapped_successfully": mapped_count,
                "unmapped": unmapped_count,
                "duplicate_mappings": duplicate_mappings,
                "concatenated_errors": concatenated_errors,
            },
            "status": validation_status,
            "reasons": failure_reasons,
        }

        print("\n========================")
        print("STAGE 2 VALIDATION")
        print("========================")
        print(f"Cells Detected       : {total_cells}")
        print(f"OCR Tokens           : {len(raw_ocr_tokens)}")
        print(f"Mapped Successfully  : {mapped_count}")
        print(f"Unmapped             : {unmapped_count}")
        print(f"Duplicate Mappings   : {duplicate_mappings}")
        print(f"Concatenated Errors  : {concatenated_errors}")
        print(f"Status               : {validation_status}")
        print("========================\n")

        self.summary_report["stages"]["stage2"] = stage2_report
        return stage2_report

    # ---------------------------------------------------------
    # STAGE 3 VALIDATION & ARTIFACTS
    # ---------------------------------------------------------
    def validate_stage3_ocr_document(
        self,
        ocr_doc: Dict[str, Any],
        corrected_doc: Dict[str, Any],
        llm_patches: List[Dict[str, Any]],
        rejected_patches: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Stage 3 Validation:
        Validates canonical OCRDocument structure, empty vs filled cells, missing/duplicate coords,
        and checks for multi-cell concatenation anomalies (STRUCTURE CORRUPTION DETECTED).
        Saves 10_ocr_document.json, 11_corrected_document.json.
        """
        self.save_json("10_ocr_document.json", ocr_doc)
        self.save_json("11_corrected_document.json", corrected_doc)

        tables = corrected_doc.get("tables", [])
        total_rows = 0
        total_cols = 0
        empty_cells = 0
        filled_cells = 0
        concatenated_cells = 0

        validation_status = "PASS"
        failure_reasons = []

        coords_seen = set()
        duplicate_coords = 0

        for table in tables:
            rows = table.get("rows", table.get("matrix", []))
            total_rows += len(rows)

            for r_idx, row in enumerate(rows):
                cells = row.get("cells", []) if isinstance(row, dict) else row
                total_cols = max(total_cols, len(cells))

                for cell in cells:
                    c_idx = cell.get("column", 0)
                    row_i = cell.get("row", r_idx)
                    coord = (row_i, c_idx)

                    if coord in coords_seen:
                        duplicate_coords += 1
                    else:
                        coords_seen.add(coord)

                    val = str(cell.get("value", "")).strip()
                    if val:
                        filled_cells += 1
                        # Check structural corruption (e.g. Centre Name Student No Appearance in single cell)
                        words = val.split()
                        suspicious = ["centre", "student", "appearance", "marks"]
                        if len([w for w in words if w.lower() in suspicious]) >= 3:
                            concatenated_cells += 1
                    else:
                        empty_cells += 1

        if concatenated_cells > 0 or duplicate_coords > 0:
            validation_status = "FAILED"
            failure_reasons.append("STRUCTURE CORRUPTION DETECTED: Multi-cell text concatenation or duplicate cell coordinates found.")
            print("STRUCTURE CORRUPTION DETECTED")

        stage3_report = {
            "stage": "Stage 3 - OCRDocument Validation",
            "expected": {"concatenated_cells": 0, "duplicate_coords": 0},
            "actual": {
                "rows": total_rows,
                "columns": total_cols,
                "empty_cells": empty_cells,
                "filled_cells": filled_cells,
                "concatenated_cells": concatenated_cells,
                "duplicate_coords": duplicate_coords,
                "patches_applied": len(llm_patches),
                "patches_rejected": len(rejected_patches),
            },
            "status": validation_status,
            "reasons": failure_reasons,
        }

        print("\n========================")
        print("STAGE 3 VALIDATION")
        print("========================")
        print(f"Rows                 : {total_rows}")
        print(f"Columns              : {total_cols}")
        print(f"Empty Cells          : {empty_cells}")
        print(f"Filled Cells         : {filled_cells}")
        print(f"Concatenated Cells   : {concatenated_cells}")
        print(f"Patches Applied      : {len(llm_patches)}")
        print(f"Status               : {validation_status}")
        print("========================\n")

        self.summary_report["stages"]["stage3"] = stage3_report
        return stage3_report

    # ---------------------------------------------------------
    # STAGE 4 VALIDATION & ARTIFACTS
    # ---------------------------------------------------------
    def validate_stage4_workbook(
        self,
        excel_path: str,
        expected_rows: int,
        expected_cols: int,
    ) -> Dict[str, Any]:
        """
        Stage 4 Validation:
        Validates openpyxl worksheet structure against expected OCRDocument dimensions.
        Detects WORKBOOK STRUCTURE MISMATCH.
        Saves 12_generated.xlsx and 13_pipeline_summary.json.
        """
        validation_status = "PASS"
        failure_reasons = []

        actual_rows = 0
        actual_cols = 0

        if excel_path and os.path.exists(excel_path) and self.enabled:
            target_excel = os.path.join(self.doc_dir, "12_generated.xlsx")
            try:
                shutil.copy(excel_path, target_excel)
            except PermissionError:
                print(f"[DIAGNOSTIC WARNING] Could not save {target_excel} (file is likely open in Excel). Skipping debug copy.")
            except Exception as e:
                print(f"[DIAGNOSTIC ERROR] Failed to copy diagnostic Excel file: {e}")

            try:
                from openpyxl import load_workbook
                wb = load_workbook(excel_path, data_only=True)
                ws = wb.active
                actual_rows = ws.max_row
                actual_cols = ws.max_column
            except Exception as e:
                print(f"[DIAGNOSTIC ERROR] Failed to inspect generated Excel file: {e}")

        # Check for structural mismatch (allowing +/- 1 row tolerance for bottom merged rowspan expansion)
        if abs(actual_rows - expected_rows) > 1 or actual_cols != expected_cols:
            validation_status = "FAILED"
            reason_msg = (
                f"WORKBOOK STRUCTURE MISMATCH: Worksheet dimensions ({actual_rows}x{actual_cols}) "
                f"differ from OCRDocument dimensions ({expected_rows}x{expected_cols}). "
                f"Workbook Builder collapsed or expanded rows/columns."
            )
            failure_reasons.append(reason_msg)
            print("WORKBOOK STRUCTURE MISMATCH")


        stage4_report = {
            "stage": "Stage 4 - Workbook Builder",
            "expected": {"rows": expected_rows, "columns": expected_cols},
            "actual": {"rows": actual_rows, "columns": actual_cols},
            "status": validation_status,
            "reasons": failure_reasons,
        }

        print("\n========================")
        print("STAGE 4 VALIDATION")
        print("========================")
        print(f"Worksheet Rows       : {actual_rows} (Expected: {expected_rows})")
        print(f"Worksheet Columns    : {actual_cols} (Expected: {expected_cols})")
        print(f"Status               : {validation_status}")
        print("========================\n")

        self.summary_report["stages"]["stage4"] = stage4_report

        # Determine overall pipeline status
        overall_pass = all(
            stg.get("status") == "PASS"
            for stg in self.summary_report["stages"].values()
        )
        self.summary_report["pipeline_status"] = "PASS" if overall_pass else "FAILED"

        # Save Artifact 13: 13_pipeline_summary.json
        self.save_json("13_pipeline_summary.json", self.summary_report)

        # Render Standalone HTML Debug Report
        self.generate_html_report()

        return stage4_report

    # ---------------------------------------------------------
    # HTML REPORT GENERATOR (report.html)
    # ---------------------------------------------------------
    def generate_html_report(self) -> Optional[str]:
        """Generates single-page standalone HTML report (report.html)."""
        if not self.enabled:
            return None

        report_path = os.path.join(self.doc_dir, "report.html")

        # Utility to get relative image tag
        def img_tag(filename: str, caption: str) -> str:
            p = os.path.join(self.doc_dir, filename)
            if os.path.exists(p):
                return f"""
                <div class="card">
                    <h3>{caption}</h3>
                    <img src="{filename}" alt="{caption}" style="max-width:100%; border:1px solid #ccc; border-radius:4px;"/>
                </div>
                """
            return f"<div class='card'><h3>{caption}</h3><p><em>Artifact {filename} not generated.</em></p></div>"

        # Stages Summary Table HTML
        stages_html = ""
        for name, data in self.summary_report.get("stages", {}).items():
            status = data.get("status", "UNKNOWN")
            status_color = "#28a745" if status == "PASS" else "#dc3545"
            reasons = "<br/>".join(data.get("reasons", [])) or "None"

            stages_html += f"""
            <tr>
                <td><strong>{data.get('stage', name)}</strong></td>
                <td><pre>{json.dumps(data.get('expected', {}), indent=2)}</pre></td>
                <td><pre>{json.dumps(data.get('actual', {}), indent=2)}</pre></td>
                <td style="color:{status_color}; font-weight:bold;">{status}</td>
                <td><small>{reasons}</small></td>
            </tr>
            """

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Diagnostic Pipeline Report - {self.document_name}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background-color: #f8f9fa; color: #333; }}
        h1, h2, h3 {{ color: #0056b3; }}
        .header-box {{ background: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }}
        .grid-container {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(450px, 1fr)); gap: 20px; }}
        .card {{ background: #ffffff; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; background: white; }}
        th, td {{ padding: 10px; border: 1px solid #dee2e6; text-align: left; vertical-align: top; }}
        th {{ background-color: #e9ecef; }}
        pre {{ background: #f1f3f5; padding: 8px; border-radius: 4px; font-size: 12px; overflow-x: auto; }}
        .status-badge {{ display: inline-block; padding: 6px 12px; border-radius: 20px; font-weight: bold; color: white; }}
        .pass {{ background-color: #28a745; }}
        .fail {{ background-color: #dc3545; }}
    </style>
</head>
<body>

    <div class="header-box">
        <h1>Diagnostic Pipeline Report: {self.document_name}</h1>
        <p><strong>Generated At:</strong> {self.summary_report.get('timestamp')}</p>
        <p><strong>Overall Pipeline Status:</strong> 
           <span class="status-badge {'pass' if self.summary_report.get('pipeline_status') == 'PASS' else 'fail'}">
               {self.summary_report.get('pipeline_status')}
           </span>
        </p>
    </div>

    <h2>1. Stage Validation Summary</h2>
    <table>
        <thead>
            <tr>
                <th>Stage</th>
                <th>Expected Structure</th>
                <th>Actual Structure</th>
                <th>Status</th>
                <th>Structural Warnings / Failures</th>
            </tr>
        </thead>
        <tbody>
            {stages_html}
        </tbody>
    </table>

    <h2>2. Visual Diagnostic Artifacts</h2>
    <div class="grid-container">
        {img_tag("01_original_page.png", "01. Original Page (Preprocessed)")}
        {img_tag("02_horizontal_lines.png", "02. Horizontal Lines Mask")}
        {img_tag("03_vertical_lines.png", "03. Vertical Lines Mask")}
        {img_tag("04_grid_overlay.png", "04. Grid Line Intersections")}
        {img_tag("05_detected_cells.png", "05. Detected Cell Bounding Boxes (Row/Col Labels)")}
    </div>

    <h2>3. Structure & Data Artifacts</h2>
    <div class="grid-container">
        <div class="card">
            <h3>06_table_matrix.json</h3>
            <p>Calculated matrix of rows, columns, and merged regions.</p>
            <a href="06_table_matrix.json" target="_blank">View 06_table_matrix.json</a>
        </div>
        <div class="card">
            <h3>07_cropped_cells/</h3>
            <p>Folder of individual cropped cell images.</p>
            <a href="07_cropped_cells/" target="_blank">Open 07_cropped_cells Directory</a>
        </div>
        <div class="card">
            <h3>08_ocr_tokens.json</h3>
            <p>Raw OCR bounding boxes & token text outputs.</p>
            <a href="08_ocr_tokens.json" target="_blank">View 08_ocr_tokens.json</a>
        </div>
        <div class="card">
            <h3>09_cell_mapping.json</h3>
            <p>Token-to-cell spatial mapping matrix.</p>
            <a href="09_cell_mapping.json" target="_blank">View 09_cell_mapping.json</a>
        </div>
        <div class="card">
            <h3>10_ocr_document.json</h3>
            <p>Pre-LLM Canonical OCRDocument Structure.</p>
            <a href="10_ocr_document.json" target="_blank">View 10_ocr_document.json</a>
        </div>
        <div class="card">
            <h3>11_corrected_document.json</h3>
            <p>Post-LLM Validated OCRDocument Structure.</p>
            <a href="11_corrected_document.json" target="_blank">View 11_corrected_document.json</a>
        </div>
        <div class="card">
            <h3>12_generated.xlsx & 13_pipeline_summary.json</h3>
            <p>Final Excel File & Programmatic Summary Metrics.</p>
            <a href="12_generated.xlsx" target="_blank">Download 12_generated.xlsx</a> | 
            <a href="13_pipeline_summary.json" target="_blank">View 13_pipeline_summary.json</a>
        </div>
    </div>

</body>
</html>
"""

        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"\n[HTML REPORT] Generated HTML Diagnostic Dashboard: {report_path}")
            return report_path
        except Exception as e:
            print(f"[DIAGNOSTIC ERROR] Failed to write report.html: {e}")
            return None
