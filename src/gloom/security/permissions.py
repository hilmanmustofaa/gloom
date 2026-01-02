"""Permission enforcement for Gloom directories and files."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path

from gloom.utils.logger import console


@dataclass
class PermissionIssue:
    """Represents a permission issue."""

    path: Path
    current_mode: int
    expected_mode: int
    is_dir: bool

    @property
    def description(self) -> str:
        """Get human readable description."""
        type_str = "Directory" if self.is_dir else "File"
        return (
            f"{type_str} has insecure permissions: {oct(self.current_mode)[-3:]} "
            f"(expected {oct(self.expected_mode)[-3:]})"
        )


class PermissionEnforcer:
    """Enforces strict permissions on Gloom files and directories."""

    # Expected permissions
    DIR_MODE = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR  # 0700
    FILE_MODE = stat.S_IRUSR | stat.S_IWUSR  # 0600

    def __init__(self, base_dir: Path) -> None:
        """Initialize permission enforcer.

        Args:
            base_dir: Base directory to enforce permissions on (e.g. ~/.gloom).
        """
        self.base_dir = base_dir

    def check(self) -> list[PermissionIssue]:
        """Check permissions of all Gloom files.

        Returns:
            List of found permission issues.
        """
        issues: list[PermissionIssue] = []

        if not self.base_dir.exists():
            return issues

        # Check base directory
        self._check_path(self.base_dir, self.DIR_MODE, issues)

        # Check all files recursively
        for path in self.base_dir.rglob("*"):
            expected = self.DIR_MODE if path.is_dir() else self.FILE_MODE
            self._check_path(path, expected, issues)

        return issues

    def fix(self, issues: list[PermissionIssue] | None = None) -> int:
        """Fix permission issues.

        Args:
            issues: Optional list of issues to fix. If None, runs check() first.

        Returns:
            Number of fixes applied.
        """
        if issues is None:
            issues = self.check()

        fixed_count = 0
        for issue in issues:
            try:
                os.chmod(issue.path, issue.expected_mode)
                fixed_count += 1
                console.print(f"[green]Fixed permissions for {issue.path.name}[/green]")
            except Exception as e:
                console.print(f"[red]Failed to fix permissions for {issue.path.name}: {e}[/red]")

        return fixed_count

    def _check_path(self, path: Path, expected_mode: int, issues: list[PermissionIssue]) -> None:
        """Check permissions for a single path."""
        try:
            stat_result = path.stat()
            # specific to unix-like systems, strictly match rwx/rw
            # We want to ensure NO group/other permissions
            current_mode = stat.S_IMODE(stat_result.st_mode)

            # We accept it if it's EXACTLY expected_mode
            if current_mode != expected_mode:
                issues.append(
                    PermissionIssue(
                        path=path,
                        current_mode=current_mode,
                        expected_mode=expected_mode,
                        is_dir=path.is_dir(),
                    )
                )
        except FileNotFoundError:
            pass  # Path might have been deleted during check
