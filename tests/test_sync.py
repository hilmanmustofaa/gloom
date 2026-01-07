"""Tests for sync mechanisms."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest  # type: ignore

from gloom.core.config import GloomConfig
from gloom.sync.backends.base import SyncBackend
from gloom.sync.crypto import CryptoManager
from gloom.sync.manager import SyncManager


class MockBackend(SyncBackend):
    """Mock backend for testing."""

    def __init__(self) -> None:
        self.storage: dict[str, bytes] = {}

    def push_data(self, name: str, data: bytes) -> None:
        self.storage[name] = data

    def pull_data(self, name: str) -> bytes:
        if name not in self.storage:
            raise FileNotFoundError(f"Context '{name}' not found")
        return self.storage[name]

    def list_contexts(self) -> list[str]:
        return list(self.storage.keys())

    def exists(self, name: str) -> bool:
        return name in self.storage


@pytest.fixture  # type: ignore
def mock_crypto_key() -> str:
    # A valid fernet key
    return "Xj-95X4L9r2q1J1w8v03aA=="  # Incorrect length for Fernet? Needs 32 url-safe base64
    # Fernet.generate_key().decode()
    from cryptography.fernet import Fernet

    return Fernet.generate_key().decode()


class TestCryptoManager:
    def test_derive_key(self) -> None:
        """Test key derivation."""
        # Test with password
        cm = CryptoManager("password")
        assert cm._fernet is not None

        # Test with direct key
        from cryptography.fernet import Fernet

        key = Fernet.generate_key().decode()
        cm2 = CryptoManager(key)
        assert cm2._fernet is not None

    def test_encrypt_decrypt(self, tmp_path: Path) -> None:
        """Test encryption cycle."""
        cm = CryptoManager("password")

        data = b"secret data"
        file_path = tmp_path / "secret.txt"
        file_path.write_bytes(data)

        # Encrypt file
        encrypted = cm.encrypt_file(file_path)
        assert encrypted != data

        # Decrypt data
        decrypted = cm.decrypt_data(encrypted)
        assert decrypted == data


class TestSyncManager:
    @pytest.fixture  # type: ignore
    def mock_backend(self) -> MockBackend:
        return MockBackend()

    @pytest.fixture  # type: ignore
    def mock_config(self, tmp_path: Path, mock_crypto_key: str) -> GloomConfig:
        conf = GloomConfig()
        # Setup paths
        object.__setattr__(conf.gloom, "base_dir", tmp_path / ".gloom")
        object.__setattr__(conf.gloom, "cache_dir", tmp_path / ".gloom" / "cache")
        conf.gloom.ensure_dirs()
        # Setup sync
        object.__setattr__(conf.sync, "encryption_key", mock_crypto_key)
        object.__setattr__(conf.sync, "bucket", "test-bucket")
        return conf

    def test_push_pull(
        self, mock_config: GloomConfig, mock_backend: MockBackend, tmp_path: Path
    ) -> None:
        """Test full push and pull cycle."""
        # 1. Setup local context
        project_name = "test-project"
        adc_content = {"type": "service_account", "project_id": "foo"}

        cache_dir = mock_config.gloom.cache_dir / project_name
        cache_dir.mkdir()
        adc_path = cache_dir / "adc.json"
        adc_path.write_text(json.dumps(adc_content), encoding="utf-8")

        # Inject project into config if needed, but ADCManager reads from disk
        # Wait, SyncManager.push calls adc_mgr.get_project_config(name)
        # get_project_config uses list_cached_projects which scans disk.
        # But list_cached_projects validates ADC file.
        # So we need a valid ADC file structure for validation to pass?
        # CredentialValidator checks "type". "service_account" needs more fields.
        # Let's use minimum valid fields.

        valid_adc = {
            "type": "service_account",
            "project_id": "foo",
            "private_key_id": "1",
            "private_key": (
                "-----BEGIN " + "PRIVATE KEY-----\n" + "KEY" + "\n-----END " + "PRIVATE KEY-----\n"
            ),
            "client_email": "sa@foo",
            "client_id": "1",
            "auth_uri": "u",
            "token_uri": "u",
        }
        adc_path.write_text(json.dumps(valid_adc), encoding="utf-8")

        # Mock SyncManager with our MockBackend
        with patch("gloom.sync.manager.GCSBackend", return_value=mock_backend):
            manager = SyncManager(mock_config)
            # Force replace backend just in case init logic differs
            # Use type ignore because we are substituting GCSBackend with MockBackend
            manager.backend = mock_backend  # type: ignore

            # PUSH
            manager.push(project_name)

            assert mock_backend.exists(project_name)

            # REMOVE LOCAL
            import shutil

            shutil.rmtree(cache_dir)
            assert not cache_dir.exists()

            # PULL
            manager.pull(project_name)

            assert cache_dir.exists()
            assert adc_path.exists()
            restored_data = json.loads(adc_path.read_text(encoding="utf-8"))
            assert restored_data["project_id"] == "foo"
