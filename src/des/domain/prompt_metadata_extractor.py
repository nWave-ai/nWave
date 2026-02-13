"""Prompt metadata extraction for audit logging.

Extracts structured metadata (feature_name, step_id, agent_name) from
Task prompts using DES marker patterns and regex.
"""

import os
import re


class PromptMetadataExtractor:
    """Extracts metadata from Task prompts for audit logging."""

    def extract_feature_name(self, prompt: str) -> str | None:
        """Extract feature_name from DES-PROJECT-ID marker.

        Args:
            prompt: Full prompt text

        Returns:
            Feature name string, or None if not found
        """
        project_match = re.search(r"<!-- DES-PROJECT-ID:\s*(.*?)\s*-->", prompt)
        return project_match.group(1) if project_match else None

    def extract_step_id(self, prompt: str) -> str | None:
        """Extract step_id from DES-STEP-ID or DES-STEP-FILE marker.

        Args:
            prompt: Full prompt text

        Returns:
            Step ID string, or None if not found
        """
        step_id_match = re.search(r"<!-- DES-STEP-ID:\s*(.*?)\s*-->", prompt)
        if step_id_match:
            return step_id_match.group(1)

        # Fallback: extract from DES-STEP-FILE marker for backward compatibility
        step_match = re.search(r"<!-- DES-STEP-FILE:\s*(.*?)\s*-->", prompt)
        if step_match:
            step_path = step_match.group(1)
            return os.path.splitext(os.path.basename(step_path))[0]

        return None

    def extract_agent_name(self, prompt: str) -> str | None:
        """Extract agent name from @agent-name pattern in prompt.

        Args:
            prompt: Full prompt text

        Returns:
            Agent name string, or None if not found
        """
        agent_match = re.search(r"@([\w-]+)\s+agent", prompt)
        return agent_match.group(1) if agent_match else None
