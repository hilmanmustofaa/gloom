"""Credential validation for Gloom."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ValidationIssue:
    """Represents a credential validation issue."""

    field: str
    message: str
    severity: str = "error"  # error or warning


class CredentialValidator:
    """Validates ADC credential files."""

    # Required fields per type
    REQUIRED_FIELDS = {
        "service_account": {
            "type",
            "project_id",
            "private_key_id",
            "private_key",
            "client_email",
            "client_id",
            "auth_uri",
            "token_uri",
        },
        "authorized_user": {
            "type",
            "client_id",
            "client_secret",
            "refresh_token",
        },
        "external_account": {
            "type",
            "audience",
            "subject_token_type",
            "token_url",
            "credential_source",
        },
    }

    def validate_file(self, path: Path) -> tuple[bool, list[ValidationIssue]]:
        """Validate a credential file.

        Args:
            path: Path to the JSON file.

        Returns:
            Tuple of (is_valid, list_of_issues).
        """
        issues: list[ValidationIssue] = []

        if not path.exists():
            issues.append(ValidationIssue("file", "File does not exist"))
            return False, issues

        try:
            content = path.read_text()
            data = json.loads(content)
        except json.JSONDecodeError:
            issues.append(ValidationIssue("json", "Invalid JSON format"))
            return False, issues
        except Exception as e:
            issues.append(ValidationIssue("file", f"Error reading file: {e}"))
            return False, issues

        return self.validate_data(data)

    def validate_data(self, data: dict[str, Any]) -> tuple[bool, list[ValidationIssue]]:
        """Validate credential data dictionary."""
        issues: list[ValidationIssue] = []

        # Check type
        creds_type = data.get("type")
        if not creds_type:
            issues.append(ValidationIssue("type", "Missing 'type' field"))
            return False, issues

        if creds_type not in self.REQUIRED_FIELDS:
            issues.append(ValidationIssue("type", f"Unknown credential type: {creds_type}"))
            return False, issues

        # Check required fields
        required = self.REQUIRED_FIELDS[creds_type]
        for field in required:
            if field not in data:
                issues.append(ValidationIssue(field, f"Missing required field: {field}"))
            elif not data[field]:
                issues.append(ValidationIssue(field, f"Field is empty: {field}"))

        # Type-specific checks
        if creds_type == "service_account":
            pk = data.get("private_key", "")
            pk_header = "-----BEGIN " + "PRIVATE KEY"
            if pk and not pk.startswith(pk_header):
                issues.append(ValidationIssue("private_key", "Invalid private key format"))

            email = data.get("client_email", "")
            if email and "@" not in email:
                issues.append(ValidationIssue("client_email", "Invalid email format"))

        return len(issues) == 0, issues
