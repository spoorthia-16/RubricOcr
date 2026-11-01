import os
import sys
import time
import json
from typing import Dict, Any, List

# Add parent directory to sys.path so backend modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from llm.correction_service import CorrectionService
from llm.client import BaseTransport, LLMClient
from llm.config import OPENAI_API_KEY


class SampleOCRTransport(BaseTransport):
    """
    Realistic transport handler for end-to-end LLM pipeline testing.
    Provides candidate patches addressing OCR typos (allowed) and mark modifications (rejected by business rules).
    """

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        # Realistic JSON response matching CorrectionResponse schema
        response_payload = {
            "patches": [
                {
                    "table_index": 0,
                    "row_index": 0,
                    "column_index": 0,
                    "old_value": "Cand1date No.",
                    "new_value": "Candidate No.",
                    "reason": "Correct digit 1 to letter i in header",
                },
                {
                    "table_index": 0,
                    "row_index": 0,
                    "column_index": 2,
                    "old_value": "Appcarance",
                    "new_value": "Appearance",
                    "reason": "Fix spelling typo in header",
                },
                {
                    "table_index": 0,
                    "row_index": 0,
                    "column_index": 5,
                    "old_value": "Total Maeks",
                    "new_value": "Total Marks",
                    "reason": "Fix header spelling typo",
                },
                {
                    "table_index": 0,
                    "row_index": 2,
                    "column_index": 1,
                    "old_value": "Bob Jon3s",
                    "new_value": "Bob Jones",
                    "reason": "Fix digit substitution in name",
                },
                {
                    "table_index": 0,
                    "row_index": 2,
                    "column_index": 2,
                    "old_value": "Appcarance OK",
                    "new_value": "Appearance OK",
                    "reason": "Fix typo in assessment comment",
                },
                {
                    "table_index": 0,
                    "row_index": 2,
                    "column_index": 4,
                    "old_value": "Fa1l",
                    "new_value": "Fail",
                    "reason": "Fix digit 1 to letter i in result status",
                },
                {
                    "table_index": 0,
                    "row_index": 3,
                    "column_index": 1,
                    "old_value": "Chaslie Brown",
                    "new_value": "Charlie Brown",
                    "reason": "Fix character substitution in candidate name",
                },
                {
                    "table_index": 0,
                    "row_index": 3,
                    "column_index": 2,
                    "old_value": "Excellant",
                    "new_value": "Excellent",
                    "reason": "Correct spelling in assessment grade",
                },
                {
                    "table_index": 0,
                    "row_index": 4,
                    "column_index": 5,
                    "old_value": "4",
                    "new_value": "74",
                    "reason": "Guess missing digit for total mark",
                },
            ],
            "confidence_in_corrections": 0.96,
        }

        time.sleep(0.5)  # Simulate network latency

        return {
            "choices": [{"message": {"content": json.dumps(response_payload)}}],
            "usage": {
                "prompt_tokens": 1650,
                "completion_tokens": 312,
                "total_tokens": 1962,
            },
        }


def run_pipeline_verification():
    overall_start = time.time()

    # 1. Load Sample OCR JSON
    sample_file = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "debug", "sample_ocr_document.json")
    )
    if not os.path.exists(sample_file):
        print(f"Error: Sample OCR file not found at {sample_file}")
        return

    with open(sample_file, "r", encoding="utf-8") as f:
        raw_document = json.load(f)

    # 2. Instantiate CorrectionService
    service = CorrectionService(allow_numeric_corrections=False, model="gpt-4.1")

    # Use OpenAITransport if valid key set, otherwise use SampleOCRTransport for deterministic validation
    if not OPENAI_API_KEY or OPENAI_API_KEY == "your_openai_api_key_here":
        service.client = LLMClient(transport=SampleOCRTransport())

    # 3. Run Pipeline Execution Engine
    result = service.correct_document(raw_document)

    execution_time = round(time.time() - overall_start, 2)

    # Extract Token Metrics
    in_tok = result.tokens.get("input_tokens", result.tokens.get("prompt_tokens", 0))
    out_tok = result.tokens.get("output_tokens", result.tokens.get("completion_tokens", 0))
    tot_tok = result.tokens.get("total_tokens", in_tok + out_tok)

    val_status = "SUCCESS" if result.validation_report.get("status") == "passed" else "FAILED"

    # 4. Pretty Print Result Summary
    print("\n========== LLM EXECUTION ==========")
    print(f"Model                : {result.model}")
    print(f"Latency              : {result.llm_latency:.2f} sec")
    print(f"Input Tokens         : {in_tok}")
    print(f"Output Tokens        : {out_tok}")
    print(f"Total Tokens         : {tot_tok}")
    print(f"")
    print(f"Applied Patches      : {result.accepted_patch_count}")
    print(f"Rejected Patches     : {result.rejected_patch_count}")
    print(f"")
    print(f"Validation           : {val_status}")
    print(f"")
    print(f"Execution Time       : {execution_time:.2f} sec")
    print("==================================\n")

    # Details of Applied Patches
    print("--- APPLIED PATCHES ---")
    for patch in result.applied_patches:
        print(
            f"  [ACCEPTED] Table {patch.get('table_index')}, Row {patch.get('row_index')}, Col {patch.get('column_index')}: "
            f"'{patch.get('old_value')}' -> '{patch.get('new_value')}' ({patch.get('reason')})"
        )

    # Details of Rejected Patches
    if result.rejected_patches:
        print("\n--- REJECTED PATCHES ---")
        for patch in result.rejected_patches:
            print(
                f"  [REJECTED - {patch.get('rejection_level')}] Table {patch.get('table_index')}, Row {patch.get('row_index')}, Col {patch.get('column_index')}: "
                f"'{patch.get('old_value')}' -> '{patch.get('new_value')}' | Reason: {patch.get('rejection_reason')}"
            )

    # 5. Save output corrected document
    output_file = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "debug", "corrected_sample_ocr_document.json"
        )
    )
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result.corrected_document, f, indent=4)

    print(f"\nCorrected OCR document saved to: {output_file}")


if __name__ == "__main__":
    run_pipeline_verification()
