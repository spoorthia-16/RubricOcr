import unittest
from llm.preprocessor import normalize_text, Preprocessor

class TestPreprocessor(unittest.TestCase):

    def test_whitespace_normalization(self):
        self.assertEqual(normalize_text(" Appearance "), "Appearance")
        self.assertEqual(normalize_text("  Good   \n\n  Job  "), "Good\nJob")
        self.assertEqual(normalize_text("Multiple    spaces"), "Multiple spaces")
        self.assertEqual(normalize_text(""), "")
        self.assertEqual(normalize_text(None), "")

    def test_empty_cell_handling(self):
        raw_doc = {
            "tables": [{
                "name": "Table1",
                "rows": [{
                    "index": 0,
                    "cells": [
                        {"row": 0, "column": 0, "value": "   ", "confidence": 1.0},
                        {"row": 0, "column": 1, "value": "Valid Data", "confidence": 0.9}
                    ]
                }]
            }]
        }
        preprocessor = Preprocessor(raw_doc)
        payload = preprocessor.build_payload()
        
        # Only 1 cell should be in the output payload (the valid one)
        cells = payload["tables"][0]["rows"][0]["cells"]
        self.assertEqual(len(cells), 1)
        self.assertEqual(cells[0]["text"], "Valid Data")

    def test_confidence_annotation_and_stats(self):
        raw_doc = {
            "tables": [{
                "name": "Table1",
                "rows": [{
                    "index": 0,
                    "cells": [
                        {"row": 0, "column": 0, "value": "High", "confidence": 0.99},
                        {"row": 0, "column": 1, "value": "Low", "confidence": 0.50}
                    ]
                }]
            }]
        }
        preprocessor = Preprocessor(raw_doc)
        payload = preprocessor.build_payload()
        
        stats = payload["statistics"]
        self.assertEqual(stats["total_cells"], 2)
        self.assertEqual(stats["low_confidence_cells"], 1)
        self.assertAlmostEqual(stats["average_confidence"], 0.745, places=3)
        
        cells = payload["tables"][0]["rows"][0]["cells"]
        self.assertEqual(cells[0]["confidence"], 0.99)
        self.assertEqual(cells[1]["confidence"], 0.50)

    def test_payload_generation(self):
        raw_doc = {
            "metadata_regions": {"title": "Test Title"},
            "tables": [{
                "name": "T1",
                "rows": [{
                    "index": 5,
                    "cells": [{"row": 5, "column": 3, "value": "CellData", "confidence": 0.8}]
                }]
            }]
        }
        preprocessor = Preprocessor(raw_doc)
        payload = preprocessor.build_payload()
        
        self.assertEqual(payload["metadata"]["title"], "Test Title")
        self.assertEqual(payload["tables"][0]["name"], "T1")
        self.assertEqual(payload["tables"][0]["rows"][0]["row_index"], 5)
        self.assertEqual(payload["tables"][0]["rows"][0]["cells"][0]["column"], 3)

if __name__ == "__main__":
    unittest.main()
