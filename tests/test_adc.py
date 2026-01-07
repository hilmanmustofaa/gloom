"""Tests for ADC management."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest  # type: ignore

from gloom.core.adc import ADCManager, ADCNotFoundError, ADCValidationError
from gloom.core.config import GloomConfig


class TestADCValidation:
    """Tests for ADC file validation."""

    def test_validate_valid_authorized_user(
        self, mock_gcloud_dir: Path, sample_adc_data: dict[str, Any]
    ) -> None:
        """Test validating a valid authorized_user ADC."""
        adc_file = mock_gcloud_dir / "test_adc.json"
        adc_file.write_text(json.dumps(sample_adc_data))

        config = GloomConfig()
        mgr = ADCManager(config)

        info = mgr.validate_adc_file(adc_file)

        assert info.credential_type == "authorized_user"
        assert info.account == "test@example.com"
        assert info.quota_project_id == "test-project-123"

    def test_validate_valid_service_account(
        self, mock_gcloud_dir: Path, sample_service_account_data: dict[str, Any]
    ) -> None:
        """Test validating a valid service_account ADC."""
        adc_file = mock_gcloud_dir / "test_sa.json"
        adc_file.write_text(json.dumps(sample_service_account_data))

        config = GloomConfig()
        mgr = ADCManager(config)

        info = mgr.validate_adc_file(adc_file)

        assert info.credential_type == "service_account"
        assert info.project_id == "test-project-456"
        assert "test-sa@" in (info.account or "")

    def test_validate_missing_file(self, temp_dir: Path) -> None:
        """Test validation fails for missing file."""
        config = GloomConfig()
        mgr = ADCManager(config)

        with pytest.raises(ADCNotFoundError):
            mgr.validate_adc_file(temp_dir / "nonexistent.json")

    def test_validate_invalid_json(self, temp_dir: Path) -> None:
        """Test validation fails for invalid JSON."""
        adc_file = temp_dir / "invalid.json"
        adc_file.write_text("not valid json {")

        config = GloomConfig()
        mgr = ADCManager(config)

        with pytest.raises(ADCValidationError, match="Invalid JSON"):
            mgr.validate_adc_file(adc_file)

    def test_validate_missing_type(self, temp_dir: Path) -> None:
        """Test validation fails for missing type field."""
        adc_file = temp_dir / "no_type.json"
        adc_file.write_text(json.dumps({"client_id": "test"}))

        config = GloomConfig()
        mgr = ADCManager(config)

        with pytest.raises(ADCValidationError, match="Missing required fields"):
            mgr.validate_adc_file(adc_file)

    def test_validate_invalid_type(self, temp_dir: Path) -> None:
        """Test validation fails for invalid credential type."""
        adc_file = temp_dir / "bad_type.json"
        adc_file.write_text(json.dumps({"type": "invalid_type"}))

        config = GloomConfig()
        mgr = ADCManager(config)

        with pytest.raises(ADCValidationError, match="Invalid credential type"):
            mgr.validate_adc_file(adc_file)


class TestADCCaching:
    """Tests for ADC caching operations."""

    def test_cache_adc(self, mock_home: Path, sample_adc_file: Path, mock_gloom_dir: Path) -> None:
        """Test caching an ADC file."""
        config = GloomConfig()
        mgr = ADCManager(config)

        project = mgr.cache_adc("test-project", source_path=sample_adc_file)

        assert project.name == "test-project"
        assert project.account == "test@example.com"

        # Verify cache file exists with correct permissions
        cached_file = mock_gloom_dir / "cache" / "test-project" / "adc.json"
        assert cached_file.exists()
        assert (cached_file.stat().st_mode & 0o777) == 0o600

    def test_cache_adc_already_exists(
        self, mock_home: Path, sample_adc_file: Path, mock_gloom_dir: Path
    ) -> None:
        """Test caching fails if project already cached."""
        config = GloomConfig()
        mgr = ADCManager(config)

        mgr.cache_adc("test-project", source_path=sample_adc_file)

        with pytest.raises(FileExistsError):
            mgr.cache_adc("test-project", source_path=sample_adc_file)

    def test_cache_adc_force_overwrite(
        self, mock_home: Path, sample_adc_file: Path, mock_gloom_dir: Path
    ) -> None:
        """Test force overwrite of cached project."""
        config = GloomConfig()
        mgr = ADCManager(config)

        mgr.cache_adc("test-project", source_path=sample_adc_file)

        # Should succeed with force=True
        project = mgr.cache_adc("test-project", source_path=sample_adc_file, force=True)
        assert project.name == "test-project"


class TestADCSwitching:
    """Tests for ADC context switching."""

    def test_switch_context(
        self, mock_home: Path, sample_adc_file: Path, mock_gloom_dir: Path, mock_gcloud_dir: Path
    ) -> None:
        """Test switching ADC context."""
        config = GloomConfig()
        mgr = ADCManager(config)

        # Cache the ADC
        mgr.cache_adc("test-project", source_path=sample_adc_file)

        # Switch to it
        project = mgr.switch_context("test-project")

        assert project.name == "test-project"

        # Verify symlink was created
        adc_path = mock_gcloud_dir / "application_default_credentials.json"
        assert adc_path.is_symlink()

    def test_switch_context_not_cached(self, mock_home: Path) -> None:
        """Test switching to non-existent context fails."""
        config = GloomConfig()
        mgr = ADCManager(config)

        with pytest.raises(ADCNotFoundError):
            mgr.switch_context("nonexistent-project")

    def test_list_cached_projects(
        self,
        mock_home: Path,
        mock_gcloud_dir: Path,
        mock_gloom_dir: Path,
        sample_adc_data: dict[str, Any],
    ) -> None:
        """Test listing cached projects."""
        config = GloomConfig()
        mgr = ADCManager(config)

        # Create multiple cached projects
        for name in ["project-a", "project-b", "project-c"]:
            cache_dir = mock_gloom_dir / "cache" / name
            cache_dir.mkdir(parents=True)
            (cache_dir / "adc.json").write_text(json.dumps(sample_adc_data))

        projects = mgr.list_cached_projects()

        assert len(projects) == 3
        names = {p.name for p in projects}
        assert names == {"project-a", "project-b", "project-c"}

    def test_remove_cached_project(
        self, mock_home: Path, sample_adc_file: Path, mock_gloom_dir: Path
    ) -> None:
        """Test removing a cached project."""
        config = GloomConfig()
        mgr = ADCManager(config)

        mgr.cache_adc("test-project", source_path=sample_adc_file)

        result = mgr.remove_cached_project("test-project")

        assert result is True
        assert not (mock_gloom_dir / "cache" / "test-project").exists()

    def test_remove_nonexistent_project(self, mock_home: Path) -> None:
        """Test removing non-existent project returns False."""
        config = GloomConfig()
        mgr = ADCManager(config)

        result = mgr.remove_cached_project("nonexistent")
        assert result is False
