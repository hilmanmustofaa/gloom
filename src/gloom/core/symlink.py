"""Symlink management utilities for atomic ADC switching."""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


class SymlinkStatus(Enum):
    """Status of a symlink target."""

    VALID = "valid"  # Symlink exists and points to valid target
    BROKEN = "broken"  # Symlink exists but target is missing
    NOT_SYMLINK = "not_symlink"  # Path exists but is not a symlink
    NOT_EXISTS = "not_exists"  # Path does not exist


@dataclass(frozen=True)
class SymlinkInfo:
    """Information about a symlink."""

    path: Path
    status: SymlinkStatus
    target: Path | None = None

    @property
    def is_valid(self) -> bool:
        """Check if symlink is valid and points to existing target."""
        return self.status == SymlinkStatus.VALID


class SymlinkError(Exception):
    """Base exception for symlink operations."""

    pass


class SymlinkManager:
    """Cross-platform symlink management with atomic operations.

    This class handles symlink creation, removal, and verification with
    emphasis on atomic operations to prevent partial states during ADC switching.
    """

    def __init__(self, backup_callback: Callable[[Path], None] | None = None) -> None:
        """Initialize SymlinkManager.

        Args:
            backup_callback: Optional callback to backup file before replacing.
        """
        self._backup_callback = backup_callback

    def get_info(self, path: Path) -> SymlinkInfo:
        """Get detailed information about a path's symlink status.

        Args:
            path: Path to check.

        Returns:
            SymlinkInfo with status and target if applicable.
        """
        if not path.exists() and not path.is_symlink():
            return SymlinkInfo(path=path, status=SymlinkStatus.NOT_EXISTS)

        if not path.is_symlink():
            return SymlinkInfo(path=path, status=SymlinkStatus.NOT_SYMLINK)

        target = Path(os.readlink(path))

        # Resolve relative symlinks and normalize path (handles macOS /var -> /private/var)
        if not target.is_absolute():
            target = path.parent / target
        # Use realpath to resolve all symlinks in the path (macOS compatibility)
        target = Path(os.path.realpath(target))

        if target.exists():
            return SymlinkInfo(path=path, status=SymlinkStatus.VALID, target=target)
        else:
            return SymlinkInfo(path=path, status=SymlinkStatus.BROKEN, target=target)

    def create_symlink(
        self,
        source: Path,
        target: Path,
        *,
        force: bool = False,
        backup: bool = True,
    ) -> SymlinkInfo:
        """Create a symlink atomically.

        Uses a temporary symlink + rename strategy for atomic creation.

        Args:
            source: The source file that the symlink will point to.
            target: The path where the symlink will be created.
            force: If True, replace existing file/symlink at target.
            backup: If True and force=True, backup existing file before replacing.

        Returns:
            SymlinkInfo for the created symlink.

        Raises:
            SymlinkError: If source doesn't exist or target exists without force.
            FileNotFoundError: If source file doesn't exist.
            FileExistsError: If target exists and force is False.
        """
        # Validate source exists
        if not source.exists():
            raise FileNotFoundError(f"Source file does not exist: {source}")

        # Handle existing target
        if target.exists() or target.is_symlink():
            if not force:
                raise FileExistsError(f"Target already exists: {target}")

            if backup and self._backup_callback and not target.is_symlink():
                self._backup_callback(target)

            self._remove_path(target)

        # Ensure parent directory exists
        target.parent.mkdir(parents=True, exist_ok=True)

        # Create symlink atomically using temp file + rename
        self._atomic_symlink(source, target)

        return self.get_info(target)

    def remove_symlink(self, path: Path, *, must_exist: bool = True) -> bool:
        """Remove a symlink.

        Args:
            path: Path to the symlink to remove.
            must_exist: If True, raise error if symlink doesn't exist.

        Returns:
            True if symlink was removed, False if it didn't exist.

        Raises:
            SymlinkError: If path is not a symlink or doesn't exist (when must_exist=True).
        """
        if not path.is_symlink():
            if path.exists():
                raise SymlinkError(f"Path is not a symlink: {path}")
            if must_exist:
                raise SymlinkError(f"Symlink does not exist: {path}")
            return False

        path.unlink()
        return True

    def switch_symlink(self, new_source: Path, target: Path) -> SymlinkInfo:
        """Switch a symlink to point to a new source atomically.

        This is the core operation for ADC context switching.

        Args:
            new_source: The new source file for the symlink.
            target: The symlink path to update.

        Returns:
            SymlinkInfo for the updated symlink.

        Raises:
            FileNotFoundError: If new_source doesn't exist.
        """
        if not new_source.exists():
            raise FileNotFoundError(f"New source file does not exist: {new_source}")

        # Atomic switch using temp symlink + rename
        self._atomic_symlink(new_source, target)

        return self.get_info(target)

    def verify_symlink(self, path: Path, expected_target: Path | None = None) -> bool:
        """Verify a symlink exists and optionally points to expected target.

        Args:
            path: Path to verify.
            expected_target: If provided, verify symlink points to this target.

        Returns:
            True if symlink is valid (and points to expected target if specified).
        """
        info = self.get_info(path)

        if not info.is_valid:
            return False

        if expected_target is not None:
            # Use realpath for comparison to handle macOS /var -> /private/var
            return info.target == Path(os.path.realpath(expected_target))

        return True

    def _atomic_symlink(self, source: Path, target: Path) -> None:
        """Create/replace symlink atomically using temp file + rename.

        Args:
            source: Source file to link to.
            target: Target path for the symlink.
        """
        # Create temp symlink in same directory (for atomic rename)
        temp_dir = target.parent
        temp_fd, temp_path_str = tempfile.mkstemp(dir=temp_dir, prefix=".gloom_symlink_")
        os.close(temp_fd)
        temp_path = Path(temp_path_str)

        try:
            # Remove temp file and create symlink
            temp_path.unlink()
            temp_path.symlink_to(source.resolve())

            # Atomic rename
            shutil.move(str(temp_path), str(target))
        except Exception:
            # Clean up on failure
            if temp_path.exists() or temp_path.is_symlink():
                temp_path.unlink(missing_ok=True)
            raise

    def _remove_path(self, path: Path) -> None:
        """Remove a path (file, symlink, or directory).

        Args:
            path: Path to remove.
        """
        if path.is_symlink():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
