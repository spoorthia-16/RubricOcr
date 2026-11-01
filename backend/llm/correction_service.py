import time
import logging
from typing import Dict, Any, List, Optional

try:
    from .preprocessor import Preprocessor
    from .prompt_builder import PromptBuilder
    from .client import LLMClient
    from .validator import Validator
    from .postprocessor import PatchApplier
    from .models import CorrectionResult
    from .utils import serialize_payload, estimate_tokens
except ImportError:
    from preprocessor import Preprocessor
    from prompt_builder import PromptBuilder
    from client import LLMClient
    from validator import Validator
    from postprocessor import PatchApplier
    from models import CorrectionResult
    from utils import serialize_payload, estimate_tokens

logger = logging.getLogger("LLMClient")


class CorrectionService:
    """
    LLM Execution Engine for the OCR Post-Processing Pipeline.
    
    Linear Workflow:
    OCRDocument -> Preprocessor -> Prompt Builder -> LLM Client -> Validator (4 Levels) -> PatchApplier -> CorrectionResult
    """

    def __init__(self, allow_numeric_corrections: bool = False, model: str = "gpt-4.1"):
        self.client = LLMClient()
        self.validator = Validator(allow_numeric_corrections=allow_numeric_corrections)
        self.model = model

    def correct_document(
        self, raw_document: Dict[str, Any], allow_numeric_corrections: Optional[bool] = None
    ) -> CorrectionResult:
        """
        Executes the linear pipeline and returns a structured CorrectionResult audit object.
        """
        # 1. Preprocessing
        logger.info("PREPROCESS_STARTED")
        preprocessor = Preprocessor(raw_document)
        payload = preprocessor.build_payload()
        payload_json = serialize_payload(payload)
        logger.info("PREPROCESS_COMPLETED")

        # 2. Prompt Building
        builder = PromptBuilder()
        builder.build_base_context().build_table_prompt(payload_json)
        messages = builder.get_messages()
        logger.info("PROMPT_BUILT")

        # 3. LLM API Call (Transport Layer)
        logger.info("REQUEST_SENT")
        llm_response = self.client.chat_with_metadata(messages)
        logger.info("RESPONSE_RECEIVED")

        raw_content = llm_response.get("content", "")
        llm_latency = llm_response.get("latency", 0.0)
        tokens = llm_response.get("tokens", {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0})
        retry_count = llm_response.get("retry_count", 0)
        transport_meta = llm_response.get("transport_meta", {})
        used_model = llm_response.get("model", self.model)

        # Token estimation fallback if usage token count is 0
        if tokens.get("total_tokens", 0) == 0:
            in_tok = estimate_tokens(payload_json)
            out_tok = estimate_tokens(raw_content)
            tokens = {
                "input_tokens": in_tok,
                "output_tokens": out_tok,
                "total_tokens": in_tok + out_tok,
            }

        # 4. Multi-Level Validation Engine
        val_start = time.time()
        applied_patches: List[Dict[str, Any]] = []
        rejected_patches: List[Dict[str, Any]] = []
        validation_report: Dict[str, Any] = {
            "level_1_transport": None,
            "level_2_schema": None,
            "level_3_patch": [],
            "level_4_business": [],
            "status": "passed",
        }

        # Level 1: Transport Validation
        l1_res = self.validator.validate_transport(raw_content, transport_meta)
        validation_report["level_1_transport"] = l1_res

        if l1_res["status"] == "success":
            response_data = l1_res["data"]

            # Level 2: Schema Validation
            l2_res = self.validator.validate_schema(response_data)
            validation_report["level_2_schema"] = l2_res

            if l2_res["status"] == "success":
                candidate_patches = l2_res.get("data", {}).get("patches", [])


                for patch in candidate_patches:
                    # Level 3: Patch Validation (Path, Datatype, Legal Op)
                    l3_res = self.validator.validate_patch(patch, raw_document)
                    validation_report["level_3_patch"].append(l3_res)

                    if l3_res["status"] == "success":
                        target_cell = l3_res.get("target_cell", {})
                        old_value = target_cell.get("value", patch.get("old_value", ""))

                        # Level 4: Business Validation (Typos Allowed, Marks Alterations Restricted)
                        l4_res = self.validator.validate_business_rules(
                            patch, old_value, allow_override=allow_numeric_corrections
                        )
                        validation_report["level_4_business"].append(l4_res)

                        if l4_res["status"] == "success":
                            logger.info(
                                f"PATCH_VALIDATED: Patch for T:{patch.get('table_index')}, R:{patch.get('row_index')}, C:{patch.get('column_index')} - '{old_value}' -> '{patch.get('new_value')}'"
                            )
                            applied_patches.append(patch)
                        else:
                            rejected_patch = dict(patch)
                            rejected_patch["rejection_level"] = "Level 4: Business"
                            rejected_patch["rejection_reason"] = l4_res.get("reason")
                            logger.info(
                                f"PATCH_REJECTED: Level 4 Business Validation Failed - {l4_res.get('reason')}"
                            )
                            rejected_patches.append(rejected_patch)
                    else:
                        rejected_patch = dict(patch)
                        rejected_patch["rejection_level"] = "Level 3: Patch"
                        rejected_patch["rejection_reason"] = l3_res.get("reason")
                        logger.info(
                            f"PATCH_REJECTED: Level 3 Patch Validation Failed - {l3_res.get('reason')}"
                        )
                        rejected_patches.append(rejected_patch)
            else:
                validation_report["status"] = "failed_schema"
                logger.error(f"SCHEMA_VALIDATION_FAILED: {l2_res.get('reason')}")
        else:
            validation_report["status"] = "failed_transport"
            logger.error(f"TRANSPORT_VALIDATION_FAILED: {l1_res.get('reason')}")

        val_duration = round(time.time() - val_start, 4)

        # 5. Patch Application (Postprocessing)
        applier = PatchApplier(raw_document)
        for patch in applied_patches:
            applier.apply_patch(patch)

        corrected_doc = applier.corrected_document
        logger.info("POSTPROCESS_COMPLETED")

        total_patch_count = len(applied_patches) + len(rejected_patches)

        # 6. Audit Result Object Construction
        result = CorrectionResult(
            original_document=raw_document,
            corrected_document=corrected_doc,
            applied_patches=applied_patches,
            rejected_patches=rejected_patches,
            validation_report=validation_report,
            llm_latency=llm_latency,
            tokens=tokens,
            model=used_model,
            retry_count=retry_count,
            patch_count=total_patch_count,
            accepted_patch_count=len(applied_patches),
            rejected_patch_count=len(rejected_patches),
            validation_duration=val_duration,
        )

        return result
