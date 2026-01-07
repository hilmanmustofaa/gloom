"""Tests for CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from gloom.cli import app

runner = CliRunner()


class TestVersionCommand:
    """Tests for version output."""

    def test_version_flag(self) -> None:
        """Test --version flag."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "gloom" in result.stdout
        assert "0.1.0" in result.stdout

    def test_version_short_flag(self) -> None:
        """Test -v flag."""
        result = runner.invoke(app, ["-v"])
        assert result.exit_code == 0


class TestListCommand:
    """Tests for list command."""

    def test_list_empty(self, mock_home: Path, mock_gloom_dir: Path) -> None:
        """Test list with no cached contexts."""
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "No cached contexts" in result.stdout

    def test_list_with_cached_projects(
        self, mock_home: Path, mock_gloom_dir: Path, sample_adc_data: dict[str, Any]
    ) -> None:
        """Test list shows cached projects."""
        # Create cached project
        cache_dir = mock_gloom_dir / "cache" / "my-project"
        cache_dir.mkdir(parents=True)
        (cache_dir / "adc.json").write_text(json.dumps(sample_adc_data))

        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "my-project" in result.stdout


class TestCacheCommands:
    """Tests for cache subcommands."""

    def test_cache_add(
        self, mock_home: Path, mock_gcloud_dir: Path, mock_gloom_dir: Path, sample_adc_file: Path
    ) -> None:
        """Test cache add command."""
        result = runner.invoke(app, ["cache", "add", "new-project", "-s", str(sample_adc_file)])
        assert result.exit_code == 0
        assert "Cached context" in result.stdout
        assert "new-project" in result.stdout

    def test_cache_add_already_exists(
        self, mock_home: Path, mock_gloom_dir: Path, mock_gcloud_dir: Path, sample_adc_file: Path
    ) -> None:
        """Test cache add fails for existing project."""
        # First add
        runner.invoke(app, ["cache", "add", "existing", "-s", str(sample_adc_file)])

        # Second add should fail
        result = runner.invoke(app, ["cache", "add", "existing", "-s", str(sample_adc_file)])
        assert result.exit_code == 1
        assert "already exists" in result.stdout

    def test_cache_remove(
        self, mock_home: Path, mock_gloom_dir: Path, sample_adc_data: dict[str, Any]
    ) -> None:
        """Test cache remove command."""
        # Create cached project
        cache_dir = mock_gloom_dir / "cache" / "to-remove"
        cache_dir.mkdir(parents=True)
        (cache_dir / "adc.json").write_text(json.dumps(sample_adc_data))

        result = runner.invoke(app, ["cache", "remove", "to-remove", "--force"])
        assert result.exit_code == 0
        assert "Removed context" in result.stdout


class TestSwitchCommand:
    """Tests for switch command."""

    def test_switch_success(
        self,
        mock_home: Path,
        mock_gloom_dir: Path,
        mock_gcloud_dir: Path,
        sample_adc_data: dict[str, Any],
    ) -> None:
        """Test switch to cached context."""
        # Create cached project
        cache_dir = mock_gloom_dir / "cache" / "switch-test"
        cache_dir.mkdir(parents=True)
        (cache_dir / "adc.json").write_text(json.dumps(sample_adc_data))

        result = runner.invoke(app, ["switch", "switch-test"])
        assert result.exit_code == 0
        assert "Switched to context" in result.stdout

    def test_switch_not_found(self, mock_home: Path, mock_gloom_dir: Path) -> None:
        """Test switch to non-existent context."""
        result = runner.invoke(app, ["switch", "nonexistent"])
        assert result.exit_code == 1
        assert "not found" in result.stdout


class TestCurrentCommand:
    """Tests for current command."""

    def test_current_no_adc(
        self, mock_home: Path, mock_gcloud_dir: Path, mock_gloom_dir: Path
    ) -> None:
        """Test current with no ADC configured."""
        result = runner.invoke(app, ["current"])
        assert result.exit_code == 1
        assert "No ADC configured" in result.stdout

    def test_current_quiet_no_context(
        self, mock_home: Path, mock_gcloud_dir: Path, mock_gloom_dir: Path
    ) -> None:
        """Test current --quiet with no context."""
        result = runner.invoke(app, ["current", "--quiet"])
        assert result.exit_code == 1
