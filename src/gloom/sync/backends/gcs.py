"""Google Cloud Storage backend for Gloom sync."""

from typing import cast

from google.cloud import storage  # type: ignore
from google.cloud.exceptions import NotFound  # type: ignore

from gloom.sync.backends.base import SyncBackend


class GCSBackend(SyncBackend):
    """Sync backend using Google Cloud Storage."""

    def __init__(self, bucket_name: str, prefix: str = "gloom/cache") -> None:
        self.bucket_name = bucket_name
        self.prefix = prefix
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

    def _get_blob_name(self, name: str) -> str:
        """Get full blob path for a context name."""
        return f"{self.prefix}/{name}.enc"

    def push_data(self, name: str, data: bytes) -> None:
        """Upload encrypted data to GCS."""
        blob_name = self._get_blob_name(name)
        blob = self.bucket.blob(blob_name)
        blob.upload_from_string(data, content_type="application/octet-stream")

    def pull_data(self, name: str) -> bytes:
        """Download data from GCS."""
        blob_name = self._get_blob_name(name)
        blob = self.bucket.blob(blob_name)
        try:
            return cast(bytes, blob.download_as_bytes())
        except NotFound as e:
            raise FileNotFoundError(f"Context '{name}' not found in bucket") from e

    def list_contexts(self) -> list[str]:
        """List contexts available in the bucket."""
        blobs = self.client.list_blobs(self.bucket_name, prefix=self.prefix)
        contexts = []
        for blob in blobs:
            if blob.name.endswith(".enc"):
                # Extract name from path: prefix/name.enc
                # Remove prefix and .enc suffix
                rel_path = blob.name[len(self.prefix) : -4]
                if rel_path.startswith("/"):
                    rel_path = rel_path[1:]
                contexts.append(rel_path)
        return contexts

    def exists(self, name: str) -> bool:
        """Check if blob exists."""
        blob_name = self._get_blob_name(name)
        blob = self.bucket.blob(blob_name)
        return cast(bool, blob.exists())
