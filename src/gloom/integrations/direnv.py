"""Direnv integration for Gloom."""

from __future__ import annotations

import os
from pathlib import Path

from gloom.core.adc import ADCManager
from gloom.core.config import GloomConfig


class DirenvHook:
    """Generates direnv configuration for Gloom."""

    def __init__(self, config: GloomConfig) -> None:
        self.config = config
        self.adc_mgr = ADCManager(config)

    def generate_hook(self, project_name: str | None = None) -> str:
        """Generate shell exports for the given project.

        If project_name is None, attempts to detect from .gloom file or GLOOM_PROJECT.
        """
        # 1. Detect project name if not provided
        if not project_name:
            project_name = self._detect_project()

        if not project_name:
            return "# No Gloom project detected."

        # 2. Get cached project details
        try:
            projects = self.adc_mgr.list_cached_projects()
            project = next((p for p in projects if p.name == project_name), None)

            if not project:
                return f"# Gloom project '{project_name}' not found in cache."

            if not project.adc_path or not project.adc_path.exists():
                return f"# Cached credentials for '{project_name}' not found."

            # 3. Generate exports
            # We set CLOUDSDK_CORE_PROJECT (gcloud) and GOOGLE_APPLICATION_CREDENTIALS (libraries)
            exports = [
                f'export CLOUDSDK_CORE_PROJECT="{project.project_id}"',
                f'export GOOGLE_APPLICATION_CREDENTIALS="{project.adc_path}"',
                f'export GLOOM_ACTIVE_CONTEXT="{project.name}"',
            ]
            return "\n".join(exports)

        except Exception as e:
            return f"# Error generating Gloom hook: {e}"

    def _detect_project(self) -> str | None:
        """Detect project name from current directory context."""
        # Check .gloom file
        cwd = Path.cwd()
        gloom_file = cwd / ".gloom"
        if gloom_file.exists():
            return gloom_file.read_text().strip()

        # Check environment variable (set by user manually?)
        return os.environ.get("GLOOM_PROJECT")
