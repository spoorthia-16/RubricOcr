import unittest
import json
import logging
from io import StringIO
from typing import Dict, Any, List

from llm.correction_service import CorrectionService
from llm.client import BaseTransport, LLMClient
from llm.models import CorrectionResult


class MockTransport(BaseTransport):
    """Mock transport layer allowing customized LLM response string or simulated exceptions."""

    def __init__(
        self,
        response_content: str = "",
        raise_timeout: bool = False,
        raise_rate_limit: bool = False,
        tokens: Dict[str, int] = None,
    ):
        self.response_content = response_content
        self.raise_timeout = raise_timeout
        self.raise_rate_limit = raise_rate_limit
        self.tokens = tokens or {"prompt_tokens": 120, "completion_tokens": 40, "total_tokens": 160}

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        if self.raise_timeout:
            raise TimeoutError("LLM API timed out after 30 seconds")
        if self.raise_rate_limit:
            raise Exception("429 Too Many Requests: Rate limit exceeded")

        return {
            "choices": [{"message": {"content": self.response_content}}],
            "usage": self.tokens,
        }


class TestLLMExecutionEngine(unittest.TestCase):

    def setUp(self):
        self.raw_doc = {
            "tables": [
                {
                    "name": "Student Marks Table",
                    "rows": [
                        {
                            "index": 0,
                            "cells": [
                                {"row": 0, "column": 0, "value": "Appcarance"},
                                {"row": 0, "column": 1, "value": "Marks"},
                            ],
                        },
                        {
                            "index": 1,
                            "cells": [
                                {"row": 1, "column": 0, "value": "Clean Code"},
                                {"row": 1, "column": 1, "value": "4"},
                            ],
                        },
                    ],
                }
            ]
        }

    def test_full_pipeline_success_and_correction_result(self):
        # LLM returns two patches: header spelling fix (allowed) and marks change (rejected in level 4)
        mock_response = json.dumps(
            {
                "patches": [
                    {
                        "table_index": 0,
                        "row_index": 0,
                        "column_index": 0,
                        "old_value": "Appcarance",
                        "new_value": "Appearance",
                        "reason": "Correct typo",
                    },
                    {
                        "table_index": 0,
                        "row_index": 1,
                        "column_index": 1,
                        "old_value": "4",
                        "new_value": "9",
                        "reason": "Upgrade mark",
                    },
                ],
                "confidence_in_corrections": 0.98,
            }
        )

        service = CorrectionService()
        service.client = LLMClient(transport=MockTransport(response_content=mock_response))

        result = service.correct_document(self.raw_doc)

        # 1. Check object type
        self.assertIsInstance(result, CorrectionResult)

        # 2. Check applied vs rejected patches
        self.assertEqual(len(result.applied_patches), 1)
        self.assertEqual(result.applied_patches[0]["new_value"], "Appearance")

        self.assertEqual(len(result.rejected_patches), 1)
        self.assertEqual(result.rejected_patches[0]["rejection_level"], "Level 4: Business")

        # 3. Check corrected document state
        corrected_header = result.corrected_document["tables"][0]["rows"][0]["cells"][0]["value"]
        self.assertEqual(corrected_header, "Appearance")

        corrected_mark = result.corrected_document["tables"][0]["rows"][1]["cells"][1]["value"]
        self.assertEqual(corrected_mark, "4")  # Unchanged because numeric patch was rejected

        # 4. Check metrics
        self.assertEqual(result.patch_count, 2)
        self.assertEqual(result.accepted_patch_count, 1)
        self.assertEqual(result.rejected_patch_count, 1)
        self.assertEqual(result.tokens["prompt_tokens" if "prompt_tokens" in result.tokens else "input_tokens"], 120)
        self.assertEqual(result.model, "gpt-4.1")

    def test_allow_numeric_corrections_override(self):
        mock_response = json.dumps(
            {
                "patches": [
                    {
                        "table_index": 0,
                        "row_index": 1,
                        "column_index": 1,
                        "old_value": "4",
                        "new_value": "9",
                        "reason": "Fix OCR digit recognition",
                    }
                ],
                "confidence_in_corrections": 0.95,
            }
        )

        # Explicitly allow numeric corrections
        service = CorrectionService(allow_numeric_corrections=True)
        service.client = LLMClient(transport=MockTransport(response_content=mock_response))

        result = service.correct_document(self.raw_doc)

        self.assertEqual(len(result.applied_patches), 1)
        self.assertEqual(result.applied_patches[0]["new_value"], "9")
        self.assertEqual(
            result.corrected_document["tables"][0]["rows"][1]["cells"][1]["value"], "9"
        )

    def test_level_1_transport_validation_empty_and_json_error(self):
        # Empty response
        service_empty = CorrectionService()
        service_empty.client = LLMClient(transport=MockTransport(response_content=""))
        res_empty = service_empty.correct_document(self.raw_doc)

        self.assertEqual(res_empty.validation_report["status"], "failed_transport")
        self.assertEqual(res_empty.accepted_patch_count, 0)

        # Invalid JSON
        service_bad_json = CorrectionService()
        service_bad_json.client = LLMClient(transport=MockTransport(response_content="INVALID JSON {{"))
        res_bad_json = service_bad_json.correct_document(self.raw_doc)

        self.assertEqual(res_bad_json.validation_report["status"], "failed_transport")
        self.assertIn("JSON parse error", res_bad_json.validation_report["level_1_transport"]["reason"])

    def test_level_2_schema_validation_error(self):
        # JSON does not match schema (missing 'patches')
        bad_schema_json = json.dumps({"wrong_key": "data"})
        service = CorrectionService()
        service.client = LLMClient(transport=MockTransport(response_content=bad_schema_json))

        result = service.correct_document(self.raw_doc)

        self.assertEqual(result.validation_report["status"], "failed_schema")
        self.assertEqual(result.validation_report["level_2_schema"]["status"], "error")

    def test_level_3_patch_validation_out_of_bounds(self):
        # Patch points to non-existent row index
        invalid_path_json = json.dumps(
            {
                "patches": [
                    {
                        "table_index": 0,
                        "row_index": 999,  # Out of bounds
                        "column_index": 0,
                        "old_value": "X",
                        "new_value": "Y",
                    }
                ]
            }
        )
        service = CorrectionService()
        service.client = LLMClient(transport=MockTransport(response_content=invalid_path_json))

        result = service.correct_document(self.raw_doc)

        self.assertEqual(len(result.applied_patches), 0)
        self.assertEqual(len(result.rejected_patches), 1)
        self.assertEqual(result.rejected_patches[0]["rejection_level"], "Level 3: Patch")

    def test_standardized_logging_events(self):
        mock_response = json.dumps(
            {
                "patches": [
                    {
                        "table_index": 0,
                        "row_index": 0,
                        "column_index": 0,
                        "old_value": "Appcarance",
                        "new_value": "Appearance",
                    }
                ]
            }
        )

        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        logger = logging.getLogger("LLMClient")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        try:
            service = CorrectionService()
            service.client = LLMClient(transport=MockTransport(response_content=mock_response))
            service.correct_document(self.raw_doc)

            log_output = log_stream.getvalue()

            required_events = [
                "PREPROCESS_STARTED",
                "PREPROCESS_COMPLETED",
                "PROMPT_BUILT",
                "REQUEST_SENT",
                "RESPONSE_RECEIVED",
                "PATCH_VALIDATED",
                "POSTPROCESS_COMPLETED",
            ]

            for event in required_events:
                self.assertIn(event, log_output)
        finally:
            logger.removeHandler(handler)


if __name__ == "__main__":
    unittest.main()
