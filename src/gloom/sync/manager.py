"""Sync manager for Gloom."""

import json
from pathlib import Path

from gloom.core.adc import ADCManager
from gloom.core.config import GloomConfig
from gloom.sync.backends.gcs import GCSBackend
from gloom.sync.crypto import CryptoManager


class SyncManager:
    """Manages synchronization of contexts."""

    def __init__(self, config: GloomConfig) -> None:
        self.config = config
        self.adc_mgr = ADCManager(config)

        # Initialize Crypto
        self.crypto = CryptoManager(config.sync.encryption_key)

        # Initialize Backend
        if config.sync.backend == "gcs":
            if not config.sync.bucket:
                raise ValueError("GCS bucket name not configured in sync.bucket")
            self.backend = GCSBackend(config.sync.bucket, config.sync.prefix)
        else:
            raise ValueError(f"Unsupported sync backend: {config.sync.backend}")

    def push(self, name: str) -> None:
        """Push a cached context to the backend."""
        # 1. Get local context info
        project = self.adc_mgr.get_project_config(name)
        if not project:
            raise ValueError(f"Context '{name}' not found locally.")

        if not project.adc_path or not project.adc_path.exists():
            raise ValueError(f"ADC file for '{name}' missing.")

        # 2. Read ADC data
        adc_data = project.adc_path.read_text(encoding="utf-8")

        # 3. Create a bundle (ADC content + metadata)
        bundle = {
            "metadata": {
                "name": project.name,
                "project_id": project.project_id,
                "account": project.account,
            },
            "adc_content": adc_data,
        }
        bundle_bytes = json.dumps(bundle).encode("utf-8")

        # 4. Encrypt (temporary memory buffer)
        # Note: In a real implementation, we should use explicit
        # encrypt_bytes/decrypt_bytes methods in CryptoManager.
        # For now, we assume _fernet is available or direct usage.

        if self.crypto._fernet:
            encrypted_data = self.crypto._fernet.encrypt(bundle_bytes)
        else:
            # If no encryption key, we upload plain (WARN user? Config says optional key)
            # But plan said "Encryption Layer". If key is None, maybe we shouldn't push?
            # Config has encryption_key as optional. If None, we push plain.
            encrypted_data = bundle_bytes

        # 5. Upload
        self.backend.push_data(name, encrypted_data)

    def pull(self, name: str, force: bool = False) -> None:
        """Pull a context from backend and restore locally."""
        # 1. Download
        encrypted_data = self.backend.pull_data(name)

        # 2. Decrypt
        if self.crypto._fernet:
            try:
                bundle_bytes = self.crypto._fernet.decrypt(encrypted_data)
            except Exception as e:
                # Fallback: maybe it's not encrypted?
                # Or wrong key?
                raise ValueError("Failed to decrypt data. Wrong key?") from e
        else:
            bundle_bytes = encrypted_data

        # 3. Parse Bundle
        bundle = json.loads(bundle_bytes)
        metadata = bundle["metadata"]
        adc_content = bundle["adc_content"]

        project_name = metadata["name"]

        # 4. Restore using ADCManager logic (cache_adc but from content)
        # We need a way to inject content directly into ADCManager.cache_adc?
        # ADCManager.cache_adc takes a source_path.
        # So we write to a temp file first.

        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
            tmp.write(adc_content)
            tmp_path = Path(tmp.name)

        try:
            self.adc_mgr.cache_adc(project_name, source_path=tmp_path, force=force)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def list_contexts(self) -> list[str]:
        """List contexts available in remote storage."""
        return self.backend.list_contexts()
