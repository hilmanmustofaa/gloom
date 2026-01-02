"""Tests for Gloom security features."""

from pathlib import Path

import pytest  # type: ignore

from gloom.security import AuditLogger, CredentialValidator, PermissionEnforcer


@pytest.fixture  # type: ignore
def mock_audit_log(tmp_path: Path) -> Path:
    """Create a temporary audit log path."""
    return tmp_path / "audit.log"


class TestPermissionEnforcer:
    def test_check_permissions(self, tmp_path: Path) -> None:
        """Test detecting insecure permissions."""
        # Create insecure directory
        insecure_dir = tmp_path / "insecure"
        insecure_dir.mkdir(mode=0o777)

        # Create insecure file
        insecure_file = insecure_dir / "file.txt"
        insecure_file.touch(mode=0o666)

        enforcer = PermissionEnforcer(insecure_dir)
        issues = enforcer.check()

        assert len(issues) >= 2
        assert any(i.path == insecure_dir and i.is_dir for i in issues)
        assert any(i.path == insecure_file and not i.is_dir for i in issues)

    def test_fix_permissions(self, tmp_path: Path) -> None:
        """Test fixing permissions."""
        base_dir = tmp_path / "test_fix"
        base_dir.mkdir(mode=0o777)
        file_path = base_dir / "secret.json"
        file_path.touch(mode=0o666)

        enforcer = PermissionEnforcer(base_dir)

        # Verify needed fix
        issues = enforcer.check()
        assert len(issues) > 0

        # Fix
        fixed = enforcer.fix(issues)
        assert fixed == len(issues)

        # Verify fixed
        assert (base_dir.stat().st_mode & 0o777) == 0o700
        assert (file_path.stat().st_mode & 0o777) == 0o600

        # Run check again, should be empty
        assert len(enforcer.check()) == 0


class TestCredentialValidator:
    def test_validate_service_account(self, tmp_path: Path) -> None:
        """Test validation of valid service account."""
        valid_json = """
        {
            "type": "service_account",
            "project_id": "test-project",
            "private_key_id": "123",
            "private_key": "-----BEGIN " + "PRIVATE KEY-----...",
            "client_email": "sa@test-project.iam.gserviceaccount.com",
            "client_id": "111",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
        """
        path = tmp_path / "valid.json"
        path.write_text(valid_json)

        validator = CredentialValidator()
        is_valid, issues = validator.validate_file(path)

        assert is_valid
        assert len(issues) == 0

    def test_validate_invalid_json(self, tmp_path: Path) -> None:
        """Test validation of invalid JSON."""
        path = tmp_path / "invalid.json"
        path.write_text("{ broken json")

        validator = CredentialValidator()
        is_valid, issues = validator.validate_file(path)

        assert not is_valid
        assert any(i.field == "json" for i in issues)

    def test_validate_missing_fields(self, tmp_path: Path) -> None:
        """Test validation with missing fields."""
        path = tmp_path / "missing.json"
        path.write_text('{"type": "service_account"}')

        validator = CredentialValidator()
        is_valid, issues = validator.validate_file(path)

        assert not is_valid
        assert any("missing required field" in i.message.lower() for i in issues)


class TestAuditLogger:
    def test_log_event(self, mock_audit_log: Path) -> None:
        """Test logging events."""
        logger = AuditLogger(mock_audit_log)

        logger.log_event("test_event", details={"foo": "bar"})

        assert mock_audit_log.exists()
        content = mock_audit_log.read_text()
        assert '"event_type": "test_event"' in content
        assert '"foo": "bar"' in content
        assert '"user":' in content
        assert '"timestamp":' in content

    def test_audit_dir_permission(self, mock_audit_log: Path) -> None:
        """Verify audit log directory is securely created."""
        # Ensure parent doesn't exist
        log_path = mock_audit_log.parent / "subdir" / "audit.log"

        AuditLogger(log_path)

        parent_mode = log_path.parent.stat().st_mode
        assert (parent_mode & 0o777) == 0o700
