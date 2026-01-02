"""Audit logging for Gloom security events."""

from __future__ import annotations

import getpass
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gloom.utils.logger import console


class AuditLogger:
    """Logs security and access events to a local audit log."""

    def __init__(self, log_path: Path) -> None:
        """Initialize audit logger.

        Args:
            log_path: Path to the audit log file (file will be created).
        """
        self.log_path = log_path
        self._ensure_log_dir()

    def log_event(
        self,
        event_type: str,
        status: str = "success",
        details: dict[str, Any] | None = None,
    ) -> None:
        """Log an audit event.

        Args:
            event_type: Type of event (e.g. 'context_switch', 'cache_add').
            status: Outcome status ('success', 'failure', 'denied').
            details: Optional dictionary of event details.
        """
        if details is None:
            details = {}

        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "status": status,
            "user": getpass.getuser(),
            "details": details,
        }

        try:
            with open(self.log_path, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            # Fallback to console error if logging fails, but don't crash
            # We want audit failures to be visible
            console.print(f"[red]Audit Logging Failed: {e}[/red]")
            logging.error(f"Failed to write audit log: {e}")

    def _ensure_log_dir(self) -> None:
        """Ensure log directory exists and has secure permissions."""
        if not self.log_path.parent.exists():
            self.log_path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
