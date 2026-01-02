"""Prompt integration for Gloom."""

from __future__ import annotations

from gloom.core.adc import ADCManager
from gloom.core.config import GloomConfig


class PromptManager:
    """Manages prompt output for Gloom status."""

    def __init__(self, config: GloomConfig) -> None:
        self.config = config
        self.adc_mgr = ADCManager(config)

    def get_prompt_info(self, format_str: str = "({project})") -> str:
        """Get formatted prompt string.

        Args:
            format_str: Format string with placeholders {project}, {account}, {type}.
        """
        current_name, info = self.adc_mgr.get_current_context()

        if not current_name:
            if not info:
                return ""
            # Not a managed context, but ADC exists
            # We might show "system" or empty depending on preference.
            # For now return empty to avoid clutter if not using Gloom.
            return ""

        if not info:
            return format_str  # Should be covered by get_current_context behavior but safe guard

        replacements = {
            "project": current_name,
            "account": info.account or "unknown",
            "type": info.credential_type or "",
        }

        try:
            return format_str.format(**replacements)
        except KeyError:
            return format_str  # Return raw if format fails
