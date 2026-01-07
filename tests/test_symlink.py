"""Tests for symlink operations."""

from __future__ import annotations

import os
from pathlib import Path

import pytest  # type: ignore

from gloom.core.symlink import SymlinkManager, SymlinkStatus


class TestSymlinkManager:
    """Tests for SymlinkManager class."""

    def test_get_info_not_exists(self, temp_dir: Path) -> None:
        """Test get_info for non-existent path."""
        mgr = SymlinkManager()
        info = mgr.get_info(temp_dir / "nonexistent")

        assert info.status == SymlinkStatus.NOT_EXISTS
        assert info.target is None

    def test_get_info_regular_file(self, temp_dir: Path) -> None:
        """Test get_info for regular file."""
        file_path = temp_dir / "regular.txt"
        file_path.write_text("content")

        mgr = SymlinkManager()
        info = mgr.get_info(file_path)

        assert info.status == SymlinkStatus.NOT_SYMLINK
        assert info.target is None

    def test_get_info_valid_symlink(self, temp_dir: Path) -> None:
        """Test get_info for valid symlink."""
        source = temp_dir / "source.txt"
        source.write_text("content")

        link = temp_dir / "link.txt"
        link.symlink_to(source)

        mgr = SymlinkManager()
        info = mgr.get_info(link)

        assert info.status == SymlinkStatus.VALID
        # Use realpath for comparison (handles macOS /var -> /private/var)
        assert info.target == Path(os.path.realpath(source))
        assert info.is_valid is True

    def test_get_info_broken_symlink(self, temp_dir: Path) -> None:
        """Test get_info for broken symlink."""
        source = temp_dir / "source.txt"
        source.write_text("content")

        link = temp_dir / "link.txt"
        link.symlink_to(source)

        # Remove source to break symlink
        source.unlink()

        mgr = SymlinkManager()
        info = mgr.get_info(link)

        assert info.status == SymlinkStatus.BROKEN
        assert info.is_valid is False

    def test_create_symlink(self, temp_dir: Path) -> None:
        """Test creating a new symlink."""
        source = temp_dir / "source.txt"
        source.write_text("content")

        target = temp_dir / "link.txt"

        mgr = SymlinkManager()
        info = mgr.create_symlink(source, target)

        assert info.status == SymlinkStatus.VALID
        assert info.target == Path(os.path.realpath(source))
        assert target.is_symlink()

    def test_create_symlink_force_replace(self, temp_dir: Path) -> None:
        """Test force-replacing existing file with symlink."""
        source = temp_dir / "source.txt"
        source.write_text("source content")

        target = temp_dir / "target.txt"
        target.write_text("original content")

        mgr = SymlinkManager()
        info = mgr.create_symlink(source, target, force=True)

        assert info.status == SymlinkStatus.VALID
        assert target.is_symlink()
        assert target.read_text() == "source content"

    def test_create_symlink_source_not_found(self, temp_dir: Path) -> None:
        """Test creating symlink with non-existent source."""
        mgr = SymlinkManager()

        with pytest.raises(FileNotFoundError):
            mgr.create_symlink(
                temp_dir / "nonexistent",
                temp_dir / "link.txt",
            )

    def test_create_symlink_target_exists_no_force(self, temp_dir: Path) -> None:
        """Test creating symlink when target exists without force."""
        source = temp_dir / "source.txt"
        source.write_text("content")

        target = temp_dir / "target.txt"
        target.write_text("existing")

        mgr = SymlinkManager()

        with pytest.raises(FileExistsError):
            mgr.create_symlink(source, target, force=False)

    def test_switch_symlink_atomic(self, temp_dir: Path) -> None:
        """Test atomic symlink switching."""
        source1 = temp_dir / "source1.txt"
        source1.write_text("content 1")

        source2 = temp_dir / "source2.txt"
        source2.write_text("content 2")

        target = temp_dir / "link.txt"

        mgr = SymlinkManager()

        # Create initial symlink
        mgr.create_symlink(source1, target)
        assert target.read_text() == "content 1"

        # Switch to source2
        info = mgr.switch_symlink(source2, target)

        assert info.status == SymlinkStatus.VALID
        assert info.target == Path(os.path.realpath(source2))
        assert target.read_text() == "content 2"

    def test_remove_symlink(self, temp_dir: Path) -> None:
        """Test removing a symlink."""
        source = temp_dir / "source.txt"
        source.write_text("content")

        link = temp_dir / "link.txt"
        link.symlink_to(source)

        mgr = SymlinkManager()
        result = mgr.remove_symlink(link)

        assert result is True
        assert not link.exists()
        assert source.exists()  # Source should remain

    def test_verify_symlink(self, temp_dir: Path) -> None:
        """Test symlink verification."""
        source = temp_dir / "source.txt"
        source.write_text("content")

        link = temp_dir / "link.txt"
        link.symlink_to(source)

        mgr = SymlinkManager()

        # Verify without expected target
        assert mgr.verify_symlink(link) is True

        # Verify with correct expected target
        assert mgr.verify_symlink(link, expected_target=source) is True

        # Verify with wrong expected target
        other = temp_dir / "other.txt"
        other.write_text("other")
        assert mgr.verify_symlink(link, expected_target=other) is False
