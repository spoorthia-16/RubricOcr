import os
import sys
import json
import unittest

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from services.pipeline_orchestrator import process_document
from services.diagnostic_manager import DiagnosticManager


class TestDiagnosticFramework(unittest.TestCase):

    def test_diagnostic_artifact_generation(self):
        test_file = os.path.join(os.path.dirname(__file__), "temp", "processed_test.png")

        # Create a sample test image if not present
        if not os.path.exists(test_file):
            import numpy as np
            import cv2
            img = np.ones((1000, 1200, 3), dtype=np.uint8) * 255
            # Draw a sample grid
            for y in range(100, 900, 100):
                cv2.line(img, (100, y), (1100, y), (0, 0, 0), 2)
            for x in range(100, 1100, 200):
                cv2.line(img, (x, 100), (x, 900), (0, 0, 0), 2)
            os.makedirs(os.path.dirname(test_file), exist_ok=True)
            cv2.imwrite(test_file, img)

        res = process_document(test_file)
        self.assertEqual(res.get("status"), "SUCCESS")

        clean_name = os.path.splitext(os.path.basename(test_file))[0]
        diag_dir = os.path.join(os.path.dirname(__file__), "debug", clean_name)

        expected_artifacts = [
            "01_original_page.png",
            "02_horizontal_lines.png",
            "03_vertical_lines.png",
            "04_grid_overlay.png",
            "05_detected_cells.png",
            "06_table_matrix.json",
            "07_cropped_cells",
            "08_ocr_tokens.json",
            "09_cell_mapping.json",
            "10_ocr_document.json",
            "11_corrected_document.json",
            "12_generated.xlsx",
            "13_pipeline_summary.json",
            "report.html"
        ]

        print(f"\nVerifying diagnostic directory: {diag_dir}")
        for artifact in expected_artifacts:
            path = os.path.join(diag_dir, artifact)
            self.assertTrue(os.path.exists(path), f"Missing diagnostic artifact: {artifact}")
            print(f"  [OK] Artifact verified: {artifact}")

        summary_path = os.path.join(diag_dir, "13_pipeline_summary.json")
        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)

        self.assertIn("stages", summary)
        self.assertIn("stage1", summary["stages"])
        self.assertIn("stage2", summary["stages"])
        self.assertIn("stage3", summary["stages"])
        self.assertIn("stage4", summary["stages"])


if __name__ == "__main__":
    unittest.main()
