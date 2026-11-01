"""
Few-shot examples to guide GPT towards consistent output structures and 
prevent hallucinations.
"""

FEW_SHOT_HEADER_CORRECTION = [
    {
        "role": "user",
        "content": '{"table_index": 0, "row_index": 0, "column_index": 3, "value": "Appcarance"}'
    },
    {
        "role": "assistant",
        "content": '{"patches": [{"table_index": 0, "row_index": 0, "column_index": 3, "old_value": "Appcarance", "new_value": "Appearance", "reason": "Fixed spelling of standard assessment criteria."}], "confidence_in_corrections": 0.99}'
    }
]

FEW_SHOT_MERGED_CELL_CORRECTION = [
    {
        "role": "user",
        "content": '{"table_index": 0, "row_index": 1, "column_index": 1, "value": "Learner_002Learner_003"}'
    },
    {
        "role": "assistant",
        "content": '{"patches": [{"table_index": 0, "row_index": 1, "column_index": 1, "old_value": "Learner_002Learner_003", "new_value": "Learner_002\\nLearner_003", "reason": "Separated incorrectly merged student names using newline."}], "confidence_in_corrections": 0.95}'
    }
]
