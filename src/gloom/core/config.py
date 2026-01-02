"""Configuration management for Gloom with XDG Base Directory compliance."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_xdg_config_home() -> Path:
    """Get XDG_CONFIG_HOME or default to ~/.config."""
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def get_xdg_data_home() -> Path:
    """Get XDG_DATA_HOME or default to ~/.local/share."""
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))


def get_xdg_cache_home() -> Path:
    """Get XDG_CACHE_HOME or default to ~/.cache."""
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))


class GcloudPaths(BaseModel):
    """Paths related to gcloud SDK configuration."""

    config_dir: Path = Field(default_factory=lambda: get_xdg_config_home() / "gcloud")
    adc_file: Path = Field(
        default_factory=lambda: get_xdg_config_home()
        / "gcloud"
        / "application_default_credentials.json"
    )
    configurations_dir: Path = Field(
        default_factory=lambda: get_xdg_config_home() / "gcloud" / "configurations"
    )
    active_config_file: Path = Field(
        default_factory=lambda: get_xdg_config_home() / "gcloud" / "active_config"
    )

    model_config = {"frozen": True}


class GloomPaths(BaseModel):
    """Paths for Gloom's own data storage."""

    base_dir: Path = Field(default_factory=lambda: Path.home() / ".gloom")
    cache_dir: Path = Field(default_factory=lambda: Path.home() / ".gloom" / "cache")
    config_file: Path = Field(default_factory=lambda: Path.home() / ".gloom" / "config.toml")
    audit_log: Path = Field(default_factory=lambda: Path.home() / ".gloom" / "audit.log")

    model_config = {"frozen": True}

    def ensure_dirs(self) -> None:
        """Create all required directories with secure permissions."""
        for dir_path in [self.base_dir, self.cache_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
            # Set directory permissions to 0700 (owner only)
            dir_path.chmod(0o700)


class ProjectConfig(BaseModel):
    """Configuration for a cached project/context."""

    name: str
    alias: str | None = None
    project_id: str | None = None
    account: str | None = None
    region: str | None = None
    cached_at: str | None = None  # ISO timestamp
    adc_path: Path | None = None

    model_config = {"frozen": True}

    def display_name(self) -> str:
        """Return alias if set, otherwise name."""
        return self.alias or self.name


class GloomConfig(BaseSettings):
    """Main configuration for Gloom CLI."""

    model_config = SettingsConfigDict(
        env_prefix="GLOOM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Feature flags
    auto_switch_direnv: bool = Field(default=False, description="Enable direnv auto-switching")
    audit_logging: bool = Field(default=True, description="Enable audit logging for switches")
    secure_permissions: bool = Field(default=True, description="Enforce 0600 on cached files")
    backup_before_switch: bool = Field(default=True, description="Backup current ADC before switch")

    # Paths (computed, not from env)
    gcloud: GcloudPaths = Field(default_factory=GcloudPaths)
    gloom: GloomPaths = Field(default_factory=GloomPaths)

    # Cached projects registry
    projects: dict[str, ProjectConfig] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        """Ensure directories exist after initialization."""
        self.gloom.ensure_dirs()

    def get_project_cache_path(self, project_name: str) -> Path:
        """Get the cache directory path for a specific project."""
        return self.gloom.cache_dir / project_name

    def get_project_adc_path(self, project_name: str) -> Path:
        """Get the cached ADC file path for a specific project."""
        return self.get_project_cache_path(project_name) / "adc.json"
