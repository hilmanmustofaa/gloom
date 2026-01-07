"""gcloud SDK configuration integration."""

from __future__ import annotations

import configparser
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from gloom.core.config import GloomConfig


class GcloudError(Exception):
    """Base exception for gcloud operations."""

    pass


class GcloudNotFoundError(GcloudError):
    """Raised when gcloud CLI is not installed or not in PATH."""

    pass


@dataclass(frozen=True)
class GcloudConfiguration:
    """Represents a gcloud named configuration."""

    name: str
    project: str | None = None
    account: str | None = None
    region: str | None = None
    zone: str | None = None
    is_active: bool = False
    properties: dict[str, dict[str, str]] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        """Human-friendly display name."""
        parts = [self.name]
        if self.project:
            parts.append(f"[{self.project}]")
        if self.account:
            parts.append(f"<{self.account}>")
        return " ".join(parts)


class GcloudConfig:
    """Manages gcloud SDK configurations.

    Integrates with gcloud named configurations to provide seamless
    switching between different GCP projects and accounts.
    """

    # Configuration file pattern
    CONFIG_PATTERN = re.compile(r"^config_(.+)$")

    def __init__(self, config: GloomConfig | None = None) -> None:
        """Initialize GcloudConfig.

        Args:
            config: Gloom configuration.
        """
        self.config = config or GloomConfig()

    def is_gcloud_installed(self) -> bool:
        """Check if gcloud CLI is installed and accessible.

        Returns:
            True if gcloud is available.
        """
        try:
            result = subprocess.run(
                ["gcloud", "--version"],  # noqa: S603,S607
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def get_active_configuration(self) -> str | None:
        """Get the name of the currently active gcloud configuration.

        Returns:
            Configuration name or None if not set.
        """
        active_config_file = self.config.gcloud.active_config_file

        if not active_config_file.exists():
            return None

        content = active_config_file.read_text(encoding="utf-8").strip()
        return content if content else None

    def list_configurations(self) -> list[GcloudConfiguration]:
        """List all gcloud named configurations.

        This reads directly from the configurations directory rather than
        running gcloud commands, for better performance.

        Returns:
            List of GcloudConfiguration objects.
        """
        configs_dir = self.config.gcloud.configurations_dir
        configurations: list[GcloudConfiguration] = []

        if not configs_dir.exists():
            return configurations

        active_name = self.get_active_configuration()

        for config_file in configs_dir.iterdir():
            if not config_file.is_file():
                continue

            match = self.CONFIG_PATTERN.match(config_file.name)
            if not match:
                continue

            config_name = match.group(1)

            try:
                gcloud_config = self._parse_config_file(
                    config_file,
                    config_name,
                    is_active=(config_name == active_name),
                )
                configurations.append(gcloud_config)
            except Exception:  # noqa: S110,S112
                # Skip malformed config files
                continue

        return sorted(configurations, key=lambda c: (not c.is_active, c.name))

    def get_configuration(self, name: str) -> GcloudConfiguration | None:
        """Get a specific configuration by name.

        Args:
            name: Configuration name.

        Returns:
            GcloudConfiguration or None if not found.
        """
        config_file = self.config.gcloud.configurations_dir / f"config_{name}"

        if not config_file.exists():
            return None

        active_name = self.get_active_configuration()
        return self._parse_config_file(
            config_file,
            name,
            is_active=(name == active_name),
        )

    def activate_configuration(self, name: str) -> GcloudConfiguration:
        """Activate a gcloud configuration.

        Args:
            name: Configuration name to activate.

        Returns:
            The activated configuration.

        Raises:
            GcloudError: If configuration doesn't exist.
        """
        config = self.get_configuration(name)
        if config is None:
            raise GcloudError(f"Configuration '{name}' not found")

        # Write to active_config file
        active_config_file = self.config.gcloud.active_config_file
        active_config_file.parent.mkdir(parents=True, exist_ok=True)
        active_config_file.write_text(name, encoding="utf-8")

        # Return updated config with is_active=True
        return GcloudConfiguration(
            name=config.name,
            project=config.project,
            account=config.account,
            region=config.region,
            zone=config.zone,
            is_active=True,
            properties=config.properties,
        )

    def create_configuration(
        self,
        name: str,
        *,
        project: str | None = None,
        account: str | None = None,
        region: str | None = None,
        zone: str | None = None,
    ) -> GcloudConfiguration:
        """Create a new gcloud configuration.

        Args:
            name: Configuration name.
            project: GCP project ID.
            account: GCP account email.
            region: Default compute region.
            zone: Default compute zone.

        Returns:
            The created configuration.

        Raises:
            GcloudError: If configuration already exists.
        """
        config_file = self.config.gcloud.configurations_dir / f"config_{name}"

        if config_file.exists():
            raise GcloudError(f"Configuration '{name}' already exists")

        # Create configurations directory if needed
        config_file.parent.mkdir(parents=True, exist_ok=True)

        # Build config content
        config = configparser.ConfigParser()

        if project or account:
            config["core"] = {}
            if project:
                config["core"]["project"] = project
            if account:
                config["core"]["account"] = account

        if region or zone:
            config["compute"] = {}
            if region:
                config["compute"]["region"] = region
            if zone:
                config["compute"]["zone"] = zone

        # Write config file
        with config_file.open("w", encoding="utf-8") as f:
            config.write(f)

        return self.get_configuration(name) or GcloudConfiguration(name=name)

    def _parse_config_file(
        self,
        config_file: Path,
        name: str,
        *,
        is_active: bool = False,
    ) -> GcloudConfiguration:
        """Parse a gcloud configuration file.

        Args:
            config_file: Path to the config file.
            name: Configuration name.
            is_active: Whether this is the active configuration.

        Returns:
            Parsed GcloudConfiguration.
        """
        parser = configparser.ConfigParser()
        parser.read(config_file, encoding="utf-8")

        # Extract common properties
        project = parser.get("core", "project", fallback=None)
        account = parser.get("core", "account", fallback=None)
        region = parser.get("compute", "region", fallback=None)
        zone = parser.get("compute", "zone", fallback=None)

        # Store all properties
        properties: dict[str, dict[str, str]] = {}
        for section in parser.sections():
            properties[section] = dict(parser.items(section))

        return GcloudConfiguration(
            name=name,
            project=project,
            account=account,
            region=region,
            zone=zone,
            is_active=is_active,
            properties=properties,
        )
