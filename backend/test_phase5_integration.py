import os
import sys
import unittest
import json

# Add backend to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

import config
from llm.correction_service import CorrectionService
from llm.models import CorrectionResult
from services.document_serializer import serialize_document
from services.workbook_builder import build_workbook
from services.worksheet_populator import populate_workbook
from services.excel_writer import write_excel


class TestPhase5OCRIntegration(unittest.TestCase):

    def setUp(self):
        sample_path = os.path.join(os.path.dirname(__file__), "debug", "sample_ocr_document.json")
        with open(sample_path, "r", encoding="utf-8") as f:
            self.raw_ocr_doc = json.load(f)

    def test_llm_mode_enabled_handoff_to_excel(self):
        # 1. OCR -> LLM Correction Engine
        engine = CorrectionService(allow_numeric_corrections=False)
        result = engine.correct_document(self.raw_ocr_doc)

        self.assertIsInstance(result, CorrectionResult)
        corrected_doc = result.corrected_document

        # 2. Check structure compatibility: Document has exact same keys & schema
        self.assertIn("tables", corrected_doc)
        self.assertEqual(len(corrected_doc["tables"]), len(self.raw_ocr_doc["tables"]))

        # 3. Handoff to Workbook Builder (Serializer -> Build Workbook -> Populate -> Export)
        # Construct matrix format compatible with finalizer/serializer
        table = corrected_doc["tables"][0]
        matrix = []
        for r in table["rows"]:
            row_cells = []
            for c in r["cells"]:
                row_cells.append({
                    "row": c.get("row", 0),
                    "column": c.get("column", 0),
                    "final_result": {"text": c.get("value", "")},
                    "rowspan": c.get("rowspan", 1),
                    "colspan": c.get("colspan", 1)
                })
            matrix.append(row_cells)

        final_doc_formatted = {
            "document_status": "READY_FOR_EXPORT",
            "tables": [{"matrix": matrix}]
        }

        serialized = serialize_document(final_doc_formatted)
        wb_bundle = build_workbook(serialized)
        wb_bundle = populate_workbook(wb_bundle, serialized)

        output_path = os.path.join(os.path.dirname(__file__), "exports", "test_phase5_llm_enabled.xlsx")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        export_res = write_excel(wb_bundle, serialized, output_path=output_path)

        self.assertEqual(export_res.get("status"), "SUCCESS")
        self.assertTrue(os.path.exists(export_res.get("file_path")))

    def test_llm_mode_disabled_ocr_only_handoff_to_excel(self):
        # OCR Only mode: raw_ocr_doc passed directly without LLM modification
        raw_doc = self.raw_ocr_doc

        table = raw_doc["tables"][0]
        matrix = []
        for r in table["rows"]:
            row_cells = []
            for c in r["cells"]:
                row_cells.append({
                    "row": c.get("row", 0),
                    "column": c.get("column", 0),
                    "final_result": {"text": c.get("value", "")},
                    "rowspan": c.get("rowspan", 1),
                    "colspan": c.get("colspan", 1)
                })
            matrix.append(row_cells)

        final_doc_formatted = {
            "document_status": "READY_FOR_EXPORT",
            "tables": [{"matrix": matrix}]
        }

        serialized = serialize_document(final_doc_formatted)
        wb_bundle = build_workbook(serialized)
        wb_bundle = populate_workbook(wb_bundle, serialized)

        output_path = os.path.join(os.path.dirname(__file__), "exports", "test_phase5_ocr_only.xlsx")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        export_res = write_excel(wb_bundle, serialized, output_path=output_path)

        self.assertEqual(export_res.get("status"), "SUCCESS")
        self.assertTrue(os.path.exists(export_res.get("file_path")))


if __name__ == "__main__":
    unittest.main()
