"""Pytest configuration and fixtures for Gloom tests."""

from __future__ import annotations

import json
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest  # type: ignore

if TYPE_CHECKING:
    pass


@pytest.fixture  # type: ignore
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture  # type: ignore
def mock_home(temp_dir: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Mock home directory for isolated testing."""
    monkeypatch.setenv("HOME", str(temp_dir))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(temp_dir / ".config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(temp_dir / ".local" / "share"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(temp_dir / ".cache"))
    return temp_dir


@pytest.fixture  # type: ignore
def mock_gcloud_dir(mock_home: Path) -> Path:
    """Create mock gcloud configuration directory."""
    gcloud_dir = mock_home / ".config" / "gcloud"
    gcloud_dir.mkdir(parents=True, exist_ok=True)
    return gcloud_dir


@pytest.fixture  # type: ignore
def mock_gloom_dir(mock_home: Path) -> Path:
    """Create mock gloom directory."""
    gloom_dir = mock_home / ".gloom"
    gloom_dir.mkdir(parents=True, exist_ok=True)
    (gloom_dir / "cache").mkdir(exist_ok=True)
    return gloom_dir


@pytest.fixture  # type: ignore
def sample_adc_data() -> dict[str, Any]:
    """Sample ADC JSON data for testing."""
    return {
        "type": "authorized_user",
        "client_id": "test-client-id.apps.googleusercontent.com",
        "client_secret": "test-client-secret",
        "refresh_token": "test-refresh-token",
        "account": "test@example.com",
        "quota_project_id": "test-project-123",
    }


@pytest.fixture  # type: ignore
def sample_adc_file(mock_gcloud_dir: Path, sample_adc_data: dict[str, Any]) -> Path:
    """Create a sample ADC file."""
    adc_file = mock_gcloud_dir / "application_default_credentials.json"
    adc_file.write_text(json.dumps(sample_adc_data), encoding="utf-8")
    return adc_file


@pytest.fixture  # type: ignore
def sample_service_account_data() -> dict[str, Any]:
    """Sample service account ADC data for testing."""
    return {
        "type": "service_account",
        "project_id": "test-project-456",
        "private_key_id": "key-id-123",
        "private_key": "-----BEGIN RSA " + "PRIVATE KEY-----\n"
        "test\n-----END RSA PRIVATE KEY-----\n",
        "client_email": "test-sa@test-project-456.iam.gserviceaccount.com",
        "client_id": "123456789",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
