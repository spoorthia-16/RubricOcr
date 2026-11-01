import unittest
from llm.postprocessor import Postprocessor, PatchApplier

class TestPostprocessor(unittest.TestCase):

    def setUp(self):
        self.raw_doc = {
            "tables": [{
                "name": "Table1",
                "rows": [
                    {
                        "index": 0,
                        "cells": [
                            {"row": 0, "column": 0, "value": "Appcarance"},
                            {"row": 0, "column": 1, "value": "Name"}
                        ]
                    }
                ]
            }]
        }

    def test_valid_patch_application(self):
        applier = PatchApplier(self.raw_doc)
        patch = {
            "table_index": 0,
            "row_index": 0,
            "column_index": 0,
            "old_value": "Appcarance",
            "new_value": "Appearance",
            "reason": "Spelling correction"
        }
        success = applier.apply_patch(patch)
        self.assertTrue(success)
        
        corrected_val = applier.corrected_document["tables"][0]["rows"][0]["cells"][0]["value"]
        self.assertEqual(corrected_val, "Appearance")

    def test_invalid_path_rejection(self):
        applier = PatchApplier(self.raw_doc)
        
        # Invalid table index
        bad_patch_1 = {"table_index": 99, "row_index": 0, "column_index": 0, "new_value": "X"}
        self.assertFalse(applier.apply_patch(bad_patch_1))
        
        # Invalid row index
        bad_patch_2 = {"table_index": 0, "row_index": 99, "column_index": 0, "new_value": "X"}
        self.assertFalse(applier.apply_patch(bad_patch_2))
        
        # Invalid column index
        bad_patch_3 = {"table_index": 0, "row_index": 0, "column_index": 99, "new_value": "X"}
        self.assertFalse(applier.apply_patch(bad_patch_3))

    def test_duplicate_patch_handling(self):
        applier = PatchApplier(self.raw_doc)
        patch = {
            "table_index": 0, "row_index": 0, "column_index": 1, 
            "old_value": "Name", "new_value": "Student Name"
        }
        
        # First application succeeds
        self.assertTrue(applier.apply_patch(patch))
        
        # If GPT returns a duplicate patch for the exact same cell, it overwrites safely
        patch_duplicate = {
            "table_index": 0, "row_index": 0, "column_index": 1, 
            "old_value": "Name", "new_value": "Student Name"
        }
        self.assertTrue(applier.apply_patch(patch_duplicate))
        
        corrected_val = applier.corrected_document["tables"][0]["rows"][0]["cells"][1]["value"]
        self.assertEqual(corrected_val, "Student Name")

    def test_conflicting_patches(self):
        applier = PatchApplier(self.raw_doc)
        patch1 = {
            "table_index": 0, "row_index": 0, "column_index": 0, 
            "new_value": "Appearance"
        }
        patch2 = {
            "table_index": 0, "row_index": 0, "column_index": 0, 
            "new_value": "Appearances" # Conflicting patch
        }
        
        self.assertTrue(applier.apply_patch(patch1))
        # The applier blindly applies the second patch because indices match. 
        # This is expected deterministic behavior. The validator will catch logic conflicts.
        self.assertTrue(applier.apply_patch(patch2))
        
        corrected_val = applier.corrected_document["tables"][0]["rows"][0]["cells"][0]["value"]
        self.assertEqual(corrected_val, "Appearances")

    def test_diff_generation(self):
        processor = Postprocessor(self.raw_doc)
        llm_response = {
            "patches": [
                {
                    "table_index": 0, "row_index": 0, "column_index": 0,
                    "old_value": "Appcarance", "new_value": "Appearance",
                    "reason": "Fix"
                }
            ],
            "confidence_in_corrections": 0.95
        }
        
        corrected = processor.apply_llm_response(llm_response)
        
        # Check that original raw document was preserved (deep copy)
        self.assertEqual(self.raw_doc["tables"][0]["rows"][0]["cells"][0]["value"], "Appcarance")
        
        # Check diff report in wrapper
        diff = corrected["diff_report"]
        self.assertEqual(len(diff["changes"]), 1)
        self.assertEqual(diff["changes"][0]["before"], "Appcarance")
        self.assertEqual(diff["changes"][0]["after"], "Appearance")
        
        # Check stats
        self.assertEqual(corrected["llm_statistics"]["patches_applied"], 1)

if __name__ == "__main__":
    unittest.main()
