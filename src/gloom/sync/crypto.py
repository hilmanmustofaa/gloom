"""Encryption utilities for Gloom sync."""

import base64
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class CryptoManager:
    """Manages encryption and decryption of files."""

    def __init__(self, key: str | None = None) -> None:
        """Initialize with an optional key/password.

        If no key is provided, encryption checks will fail.
        The input key can be a password which will be derived into a Fernet key,
        or a pre-generated Fernet key.
        """
        self._fernet: Fernet | None = None
        if key:
            self._fernet = Fernet(self._derive_key(key))

    def _derive_key(self, input_key: str) -> bytes:
        """Derive a URL-safe base64-encoded 32-byte key."""
        # If it's already a valid Fernet key, return it
        try:
            input_bytes = input_key.encode()
            Fernet(input_bytes)
            return input_bytes
        except Exception:
            # Otherwise derive from password (salt should ideally be stored,
            # but for simplicity of sharing we might use a static salt or expect a full key).
            # For now, let's assume the user provides a raw Fernet key or we use a static salt
            # to allow deterministic derivation across machines (if they share the password).

            # Using a static salt for deterministic derivation from a passphrase.
            # In production, salt should be random and stored, but this requires
            # syncing the config/salt too.
            salt = b"gloom-sync-salt"
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            return base64.urlsafe_b64encode(kdf.derive(input_key.encode()))

    def encrypt_file(self, path: Path) -> bytes:
        """Read file and return encrypted bytes."""
        if not self._fernet:
            raise ValueError("Encryption key not configured.")

        data = path.read_bytes()
        return self._fernet.encrypt(data)

    def decrypt_data(self, data: bytes) -> bytes:
        """Decrypt data."""
        if not self._fernet:
            raise ValueError("Encryption key not configured.")

        return self._fernet.decrypt(data)
