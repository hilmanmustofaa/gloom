"""Tests for ecosystem integrations."""

from pathlib import Path
from unittest.mock import patch

import pytest  # type: ignore

from gloom.core.config import GloomConfig, ProjectConfig
from gloom.integrations import DirenvHook, PromptManager


@pytest.fixture  # type: ignore
def mock_config(tmp_path: Path) -> GloomConfig:
    """Create a mock configuration."""
    conf = GloomConfig()
    # Override paths to use tmp_path
    object.__setattr__(conf.gloom, "base_dir", tmp_path / ".gloom")
    object.__setattr__(conf.gloom, "cache_dir", tmp_path / ".gloom" / "cache")
    conf.gloom.ensure_dirs()
    return conf


class TestDirenvHook:
    def test_generate_hook_miss(self, mock_config: GloomConfig) -> None:
        """Test hook generation when project not found."""
        hook = DirenvHook(mock_config)
        output = hook.generate_hook("nonexistent")
        assert "not found" in output

    def test_generate_hook_success(self, mock_config: GloomConfig) -> None:
        """Test successful hook generation."""
        # Create a mock cached project
        proj_dir = mock_config.gloom.cache_dir / "testproj"
        proj_dir.mkdir()
        adc_path = proj_dir / "adc.json"
        adc_path.touch()

        # Inject into config
        proj = ProjectConfig(name="testproj", project_id="my-project-id", adc_path=adc_path)
        mock_config.projects["testproj"] = proj

        # Test
        hook = DirenvHook(mock_config)

        with patch("gloom.core.adc.ADCManager.list_cached_projects", return_value=[proj]):
            output = hook.generate_hook("testproj")

        assert 'export CLOUDSDK_CORE_PROJECT="my-project-id"' in output
        assert f'export GOOGLE_APPLICATION_CREDENTIALS="{adc_path}"' in output
        assert 'export GLOOM_ACTIVE_CONTEXT="testproj"' in output

    def test_detect_project(self, mock_config: GloomConfig, tmp_path: Path) -> None:
        """Test project detection from .gloom file."""
        hook = DirenvHook(mock_config)

        # Test .gloom detection
        # Use a subdirectory for CWD to avoid conflict with .gloom config dir
        cwd = tmp_path / "project"
        cwd.mkdir()

        gloom_file = cwd / ".gloom"
        gloom_file.write_text("detected-project")

        with patch("pathlib.Path.cwd", return_value=cwd):
            proj = hook._detect_project()
            assert proj == "detected-project"


class TestPromptManager:
    def test_get_prompt_empty(self, mock_config: GloomConfig) -> None:
        """Test prompt when no context active."""
        prompt = PromptManager(mock_config)
        with patch("gloom.core.adc.ADCManager.get_current_context", return_value=(None, None)):
            assert prompt.get_prompt_info() == ""

    def test_get_prompt_format(self, mock_config: GloomConfig) -> None:
        """Test prompt formatting."""
        prompt = PromptManager(mock_config)

        # Mock class for adc info
        class MockInfo:
            account = "me@example.com"
            credential_type = "service_account"

        with patch(
            "gloom.core.adc.ADCManager.get_current_context", return_value=("prod", MockInfo())
        ):
            assert prompt.get_prompt_info("({project})") == "(prod)"
            assert prompt.get_prompt_info("[{project}:{account}]") == "[prod:me@example.com]"
