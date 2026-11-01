from typing import List, Dict
try:
    from .prompts import (
        SYSTEM_PROMPT, 
        GENERAL_RULES, 
        HEADER_CORRECTION_PROMPT,
        METADATA_PROMPT,
        TABLE_PROMPT,
        COMMENT_PROMPT,
        PATCH_RESPONSE_PROMPT
    )
except ImportError:
    from prompts import (
        SYSTEM_PROMPT, 
        GENERAL_RULES, 
        HEADER_CORRECTION_PROMPT,
        METADATA_PROMPT,
        TABLE_PROMPT,
        COMMENT_PROMPT,
        PATCH_RESPONSE_PROMPT
    )


class PromptBuilder:
    """Dynamically constructs LLM prompts based on task context."""
    
    def __init__(self):
        self.messages: List[Dict[str, str]] = []
        
    def _add_system_message(self, content: str):
        self.messages.append({"role": "system", "content": content})
        
    def _add_user_message(self, content: str):
        self.messages.append({"role": "user", "content": content})
        
    def build_base_context(self) -> 'PromptBuilder':
        """Builds the mandatory base instructions."""
        base_instructions = f"{SYSTEM_PROMPT}\n{GENERAL_RULES}\n{PATCH_RESPONSE_PROMPT}"
        self._add_system_message(base_instructions)
        return self
        
    def build_header_prompt(self, ocr_json: str) -> 'PromptBuilder':
        """Assembles prompt specifically for correcting table headers."""
        self._add_system_message(HEADER_CORRECTION_PROMPT)
        self._add_user_message(f"Here are the headers to review:\n{ocr_json}")
        return self
        
    def build_table_prompt(self, ocr_json: str) -> 'PromptBuilder':
        """Assembles prompt specifically for correcting table bodies/marks."""
        self._add_system_message(TABLE_PROMPT)
        self._add_user_message(f"Here is the table body to review:\n{ocr_json}")
        return self
        
    def get_messages(self) -> List[Dict[str, str]]:
        """Returns the fully constructed message list for the LLM client."""
        return self.messages
