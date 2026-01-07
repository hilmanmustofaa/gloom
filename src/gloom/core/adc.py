"""ADC (Application Default Credentials) cache management."""

from __future__ import annotations

import json
import shutil
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from gloom.core.config import GloomConfig, ProjectConfig
from gloom.core.symlink import SymlinkManager, SymlinkStatus

if TYPE_CHECKING:
    pass


class ADCError(Exception):
    """Base exception for ADC operations."""

    pass


class ADCNotFoundError(ADCError):
    """Raised when ADC file is not found."""

    pass


class ADCValidationError(ADCError):
    """Raised when ADC file fails validation."""

    pass


@dataclass(frozen=True)
class ADCInfo:
    """Information extracted from an ADC file."""

    client_id: str | None = None
    client_secret_masked: bool = False
    account: str | None = None
    project_id: str | None = None
    quota_project_id: str | None = None
    credential_type: str | None = None  # authorized_user, service_account, etc.

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> ADCInfo:
        """Create ADCInfo from parsed JSON data."""
        return cls(
            client_id=data.get("client_id"),
            client_secret_masked="client_secret" in data,
            account=data.get("account") or data.get("client_email"),
            project_id=data.get("project_id"),
            quota_project_id=data.get("quota_project_id"),
            credential_type=data.get("type"),
        )


class ADCManager:
    """Manages ADC caching, validation, and symlink-based switching.

    This is the core component that enables fast context switching by:
    1. Caching ADC files per-project in ~/.gloom/cache/<project>/
    2. Using symlinks to point ~/.config/gcloud/application_default_credentials.json
       to the appropriate cached file
    3. Providing atomic switch operations
    """

    # Required fields for a valid ADC file
    REQUIRED_FIELDS = {"type"}
    # Accepted credential types
    VALID_TYPES = {"authorized_user", "service_account", "external_account"}

    def __init__(self, config: GloomConfig | None = None) -> None:
        """Initialize ADCManager.

        Args:
            config: Gloom configuration. If None, uses default config.
        """
        self.config = config or GloomConfig()
        self.symlink_mgr = SymlinkManager(backup_callback=self._backup_file)

    def validate_adc_file(self, path: Path) -> ADCInfo:
        """Validate an ADC file and extract information.

        Args:
            path: Path to the ADC JSON file.

        Returns:
            ADCInfo with extracted credential information.

        Raises:
            ADCNotFoundError: If file doesn't exist.
            ADCValidationError: If file is not valid JSON or missing required fields.
        """
        if not path.exists():
            raise ADCNotFoundError(f"ADC file not found: {path}")

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise ADCValidationError(f"Invalid JSON in ADC file: {e}") from e

        # Check required fields
        missing = self.REQUIRED_FIELDS - set(data.keys())
        if missing:
            raise ADCValidationError(f"Missing required fields: {missing}")

        # Check credential type
        cred_type = data.get("type")
        if cred_type not in self.VALID_TYPES:
            raise ADCValidationError(
                f"Invalid credential type '{cred_type}'. Expected one of: {self.VALID_TYPES}"
            )

        return ADCInfo.from_json(data)

    def cache_adc(
        self,
        project_name: str,
        source_path: Path | None = None,
        *,
        force: bool = False,
    ) -> ProjectConfig:
        """Cache an ADC file for a project.

        Args:
            project_name: Name/alias for this cached context.
            source_path: Path to ADC file to cache. If None, uses current active ADC.
            force: Overwrite existing cached project if True.

        Returns:
            ProjectConfig for the cached project.

        Raises:
            ADCError: If caching fails.
            FileExistsError: If project already cached and force=False.
        """
        # Determine source
        if source_path is None:
            source_path = self.config.gcloud.adc_file

        # Validate source
        adc_info = self.validate_adc_file(source_path)

        # Check if already cached
        cache_dir = self.config.get_project_cache_path(project_name)
        cached_adc = self.config.get_project_adc_path(project_name)

        if cached_adc.exists() and not force:
            raise FileExistsError(
                f"Project '{project_name}' already cached at {cache_dir}. "
                "Use force=True to overwrite."
            )

        # Create cache directory
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_dir.chmod(0o700)

        # Copy ADC file to cache with secure permissions
        shutil.copy2(source_path, cached_adc)
        cached_adc.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600

        # Create project config
        project_config = ProjectConfig(
            name=project_name,
            project_id=adc_info.project_id or adc_info.quota_project_id,
            account=adc_info.account,
            cached_at=datetime.now(timezone.utc).isoformat(),
            adc_path=cached_adc,
        )

        return project_config

    def switch_context(self, project_name: str) -> ProjectConfig:
        """Switch ADC context to a cached project.

        This is the main operation - it updates the symlink at
        ~/.config/gcloud/application_default_credentials.json to point
        to the cached ADC file for the specified project.

        Args:
            project_name: Name of the cached project to switch to.

        Returns:
            ProjectConfig of the activated project.

        Raises:
            ADCNotFoundError: If project is not cached.
        """
        cached_adc = self.config.get_project_adc_path(project_name)

        if not cached_adc.exists():
            raise ADCNotFoundError(
                f"Project '{project_name}' not found in cache. "
                f"Use 'gloom cache add {project_name}' first."
            )

        # Validate cached ADC is still valid
        adc_info = self.validate_adc_file(cached_adc)

        # Switch symlink atomically
        self.symlink_mgr.switch_symlink(
            new_source=cached_adc,
            target=self.config.gcloud.adc_file,
        )

        return ProjectConfig(
            name=project_name,
            project_id=adc_info.project_id or adc_info.quota_project_id,
            account=adc_info.account,
            adc_path=cached_adc,
        )

    def get_current_context(self) -> tuple[str | None, ADCInfo | None]:
        """Get the currently active ADC context.

        Returns:
            Tuple of (project_name, adc_info) if symlink points to cached project,
            otherwise (None, adc_info) if ADC exists but isn't a gloom symlink.
        """
        adc_path = self.config.gcloud.adc_file
        info = self.symlink_mgr.get_info(adc_path)

        # No ADC file
        if info.status == SymlinkStatus.NOT_EXISTS:
            return (None, None)

        # ADC exists but is not a symlink (not managed by gloom)
        if info.status == SymlinkStatus.NOT_SYMLINK:
            try:
                adc_info = self.validate_adc_file(adc_path)
                return (None, adc_info)
            except ADCError:
                return (None, None)

        # Broken symlink
        if info.status == SymlinkStatus.BROKEN:
            return (None, None)

        # Valid symlink - check if it points to our cache
        if info.target is not None:
            target = info.target
            cache_dir = self.config.gloom.cache_dir

            # Check if target is in our cache directory
            try:
                relative = target.relative_to(cache_dir)
                project_name = relative.parts[0] if relative.parts else None

                if project_name:
                    adc_info = self.validate_adc_file(target)
                    return (project_name, adc_info)
            except ValueError:
                # Target is not in cache dir
                pass

            # Symlink exists but points outside our cache
            try:
                adc_info = self.validate_adc_file(target)
                return (None, adc_info)
            except ADCError:
                return (None, None)

        return (None, None)

    def list_cached_projects(self) -> list[ProjectConfig]:
        """List all cached projects.

        Returns:
            List of ProjectConfig for each cached project.
        """
        cache_dir = self.config.gloom.cache_dir
        projects: list[ProjectConfig] = []

        if not cache_dir.exists():
            return projects

        for project_dir in cache_dir.iterdir():
            if not project_dir.is_dir():
                continue

            adc_file = project_dir / "adc.json"
            if not adc_file.exists():
                continue

            try:
                adc_info = self.validate_adc_file(adc_file)
                projects.append(
                    ProjectConfig(
                        name=project_dir.name,
                        project_id=adc_info.project_id or adc_info.quota_project_id,
                        account=adc_info.account,
                        adc_path=adc_file,
                    )
                )
            except ADCError:
                # Skip invalid cached ADCs
                continue

        return projects

    def remove_cached_project(self, project_name: str) -> bool:
        """Remove a cached project.

        Args:
            project_name: Name of the project to remove.

        Returns:
            True if project was removed, False if it didn't exist.
        """
        cache_dir = self.config.get_project_cache_path(project_name)

        if not cache_dir.exists():
            return False

        shutil.rmtree(cache_dir)
        return True

    def _backup_file(self, path: Path) -> None:
        """Create a backup of a file before replacing.

        Args:
            path: Path to backup.
        """
        if not path.exists() or path.is_symlink():
            return

        backup_path = path.with_suffix(f"{path.suffix}.gloom_backup")
        shutil.copy2(path, backup_path)
